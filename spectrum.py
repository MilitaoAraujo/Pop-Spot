# Visualizador de espectro em tempo real via PulseAudio/PipeWire (parec + FFT)
# Real-time audio spectrum visualizer via PulseAudio/PipeWire (parec + FFT)
# Windows: usa sounddevice + WASAPI loopback em vez de parec

import subprocess
import threading
import logging
import sys

log = logging.getLogger("widget.spectrum")

N_BARS = 16
RATE   = 22050  # 22 kHz is enough for a music spectrum
CHUNK  = 1024
DECAY  = 0.55   # suavização das barras / bar smoothing (0 = instant, 1 = no response)


class AudioSpectrum:
    def __init__(self):
        self._bars    = [0.0] * N_BARS
        self._lock    = threading.Lock()
        self._proc    = None   # usado apenas no backend Linux (parec)
        self._running = False
        self._start_lock = threading.Lock()

    def start(self):
        with self._start_lock:
            if self._running:
                return
            self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        proc = self._proc
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            except Exception:
                pass

    def get_bars(self) -> list:
        with self._lock:
            return list(self._bars)

    def _loop(self):
        try:
            import numpy as np
        except ImportError:
            log.warning("numpy não encontrado — espectro desativado")
            self._running = False
            return

        if sys.platform == "win32":
            self._loop_windows(np)
        else:
            self._loop_linux(np)

    # ── Backend Linux: parec (PulseAudio / PipeWire) ──────────────────────

    def _loop_linux(self, np):
        try:
            self._proc = subprocess.Popen(
                [
                    "parec",
                    f"--rate={RATE}",
                    "--channels=1",
                    "--format=s16le",
                    "--latency-msec=80",
                    "-d", "@DEFAULT_MONITOR@",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            log.warning("parec não encontrado — espectro desativado")
            self._running = False
            return

        chunk_bytes = CHUNK * 2
        while self._running:
            raw = self._proc.stdout.read(chunk_bytes)
            if len(raw) < chunk_bytes:
                break
            self._process(raw, np)

        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        except Exception:
            pass
        self._running = False

    # ── Backend Windows: sounddevice + WASAPI loopback ────────────────────

    def _loop_windows(self, np):
        try:
            import sounddevice as sd
        except ImportError:
            log.warning("sounddevice não encontrado — espectro desativado. Execute: pip install sounddevice")
            self._running = False
            return

        try:
            wasapi = sd.WasapiSettings(loopback=True)
        except AttributeError:
            log.warning("sounddevice sem suporte WASAPI — espectro desativado")
            self._running = False
            return

        # Encontra o dispositivo de saída padrão
        out_idx = sd.default.device[1]
        if out_idx < 0:
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_output_channels"] > 0:
                    out_idx = i
                    break
        if out_idx < 0:
            log.warning("Nenhum dispositivo de saída encontrado — espectro desativado")
            self._running = False
            return

        # Usa a taxa nativa do dispositivo; tenta fallbacks se falhar
        dev_info   = sd.query_devices(out_idx)
        taxa_nativa = int(dev_info.get("default_samplerate", 48000))
        log.debug("Espectro: dispositivo %d (%s), taxa nativa %d Hz",
                  out_idx, dev_info.get("name", "?"), taxa_nativa)

        stream = None
        for taxa in (taxa_nativa, 48000, 44100, 22050):
            for canais in (2, 1):
                try:
                    stream = sd.InputStream(
                        device=out_idx,
                        samplerate=taxa,
                        channels=canais,
                        dtype="int16",
                        extra_settings=wasapi,
                        blocksize=CHUNK,
                    )
                    log.debug("Espectro WASAPI aberto: %d Hz, %dch", taxa, canais)
                    break
                except Exception as e:
                    log.debug("WASAPI %dHz %dch: %s", taxa, canais, e)
            if stream is not None:
                break

        if stream is None:
            log.warning("WASAPI loopback não disponível em nenhuma configuração — espectro desativado")
            self._running = False
            return

        with stream:
            while self._running:
                try:
                    data, _ = stream.read(CHUNK)
                    # Converte stereo → mono se necessário
                    if data.ndim > 1:
                        data = data.mean(axis=1).astype(np.int16)
                    self._process(data.tobytes(), np)
                except Exception as e:
                    log.debug("sounddevice leitura: %s", e)
                    break

        self._running = False

    def _process(self, raw: bytes, np):
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        fft     = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
        n       = len(fft)

        new_bars = []
        for i in range(N_BARS):
            lo = int(n * (i     / N_BARS) ** 2.0)
            hi = int(n * ((i+1) / N_BARS) ** 2.0)
            lo, hi = max(lo, 0), min(hi, n - 1)
            val = float(np.mean(fft[lo:hi+1])) if hi > lo else float(fft[lo])
            new_bars.append(val)

        peak = max(new_bars) or 1.0
        new_bars = [min(v / peak, 1.0) for v in new_bars]

        with self._lock:
            for i in range(N_BARS):
                self._bars[i] = self._bars[i] * DECAY + new_bars[i] * (1 - DECAY)

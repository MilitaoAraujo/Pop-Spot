# Visualizador de espectro em tempo real via PulseAudio/PipeWire (parec + FFT)
# Real-time audio spectrum visualizer via PulseAudio/PipeWire (parec + FFT)
# Windows: usa soundcard + WASAPI loopback em vez de parec

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

    # ── Backend Windows: soundcard (WASAPI loopback automático) ──────────

    def _loop_windows(self, np):
        try:
            import soundcard as sc
        except ImportError:
            log.warning("soundcard não encontrado — espectro desativado. "
                        "Execute: pip install soundcard --break-system-packages")
            self._running = False
            return

        try:
            speaker = sc.default_speaker()
            mic     = sc.get_microphone(speaker.id, include_loopback=True)
            log.debug("Espectro soundcard: loopback de '%s'", speaker.name)
        except Exception as e:
            log.warning("soundcard loopback não disponível: %s — espectro desativado", e)
            self._running = False
            return

        try:
            with mic.recorder(samplerate=RATE, channels=1, blocksize=CHUNK) as rec:
                while self._running:
                    try:
                        data = rec.record(numframes=CHUNK)   # float32 [-1, 1]
                        pcm  = (np.clip(data.flatten(), -1.0, 1.0) * 32767).astype(np.int16)
                        self._process(pcm.tobytes(), np)
                    except Exception as e:
                        log.debug("soundcard leitura: %s", e)
                        break
        except Exception as e:
            log.warning("soundcard stream: %s", e)

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

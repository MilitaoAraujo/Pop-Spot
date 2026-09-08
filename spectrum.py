# Visualizador de espectro em tempo real
# Linux: PulseAudio/PipeWire (parec + FFT)
# Windows: WASAPI loopback (soundcard + FFT)

from __future__ import annotations

import array
import math
import subprocess
import sys
import threading
import logging

log = logging.getLogger("widget.spectrum")

N_BARS = 16
RATE   = 22050
CHUNK  = 1024
DECAY  = 0.55


class AudioSpectrum:
    def __init__(self):
        self._bars       = [0.0] * N_BARS
        self._lock       = threading.Lock()
        self._proc       = None
        self._running    = False
        self._start_lock = threading.Lock()
        self._np         = None

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
        self._proc = None
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            except Exception:
                pass
        with self._lock:
            self._bars = [0.0] * N_BARS

    def get_bars(self) -> list:
        with self._lock:
            return list(self._bars)

    def _loop(self):
        try:
            import numpy as np
            self._np = np
        except ImportError:
            self._np = None
            log.info("numpy ausente — espectro em modo Python puro")

        if sys.platform == "win32":
            self._loop_wasapi()
        else:
            self._loop_parec()

    def _loop_parec(self):
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
            self._processar(raw)

        try:
            if self._proc:
                self._proc.terminate()
                self._proc.wait(timeout=2)
        except Exception:
            pass
        self._running = False

    def _loop_wasapi(self):
        # `sounddevice`/PortAudio não expõe loopback de saída no Windows
        # (WasapiSettings não tem parâmetro `loopback`) — usa `soundcard`,
        # que fala direto com o WASAPI e sabe gravar o que está tocando.
        try:
            import soundcard as sc
        except ImportError:
            log.warning("soundcard ausente — espectro Windows desativado")
            self._running = False
            return
        try:
            saida = sc.default_speaker()
            mic = sc.get_microphone(saida.id, include_loopback=True)
        except Exception as e:
            log.warning("WASAPI loopback: %s", e)
            self._running = False
            return
        try:
            with mic.recorder(samplerate=RATE, channels=1, blocksize=CHUNK) as rec:
                while self._running:
                    amostras = rec.record(numframes=CHUNK)
                    if amostras.size:
                        self._processar_amostras(amostras[:, 0])
        except Exception as e:
            log.debug("WASAPI read: %s", e)
        finally:
            self._running = False

    def _processar_amostras(self, amostras):
        """Amostras float32 em [-1, 1] (via `soundcard`), já normalizadas."""
        if self._np is None:
            return
        self._aplicar_barras(self._fft_bars(amostras, self._np))

    def _processar(self, raw: bytes):
        if self._np is not None:
            self._process_numpy(raw, self._np)
        else:
            self._process_puro(raw)

    def _aplicar_barras(self, new_bars):
        peak = max(new_bars) or 1.0
        new_bars = [min(v / peak, 1.0) for v in new_bars]
        with self._lock:
            for i in range(N_BARS):
                self._bars[i] = self._bars[i] * DECAY + new_bars[i] * (1 - DECAY)

    def _process_numpy(self, raw: bytes, np):
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        self._aplicar_barras(self._fft_bars(samples, np))

    @staticmethod
    def _fft_bars(samples, np) -> list:
        if len(samples) < 8:
            return [0.0] * N_BARS
        fft = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
        n = len(fft)
        bars = []
        for i in range(N_BARS):
            lo = int(n * (i / N_BARS) ** 2.0)
            hi = int(n * ((i + 1) / N_BARS) ** 2.0)
            lo, hi = max(lo, 0), min(hi, n - 1)
            val = float(np.mean(fft[lo:hi + 1])) if hi > lo else float(fft[lo])
            bars.append(val)
        return bars

    def _process_puro(self, raw: bytes):
        samples = array.array("h")
        samples.frombytes(raw)
        step = max(1, len(samples) // 256)
        xs = [samples[i] / 32768.0 for i in range(0, len(samples), step)]
        n = len(xs)
        if n < 8:
            return
        half = (n - 1) / 2.0 or 1.0
        xs = [x * (1.0 - abs(i - half) / half) for i, x in enumerate(xs)]
        new_bars = []
        for i in range(N_BARS):
            k = max(1, int((n // 2 - 1) * ((i + 1) / N_BARS) ** 2.0))
            re = im = 0.0
            for idx, x in enumerate(xs):
                ang = 2.0 * math.pi * k * idx / n
                re += x * math.cos(ang)
                im -= x * math.sin(ang)
            new_bars.append(math.hypot(re, im) / n)
        self._aplicar_barras(new_bars)

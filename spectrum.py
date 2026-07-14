# Visualizador de espectro em tempo real via PulseAudio/PipeWire (parec + FFT)

import subprocess
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

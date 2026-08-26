from math import sin, cos, pi


class Biquad:
    LOPASS = "lowpass"
    HIGHPASS = "highpass"

    def __init__(self, fs_hz: float, f0_hz: float, q: float = 0.707, kind: str = "lowpass"):
        self.fs = fs_hz
        self.kind = kind
        self.q = q
        self.f0 = f0_hz

        self.b0 = self.b1 = self.b2 = 0.0
        self.a0 = self.a1 = self.a2 = 0.0

        self.x1 = self.x2 = 0.0
        self.y1 = self.y2 = 0.0
        self._recompute()

    def _recompute(self):
        # защитим Q и частоты
        q = max(1e-6, float(self.q))
        f0 = min(max(self.f0, 1e-6), self.fs * 0.45)
        w0 = 2.0 * pi * f0 / self.fs
        cw = cos(w0)
        sw = sin(w0)
        alpha = sw / (2.0 * q)

        if self.kind == self.LOPASS:
            b0 = (1.0 - cw) * 0.5
            b1 = 1.0 - cw
            b2 = (1.0 - cw) * 0.5
            a0 = 1.0 + alpha
            a1 = -2.0 * cw
            a2 = 1.0 - alpha
        elif self.kind == self.HIGHPASS:
            b0 = (1.0 + cw) * 0.5
            b1 = -(1.0 + cw)
            b2 = (1.0 + cw) * 0.5
            a0 = 1.0 + alpha
            a1 = -2.0 * cw
            a2 = 1.0 - alpha
        else:
            raise ValueError("kind must be 'lowpass' or 'highpass'")

        # нормализация
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0

    def reset(self, x0: float = 0.0):
        self.x1 = self.x2 = x0
        self.y1 = self.y2 = x0

    def set_cutoff(self, f0_hz: float):
        self.f0 = f0_hz
        self._recompute()

    def set_q(self, q: float):
        self.q = q
        self._recompute()

    def update(self, x: float) -> float:
        # Direct Form I
        y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 \
            - self.a1 * self.y1 - self.a2 * self.y2
        self.x2 = self.x1
        self.x1 = x
        self.y2 = self.y1
        self.y1 = y
        return y

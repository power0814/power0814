"""테스트용 합성 '말소리': 성문 펄스열 + 음절마다 바뀌는 포먼트 + 음절 리듬."""
import numpy as np
from scipy.signal import lfilter

VOWELS = [(730, 1090, 2440), (270, 2290, 3010), (300, 870, 2240), (530, 1840, 2480), (570, 840, 2410)]


def _formant(x, f, bw, sr):
    r = np.exp(-np.pi * bw / sr)
    th = 2 * np.pi * f / sr
    return lfilter([1 - r], [1, -2 * r * np.cos(th), r * r], x)


def speech(dur, f0, sr=44100, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    out = np.zeros(n)
    t = 0
    while t < n:
        syl = int(sr * rng.uniform(0.15, 0.3))
        m = min(syl, n - t)
        f = f0 * (1 + 0.1 * np.sin(np.linspace(0, rng.uniform(1, 3), m)))
        ph = np.cumsum(f / sr)
        src = (np.diff(np.floor(ph), prepend=0) > 0).astype(float) + 0.02 * rng.standard_normal(m)
        v = VOWELS[rng.integers(len(VOWELS))]
        y = sum(_formant(src, fm, 80 + 40 * k, sr) for k, fm in enumerate(v))
        env = np.sin(np.linspace(0, np.pi, m)) ** 0.5
        out[t:t + m] = y * env
        t += syl
    return (out / (np.abs(out).max() + 1e-9) * 0.5).astype(np.float32)


def program(sr=44100):
    """[말 A 4s][쉼 1s][말 B 4s][쉼 1s][말 A 3s + 음악][쉼 1s] 를 두 번."""
    sil = np.zeros(sr, np.float32)
    tone = 0.3 * np.sin(2 * np.pi * 440 * np.arange(3 * sr) / sr).astype(np.float32)
    parts = []
    for k in range(2):
        parts += [speech(4, 120, sr, 10 + k), sil, speech(4, 260, sr, 20 + k), sil,
                  speech(3, 120, sr, 30 + k) + tone, sil]
    return np.concatenate(parts)

"""발화 구간 찾기 (Silero VAD)."""

from __future__ import annotations

import numpy as np

SR = 16000


def merge_segments(spans: list[tuple[float, float]], max_gap: float, min_dur: float,
                   max_dur: float) -> list[tuple[float, float]]:
    """짧은 쉼으로 끊긴 발화를 max_dur 안에서 이어 붙이고, min_dur보다 짧은 건 버린다."""
    out: list[list[float]] = []
    for s, e in sorted(spans):
        if out and s - out[-1][1] <= max_gap and e - out[-1][0] <= max_dur:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out if min_dur <= e - s <= max_dur]


class SileroVAD:
    def __init__(self, threshold: float = 0.5, min_silence_ms: int = 300, pad_ms: int = 100):
        from silero_vad import load_silero_vad

        self.model = load_silero_vad()
        self.threshold = threshold
        self.min_silence_ms = min_silence_ms
        self.pad_ms = pad_ms

    def __call__(self, wav16: np.ndarray, max_dur: float) -> list[tuple[float, float]]:
        import torch
        from silero_vad import get_speech_timestamps

        ts = get_speech_timestamps(
            torch.from_numpy(np.ascontiguousarray(wav16)), self.model, sampling_rate=SR,
            threshold=self.threshold, min_speech_duration_ms=250,
            max_speech_duration_s=max_dur, min_silence_duration_ms=self.min_silence_ms,
            speech_pad_ms=self.pad_ms,
        )
        return [(t["start"] / SR, t["end"] / SR) for t in ts]

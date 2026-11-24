"""목소리/배경음 분리."""

from __future__ import annotations

import numpy as np


class Passthrough:
    """이미 깨끗한 음원(배경음 없음)일 때. 배경음은 없는 것으로 친다."""

    sr = 44100
    channels = 1

    def __call__(self, mix: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
        return mix.mean(0), None


class Demucs:
    """Demucs로 vocals 스템만 뽑고 나머지 스템의 합을 배경음으로 돌려준다."""

    channels = 2

    def __init__(self, name: str = "htdemucs", device: str = "cpu", shifts: int = 0,
                 overlap: float = 0.25, model=None):
        import torch

        if model is None:
            from demucs.pretrained import get_model

            model = get_model(name)
        self.model = model.eval()
        self.device = device
        self.shifts = shifts
        self.overlap = overlap
        self.sr = int(model.samplerate)
        self.vocals = list(model.sources).index("vocals")
        self._torch = torch

    def __call__(self, mix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        from demucs.apply import apply_model

        torch = self._torch
        wav = torch.from_numpy(mix)
        ref = wav.mean(0)
        mean, std = ref.mean(), ref.std() + 1e-8
        with torch.no_grad():
            out = apply_model(self.model, ((wav - mean) / std)[None], shifts=self.shifts,
                              split=True, overlap=self.overlap, device=self.device)[0]
        out = out * std + mean
        vocals = out[self.vocals]
        bgm = out.sum(0) - vocals
        return vocals.mean(0).cpu().numpy(), bgm.mean(0).cpu().numpy()

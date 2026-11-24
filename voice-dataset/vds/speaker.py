"""화자 임베딩 (SpeechBrain ECAPA-TDNN)과 기준 목소리."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def l2norm(x: np.ndarray) -> np.ndarray:
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-9)


class Ecapa:
    """16 kHz 모노 파형 목록 → (n, 192) 단위 벡터."""

    def __init__(self, device: str = "cpu", cache_dir: Path | None = None, batch: int = 32):
        from speechbrain.inference.speaker import EncoderClassifier

        self.model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(cache_dir or Path.home() / ".cache" / "vds" / "ecapa"),
            run_opts={"device": device},
        )
        self.batch = batch

    def __call__(self, wavs: list[np.ndarray]) -> np.ndarray:
        import torch

        out = np.zeros((len(wavs), 192), np.float32)
        order = sorted(range(len(wavs)), key=lambda i: len(wavs[i]))
        for b in range(0, len(order), self.batch):
            idx = order[b:b + self.batch]
            n = max(len(wavs[i]) for i in idx)
            x = torch.zeros(len(idx), n)
            lens = torch.zeros(len(idx))
            for j, i in enumerate(idx):
                x[j, :len(wavs[i])] = torch.from_numpy(wavs[i])
                lens[j] = len(wavs[i]) / n
            with torch.no_grad():
                e = self.model.encode_batch(x, wav_lens=lens).squeeze(1).cpu().numpy()
            out[idx] = e
        return l2norm(out)


def centroid(embs: np.ndarray) -> np.ndarray:
    return l2norm(embs.mean(0))


def save_reference(path: Path, emb: np.ndarray, n: int) -> None:
    np.savez(path, emb=emb, n=n)


def load_reference(path: Path) -> np.ndarray:
    if not path.exists():
        raise SystemExit(f"{path} 가 없습니다. 먼저 `python -m vds reference` 로 기준 목소리를 만드세요.")
    return np.load(path)["emb"]

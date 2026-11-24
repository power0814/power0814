"""구간 wav마다 faster-whisper로 받아쓰기."""

from __future__ import annotations

import json
import time
from pathlib import Path


def transcribe_all(work: Path, model_name: str, device: str, compute_type: str,
                   language: str = "ko", beam_size: int = 5, initial_prompt: str | None = None,
                   log=print, model=None) -> None:
    if model is None:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_name, device=device, compute_type=compute_type)

    metas = sorted((work / "meta").glob("*.json"))
    metas = [m for m in metas if not m.name.endswith(".text.json")]
    for mi, meta_path in enumerate(metas):
        out_path = meta_path.with_name(meta_path.stem + ".text.json")
        if out_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        vid = meta["id"]
        res = {}
        t0 = time.time()
        for seg in meta["segments"]:
            wav = work / "segments" / vid / f"{seg['name']}.wav"
            parts, _ = model.transcribe(
                str(wav), language=language, beam_size=beam_size, vad_filter=False,
                condition_on_previous_text=False, without_timestamps=True,
                initial_prompt=initial_prompt,
            )
            parts = list(parts)
            if not parts:
                res[seg["name"]] = {"text": "", "logprob": -10.0, "no_speech": 1.0, "compression": 0.0}
                continue
            total = sum(len(p.text) for p in parts) or 1
            res[seg["name"]] = {
                "text": " ".join(p.text.strip() for p in parts).strip(),
                "logprob": round(sum(p.avg_logprob * len(p.text) for p in parts) / total, 4),
                "no_speech": round(max(p.no_speech_prob for p in parts), 4),
                "compression": round(max(p.compression_ratio for p in parts), 3),
            }
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        tmp.replace(out_path)
        log(f"[{mi + 1}/{len(metas)}] {vid}: {len(res)}개 받아씀 ({time.time() - t0:.0f}s)")

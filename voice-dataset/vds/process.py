"""영상 하나 → 분리 → 발화 구간 → 품질·화자 거르기 → 구간 wav."""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from . import audio
from .vad import SR as VAD_SR
from .vad import merge_segments


@dataclass
class Params:
    chunk_sec: float = 600.0   # 긴 방송은 이 길이씩 끊어 분리한다 (메모리 때문)
    min_dur: float = 1.5
    max_dur: float = 12.0
    merge_gap: float = 0.4
    # 아래는 "일단 저장할지"의 느슨한 기준. 최종 기준은 export에서 다시 건다.
    min_rms_db: float = -45.0
    max_clip: float = 0.001
    max_bgm_db: float = -3.0
    min_sim: float = 0.25
    fade_ms: float = 10.0


def find_sources(dirs: list[Path]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in audio.AUDIO_EXTS:
                continue
            vid = re.sub(r"[^\w.-]+", "_", p.stem)
            base, k = vid, 1
            while vid in found:
                k += 1
                vid = f"{base}~{k}"
            found[vid] = p
    return found


def _fade(x: np.ndarray, n: int) -> np.ndarray:
    if n <= 0 or len(x) < 2 * n:
        return x
    x = x.copy()
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    x[:n] *= ramp
    x[-n:] *= ramp[::-1]
    return x


def process_source(vid: str, src: Path, work: Path, sep, vad, embed, ref: np.ndarray,
                   p: Params, log=print) -> dict:
    meta_dir = work / "meta"
    meta_path = meta_dir / f"{vid}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())

    seg_dir = work / "segments" / vid
    total = audio.probe_duration(src)
    sr = sep.sr
    fade = int(sr * p.fade_ms / 1000)
    kept: list[dict] = []
    embs: list[np.ndarray] = []
    rejected: Counter = Counter()
    t0 = time.time()

    starts = [float(c) for c in np.arange(0.0, total, p.chunk_sec)]
    for ci, c0 in enumerate(starts):
        mix = audio.load(src, sr, sep.channels, start=c0, duration=p.chunk_sec)
        n = mix.shape[1]
        if n < sr * p.min_dur:
            continue
        voice, bgm = sep(mix)
        voice16 = audio.resample(voice, sr, VAD_SR)
        spans = merge_segments(vad(voice16, p.max_dur), p.merge_gap, p.min_dur, p.max_dur)
        clen = n / sr
        first, last = ci == 0, ci == len(starts) - 1

        cands = []
        for s, e in spans:
            # 청크 경계에 걸친 구간은 말이 잘렸을 수 있다
            if (s < 0.05 and not first) or (e > clen - 0.05 and not last):
                rejected["chunk_edge"] += 1
                continue
            a, b = int(s * sr), int(e * sr)
            m = audio.measure(voice[a:b], None if bgm is None else bgm[a:b])
            if m["rms_db"] < p.min_rms_db:
                rejected["quiet"] += 1
            elif m["clip"] > p.max_clip:
                rejected["clipped"] += 1
            elif m["bgm_db"] > p.max_bgm_db:
                rejected["bgm"] += 1
            else:
                cands.append((s, e, a, b, m))

        if cands:
            e16 = embed([voice16[int(s * VAD_SR):int(e * VAD_SR)] for s, e, *_ in cands])
            sims = e16 @ ref
            for (s, e, a, b, m), emb, sim in zip(cands, e16, sims):
                if sim < p.min_sim:
                    rejected["speaker"] += 1
                    continue
                s_abs, e_abs = c0 + s, c0 + e
                name = f"{vid}_{int(s_abs * 1000):09d}_{int(e_abs * 1000):09d}"
                audio.write_wav(seg_dir / f"{name}.wav", _fade(voice[a:b], fade), sr)
                kept.append({"name": name, "start": round(s_abs, 3), "end": round(e_abs, 3),
                             "dur": round(e - s, 3), "sim": round(float(sim), 4), **m})
                embs.append(emb)

        done = min(c0 + p.chunk_sec, total)
        speed = done / max(time.time() - t0, 1e-6)
        log(f"  [{vid}] {done / 60:6.1f}/{total / 60:.1f}분  남긴 구간 {len(kept)}  ({speed:.1f}x 실시간)")

    meta = {
        "id": vid, "source": str(src), "duration": round(total, 2), "sr": sr,
        "params": asdict(p), "rejected": dict(rejected), "segments": kept,
    }
    meta_dir.mkdir(parents=True, exist_ok=True)
    np.save(meta_dir / f"{vid}.npy", np.array(embs, np.float32).reshape(-1, len(ref)))
    tmp = meta_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    tmp.replace(meta_path)  # json이 있으면 이 영상은 끝난 것
    return meta

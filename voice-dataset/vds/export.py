"""남긴 구간에 최종 기준을 걸어 학습용 데이터셋으로 내보낸다."""

from __future__ import annotations

import json
import random
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import audio
from .speaker import centroid

# Whisper가 한국어 무음·잡음에서 자주 지어내는 문장
HALLUCINATIONS = [
    "시청해 주셔서 감사합니다", "시청해주셔서 감사합니다", "구독과 좋아요", "구독 좋아요",
    "좋아요와 구독", "자막 제공", "자막 제작", "한글자막", "MBC 뉴스", "KBS 뉴스",
    "SBS 뉴스", "다음 영상에서 만나요", "끝까지 시청",
]
_LAUGH = re.compile(r"[ㅋㅎㅠㅜ하흐크킥헤호히푸\s.,!?~…\-]+")
_CHARS = re.compile(r"[가-힣A-Za-z0-9]")


@dataclass
class Rules:
    min_sim: float = 0.55
    max_bgm_db: float = -15.0
    min_rms_db: float = -40.0
    min_logprob: float = -0.8
    max_no_speech: float = 0.6
    max_compression: float = 2.4
    min_cps: float = 1.5      # 초당 글자 수 (공백·문장부호 제외)
    max_cps: float = 12.0
    max_same_text: int = 20   # 같은 문장은 이만큼까지만
    refine: bool = True
    refine_sim: float = 0.65
    refine_bgm_db: float = -20.0


def _norm_text(t: str) -> str:
    return re.sub(r"\s+", "", t)


def judge(seg: dict, tr: dict | None, sim: float, r: Rules) -> str | None:
    """버릴 이유를 돌려준다. 남기면 None."""
    if tr is None:
        return "not_transcribed"
    text = tr["text"]
    if sim < r.min_sim:
        return "speaker"
    if seg["bgm_db"] > r.max_bgm_db:
        return "bgm"
    if seg["rms_db"] < r.min_rms_db:
        return "quiet"
    if not text or _LAUGH.fullmatch(text):
        return "laugh_only"
    n = len(_CHARS.findall(text))
    if n < 2:
        return "too_short_text"
    if any(h.replace(" ", "") in _norm_text(text) for h in HALLUCINATIONS):
        return "hallucination"
    if tr["no_speech"] > r.max_no_speech:
        return "no_speech"
    if tr["logprob"] < r.min_logprob:
        return "low_confidence"
    if tr["compression"] > r.max_compression:
        return "repetitive"
    cps = n / seg["dur"]
    if not r.min_cps <= cps <= r.max_cps:
        return "speech_rate"
    return None


def load_all(work: Path):
    rows = []  # (vid, seg, transcript|None)
    embs = []
    for meta_path in sorted((work / "meta").glob("*.json")):
        if meta_path.name.endswith(".text.json"):
            continue
        meta = json.loads(meta_path.read_text())
        tpath = meta_path.with_name(meta_path.stem + ".text.json")
        texts = json.loads(tpath.read_text()) if tpath.exists() else {}
        e = np.load(meta_path.with_suffix(".npy"))
        assert len(e) == len(meta["segments"]), meta_path
        for seg in meta["segments"]:
            rows.append((meta["id"], seg, texts.get(seg["name"])))
        embs.append(e)
    return rows, (np.concatenate(embs) if embs else np.zeros((0, 192), np.float32))


def export(work: Path, out: Path, speaker: str, language: str, sr: int, rules: Rules,
           ref: np.ndarray, normalize_db: float | None = -20.0, dry_run: bool = False,
           audit: int = 40, seed: int = 0, log=print) -> dict:
    rows, embs = load_all(work)
    if not rows:
        raise SystemExit("남긴 구간이 없습니다. process를 먼저 돌리세요.")

    center = ref
    sims = embs @ center
    if rules.refine:
        # 기준 목소리와 확실히 같고 깨끗한 구간들로 중심을 다시 잡는다.
        # 기준 클립 몇 개보다 실제 데이터 수천 개의 평균이 그 사람 목소리를 더 잘 대표한다.
        good = (sims >= rules.refine_sim) & np.array([s["bgm_db"] <= rules.refine_bgm_db for _, s, _ in rows])
        if good.sum() >= 50:
            center = centroid(embs[good])
            sims = embs @ center
            log(f"중심 다시 잡음: 깨끗한 구간 {int(good.sum())}개 기준 (원래 기준과 유사도 {float(center @ ref):.3f})")
        else:
            log(f"중심 다시 잡기 건너뜀: 기준을 넘는 구간이 {int(good.sum())}개뿐")

    reasons: Counter = Counter()
    same: Counter = Counter()
    keep = []
    for (vid, seg, tr), sim in zip(rows, sims):
        why = judge(seg, tr, float(sim), rules)
        if why is None:
            key = _norm_text(tr["text"])
            same[key] += 1
            if same[key] > rules.max_same_text:
                why = "duplicate_text"
        if why:
            reasons[why] += 1
        else:
            keep.append((vid, seg, tr, float(sim)))

    total_h = sum(s["dur"] for _, s, _ in rows) / 3600
    keep_h = sum(s["dur"] for _, s, _, _ in keep) / 3600
    q = np.percentile(sims, [5, 25, 50, 75, 95]).round(3).tolist()
    summary = {
        "speaker": speaker, "videos": len({v for v, _, _ in rows}),
        "candidates": len(rows), "candidate_hours": round(total_h, 2),
        "kept": len(keep), "kept_hours": round(keep_h, 2),
        "rejected": dict(reasons.most_common()), "sim_percentiles_5_25_50_75_95": q,
        "rules": rules.__dict__,
    }
    log(f"후보 {len(rows)}개 ({total_h:.2f}시간) → 남김 {len(keep)}개 ({keep_h:.2f}시간)")
    for k, v in reasons.most_common():
        log(f"  버림 {k:16s} {v}")
    log(f"  화자 유사도 분포 (5/25/50/75/95%): {q}")
    if dry_run:
        return summary

    wav_dir = out / "wavs"
    wav_dir.mkdir(parents=True, exist_ok=True)
    meta_lines, list_lines = [], []
    for i, (vid, seg, tr, sim) in enumerate(keep):
        x, src_sr = audio.read_wav(work / "segments" / vid / f"{seg['name']}.wav")
        x = audio.resample(x, src_sr, sr)
        if normalize_db is not None:
            x = audio.normalize_loudness(x, normalize_db)
        dst = wav_dir / f"{seg['name']}.wav"
        audio.write_wav(dst, x, sr)
        text = tr["text"].replace("|", " ").replace("\n", " ")
        meta_lines.append(f"{seg['name']}|{text}")
        list_lines.append(f"{dst.resolve()}|{speaker}|{language}|{text}")
        if (i + 1) % 5000 == 0:
            log(f"  {i + 1}/{len(keep)} 내보냄")
    (out / "metadata.csv").write_text("\n".join(meta_lines) + "\n", encoding="utf-8")
    (out / f"{speaker}.list").write_text("\n".join(list_lines) + "\n", encoding="utf-8")

    if audit:
        # 화자 기준선 근처 구간을 귀로 들어 보고 min_sim을 고르기 위한 샘플
        adir = out / "audit"
        shutil.rmtree(adir, ignore_errors=True)
        adir.mkdir()
        near = [(v, s, float(x)) for (v, s, _), x in zip(rows, sims) if abs(x - rules.min_sim) <= 0.08]
        random.Random(seed).shuffle(near)
        for v, s, x in near[:audit]:
            tag = "keep" if x >= rules.min_sim else "drop"
            shutil.copy(work / "segments" / v / f"{s['name']}.wav", adir / f"{x:.3f}_{tag}_{s['name']}.wav")

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    log(f"→ {out}")
    return summary

"""python -m vds {download,reference,process,transcribe,export,all}"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from pathlib import Path

import numpy as np


def pick_device(d: str) -> str:
    if d != "auto":
        return d
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def make_separator(args, device):
    from .separate import Demucs, Passthrough

    if args.separator == "none":
        return Passthrough()
    return Demucs(args.demucs_model, device=device, shifts=args.shifts)


def cmd_download(args):
    from .download import download

    if not args.urls and not args.batch_file:
        raise SystemExit("URL이나 -a 목록 파일을 주세요.")
    return download(args.work, args.urls, args.batch_file, args.min_duration, args.max_downloads,
                    args.reject_title, args.match_title, args.cookies_from_browser, args.cookies,
                    args.sleep)


def cmd_reference(args):
    from . import audio
    from .process import find_sources
    from .speaker import Ecapa, centroid, save_reference
    from .vad import SR, SileroVAD, merge_segments

    device = pick_device(args.device)
    sep, vad, embed = make_separator(args, device), SileroVAD(), Ecapa(device)
    clips = []
    for vid, src in find_sources([args.ref_dir]).items():
        mix = audio.load(src, sep.sr, sep.channels, duration=600)
        voice, _ = sep(mix)
        v16 = audio.resample(voice, sep.sr, SR)
        spans = merge_segments(vad(v16, 12.0), 0.4, 1.5, 12.0)
        clips += [v16[int(s * SR):int(e * SR)] for s, e in spans]
        print(f"  {src.name}: 발화 {len(spans)}개")
    if len(clips) < 5:
        raise SystemExit(f"기준 발화가 {len(clips)}개뿐입니다. 본인 목소리만 나오는 클립을 더 넣어 주세요.")
    e = embed(clips)
    c = centroid(e)
    sims = e @ c
    args.work.mkdir(parents=True, exist_ok=True)
    save_reference(args.work / "reference.npz", c, len(clips))
    print(f"기준 목소리: 발화 {len(clips)}개, 중심과의 유사도 최소 {sims.min():.3f} / 중앙 {np.median(sims):.3f}")
    if sims.min() < 0.4:
        print("  ! 다른 사람 목소리가 섞인 기준 클립이 있을 수 있습니다. 확인해 보세요.")


def cmd_process(args):
    from .process import Params, find_sources, process_source
    from .speaker import Ecapa, load_reference
    from .vad import SileroVAD

    ref = load_reference(args.work / "reference.npz")
    sources = find_sources([args.work / "raw", *args.input])
    todo = {k: v for k, v in sources.items() if not (args.work / "meta" / f"{k}.json").exists()}
    print(f"원본 {len(sources)}개 중 남은 것 {len(todo)}개")
    if not todo:
        return
    device = pick_device(args.device)
    sep, vad, embed = make_separator(args, device), SileroVAD(), Ecapa(device)
    p = Params(**{f.name: getattr(args, f.name) for f in fields(Params) if hasattr(args, f.name)})
    for i, (vid, src) in enumerate(todo.items()):
        print(f"[{i + 1}/{len(todo)}] {src.name}")
        try:
            meta = process_source(vid, src, args.work, sep, vad, embed, ref, p)
        except Exception as e:  # 깨진 파일 하나 때문에 밤새 돌린 게 멈추지 않게
            print(f"  ! 실패: {e!r}", file=sys.stderr)
            continue
        h = sum(s["dur"] for s in meta["segments"]) / 3600
        print(f"  → 구간 {len(meta['segments'])}개, {h:.2f}시간, 버림 {meta['rejected']}")


def cmd_transcribe(args):
    from .transcribe import transcribe_all

    device = pick_device(args.device)
    ct = args.compute_type if args.compute_type != "auto" else ("float16" if device == "cuda" else "int8")
    transcribe_all(args.work, args.model, device, ct, args.language, args.beam_size, args.initial_prompt)


def cmd_export(args):
    from .export import Rules, export
    from .speaker import load_reference

    r = Rules(**{f.name: getattr(args, f.name) for f in fields(Rules) if hasattr(args, f.name)})
    export(args.work, args.out or args.work / "dataset", args.speaker, args.language, args.sr, r,
           load_reference(args.work / "reference.npz"),
           None if args.no_normalize else args.normalize_db, args.dry_run, args.audit)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vds", description="영상에서 한 사람의 깨끗한 목소리 데이터셋 뽑기")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, device=True):
        sp.add_argument("--work", type=Path, default=Path("work"), help="작업 폴더 (기본 ./work)")
        if device:
            sp.add_argument("--device", default="auto", help="auto | cuda | cpu")

    def separation(sp):
        sp.add_argument("--separator", choices=["demucs", "none"], default="demucs",
                        help="none: 배경음 없는 원본일 때 분리 생략")
        sp.add_argument("--demucs-model", default="htdemucs", help="htdemucs | htdemucs_ft(느리지만 더 깨끗)")
        sp.add_argument("--shifts", type=int, default=0, help="Demucs shift 횟수 (늘리면 조금 더 깨끗, 그만큼 느림)")

    sp = sub.add_parser("download", help="yt-dlp로 오디오 받기")
    common(sp, device=False)
    sp.add_argument("urls", nargs="*", help="채널·재생목록·영상 URL")
    sp.add_argument("-a", "--batch-file", type=Path, help="URL 목록 파일 (한 줄에 하나)")
    sp.add_argument("--min-duration", type=int, default=60, help="이보다 짧은 영상(쇼츠 등)은 건너뜀, 초")
    sp.add_argument("--max-downloads", type=int)
    sp.add_argument("--reject-title", help="제목이 이 정규식에 맞으면 건너뜀 (예: '노래|커버|cover|MV')")
    sp.add_argument("--match-title", help="제목이 이 정규식에 맞는 것만")
    sp.add_argument("--cookies-from-browser", help="chrome | firefox | edge … (연령·멤버십 제한 영상용)")
    sp.add_argument("--cookies", type=Path)
    sp.add_argument("--sleep", type=float, default=1.0)
    sp.set_defaults(fn=cmd_download)

    sp = sub.add_parser("reference", help="본인 목소리만 나오는 클립으로 기준 목소리 만들기")
    common(sp)
    separation(sp)
    sp.add_argument("ref_dir", type=Path)
    sp.set_defaults(fn=cmd_reference)

    sp = sub.add_parser("process", help="분리 → 발화 자르기 → 품질·화자 거르기")
    common(sp)
    separation(sp)
    sp.add_argument("--input", type=Path, nargs="*", default=[], help="work/raw 말고 더 읽을 폴더 (직접 받은 다시보기 등)")
    sp.add_argument("--chunk-sec", type=float, default=600.0)
    sp.add_argument("--min-dur", type=float, default=1.5)
    sp.add_argument("--max-dur", type=float, default=12.0)
    sp.add_argument("--min-sim", type=float, default=0.25, help="이 아래 화자 유사도는 저장도 안 함 (느슨하게)")
    sp.add_argument("--max-bgm-db", type=float, default=-3.0)
    sp.set_defaults(fn=cmd_process)

    sp = sub.add_parser("transcribe", help="faster-whisper로 받아쓰기")
    common(sp)
    sp.add_argument("--model", default="large-v3", help="large-v3 | large-v3-turbo(더 빠름) …")
    sp.add_argument("--compute-type", default="auto")
    sp.add_argument("--language", default="ko")
    sp.add_argument("--beam-size", type=int, default=5)
    sp.add_argument("--initial-prompt", help="자주 나오는 고유명사를 적어 두면 표기가 맞아진다")
    sp.set_defaults(fn=cmd_transcribe)

    sp = sub.add_parser("export", help="최종 기준으로 걸러 데이터셋 만들기")
    common(sp, device=False)
    sp.add_argument("--out", type=Path)
    sp.add_argument("--speaker", default="speaker")
    sp.add_argument("--language", default="ko")
    sp.add_argument("--sr", type=int, default=44100)
    sp.add_argument("--normalize-db", type=float, default=-20.0)
    sp.add_argument("--no-normalize", action="store_true")
    sp.add_argument("--dry-run", action="store_true", help="파일은 안 쓰고 몇 시간 남는지만 보기")
    sp.add_argument("--audit", type=int, default=40, help="화자 기준선 근처 샘플 몇 개를 audit/에 복사할지")
    sp.add_argument("--min-sim", type=float, default=0.55)
    sp.add_argument("--max-bgm-db", type=float, default=-15.0)
    sp.add_argument("--min-logprob", type=float, default=-0.8)
    sp.add_argument("--max-no-speech", type=float, default=0.6)
    sp.add_argument("--max-same-text", type=int, default=20)
    sp.add_argument("--no-refine", dest="refine", action="store_false")
    sp.set_defaults(fn=cmd_export)

    args = ap.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())

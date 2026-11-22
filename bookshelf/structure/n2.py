"""'두 권까지' 조건: 아무 책 하나, 아무 책 둘을 함께 뺀 모든 경우를 푼다 (경우마다 병렬).

판정 (모든 경우)
- 안정 (메커니즘 없음)
- 꺼낼 수 있음: 뺀 책의 덮개가 따라 내려온 거리 Δ ≤ 1.5 mm (쐐기 2 mm − 틈 0.5 mm)
- 강도: 막대 휨응력 ≤ 재료 허용값
- 평형 (analyze.case 가 확인)
두 번째 책의 Δ 는 '첫 권을 이미 뺀 상태에서 둘째를 뺄 때' 가 더 나쁠 수 있으나, 여기서는 둘이 빠진 최종 상태를
S0 와 비교한다 (덮개가 내려온 총량이라 더 보수적이다).

python3 structure/n2.py out/bond/s3/layout.json --mats petg16,beech12 --out out/bond/s3/n2.json
"""
import argparse
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).parent))
import analyze as A  # noqa: E402
import model as MD  # noqa: E402

_L, _base = None, {}


def init(path):
    global _L
    _L = json.load(open(path))


def work(args):
    mat, play, removed = args
    key = (mat, play)
    if key not in _base:
        _base[key] = A.case(_L, mat, detail="clip", play=play)
    base = _base[key]
    t0 = time.time()
    res = A.case(_L, mat, removed=set(removed), detail="clip", play=play)
    out = dict(mat=mat, removed=list(removed), seconds=time.time() - t0)
    if "unstable" in res:
        out["unstable"] = True
        return out
    out.update(drop=A.cap_drop(_L, base, res, list(removed)) if removed else 0.0, sigma=res["sigma_max"],
               clip=res["clip_tension_max"], sag=res["rod_sag_max"], eq=res["equilibrium_error"],
               ground=res["ground_share"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("layout")
    ap.add_argument("--mats", default="petg16,beech12")
    ap.add_argument("--play", type=float, default=0.2)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    L = json.load(open(a.layout))
    ids = [b["id"] for b in L["books"]]
    cases = [()] + [(i,) for i in ids] + list(itertools.combinations(ids, 2))
    tasks = [(m, a.play, c) for m in a.mats.split(",") for c in cases]
    t0 = time.time()
    rows = []
    with Pool(a.jobs, initializer=init, initargs=(a.layout,)) as pool:
        for k, r in enumerate(pool.imap_unordered(work, tasks, chunksize=2)):
            rows.append(r)
            if (k + 1) % 50 == 0:
                print(f"  {k + 1}/{len(tasks)}  {time.time() - t0:.0f}s", flush=True)
    summary = {}
    for mat in a.mats.split(","):
        rs = [r for r in rows if r["mat"] == mat]
        allow = MD.MATS[mat]["allow"]
        ok = [r for r in rs if not r.get("unstable")]
        single = [r for r in ok if len(r["removed"]) == 1]
        pair = [r for r in ok if len(r["removed"]) == 2]

        def worst(xs, k):
            return max(xs, key=lambda r: r[k]) if xs else None
        s = dict(
            cases=len(rs), unstable=[r["removed"] for r in rs if r.get("unstable")],
            single_drop=worst(single, "drop"), pair_drop=worst(pair, "drop"),
            sigma=worst(ok, "sigma"), clip=worst(ok, "clip"),
            fail_drop=[r["removed"] for r in ok if r["drop"] > A.DROP - A.CLEAR],
            fail_sigma=[r["removed"] for r in ok if r["sigma"] > allow],
            eq_max=max(r["eq"] for r in ok), ground_max=max(r["ground"] for r in ok))
        s["pass"] = not s["unstable"] and not s["fail_drop"] and not s["fail_sigma"]
        summary[mat] = s
        print(f"{mat:8} cases {s['cases']} | unstable {len(s['unstable'])} {s['unstable'][:6]} | "
              f"Δ single {s['single_drop']['drop']:.2f} {s['single_drop']['removed']} pair {s['pair_drop']['drop']:.2f} "
              f"{s['pair_drop']['removed']} | σ {s['sigma']['sigma']:.2f}/{allow} {s['sigma']['removed']} | "
              f"clip {s['clip']['clip']:.1f} N | fail Δ {len(s['fail_drop'])} {s['fail_drop'][:6]} | "
              f"eq {s['eq_max']:.0e} | {'PASS' if s['pass'] else 'FAIL'}")
    Path(a.out).write_text(json.dumps(dict(layout=a.layout, play=a.play, summary=summary, rows=rows),
                                      ensure_ascii=False, indent=1, default=float))
    print(f"done {time.time() - t0:.0f}s → {a.out}")


if __name__ == "__main__":
    main()

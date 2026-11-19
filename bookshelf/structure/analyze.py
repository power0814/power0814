"""2안(책 기둥 + 줄눈 막대) 구조 해석.

경우
- S0: 책 전부.
- 한 권 빼기: 책마다 하나씩 (28가지).
- 두 권 빼기: 같은 줄에서 이웃한 두 권 (참고. 설계 조건은 아니다).
재료: model.MATS. 장기 하중 (크리프로 줄인 E). 접촉 강성 k_c, 클립 강성 k_clip 기본 5000 N/mm.

이음 상세
- plain        막대가 홈에 얹혀 있기만 하다.
- clip, play 0 덮개·받침이 막대를 양방향으로 꽉 잡는다.
- clip, play p 막대가 홈에 앉아 누를 때는 압축, p mm 보다 더 들릴 때만 걸쇠가 당긴다.

맞춤 오차: 모든 압축 접촉(책-덮개, 책-받침, 받침-바닥)에 0 ~ 0.3 mm 의 초기 틈. 접촉마다 값은
(표본 번호, 접촉 이름)만으로 정해진다 (계산 순서와 무관).

판정 (한 권 빼기의 모든 경우에 대해)
1. 꺼낼 수 있음: 쐐기를 빼면 책이 2 mm 내려간다. 그 사이 덮개가 Δ 만큼 따라 내려오면 틈은 2 − Δ.
   0.5 mm 이상 남아야 한다 → Δ ≤ 1.5 mm.
2. 강도: 막대 최대 휨응력 ≤ 재료의 장기 허용값.
3. 안정: 메커니즘 없음.
4. 평형: 모든 경우에서 바닥 반력 + 접지 스프링 = 전체 하중 (상대 오차 1e-7 이하, 실제로는 대부분 1e-12 이하). 아니면 해석을 멈춘다.
클립이 막대에서 뽑히는 힘은 판정이 아니라 설계 요구값으로 보고한다.

사용법: python3 structure/analyze.py [--samples 4] [--jobs 4]
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).parent))
import model as MD  # noqa: E402
from solver import Unstable  # noqa: E402

ROOT = Path(__file__).parent.parent
DROP, CLEAR = 2.0, 0.5
GMAX = 0.3
MATS = ["petg12", "petg16", "beech12", "alu12"]


def gap_fn(seed):
    if seed is None:
        return None

    def gap(kind, bid, y, x):
        h = hashlib.sha256(f"{seed}|{kind}|{bid}|{y:.3f}|{x:.3f}".encode()).digest()
        return random.Random(h).uniform(0.0, GMAX)
    return gap


def case(L, mat, removed=(), **kw):
    m, info = MD.build(L, mat, removed=removed, **kw)
    try:
        r = m.solve()
    except Unstable as e:
        return dict(unstable=str(e))
    res = MD.results(m, info, r)
    if res["equilibrium_error"] > 1e-7:     # 해석기 수렴 허용치(강성×변위의 1e-8)와 맞춘다
        raise RuntimeError(f"equilibrium error {res['equilibrium_error']} ({mat}, removed {removed})")
    res["_u"], res["_info"] = r["u"], info
    return res


def cap_drop(L, base, res, bids):
    """뺀 책들의 머리 자리에서 덮개(plain 이면 막대)가 S0 대비 얼마나 내려왔나 (mm, 아래로 +)."""
    worst = 0.0
    for bid in bids:
        before = MD.cap_underside(L, base["_info"], base["_u"], bid)
        try:
            after = MD.cap_underside(L, res["_info"], res["_u"], bid)
        except KeyError:
            continue                  # 덮개가 책과 함께 빠지는 줄 (막대 없음)
        worst = max([worst] + [b - a for b, a in zip(before, after)])
    return worst


def group(args):
    """한 재료·한 상세·한 맞춤 표본에 대해 S0, 한 권 빼기 28, (선택) 두 권 빼기."""
    L, mat, opts, seed, pairs = args
    kw = dict(opts); kw["gaps"] = gap_fn(seed)
    t0 = time.time()
    out = dict(mat=mat, opts=opts, seed=seed, single=[], pair=[])
    base = case(L, mat, **kw)
    if "unstable" in base:
        out["base_unstable"] = True
        return out
    out["base"] = dict(sigma=base["sigma_max"], sag=base["rod_sag_max"], clip=base["clip_tension_max"],
                       load=base["load_total"], ground=base["ground_share"], head=base["head_force"])
    worst_ground = base["ground_share"]
    for b in L["books"]:
        res = case(L, mat, removed={b["id"]}, **kw)
        row = dict(id=b["id"])
        if "unstable" in res:
            row["unstable"] = True
        else:
            row.update(drop=cap_drop(L, base, res, [b["id"]]), sigma=res["sigma_max"], clip=res["clip_tension_max"],
                       sag=res["rod_sag_max"], head=res["head_force"])
            worst_ground = max(worst_ground, res["ground_share"])
        out["single"].append(row)
    if pairs:
        for r in L["runs"]:
            for a, b in zip(r["cells"], r["cells"][1:]):
                res = case(L, mat, removed={a, b}, **kw)
                row = dict(ids=[a, b])
                if "unstable" in res:
                    row["unstable"] = True
                else:
                    row.update(drop=cap_drop(L, base, res, [a, b]), sigma=res["sigma_max"],
                               clip=res["clip_tension_max"])
                out["pair"].append(row)
    out["ground_max"] = worst_ground
    out["seconds"] = time.time() - t0
    return out


def summary(g):
    if g.get("base_unstable"):
        return dict(base_unstable=True)
    ok = [s for s in g["single"] if not s.get("unstable")]
    s = dict(unstable=[x["id"] for x in g["single"] if x.get("unstable")])
    s["drop"] = max((x["drop"] for x in ok), default=0.0)
    s["drop_id"] = max(ok, key=lambda x: x["drop"])["id"] if ok else None
    s["sigma"] = max([x["sigma"] for x in ok] + [g["base"]["sigma"]])
    s["sigma_id"] = max(ok, key=lambda x: x["sigma"])["id"] if ok else None
    s["clip"] = max([x["clip"] for x in ok] + [g["base"]["clip"]])
    s["clip_id"] = max(ok, key=lambda x: x["clip"])["id"] if ok else None
    allow = MD.MATS[g["mat"]]["allow"]
    s["pass"] = (not s["unstable"]) and s["drop"] <= DROP - CLEAR and s["sigma"] <= allow
    if g["pair"]:
        okp = [p for p in g["pair"] if not p.get("unstable")]
        s["pair_unstable"] = [p["ids"] for p in g["pair"] if p.get("unstable")]
        s["pair_fail"] = [p["ids"] for p in okp if p["drop"] > DROP - CLEAR or p["sigma"] > allow]
        s["pair_drop"] = max((p["drop"] for p in okp), default=0.0)
    return s


def label(opts):
    if opts.get("detail") == "plain":
        return "plain"
    extra = {k: v for k, v in opts.items() if k not in ("detail", "play")}
    return f"clip play {opts.get('play', 0.5)}" + (f" {extra}" if extra else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default=str(ROOT / "out/runs/layout.json"))
    ap.add_argument("--out", default=str(ROOT / "out/runs/structure.json"))
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--plays", default="0,0.2,0.5")
    ap.add_argument("--main-play", type=float, default=None, help="민감도·두 권 빼기에 쓸 유격. 없으면 표본 결과로 고른다")
    a = ap.parse_args()
    L = json.load(open(a.layout))
    plays = [float(p) for p in a.plays.split(",")]

    from multiprocessing import Pool
    t0 = time.time()

    def run(tasks, title):
        print(f"== {title} ({len(tasks)} groups)", flush=True)
        res = []
        with Pool(a.jobs) as pool:
            for g in pool.imap(group, tasks):
                s = summary(g); g["summary"] = s; res.append(g)
                tag = f"{g['mat']:8} {label(g['opts']):32} seed {g['seed']}"
                if s.get("base_unstable"):
                    print(f"  {tag} | S0 UNSTABLE", flush=True); continue
                print(f"  {tag} | unstable {s['unstable'] or '-'} Δ {s['drop']:.2f} ({s['drop_id']}) "
                      f"σ {s['sigma']:.2f} ({s['sigma_id']}) clip {s['clip']:.1f} N ({s['clip_id']}) "
                      f"ground {g['ground_max']:.0e} {'PASS' if s['pass'] else 'FAIL'} [{g['seconds']:.0f}s]", flush=True)
        return res

    rep = dict(criteria=dict(drop=DROP, clearance=CLEAR, gap_max=GMAX), layout=a.layout)
    # 1) 이음 상세와 유격: 완벽한 맞춤 + 맞춤 오차 표본
    tasks = []
    for mat in MATS:
        tasks.append((L, mat, dict(detail="plain"), None, False))
        for p in plays:
            for seed in [None] + list(range(1, a.samples + 1)):
                tasks.append((L, mat, dict(detail="clip", play=p), seed, False))
    rep["detail_study"] = run(tasks, "이음 상세 × 유격 × 맞춤 오차")

    # 유격 고르기: 모든 재료·표본에서 판정을 통과하는 것 중 클립 힘이 가장 작은 것
    def worst(mat, p, key):
        gs = [g for g in rep["detail_study"] if g["mat"] == mat and g["opts"].get("detail") == "clip"
              and g["opts"].get("play") == p]
        return gs
    choice = a.main_play
    if choice is None:
        scores = {}
        for p in plays:
            gs = [g for g in rep["detail_study"] if g["opts"].get("detail") == "clip" and g["opts"].get("play") == p
                  and g["mat"] in ("petg16", "beech12", "alu12")]
            ok = all(g["summary"].get("pass") for g in gs)
            scores[p] = (not ok, max(g["summary"].get("clip", 1e9) for g in gs))
        choice = min(plays, key=lambda p: scores[p])
        print(f"chosen play {choice} mm  (scores {scores})")
    rep["main_play"] = choice

    # 2) 고른 상세에서 두 권 빼기, 민감도
    tasks = [(L, mat, dict(detail="clip", play=choice), None, True) for mat in MATS]
    for mat in MATS:
        for extra in (dict(k_c=500.0), dict(k_c=50000.0), dict(k_clip=500.0), dict(k_clip=50000.0),
                      dict(long_term=False)):
            tasks.append((L, mat, dict(detail="clip", play=choice, **extra), None, False))
    rep["main_and_sensitivity"] = run(tasks, f"유격 {choice} mm: 두 권 빼기와 민감도")
    for part in ("detail_study", "main_and_sensitivity"):
        for g in rep[part]:
            for row in g["single"]:
                row.pop("head", None)
    Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float))
    print(f"done in {time.time() - t0:.0f}s → {a.out}")


if __name__ == "__main__":
    main()

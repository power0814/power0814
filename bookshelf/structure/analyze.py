"""2안(책 기둥 + 줄눈 막대) 구조 해석.

경우
- S0: 책 전부.
- 한 권 빼기: 책마다 하나씩 (28가지).
- 두 권 빼기: 같은 줄에서 이웃한 두 권 (참고. 설계 조건은 아니다).
재료: model.MATS. 장기 하중 (크리프로 줄인 E). 접촉 강성 k_c, 클립 강성 k_clip 기본 5000 N/mm.

판정 (한 권 빼기의 모든 경우에 대해)
1. 꺼낼 수 있음: 쐐기를 빼면 책이 2 mm 내려간다. 그 사이 덮개가 Δ 만큼 따라 내려오면 틈은 2 − Δ.
   0.5 mm 이상 남아야 한다 → Δ ≤ 1.5 mm.
2. 강도: 막대 최대 휨응력 ≤ 재료의 장기 허용값.
3. 안정: 메커니즘 없음.
4. 클립: 덮개·받침 클립 한 점이 막대에서 뽑히는 힘 ≤ 10 N (스냅 고정의 설계 목표값, 가정).
5. 평형: 모든 경우에서 바닥 반력 합 = 전체 하중 (상대 오차 1e-9 이하). 아니면 해석을 멈춘다.

사용법: python3 structure/analyze.py [--layout out/runs/layout.json] [--out out/runs]
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import model as MD  # noqa: E402
from solver import Unstable  # noqa: E402

DROP, CLEAR, CLIP_ALLOW = 2.0, 0.5, 10.0


def case(L, mat, removed=(), **kw):
    m, info = MD.build(L, mat, removed=removed, **kw)
    try:
        r = m.solve()
    except Unstable as e:
        return dict(unstable=str(e))
    res = MD.results(m, info, r)
    if res["equilibrium_error"] > 1e-9:
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


def sweep(L, mat, pairs=True, **kw):
    base = case(L, mat, **kw)
    if "unstable" in base:
        return dict(mat=mat, base_unstable=base["unstable"])
    out = dict(mat=mat, name=MD.MATS[mat]["name"], allow=MD.MATS[mat]["allow"], opts={k: v for k, v in kw.items()
               if k != "gaps"}, base=dict(sigma=base["sigma_max"], sag=base["rod_sag_max"],
               clip=base["clip_tension_max"], load=base["load_total"]), single=[], pair=[])
    for b in L["books"]:
        res = case(L, mat, removed={b["id"]}, **kw)
        row = dict(id=b["id"], carried=base["head_force"].get(b["id"], 0.0))
        if "unstable" in res:
            row["unstable"] = True
        else:
            row.update(drop=cap_drop(L, base, res, [b["id"]]), sigma=res["sigma_max"], where=res["sigma_where"],
                       sag=res["rod_sag_max"], clip=res["clip_tension_max"])
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
    ok = [s for s in out["single"] if not s.get("unstable")]
    out["single_unstable"] = [s["id"] for s in out["single"] if s.get("unstable")]
    if ok:
        out["single_drop_max"] = max(s["drop"] for s in ok)
        out["single_drop_worst"] = max(ok, key=lambda s: s["drop"])["id"]
        out["single_sigma_max"] = max(max(s["sigma"] for s in ok), base["sigma_max"])
        out["single_sigma_worst"] = max(ok, key=lambda s: s["sigma"])["id"]
        out["single_clip_max"] = max(max(s["clip"] for s in ok), base["clip_tension_max"])
    out["pass_drop"] = bool(ok) and out["single_drop_max"] <= DROP - CLEAR and not out["single_unstable"]
    out["pass_sigma"] = bool(ok) and out["single_sigma_max"] <= MD.MATS[mat]["allow"]
    out["pass_clip"] = bool(ok) and out["single_clip_max"] <= CLIP_ALLOW
    okp = [p for p in out["pair"] if not p.get("unstable")]
    out["pair_unstable"] = [p["ids"] for p in out["pair"] if p.get("unstable")]
    out["pair_drop_max"] = max((p["drop"] for p in okp), default=0.0)
    out["pair_sigma_max"] = max((p["sigma"] for p in okp), default=0.0)
    out["pair_fail"] = [p["ids"] for p in okp if p["drop"] > DROP - CLEAR or p["sigma"] > MD.MATS[mat]["allow"]
                        or p["clip"] > CLIP_ALLOW]
    out["pass"] = out["pass_drop"] and out["pass_sigma"] and out["pass_clip"]
    return out


def line(s):
    if "base_unstable" in s:
        return f"{s['mat']:8} base case unstable: {s['base_unstable']}"
    txt = (f"{s['mat']:8} S0 σ {s['base']['sigma']:.2f} sag {s['base']['sag']:.3f} | one out: unstable "
           f"{s['single_unstable'] or '-'}")
    if "single_drop_max" in s:
        txt += (f", Δmax {s['single_drop_max']:.2f} mm ({s['single_drop_worst']}), σmax {s['single_sigma_max']:.2f}"
                f" ({s['single_sigma_worst']}) / {s['allow']} MPa, clip {s['single_clip_max']:.2f} N")
    if s["pair"]:
        txt += (f" | pairs: {len(s['pair_unstable'])}/{len(s['pair'])} unstable, Δ {s['pair_drop_max']:.2f}, "
                f"σ {s['pair_sigma_max']:.2f}, fail {s['pair_fail'] or '-'}")
    return txt + f" | {'PASS' if s['pass'] else 'FAIL'}"


def tolerance(L, mat, n=30, gmax=0.3, seed=1, **kw):
    """맞춤 오차: 모든 압축 접촉에 0 ~ gmax mm 의 초기 틈을 무작위로. 한 권 빼기 전부를 다시 본다."""
    rng = random.Random(seed)
    worst = dict(drop=0.0, sigma=0.0, clip=0.0, unstable=0, cases=0)
    for _ in range(n):
        table = {}

        def gap(kind, bid, y, x, table=table):
            key = (kind, bid, y, round(x, 3))
            if key not in table:
                table[key] = rng.uniform(0, gmax)
            return table[key]
        base = case(L, mat, gaps=gap, **kw)
        worst["cases"] += 1
        if "unstable" in base:
            worst["unstable"] += 1; continue
        worst["sigma"] = max(worst["sigma"], base["sigma_max"])
        for b in L["books"]:
            res = case(L, mat, removed={b["id"]}, gaps=gap, **kw)
            worst["cases"] += 1
            if "unstable" in res:
                worst["unstable"] += 1; continue
            worst["drop"] = max(worst["drop"], cap_drop(L, base, res, [b["id"]]))
            worst["sigma"] = max(worst["sigma"], res["sigma_max"])
            worst["clip"] = max(worst["clip"], res["clip_tension_max"])
    return worst


def main():
    ap = argparse.ArgumentParser()
    root = Path(__file__).parent.parent
    ap.add_argument("--layout", default=str(root / "out/runs/layout.json"))
    ap.add_argument("--out", default=str(root / "out/runs"))
    ap.add_argument("--mats", default="petg12,petg16,beech12,alu12")
    ap.add_argument("--tol-samples", type=int, default=20)
    a = ap.parse_args()
    L = json.load(open(a.layout))
    mats = a.mats.split(",")
    rep = dict(layout=a.layout, criteria=dict(drop=DROP, clearance=CLEAR, clip_allow=CLIP_ALLOW),
               main=[], plain=[], sensitivity=[], tolerance=[], snap_check=[])

    print("== snap check (절점 합치기 0.5 mm vs 0.05 mm, 27 빼기)")
    for snap in (0.5, 0.05):
        r = case(L, "petg12", removed={"27"}, snap=snap)
        rep["snap_check"].append(dict(snap=snap, sigma=r["sigma_max"], sag=r["rod_sag_max"]))
        print(f"  snap {snap}: σ {r['sigma_max']:.6f}  sag {r['rod_sag_max']:.6f}")

    print("== 클립 상세 (덮개·받침이 막대에 끼워져 남는다)")
    for mat in mats:
        s = sweep(L, mat); rep["main"].append(s); print(line(s))
    print("== 비교: 얹기만 한 상세 (클립 없음)")
    for mat in mats:
        s = sweep(L, mat, pairs=False, detail="plain"); rep["plain"].append(s); print(line(s))
    print("== 민감도 (클립 상세, 한 권 빼기)")
    for mat in mats:
        for kw in (dict(k_c=500.0), dict(k_c=50000.0), dict(k_clip=500.0), dict(k_clip=50000.0),
                   dict(long_term=False)):
            s = sweep(L, mat, pairs=False, **kw)
            rep["sensitivity"].append(dict(mat=mat, opts=kw, drop=s.get("single_drop_max"),
                                           sigma=s.get("single_sigma_max"), clip=s.get("single_clip_max"),
                                           unstable=s.get("single_unstable"), passed=s.get("pass")))
            print(f"  {mat:8} {str(kw):24} Δmax {s.get('single_drop_max', float('nan')):.2f}  "
                  f"σmax {s.get('single_sigma_max', float('nan')):.2f}  clip {s.get('single_clip_max', float('nan')):.2f}"
                  f"  unstable {s.get('single_unstable') or '-'}  {'PASS' if s.get('pass') else 'FAIL'}")
    if a.tol_samples:
        print(f"== 맞춤 오차 (모든 압축 접촉에 0–0.3 mm 무작위 틈, {a.tol_samples}회 × 29경우)")
        for mat in mats:
            w = tolerance(L, mat, n=a.tol_samples)
            rep["tolerance"].append(dict(mat=mat, samples=a.tol_samples, gmax=0.3, **w))
            print(f"  {mat:8} Δmax {w['drop']:.2f}  σmax {w['sigma']:.2f}  clip {w['clip']:.2f}  "
                  f"unstable {w['unstable']}/{w['cases']}")
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "structure.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()

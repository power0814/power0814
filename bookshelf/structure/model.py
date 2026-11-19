"""runs 배치(layout.json)를 해석 모델로 바꾼다.

두 가지 이음 상세를 모델링한다.

detail="plain"  막대가 홈에 얹혀 있기만 하다.
  덮개와 받침은 책에 붙은 것으로 보고, 책 머리/발 ↔ 막대 접촉이 압축만 받는다.
  책을 빼면 책·받침·쐐기가 빠지고 덮개는 막대에 걸려 남는다 (무게만 막대에).

detail="clip"   덮개와 받침이 막대에 끼워져(스냅) 막대와 함께 남는다. 책과 쐐기만 빠진다.
  덮개·받침 = 강체 (w, ax, ay). 막대와의 연결은 양방향(클립), 책과의 접촉은 압축만.
  덮개는 줄의 모든 막대 줄을 가로로 묶어서, 막대 한 줄만 따로 시소처럼 들리지 못하게 한다.
  클립에 걸리는 인장(뽑히는 힘)을 따로 보고한다.

공통
- 막대: 줄(run)마다, 막대 줄(y)마다 x 방향 연속보 (티모셴코). 절점은 막대 끝과 모든 접촉점.
- 책: 강체 (w0, ax, ay), 기준점 = 무게중심 (xc, cg_y).
- 선 접촉(두께 t)은 2점 가우스 위치 xc ± t/(2√3) 로 나눈다.
- 하중: 책, 받침, 덮개 무게. 막대 자중 (일관 절점 하중).
"""
from __future__ import annotations

import math
from collections import defaultdict

from solver import Model

G_ACC = 9.81           # m/s², kg·G_ACC = N

MATS = {
    # E: 단기 탄성계수 (MPa), creep: 장기 하중에서 E 를 나누는 값, allow: 장기 허용 휨응력 (MPa)
    "petg12": dict(name="출력 PETG Ø12 (속 100%)", E=1800.0, creep=2.5, G=650.0, D=12.0, d=0.0,
                   allow=8.0, rho=1.27e-6, kappa=0.9),
    "petg16": dict(name="출력 PETG Ø16 (속 100%)", E=1800.0, creep=2.5, G=650.0, D=16.0, d=0.0,
                   allow=8.0, rho=1.27e-6, kappa=0.9),
    "beech12": dict(name="너도밤나무 환봉 Ø12", E=11000.0, creep=1.6, G=690.0, D=12.0, d=0.0,
                    allow=18.0, rho=0.72e-6, kappa=0.9),
    "alu12": dict(name="알루미늄 관 Ø12 × 1.5", E=69000.0, creep=1.0, G=26000.0, D=12.0, d=9.0,
                  allow=70.0, rho=2.70e-6, kappa=0.53),
}

PETG_PART = 1.27e-6 * 0.45   # 받침·덮개: PETG, 채움 포함 평균 밀도 (kg/mm³) 가정


def section(m):
    D, d = m["D"], m["d"]
    A = math.pi / 4 * (D * D - d * d)
    I = math.pi / 64 * (D ** 4 - d ** 4)
    return A, I


def part_masses(b, P):
    """받침·덮개 질량 추정 (kg)."""
    foot = (b["t"] + 2 * P["side"]) * b["w"]
    cap = foot * (P["cap_t"] - P["rod_r"] + 4.0) * PETG_PART
    shoe = foot * b["shoe"] * PETG_PART
    return shoe, cap


def merge_close(xs, tol):
    """정렬된 좌표에서 tol 안으로 붙은 것들을 하나로. 첫 묶음은 첫 값, 끝 묶음은 끝 값(막대 끝), 나머지는 평균."""
    out = [[xs[0]]]
    for x in xs[1:]:
        if x - out[-1][-1] <= tol:
            out[-1].append(x)
        else:
            out.append([x])
    res = []
    for k, grp in enumerate(out):
        if k == 0:
            res.append(grp[0])
        elif k == len(out) - 1:
            res.append(grp[-1])
        else:
            res.append(sum(grp) / len(grp))
    return res


def gauss2(b):
    h = b["t"] / (2 * math.sqrt(3))
    return [b["xc"] - h, b["xc"] + h]


def face_pts(b, P):
    """책 머리·발 면의 접촉점: 두께 방향 가우스 2점 × 깊이 방향 앞뒤 끝에서 10 mm 안쪽."""
    return [(x, y) for y in (P["y0"] + 10.0, P["y0"] + b["w"] - 10.0) for x in gauss2(b)]


def build(L, mat="petg12", removed=(), k_c=5000.0, long_term=True, gaps=None, snap=0.5,
          detail="clip", k_clip=5000.0):
    """gaps: callable(kind, book_id, y, x) → 초기 틈 (mm). 없으면 모두 0 (완벽한 맞춤).
    snap: 이 거리(mm) 안의 막대 절점은 하나로 합친다 (아주 짧은 요소가 강성 행렬을 망치지 않게)."""
    P = L["params"]
    M = MATS[mat]
    A, I = section(M)
    E = M["E"] / (M["creep"] if long_term else 1.0)
    Gs = M["G"] / (M["creep"] if long_term else 1.0)
    EI, KGA = E * I, M["kappa"] * Gs * A
    removed = set(removed)
    books = {b["id"]: b for b in L["books"]}
    runs = {r["id"]: r for r in L["runs"]}
    m = Model()
    info = dict(rods={}, books={}, caps={}, shoes={}, loads_total=0.0, EI=EI, A=A, I=I, c=M["D"] / 2, mat=M,
                detail=detail)
    gap = gaps or (lambda *a: 0.0)

    for rid, r in runs.items():
        if detail == "plain":
            alive = [c for c in r["cells"] + r["upper"] if c not in removed]
            if not alive:
                continue         # 덮개만 남은 줄: 막대도 함께 내려진 것으로 본다
        for y in r["rows"]:
            xs = {r["x0"], r["x1"]}
            for c in r["cells"]:
                xs.update(gauss2(books[c]))
            for c in r["upper"]:
                if y in books[c]["rows_below"] and (detail == "clip" or c not in removed):
                    xs.update(gauss2(books[c]))
            xs = merge_close(sorted(xs), snap)
            assert all(r["x0"] - 1e-9 <= x <= r["x1"] + 1e-9 for x in xs), (rid, y)
            nodes = [m.dofs(2) for _ in xs]
            q = M["rho"] * A * G_ACC
            for (a, b), (x0, x1) in zip(zip(nodes, nodes[1:]), zip(xs, xs[1:])):
                Le = x1 - x0
                m.beam(a[0], a[1], b[0], b[1], Le, EI, KGA, tag=(rid, y, x0, x1))
                # 등분포 자중의 일관 절점 하중 (절점 처짐이 정확해진다): 힘 qL/2, 모멘트 ∓qL²/12
                m.load(a[0], -q * Le / 2); m.load(b[0], -q * Le / 2)
                m.load(a[1], -q * Le * Le / 12); m.load(b[1], q * Le * Le / 12)
                info["loads_total"] += q * Le
            info["rods"][(rid, y)] = dict(xs=xs, nodes=nodes)

    def rod_w(rid, y, x):
        rod = info["rods"][(rid, y)]
        j = min(range(len(rod["xs"])), key=lambda k: abs(rod["xs"][k] - x))
        assert abs(rod["xs"][j] - x) <= snap / 2 + 1e-9, (rid, y, x, rod["xs"][j])
        return rod["nodes"][j][0]

    def body(W):
        d = m.dofs(3); m.load(d[0], -W); info["loads_total"] += W
        return d

    def rel(top, bot, xc, yc, x, y):
        """d = w_top(x, y) − w_bot(x, y). top/bot: 강체 자유도 3개, 막대 처짐 자유도 하나, 또는 None(바닥)."""
        t = defaultdict(float)
        for dofs, s in ((top, 1.0), (bot, -1.0)):
            if dofs is None:
                continue
            if isinstance(dofs, int):
                t[dofs] += s
            else:
                t[dofs[0]] += s; t[dofs[1]] += s * (y - yc); t[dofs[2]] += s * (x - xc)
        return dict(t)

    for bid, b in books.items():
        shoe_kg, cap_kg = part_masses(b, P)
        xc, yc = b["xc"], b["cg_y"]
        crun = runs[b["run"]]
        if detail == "plain":
            if bid in removed:
                pts = [(y, x) for y in crun["rows"] for x in gauss2(b) if (b["run"], y) in info["rods"]]
                if pts:   # 덮개는 막대에 걸려 남는다
                    W = cap_kg * G_ACC
                    for y, x in pts:
                        m.load(rod_w(b["run"], y, x), -W / len(pts))
                    info["loads_total"] += W
                continue
            bk = body((b["kg"] + shoe_kg + cap_kg) * G_ACC)
            info["books"][bid] = dict(dofs=bk)
            for y in crun["rows"]:
                for x in gauss2(b):
                    m.spring(rel(rod_w(b["run"], y, x), bk, xc, yc, x, y), k_c / 2,
                             g0=gap("cap", bid, y, x), tag=("cap", bid, b["run"], y, x))
            if b["base"] is None:
                for x, y in face_pts(b, P):
                    m.spring(rel(bk, None, xc, yc, x, y), k_c / 2, g0=gap("floor", bid, y, x),
                             tag=("floor", bid, None, y, x))
            else:
                for y in b["rows_below"]:
                    for x in gauss2(b):
                        m.spring(rel(bk, rod_w(b["base"], y, x), xc, yc, x, y), k_c / 2,
                                 g0=gap("shoe", bid, y, x), tag=("shoe", bid, b["base"], y, x))
            continue

        # ---- clip: 덮개·받침은 막대에 끼워져 남는다 ----
        # 막대가 없는 줄(책 둘 이하)의 덮개는 책 머리에 얹혀 있을 뿐이고, 책을 빼면 함께 빠진다.
        if not crun["rows"] and bid in removed:
            cap = None
        else:
            cap = body(cap_kg * G_ACC); info["caps"][bid] = dict(dofs=cap)
        for y in crun["rows"]:
            for x in gauss2(b):
                m.spring(rel(rod_w(b["run"], y, x), cap, xc, yc, x, y), k_clip, comp=False,
                         tag=("clip_cap", bid, b["run"], y, x))
        shoe = body(shoe_kg * G_ACC); info["shoes"][bid] = dict(dofs=shoe)
        if b["base"] is None:
            for x, y in face_pts(b, P):
                m.spring(rel(shoe, None, xc, yc, x, y), k_c / 2, g0=gap("floor", bid, y, x),
                         tag=("floor", bid, None, y, x))
        else:
            for y in b["rows_below"]:
                for x in gauss2(b):
                    m.spring(rel(shoe, rod_w(b["base"], y, x), xc, yc, x, y), k_clip, comp=False,
                             tag=("clip_shoe", bid, b["base"], y, x))
        if bid in removed:
            continue
        bk = body(b["kg"] * G_ACC); info["books"][bid] = dict(dofs=bk)
        for x, y in face_pts(b, P):
            if cap is not None:
                m.spring(rel(cap, bk, xc, yc, x, y), k_c / 2, g0=gap("cap", bid, y, x),
                         tag=("cap", bid, b["run"], y, x))
            m.spring(rel(bk, shoe, xc, yc, x, y), k_c / 2, g0=gap("shoe", bid, y, x),
                     tag=("shoe", bid, b["base"], y, x))
    info["rod_w"] = rod_w
    info["face_pts"] = lambda b: face_pts(b, P)
    return m, info


def cap_underside(L, info, u, bid):
    """책 머리 자리에서 덮개 아랫면(plain 이면 막대)의 처짐들 (mm, 위로 +)."""
    b = next(x for x in L["books"] if x["id"] == bid)
    run = next(r for r in L["runs"] if r["id"] == b["run"])
    if info["detail"] == "clip":
        w0, ax, ay = info["caps"][bid]["dofs"]
        return [u[w0] + u[ax] * (y - b["cg_y"]) + u[ay] * (x - b["xc"]) for x, y in info["face_pts"](b)]
    return [u[info["rod_w"](b["run"], y, x)] for y in run["rows"] for x in gauss2(b) if (b["run"], y) in info["rods"]]


def results(m, info, r):
    """해석 결과 요약값."""
    u, f = r["u"], r["f"]
    out = dict(iterations=r["iterations"], indifferent=r.get("indifferent", False))
    floor = sum(fi for s, fi in zip(m.springs, f) if s["tag"] and s["tag"][0] == "floor")
    out["floor_reaction"] = floor
    out["load_total"] = info["loads_total"]
    out["equilibrium_error"] = abs(floor - info["loads_total"]) / info["loads_total"]
    smax, where = 0.0, None
    for tag, Lm, V1, M1, V2, M2 in m.beam_forces(u):
        for Mx in (M1, M2):
            s = abs(Mx) * info["c"] / info["I"]
            if s > smax:
                smax, where = s, tag
    out["sigma_max"], out["sigma_where"] = smax, where
    wmax, wwhere = 0.0, None
    for key, rod in info["rods"].items():
        for x, n in zip(rod["xs"], rod["nodes"]):
            if -u[n[0]] > wmax:
                wmax, wwhere = -u[n[0]], (key, x)
    out["rod_sag_max"], out["rod_sag_where"] = wmax, wwhere
    head = defaultdict(float); lifted = 0; clip_t, clip_where = 0.0, None
    for s, fi, act in zip(m.springs, f, r["active"]):
        tag = s["tag"]
        if tag and tag[0] == "cap":
            head[tag[1]] += fi
        if s["comp"] and not act:
            lifted += 1
        if tag and tag[0].startswith("clip") and -fi > clip_t:
            clip_t, clip_where = -fi, tag
    out["head_force"] = dict(head)
    out["lifted_contacts"] = lifted
    out["clip_tension_max"], out["clip_tension_where"] = clip_t, clip_where
    return out

"""runs 배치(layout.json)를 해석 모델로 바꾼다.

두 가지 이음 상세를 모델링한다.

detail="plain"  막대가 홈에 얹혀 있기만 하다.
  덮개와 받침은 책에 붙은 것으로 보고, 책 머리/발 ↔ 막대 접촉이 압축만 받는다.
  책을 빼면 책·받침·쐐기가 빠지고 덮개는 막대에 걸려 남는다 (무게만 막대에).

detail="clip"   덮개와 받침이 막대에 끼워져(스냅) 막대와 함께 남는다. 책과 쐐기만 빠진다.
  덮개·받침 = 강체 (w, ax, ay). 책과의 접촉은 압축만.
  막대와의 연결: play = 0 이면 양방향으로 꽉 잡는다. play > 0 이면 막대가 홈에 앉아 누를 때는 압축(seat),
  play 보다 더 들릴 때만 걸쇠(latch)가 당긴다. 덮개는 줄의 모든 막대 줄을 가로로 묶어서, 막대 한 줄만 따로
  시소처럼 들리지 못하게 한다. 클립에 걸리는 인장(뽑히는 힘)을 따로 보고한다.

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


def gauss_seg(a, b):
    """선 접촉 [a, b] 의 2점 가우스 위치 (아주 짧으면 가운데 한 점)."""
    if b - a < 0.5:
        return [(a + b) / 2]
    c, h = (a + b) / 2, (b - a) / (2 * math.sqrt(3))
    return [c - h, c + h]


def shoe_segments(b, P):
    """받침이 아래에서 딛는 구간: [(run 또는 None, [x...], rows)]. 계단형 받침이면 여러 개.
    한 구간짜리는 예전과 같이 책 두께의 가우스점 (gauss2) 을 쓴다."""
    sups = b.get("supports")
    if not sups:
        return [(b["base"], gauss2(b), b["rows_below"])]
    if len(sups) == 1:
        s = sups[0]
        return [(s["run"], gauss2(b), s["rows"])]
    lo, hi = b["x0"] + P["side"], b["x1"] - P["side"]
    out = []
    for s in sups:
        a, c = max(s["x0"], lo), min(s["x1"], hi)
        if c - a > 1e-9:
            out.append((s["run"], gauss_seg(a, c), s["rows"]))
    return out


def pier_mass(p):
    """기둥 질량 추정 (kg): 열린 사다리꼴 틀이라 꽉 찬 부피의 절반 × 부품 밀도."""
    h = p["top"] - min(s["base"] for s in p["supports"])
    return (p["x1"] - p["x0"]) * p["depth"] * h * PETG_PART * 0.5


def face_pts(b, P):
    """책 머리·발 면의 접촉점: 두께 방향 가우스 2점 × 깊이 방향 앞뒤 끝에서 10 mm 안쪽."""
    return [(x, y) for y in (P["y0"] + 10.0, P["y0"] + b["w"] - 10.0) for x in gauss2(b)]


def build(L, mat="petg12", removed=(), k_c=5000.0, long_term=True, gaps=None, snap=0.5,
          detail="clip", k_clip=5000.0, play=0.2, ground=1e-12):
    """gaps: callable(kind, book_id, y, x) → 초기 틈 (mm). 없으면 모두 0 (완벽한 맞춤).
    snap: 이 거리(mm) 안의 막대 절점은 하나로 합친다 (아주 짧은 요소가 강성 행렬을 망치지 않게).
    play: 클립의 상하 유격 (mm). 0 이면 클립이 양방향으로 꽉 잡는다. 0 보다 크면 막대가 홈에 앉아 누를 때는
          압축으로 받고, 막대가 그 거리보다 더 들릴 때만 걸쇠가 당긴다.
    ground: 모든 자유도에 거는 아주 약한 접지 스프링, 최대 대각 강성에 대한 비 (해석기 설명 참고)."""
    P = L["params"]
    M = MATS[mat]
    A, I = section(M)
    E = M["E"] / (M["creep"] if long_term else 1.0)
    Gs = M["G"] / (M["creep"] if long_term else 1.0)
    EI, KGA = E * I, M["kappa"] * Gs * A
    removed = set(removed)
    books = {b["id"]: b for b in L["books"]}
    runs = {r["id"]: r for r in L["runs"]}
    piers = {p["id"]: p for p in L.get("piers", [])}
    if piers and detail != "clip":
        raise ValueError("piers are modelled only with the clip detail")
    m = Model()
    m.ground = ground
    info = dict(rods={}, books={}, caps={}, shoes={}, loads_total=0.0, EI=EI, A=A, I=I, c=M["D"] / 2, mat=M,
                detail=detail, vertical=[])
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
            for c in set(r["upper"]):
                if detail == "plain" and c in removed:
                    continue
                for srun, sxs, srows in shoe_segments(books[c], P):
                    if srun == rid and srows and y in srows:
                        xs.update(sxs)
            for pid in r.get("piers", []):
                xs.update(gauss_seg(piers[pid]["x0"], piers[pid]["x1"]))
            for pid in r.get("upper_piers", []):
                for s in piers[pid]["supports"]:
                    if s["run"] == rid:
                        xs.update(gauss_seg(s["x0"], s["x1"]))
            xs = merge_close(sorted(xs), snap)
            assert all(r["x0"] - 1e-9 <= x <= r["x1"] + 1e-9 for x in xs), (rid, y)
            nodes = [m.dofs(2) for _ in xs]
            info["vertical"] += [n[0] for n in nodes]
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
        info["vertical"].append(d[0])
        return d

    def clip(terms, tag):
        """클립. terms 는 d = (막대 쪽이 위) − (아래) 로, 누르면 d < 0."""
        if play <= 0:
            m.spring(terms, k_clip, comp=False, tag=("clip",) + tag)
        else:
            m.spring(terms, k_clip, comp=True, tag=("seat",) + tag)
            m.spring({k: -v for k, v in terms.items()}, k_clip, g0=play, comp=True, tag=("latch",) + tag)

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
                clip(rel(rod_w(b["run"], y, x), cap, xc, yc, x, y), ("cap", bid, b["run"], y, x))
        shoe = body(shoe_kg * G_ACC); info["shoes"][bid] = dict(dofs=shoe)
        for srun, sxs, srows in shoe_segments(b, P):
            if srun is None:
                for y in (P["y0"] + 10.0, P["y0"] + b["w"] - 10.0):
                    for x in sxs:
                        m.spring(rel(shoe, None, xc, yc, x, y), k_c / 2, g0=gap("floor", bid, y, x),
                                 tag=("floor", bid, None, y, x))
            else:
                for y in srows:
                    for x in sxs:
                        clip(rel(shoe, rod_w(srun, y, x), xc, yc, x, y), ("shoe", bid, srun, y, x))
        if bid in removed:
            continue
        bk = body(b["kg"] * G_ACC); info["books"][bid] = dict(dofs=bk)
        for x, y in face_pts(b, P):
            if cap is not None:
                m.spring(rel(cap, bk, xc, yc, x, y), k_c / 2, g0=gap("cap", bid, y, x),
                         tag=("cap", bid, b["run"], y, x))
            m.spring(rel(bk, shoe, xc, yc, x, y), k_c / 2, g0=gap("shoe", bid, y, x),
                     tag=("shoe", bid, b["base"], y, x))
    # ---- 기둥: 빼지 않는다. 위로는 맡은 줄들의 막대에, 아래로는 바닥(압축) 또는 아래 줄 막대(클립)에 물린다 ----
    info["piers"] = {}
    for pid, p in piers.items():
        pb = body(pier_mass(p) * G_ACC); info["piers"][pid] = dict(dofs=pb)
        xc, yc = p["xc"], P["y0"] + p["depth"] / 2
        for rid in p["runs"]:
            for y in runs[rid]["rows"]:
                for x in gauss_seg(p["x0"], p["x1"]):
                    clip(rel(rod_w(rid, y, x), pb, xc, yc, x, y), ("pier_top", pid, rid, y, x))
        for s in p["supports"]:
            if s["run"] is None:
                for y in (P["y0"] + 10.0, P["y0"] + p["depth"] - 10.0):
                    for x in gauss_seg(s["x0"], s["x1"]):
                        m.spring(rel(pb, None, xc, yc, x, y), k_c / 2, g0=gap("floor", pid, y, x),
                                 tag=("floor", pid, None, y, x))
            else:
                for y in runs[s["run"]]["rows"]:
                    if y > P["y0"] + p["depth"] - P["edge"]:
                        continue
                    for x in gauss_seg(s["x0"], s["x1"]):
                        clip(rel(pb, rod_w(s["run"], y, x), xc, yc, x, y), ("pier_base", pid, s["run"], y, x))
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
    ground = float(sum(r["ground_f"][d] for d in info["vertical"]))
    out["floor_reaction"] = floor
    out["ground_share"] = abs(ground) / info["loads_total"]   # 접지 스프링이 받은 몫: 무시할 만해야 한다
    out["load_total"] = info["loads_total"]
    out["equilibrium_error"] = abs(floor + ground - info["loads_total"]) / info["loads_total"]
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
        pull = -fi if (tag and tag[0] == "clip") else (fi if (tag and tag[0] == "latch") else 0.0)
        if pull > clip_t:
            clip_t, clip_where = pull, tag
    out["head_force"] = dict(head)
    out["lifted_contacts"] = lifted
    out["clip_tension_max"], out["clip_tension_where"] = clip_t, clip_where
    return out

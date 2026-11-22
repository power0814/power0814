"""모델 빌더 검증: 손으로 풀 수 있는 작은 배치로 끝까지 확인한다. 실행: python3 structure/test_model.py

배치: 바닥에 책 셋 [얇은 n1][가운데 m][얇은 n2], 그 위 가운데에 책 u 하나.
- n1, n2 는 두께를 거의 0 으로 해 막대에 핀 받침처럼 작용하게 하고, 접촉 강성을 아주 크게 둔다.
- m 을 빼면 막대 두 줄(y=15, 95)이 n1–n2 사이 단순보가 되어 u 를 받는다.
  줄별 하중 = 지레 법칙, 줄마다 u 의 두 가우스점에 P 씩 → 하중점 처짐 = P a² (3L − 4a) / 6EI + P a / κGA.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import model as MD  # noqa: E402
from solver import Unstable  # noqa: E402

PARAMS = dict(y0=5.0, rows=[15.0, 95.0, 175.0, 255.0], edge=10.0, side=2.0, s_min=14.0, cap_t=10.0, rod_r=6.0)


def close(a, b, rel=1e-6, what=""):
    if abs(a - b) > rel * abs(b):
        raise AssertionError(f"{what}: got {a!r}, expected {b!r}")


def book(id_, x0, t, w, kg, run, base=None, rows_below=None):
    return dict(id=id_, t=t, w=w, h=200.0, kg=kg, x0=x0, x1=x0 + t + 4, xc=x0 + (t + 4) / 2,
                cg_y=5.0 + w / 2, run=run, base=base, rows_below=rows_below, shoe=20.0)


def layout(tm=92.0, tu=40.0, wu=120.0, kg_u=2.0):
    n1 = book("n1", 0.0, 1e-9, 120.0, 1.0, "R0")
    m_ = book("m", n1["x1"], tm, 120.0, 1.0, "R0")
    n2 = book("n2", m_["x1"], 1e-9, 120.0, 1.0, "R0")
    xc = (n1["xc"] + n2["xc"]) / 2
    u = book("u", xc - (tu + 4) / 2, tu, wu, kg_u, "R1", base="R0", rows_below=[15.0, 95.0])
    runs = [dict(id="R0", rows=[15.0, 95.0], x0=n1["xc"], x1=n2["xc"], cells=["n1", "m", "n2"], upper=["u"]),
            dict(id="R1", rows=[15.0, 95.0], x0=u["x0"], x1=u["x1"], cells=["u"], upper=[])]
    return dict(params=PARAMS, books=[n1, m_, n2, u], runs=runs)


def setup():
    # 막대 자중은 실제 값(PETG)으로 둔다. 하중이 0 인 부재는 무차별 평형이 되어 해가 하나로 정해지지 않는다.
    MD.MATS["test"] = dict(MD.MATS["petg12"], creep=1.0)
    MD.PETG_PART = 0.0


def pin_thin(m, info):
    """두께가 0 인 책은 두 접촉점이 겹쳐 y축 회전(ay)이 정해지지 않는다. 접촉점 간격이 1e-9 mm 라 이 회전은 막대와 사실상 따로 논다. 1e3 N·mm/rad 스프링으로 잡아도 결과에 영향이 없다."""
    for bid in ("n1", "n2"):
        for part in ("books", "caps", "shoes"):
            if bid in info[part]:
                m.spring({info[part][bid]["dofs"][2]: 1.0}, 1e3, comp=False)


def t_bridge_matches_hand_calc():
    for detail in ("plain", "clip"):
        bridge(detail)


def bridge(detail):
    """clip 이어도 u 가 가운데에 있으면 각 막대 줄이 좌우 대칭으로 처져 받침(강체)의 비틀림 구속이 생기지 않는다.
    그래서 같은 손계산이 맞아야 한다."""
    setup()
    L = layout()
    m, info = MD.build(L, "test", removed={"m"}, k_c=1e9, k_clip=1e9, detail=detail, ground=0.0)
    pin_thin(m, info)
    r = m.solve()
    M = MD.MATS["test"]; A, I = MD.section(M)
    EI, KGA = M["E"] * I, M["kappa"] * M["G"] * A
    u = next(b for b in L["books"] if b["id"] == "u")
    sup = [L["books"][0]["xc"], L["books"][2]["xc"]]
    span = sup[1] - sup[0]
    a = (u["xc"] - u["t"] / (2 * math.sqrt(3))) - sup[0]
    q = M["rho"] * A * MD.G_ACC                       # 막대 자중 (N/mm)
    top = next(r for r in L["runs"] if r["id"] == "R1")
    Wu = u["kg"] * MD.G_ACC
    Wtop = q * (top["x1"] - top["x0"])                 # u 머리에 얹힌 꼭대기 막대 한 줄의 자중 (그 줄 바로 아래로 간다)
    for y in (15.0, 95.0):
        other = 95.0 if y == 15.0 else 15.0
        Wrow = Wu * abs(other - u["cg_y"]) / 80.0 + Wtop   # 책 무게는 지레 법칙, 막대 자중은 같은 줄로
        P = Wrow / 2
        exp = P * a * a * (3 * span - 4 * a) / (6 * EI) + P * a / KGA
        # 자중 등분포 q 에 의한 x = a 의 처짐 (휨 + 전단)
        exp += q * a * (span ** 3 - 2 * span * a * a + a ** 3) / (24 * EI) + q * a * (span - a) / (2 * KGA)
        x_load = u["xc"] - u["t"] / (2 * math.sqrt(3))
        w_load = r["u"][info["rod_w"]("R0", y, x_load)]
        w_sup = r["u"][info["rod_w"]("R0", y, sup[0])]
        close(-(w_load - w_sup), exp, rel=1e-5, what=f"{detail} row {y} bridge deflection")
    res = MD.results(m, info, r)
    # 1e9 N/mm 스프링이 섞이면 반올림 오차가 1e-16 × 1e9 / 하중 정도로 커진다
    assert res["equilibrium_error"] < 1e-8, res["equilibrium_error"]


def t_full_support_takes_load_directly():
    """m 이 있으면 u 의 하중은 거의 다 m 으로 곧장 내려간다 (n1, n2 는 거의 안 받는다)."""
    for detail in ("plain", "clip"):
        full_support(detail)


def full_support(detail):
    setup()
    L = layout()
    m, info = MD.build(L, "test", k_c=1e6, detail=detail, ground=0.0)
    pin_thin(m, info)
    r = m.solve(); res = MD.results(m, info, r)
    M = MD.MATS["test"]; A, _ = MD.section(M); q = M["rho"] * A * MD.G_ACC
    rods = 2 * q * sum(rr["x1"] - rr["x0"] for rr in L["runs"])      # 막대 전부의 자중
    W = 2.0 * MD.G_ACC
    head = res["head_force"]
    # u 의 무게와 막대 자중을 합한 것이 m, n1, n2 머리로 나뉜다 (평형)
    close(head["m"] + head["n1"] + head["n2"], W + rods, rel=1e-9, what="vertical equilibrium of caps")
    # 이웃 둘이 받는 몫은 막대 자중 정도뿐: u 의 무게는 사실상 모두 m 으로 곧장 내려간다
    assert head["n1"] + head["n2"] < rods + 0.01 * W, (head, rods)
    assert res["equilibrium_error"] < 1e-9


def t_unsupported_detected():
    """양쪽 이웃까지 빼면 막대가 받칠 곳이 없다 → 불안정."""
    for detail in ("plain", "clip"):
        setup()
        L = layout()
        m, info = MD.build(L, "test", removed={"m", "n1", "n2"}, k_c=1e6, detail=detail)
        pin_thin(m, info)
        try:
            m.solve()
        except Unstable:
            continue
        raise AssertionError(f"{detail}: missing support not detected")


def t_ground_springs_negligible():
    """접지 스프링(해석기의 수치 장치)을 기본값으로 켜도 결과가 1e-4 안에서 같고, 받는 몫이 1e-6 미만이다."""
    setup()
    L = layout()
    out = []
    for g in (0.0, 1e-12):
        m, info = MD.build(L, "test", removed={"m"}, k_c=1e6, k_clip=1e6, ground=g)
        pin_thin(m, info)
        r = m.solve(); res = MD.results(m, info, r)
        assert res["equilibrium_error"] < 1e-9, res["equilibrium_error"]
        out.append((res["rod_sag_max"], res["sigma_max"], res["ground_share"]))
    close(out[1][0], out[0][0], rel=1e-4, what="sag with ground springs")
    close(out[1][1], out[0][1], rel=1e-4, what="stress with ground springs")
    assert out[1][2] < 1e-6, out[1][2]


def t_stepped_shoe_splits_by_symmetry():
    """계단형 받침: 두 줄 A, B 의 경계에 책 u 가 대칭으로 걸치면 A 와 B 막대가 u 의 무게를 반씩 받는다.
    양 끝에는 기둥을 두어 그 경로도 함께 지나간다."""
    setup()
    side = 2.0

    def bk(i, x0, run):
        t = 76.0 / 3 - 2 * side          # 세 칸이 기둥 사이 76 mm 에 꼭 맞게 (14–90, 104–180): 97 에 대해 대칭
        return dict(id=i, t=t, w=120.0, h=200.0, kg=1.0, x0=x0, x1=x0 + t + 2 * side, xc=x0 + (t + 2 * side) / 2,
                    cg_y=5.0 + 60.0, run=run, base=None, rows_below=None, shoe=20.0,
                    supports=[dict(run=None, x0=x0, x1=x0 + t + 2 * side, base=0.0, shoe=20.0, rows=None)])
    A = [bk(f"a{k}", 14.0 + 76.0 / 3 * k, "A") for k in range(3)]
    Bb = [bk(f"b{k}", 104.0 + 76.0 / 3 * k, "B") for k in range(3)]
    u = dict(id="u", t=26.0, w=120.0, h=200.0, kg=2.0, x0=89.0 - 15.0 + 15.0, x1=0, xc=0, cg_y=65.0, run="U",
             base="A", rows_below=[15.0, 95.0], shoe=20.0)
    u["x0"] = 104.0 - 15.0 - 7.0          # 기둥(90–104)의 가운데 97 에 대해 대칭
    u["x1"] = u["x0"] + 30.0; u["xc"] = (u["x0"] + u["x1"]) / 2
    assert abs(u["xc"] - 97.0) < 1e-9
    u["supports"] = [dict(run="A", x0=u["x0"], x1=97.0, base=230.0, shoe=20.0, rows=[15.0, 95.0]),
                     dict(run="B", x0=97.0, x1=u["x1"], base=230.0, shoe=20.0, rows=[15.0, 95.0])]
    piers = [dict(id="P0", x0=0.0, x1=14.0, xc=7.0, runs=["A"], top=230.0, rows=[15.0, 95.0], depth=110.0,
                  supports=[dict(run=None, x0=0.0, x1=14.0, base=0.0)]),
             dict(id="P1", x0=90.0, x1=104.0, xc=97.0, runs=["A", "B"], top=230.0, rows=[15.0, 95.0], depth=110.0,
                  supports=[dict(run=None, x0=90.0, x1=104.0, base=0.0)]),
             dict(id="P2", x0=180.0, x1=194.0, xc=187.0, runs=["B"], top=230.0, rows=[15.0, 95.0], depth=110.0,
                  supports=[dict(run=None, x0=180.0, x1=194.0, base=0.0)])]
    runs = [dict(id="A", rows=[15.0, 95.0], x0=0.0, x1=104.0, cells=[b["id"] for b in A], upper=["u"],
                 piers=["P0", "P1"], upper_piers=[]),
            dict(id="B", rows=[15.0, 95.0], x0=90.0, x1=194.0, cells=[b["id"] for b in Bb], upper=["u"],
                 piers=["P1", "P2"], upper_piers=[]),
            dict(id="U", rows=[], x0=u["x0"], x1=u["x1"], cells=["u"], upper=[], piers=[], upper_piers=[])]
    L = dict(params=dict(PARAMS, side=side), books=A + Bb + [u], runs=runs, piers=piers)
    MD_pm = MD.pier_mass
    MD.pier_mass = lambda p: 0.0
    try:
        # 이 시험은 받침·덮개·기둥 질량을 0 으로 둔다. 무게가 없는 부재는 클립 유격(0.2 mm) 안에서 떠서 해가 하나로
        # 정해지지 않으므로 접지 스프링(기본값)을 켠다. 좌우 대칭이라 반씩 나뉘는 결과에는 영향이 없다.
        m, info = MD.build(L, "test", k_c=1e6, k_clip=1e6)
        r = m.solve(); res = MD.results(m, info, r)
    finally:
        MD.pier_mass = MD_pm
    assert res["equilibrium_error"] < 1e-9, res["equilibrium_error"]
    on = {"A": 0.0, "B": 0.0}
    for s, f in zip(m.springs, r["f"]):
        tag = s["tag"]
        if tag and tag[0] in ("seat", "latch") and tag[1] == "shoe" and tag[2] == "u":
            on[tag[3]] += f if tag[0] == "seat" else -f
    W = 2.0 * MD.G_ACC
    close(on["A"], W / 2, rel=1e-6, what="stepped shoe share on A")
    close(on["B"], W / 2, rel=1e-6, what="stepped shoe share on B")


TESTS = [t_stepped_shoe_splits_by_symmetry, t_ground_springs_negligible, t_bridge_matches_hand_calc, t_full_support_takes_load_directly, t_unsupported_detected]

if __name__ == "__main__":
    bad = 0
    for t in TESTS:
        try:
            t(); print(f"ok    {t.__name__}")
        except Exception as e:  # noqa: BLE001
            bad += 1; print(f"FAIL  {t.__name__}: {type(e).__name__} {e}")
    print(f"{len(TESTS) - bad}/{len(TESTS)} passed")
    sys.exit(1 if bad else 0)

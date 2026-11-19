"""해석기 검증: 교과서 해와 비교한다. 실행: python3 structure/test_solver.py"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from solver import Model, Unstable  # noqa: E402

E, D = 2000.0, 12.0
I = math.pi * D ** 4 / 64
A = math.pi * D * D / 4
G = E / (2 * 1.38)
KGA = 0.9 * G * A
EI = E * I
STIFF = 1e9


def close(a, b, rel=1e-6, ab=1e-9, what=""):
    if abs(a - b) > max(ab, rel * abs(b)):
        raise AssertionError(f"{what}: got {a!r}, expected {b!r}")


def beam_line(m, xs, EI=EI, GAs=None):
    """xs 위치에 절점을 두고 보를 잇는다. 절점마다 (w, θ)."""
    nodes = [m.dofs(2) for _ in xs]
    for (a, b), (x0, x1) in zip(zip(nodes, nodes[1:]), zip(xs, xs[1:])):
        m.beam(a[0], a[1], b[0], b[1], x1 - x0, EI, GAs)
    return nodes


def t_cantilever():
    for gas in (None, KGA):
        L, P = 300.0, 10.0
        m = Model(); n = beam_line(m, [0, 100, 170, 300], GAs=gas)
        m.fix(n[0][0]); m.fix(n[0][1]); m.load(n[-1][0], -P)
        r = m.solve(); u = r['u']
        shear = 0 if gas is None else P * L / gas
        close(u[n[-1][0]], -(P * L ** 3 / (3 * EI) + shear), what="cantilever tip w")
        close(u[n[-1][1]], -P * L ** 2 / (2 * EI), what="cantilever tip θ")
        tag, Le, V1, M1, V2, M2 = m.beam_forces(u)[0]
        close(abs(M1), P * L, what="root moment")


def t_simply_supported_contacts():
    L, P = 200.0, 7.0
    m = Model(); n = beam_line(m, [0, 50, 100, 200])
    for k in (0, 3):
        m.spring({n[k][0]: 1.0}, STIFF)  # 받침: 보가 아래로 내려가면 압축
    m.load(n[2][0], -P)
    r = m.solve()
    close(r['u'][n[2][0]], -P * L ** 3 / (48 * EI), rel=1e-5, what="SS midspan")
    close(r['f'].sum(), P, what="reaction sum")
    close(r['f'][0], P / 2, what="reaction A")


def t_two_span():
    L, P = 150.0, 9.0
    xs = [0, L / 2, L, 1.5 * L, 2 * L]
    # 양방향 받침: 교과서 해 R_A=13/32P, R_B=11/16P, R_C=-3/32P
    m = Model(); n = beam_line(m, xs)
    for k in (0, 2, 4):
        m.spring({n[k][0]: 1.0}, STIFF, comp=False)
    m.load(n[1][0], -P)
    f = m.solve()['f']
    close(f[0], 13 / 32 * P, rel=1e-5, what="R_A bilateral")
    close(f[1], 22 / 32 * P, rel=1e-5, what="R_B bilateral")
    close(f[2], -3 / 32 * P, rel=1e-5, what="R_C bilateral")
    # 압축 전용: C 가 들리고 단순보 + 내민보가 된다. C 의 들림 = θ_B·L = PL³/16EI
    m = Model(); n = beam_line(m, xs)
    for k in (0, 2, 4):
        m.spring({n[k][0]: 1.0}, STIFF)
    m.load(n[1][0], -P)
    r = m.solve()
    close(r['f'][2], 0.0, ab=1e-9, what="R_C compression-only")
    close(r['f'][0], P / 2, rel=1e-5, what="R_A compression-only")
    close(r['u'][n[4][0]], P * L ** 3 / (16 * EI), rel=1e-4, what="uplift at C")


def t_gap():
    L, P, g0 = 300.0, 20.0, 0.5
    xs = [0, L / 2, L]
    d0 = P * L ** 3 / (48 * EI)
    assert d0 > g0
    m = Model(); n = beam_line(m, xs)
    m.spring({n[0][0]: 1.0}, STIFF); m.spring({n[2][0]: 1.0}, STIFF)
    m.spring({n[1][0]: 1.0}, STIFF, g0=g0)
    m.load(n[1][0], -P)
    r = m.solve()
    close(r['f'][2], (d0 - g0) * 48 * EI / L ** 3, rel=1e-4, what="gap contact force")
    close(r['u'][n[1][0]], -g0, rel=1e-4, what="gap closes to g0")
    # 틈이 처짐보다 크면 힘 0
    m = Model(); n = beam_line(m, xs)
    m.spring({n[0][0]: 1.0}, STIFF); m.spring({n[2][0]: 1.0}, STIFF)
    m.spring({n[1][0]: 1.0}, STIFF, g0=d0 * 1.5)
    m.load(n[1][0], -P)
    r = m.solve()
    close(r['f'][2], 0.0, what="open gap")
    close(r['u'][n[1][0]], -d0, rel=1e-5, what="free midspan")


def rigid_on_ground(m, xc, yc, pts, k=STIFF):
    w0, ax, ay = m.dofs(3)
    for (x, y) in pts:
        m.spring({w0: 1.0, ax: y - yc, ay: x - xc}, k)
    return w0, ax, ay


def t_rigid_lever():
    W, y1, y2, yc = 30.0, 15.0, 95.0, 50.0
    m = Model()
    w0, ax, ay = rigid_on_ground(m, 0, yc, [(-5, y1), (5, y1), (-5, y2), (5, y2)])
    m.load(w0, -W)
    f = m.solve()['f']
    close(f[0] + f[1], W * (y2 - yc) / (y2 - y1), rel=1e-6, what="lever front")
    close(f[2] + f[3], W * (yc - y1) / (y2 - y1), rel=1e-6, what="lever back")
    # 무게중심이 받침 밖이면 메커니즘
    m = Model()
    w0, ax, ay = rigid_on_ground(m, 0, 120.0, [(-5, y1), (5, y1), (-5, y2), (5, y2)])
    m.load(w0, -W)
    try:
        m.solve()
    except Unstable:
        pass
    else:
        raise AssertionError("tipping block not detected")


def t_block_on_beams():
    """강체 하나가 단순보 두 개 (y=15, y=95) 의 가운데에 얹힘. 지레 법칙대로 나뉘고 처짐 = R L³/48EI."""
    L, W, yc = 240.0, 40.0, 35.0
    m = Model()
    mids = []
    for y in (15.0, 95.0):
        n = beam_line(m, [0, L / 2 - 4, L / 2 + 4, L])
        m.spring({n[0][0]: 1.0}, STIFF); m.spring({n[3][0]: 1.0}, STIFF)
        mids.append((y, n))
    w0, ax, ay = m.dofs(3)
    for y, n in mids:
        for j, x in ((1, -4.0), (2, 4.0)):  # 블록 바닥 - 보: d = w_block - w_beam
            m.spring({w0: 1.0, ax: y - yc, ay: x, n[j][0]: -1.0}, STIFF)
    m.load(w0, -W)
    r = m.solve()
    share = {15.0: W * (95 - yc) / 80, 95.0: W * (yc - 15) / 80}
    for i, (y, n) in enumerate(mids):
        f_end = r['f'][2 * i] + r['f'][2 * i + 1]
        close(f_end, share[y], rel=1e-5, what=f"beam {y} reaction")
    # 두 하중점 (±4) 각 R/2 인 단순보의 중앙 처짐: 2 * (R/2) b (3L² − 4b²) / 48EI, b = L/2 − 4
    b = L / 2 - 4
    for y, n in mids:
        R = share[y]
        exp = 2 * (R / 2) * b * (3 * L * L - 4 * b * b) / (48 * EI)
        mid = (r['u'][n[1][0]] + r['u'][n[2][0]]) / 2
        close(mid, -exp, rel=2e-3, what=f"beam {y} deflection under block")


def t_mesh_invariance():
    P = 5.0
    out = []
    for xs in ([0, 60, 200], [0, 20, 40, 60, 90, 140, 200]):
        m = Model(); n = beam_line(m, xs, GAs=KGA)
        m.spring({n[0][0]: 1.0}, STIFF); m.spring({n[-1][0]: 1.0}, STIFF)
        j = xs.index(60); m.load(n[j][0], -P)
        out.append(m.solve()['u'][n[j][0]])
    close(out[0], out[1], rel=1e-9, what="mesh invariance")


def t_uniform_load_consistent():
    """단순보 등분포: 일관 절점 하중이면 절점 처짐이 정확하다. 중앙 = 5qL⁴/384EI (+ 전단 qL²/8κGA)."""
    L, q = 240.0, 0.05
    for gas in (None, KGA):
        xs = [0, 37, 120, 190, 240]
        m = Model(); n = beam_line(m, xs, GAs=gas)
        m.spring({n[0][0]: 1.0}, STIFF, comp=False); m.spring({n[-1][0]: 1.0}, STIFF, comp=False)
        for (a, b), (x0, x1) in zip(zip(n, n[1:]), zip(xs, xs[1:])):
            Le = x1 - x0
            m.load(a[0], -q * Le / 2); m.load(b[0], -q * Le / 2)
            m.load(a[1], -q * Le * Le / 12); m.load(b[1], q * Le * Le / 12)
        u = m.solve()['u']
        shear = 0 if gas is None else q * L * L / (8 * gas)
        close(u[n[2][0]], -(5 * q * L ** 4 / (384 * EI) + shear), rel=1e-5, what="uniform load midspan")


def t_neutral_diagonal():
    """강체가 대각선 두 모서리에만 닿고(다른 둘은 틈 0.5 mm) 무게중심이 그 대각선 위: 무차별 평형.
    해로 받아들이되 표시하고, 반력은 W/2 씩이어야 한다."""
    W = 20.0
    m = Model()
    w0, ax, ay = m.dofs(3)
    pts = [(-20, -60, 0.0), (20, 60, 0.0), (-20, 60, 0.5), (20, -60, 0.5)]
    for x, y, g in pts:
        m.spring({w0: 1.0, ax: y, ay: x}, 1e4, g0=g)
    m.load(w0, -W)
    r = m.solve()
    assert r["indifferent"], "neutral equilibrium not flagged"
    close(r["f"][0], W / 2, rel=1e-6, what="diagonal reaction 1")
    close(r["f"][1], W / 2, rel=1e-6, what="diagonal reaction 2")
    close(r["f"][2] + r["f"][3], 0.0, ab=1e-9, what="open corners")


TESTS = [t_neutral_diagonal, t_uniform_load_consistent, t_cantilever, t_simply_supported_contacts, t_two_span, t_gap, t_rigid_lever,
         t_block_on_beams, t_mesh_invariance]

if __name__ == '__main__':
    bad = 0
    for t in TESTS:
        try:
            t(); print(f"ok    {t.__name__}")
        except Exception as e:  # noqa: BLE001
            bad += 1; print(f"FAIL  {t.__name__}: {e}")
    print(f"{len(TESTS) - bad}/{len(TESTS)} passed")
    sys.exit(1 if bad else 0)

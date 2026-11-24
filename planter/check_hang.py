"""팔 하나가 코어에 걸려 버티는지 손계산 (2D, 팔 축을 지나는 세로 단면).

팔에 작용하는 힘
- 무게: 팔 자체 (슬라이서 무게, 무게중심은 STL 에서) + 흙 화분 (창 가운데)
- 갈고리: 걸이 턱 45° 경사면에서. 법선 방향 (코어 쪽 + 위), 경사면 따라 마찰
- 발꿈치: 받침 링 세로면에서. 법선 방향 (코어 밖), 세로 마찰

45° 경사면은 마찰이 없으면 가로 힘을 세로 힘만큼만 낼 수 있다. 팔이 길어 처지려는 모멘트가 크면
갈고리가 경사면을 타고 올라가려 하고, 그걸 막는 몫은 마찰이 진다. 버티는 데 필요한 최소 마찰계수를 구한다.

python3 planter/check_hang.py
"""
import numpy as np
import trimesh
from scipy.optimize import linprog
from pathlib import Path

HERE = Path(__file__).parent
g = 9.81

# cross_floor.scad 치수
Rc, cl_out, cl_z, gapc, reach = 45, 7, 56, 0.6, 320
k = Rc + cl_out - cl_z                     # 턱 경사면 z = r − k
xt = Rc + 1.2                              # 갈고리 끝
hook_pt = np.array([(xt + Rc + cl_out) / 2, (xt + Rc + cl_out) / 2 - k])   # 경사면 접촉 구간 가운데
hook_n = np.array([-1.0, 1.0]) / np.sqrt(2)  # 턱이 팔을 미는 방향
hook_t = np.array([1.0, 1.0]) / np.sqrt(2)   # 경사면 방향 (마찰)
heel_x = Rc + cl_out
heel_z = (-68, -54)

# 팔 자체: 무게는 슬라이서 값, 무게중심은 STL (출력 방향: 높이 = reach − x)
arm_g = 279
arm = trimesh.load(HERE / "stl/cross_arm.stl")
arm_x = reach - arm.center_mass[2]

def need_mu(loads, heel_zc):
    """loads: [(N, x)] 아래로. 버티는 데 필요한 최소 마찰계수와 그때 힘."""
    heel_pt = np.array([heel_x, heel_zc])
    W = sum(f for f, _ in loads)
    Mw = sum(-f * (x - heel_pt[0]) for f, x in loads)          # 발꿈치 점에 대한 모멘트 (반시계 +)
    def arm_of(p, d):                                         # 점 p 에 방향 d 단위 힘의 모멘트
        r = p - heel_pt
        return r[0] * d[1] - r[1] * d[0]
    # 미지수: N1, F1, N2, F2 (F 는 ± 가능)
    A_eq = np.array([
        [hook_n[0], hook_t[0], 1, 0],
        [hook_n[1], hook_t[1], 0, 1],
        [arm_of(hook_pt, hook_n), arm_of(hook_pt, hook_t), 0, 0],
    ])
    b_eq = np.array([0, W, -Mw])
    def feasible(mu):
        A_ub = np.array([[-mu, 1, 0, 0], [-mu, -1, 0, 0], [0, 0, -mu, 1], [0, 0, -mu, -1]])
        r = linprog(np.zeros(4), A_ub=A_ub, b_ub=np.zeros(4), A_eq=A_eq, b_eq=b_eq,
                    bounds=[(0, None), (None, None), (0, None), (None, None)])
        return r.status == 0, r.x
    lo, hi = 0.0, 2.0
    for _ in range(50):
        mid = (lo + hi) / 2
        ok, _ = feasible(mid)
        lo, hi = (lo, mid) if ok else (mid, hi)
    ok, x = feasible(hi)
    return hi, x, W

print(f"팔 {arm_g} g, 무게중심 x = {arm_x:.0f} mm (코어 축에서)")
print(f"갈고리 접촉 ({hook_pt[0]:.1f}, {hook_pt[1]:.1f}), 발꿈치 x = {heel_x}, z = {heel_z}")
cases = {
    "빈 팔": [(arm_g / 1000 * g, arm_x)],
    "흙 화분 1.5 kg (창 가운데)": [(arm_g / 1000 * g, arm_x), (1.5 * g, 215)],
    "흙 화분 2.5 kg (창 가운데)": [(arm_g / 1000 * g, arm_x), (2.5 * g, 215)],
    "흙 2.5 kg 을 바깥 끝에": [(arm_g / 1000 * g, arm_x), (2.5 * g, 290)],
}
for name, loads in cases.items():
    for hz in heel_z:
        mu, x, W = need_mu(loads, hz)
        N1, F1, N2, F2 = x
        print(f"{name:24s} 발꿈치 z={hz:4d}: 필요 마찰계수 {mu:.3f} | 무게 {W:5.1f} N, "
              f"갈고리 법선 {N1:5.1f} N, 발꿈치 {N2:5.1f} N")

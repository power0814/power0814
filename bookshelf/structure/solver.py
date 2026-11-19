"""연직 하중용 작은 구조 해석기.

- 보: 2D 티모셴코 보 요소 (자유도: 처짐 w, 회전 θ = dw/dx). x 방향 막대에 쓴다.
- 강체: 책. 자유도 (w0, ax, ay). 점 (x, y)의 처짐 = w0 + ax·(y − yc) + ay·(x − xc).
- 접촉 스프링: 압축만 받는다 (떨어지면 힘 0). 초기 틈 g0을 줄 수 있다.
- 고정 자유도, 절점 하중.

부호: z 위쪽이 +. 하중은 아래로 음수.
접촉 스프링은 상대 변위 d = c·u 로 정의하고, 파고듦 p = −d − g0 > 0 일 때 힘 f = k·p (압축) 가 생긴다.
평형식: (K_보 + Σ_활성 k c cᵀ) u = F − Σ_활성 k g0 c
"""
from __future__ import annotations

import numpy as np


class Unstable(Exception):
    """활성 접촉만으로는 평형을 이룰 수 없음 (메커니즘)."""


class Model:
    def __init__(self):
        self.n = 0
        self.beams = []      # (dofs[4], L, EI, phi, tag)
        self.springs = []    # dict(terms, k, g0, comp, tag)
        self.F = []          # 절점 하중 (리스트로 쌓고 해석 때 배열로)
        self.fixed = set()

    # ---- 구성 ----
    def dofs(self, k: int) -> list[int]:
        out = list(range(self.n, self.n + k))
        self.n += k
        self.F.extend([0.0] * k)
        return out

    def beam(self, w1, t1, w2, t2, L, EI, GAs=None, tag=None):
        """GAs = κGA (전단 강성). None 이면 오일러-베르누이."""
        if L <= 0:
            raise ValueError(f"beam length {L}")
        phi = 0.0 if GAs is None else 12 * EI / (GAs * L * L)
        self.beams.append(([w1, t1, w2, t2], L, EI, phi, tag))

    def spring(self, terms: dict, k: float, g0: float = 0.0, comp: bool = True, tag=None):
        """terms: {dof: 계수}. d = Σ c_i u_i. comp=True 면 압축만."""
        self.springs.append(dict(terms=dict(terms), k=float(k), g0=float(g0), comp=comp, tag=tag))

    def load(self, dof, f):
        self.F[dof] += f

    def fix(self, dof):
        self.fixed.add(dof)

    # ---- 요소 ----
    @staticmethod
    def k_beam(L, EI, phi):
        c = EI / ((1 + phi) * L ** 3)
        return c * np.array([
            [12, 6 * L, -12, 6 * L],
            [6 * L, (4 + phi) * L * L, -6 * L, (2 - phi) * L * L],
            [-12, -6 * L, 12, -6 * L],
            [6 * L, (2 - phi) * L * L, -6 * L, (4 + phi) * L * L],
        ])

    # ---- 해석 ----
    def _base(self):
        K = np.zeros((self.n, self.n))
        for d, L, EI, phi, _ in self.beams:
            K[np.ix_(d, d)] += self.k_beam(L, EI, phi)
        return K

    def solve(self, max_iter=500):
        """압축 전용 접촉 문제를 에너지 최소화로 푼다.

        전체 퍼텐셜 에너지
            Π(u) = ½ uᵀK u − Fᵀu + Σ ½ k φ(p)²,  p = −c·u − g0,  φ = max(p, 0) (압축 전용) 또는 p (양방향)
        는 볼록하고 한 번 미분 가능한 조각별 2차식이다. 그 최솟점이 평형이며, 압축 전용 조건(인장 없음, 떨어진 곳은
        파고들지 않음)을 저절로 만족한다. 감쇠 뉴턴법 + 아르미호 선 탐색으로 최솟점을 찾는다.

        받침이 모자라면 (메커니즘에 하중이 걸리면) Π 가 아래로 끝없이 내려가 변위가 발산한다 → Unstable.
        """
        K0 = self._base()
        F = np.array(self.F, float)
        free = np.array([i for i in range(self.n) if i not in self.fixed], int)
        ns = len(self.springs)
        B = np.zeros((ns, self.n))
        for i, s in enumerate(self.springs):
            for d, c in s['terms'].items():
                B[i, d] += c
        g0 = np.array([s['g0'] for s in self.springs]) if ns else np.zeros(0)
        kk = np.array([s['k'] for s in self.springs]) if ns else np.zeros(0)
        comp = np.array([s['comp'] for s in self.springs], bool) if ns else np.zeros(0, bool)

        def parts(u):
            p = -(B @ u) - g0
            phi = np.where(comp, np.maximum(p, 0.0), p)
            return p, phi

        def energy(u):
            _, phi = parts(u)
            return 0.5 * u @ (K0 @ u) - F @ u + 0.5 * np.sum(kk * phi * phi)

        u = np.zeros(self.n)
        prev_act, prev_exact, last_t, inexact_run = None, False, 0.0, 0
        Ehist, flat = [], False
        scaleF = np.abs(F).max() + 1e-30
        for it in range(max_iter):
            p, phi = parts(u)
            grad = K0 @ u - F - B.T @ (kk * phi)
            # 무차별 평형: 강체가 대각선 두 점에만 닿고 무게중심이 그 대각선 위에 있으면 그 축 회전은 에너지 0 이다.
            # 그 방향으로 움직여도 접촉 길이·막대 변형이 그대로라 힘과 응력은 같다. 에너지가 더 줄지 않고 잔차가
            # 충분히 작으면 해로 받아들이고 표시한다.
            Ehist.append(energy(u))
            if len(Ehist) > 20 and not prev_exact:
                dE = Ehist[-21] - Ehist[-1]
                act_now = np.where(comp, p >= 0.0, True)
                Hd0 = np.abs(np.diag(K0 + B.T @ (B * (kk * act_now)[:, None]))[free]).max()
                if dE <= 1e-12 * abs(Ehist[-1]) and \
                        np.abs(grad[free]).max() <= 1e-8 * (Hd0 * np.abs(u).max() + scaleF):
                    flat = True
                    break
            # 에너지의 조각 경계(p = 0)와 똑같이 나눠야 아래 종료 판정이 정확하다. 하중이 전혀 없는 부재가 힘 0 으로
            # 얹혀 있으면 무차별 평형이라 여기서 끝나지 않는다 (실제 모델은 모든 부재에 자중이 있다).
            act = np.where(comp, p >= 0.0, True)
            # 끝: 바로 앞 걸음이 정칙 행렬로 푼 온전한 뉴턴 걸음이었고 접촉 상태가 그대로면,
            # 지금 점은 그 2차 조각의 정확한 최솟점이다 (조각별 2차 함수의 유한 종료).
            if prev_exact and last_t == 1.0 and np.array_equal(act, prev_act):
                break
            # 첫 걸음은 모든 접촉이 닿았다고 보고 방향을 잡는다 (초기 틈이 있으면 u = 0 에서 모두 떨어져 있어
            # 부재가 허공에 뜬 채로 시작하기 때문). 방향만 정할 뿐, 해의 정확성은 선 탐색과 종료 판정이 보장한다.
            Hact = np.ones_like(act) if it == 0 else act
            H = K0 + B.T @ (B * (kk * Hact)[:, None])
            gf, Hf = grad[free], H[np.ix_(free, free)]
            try:
                Lc = np.linalg.cholesky(Hf)
                if (np.diag(Lc) ** 2).min() < 1e-14 * np.diag(Hf).max():
                    raise np.linalg.LinAlgError
                step = np.linalg.solve(Hf, -gf); exact = True
            except np.linalg.LinAlgError:
                # 받침이 모자란 부재가 있다: 떨어진 접촉의 강성을 1e-3 배로 살짝 넣어 '곧 닿을 곳' 쪽으로 걸음을 잡는다.
                # (단위 행렬로 정칙화하면 방향이 물리적으로 엉뚱해져 선 탐색이 아주 작은 걸음만 받아들인다.)
                Hr = H + B.T @ (B * (1e-3 * kk * (comp & ~Hact))[:, None])
                Hr = Hr[np.ix_(free, free)]
                reg = 1e-12 * max(np.abs(np.diag(Hr)).max(), 1.0)
                step = np.linalg.solve(Hr + reg * np.eye(len(free)), -gf); exact = False
            E0, slope, t = energy(u), gf @ step, 1.0
            if slope >= 0:
                step, slope, exact = -gf, -(gf @ gf), False
            while t > 1e-14:
                un = u.copy(); un[free] += t * step
                if energy(un) <= E0 + 1e-4 * t * slope:
                    break
                t *= 0.5
            # 종료 판정은 '이 걸음을 계산할 때 쓴 접촉 상태'와 비교해야 한다
            u, last_t, prev_act, prev_exact = un, t, Hact, exact
            inexact_run = 0 if exact else inexact_run + 1
            # 이 책장에서 실제 변위는 수 mm, 회전은 0.01 rad 수준이다. 100 (mm 또는 rad) 을 넘거나,
            # 강성 행렬이 계속 특이해서 정칙화한 걸음만 200번 이어지면 받침이 모자란 것이다.
            if not np.all(np.isfinite(u)) or np.abs(u).max() > 100.0 or inexact_run > 200:
                raise Unstable(f"no stable support (iteration {it}, max |u| {np.abs(u).max():.3g})")
        else:
            raise RuntimeError("Newton did not converge")
        p, phi = parts(u)
        f = kk * phi
        act = np.where(comp, p > 0.0, True)
        # 잔차 검사
        grad = K0 @ u - F - B.T @ f
        Hd = np.abs(np.diag(K0 + B.T @ (B * kk[:, None]))[free]).max() if len(free) else 1.0
        if np.abs(grad[free]).max() > 1e-8 * (Hd * np.abs(u).max() + scaleF):
            raise RuntimeError(f"residual {np.abs(grad[free]).max():.3e}")
        # 무차별 평형(하중이 없는 방향으로 강성 0) 여부: 경고용
        Hf = (K0 + B.T @ (B * (kk * act)[:, None]))[np.ix_(free, free)]
        try:
            Lc = np.linalg.cholesky(Hf)
            indifferent = bool((np.diag(Lc) ** 2).min() < 1e-14 * np.diag(Hf).max())
        except np.linalg.LinAlgError:
            indifferent = True
        return dict(u=u, f=f, active=act, iterations=it + 1, indifferent=indifferent or flat)

    def beam_forces(self, u):
        """요소마다 (tag, L, V1, M1, V2, M2). 부재 끝에서 요소에 작용하는 힘."""
        out = []
        for d, L, EI, phi, tag in self.beams:
            f = self.k_beam(L, EI, phi) @ u[d]
            out.append((tag, L, *f))
        return out

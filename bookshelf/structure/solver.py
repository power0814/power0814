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
        # 모든 자유도에 거는 아주 약한 접지 스프링. 자유도마다 (모든 접촉을 닫은 강성 행렬의 그 자유도 대각값) × ground.
        # (자유도마다 단위가 달라서 — mm 와 rad — 전체 최댓값 하나로 정하면 안 된다.)
        # 0 이 아니면 강성 행렬이 늘 정칙이라 뉴턴 걸음이 언제나 정확하고, 진짜 메커니즘은 변위 ≈ 하중/접지강성
        # 으로 곧바로 발산해 드러난다. 이 스프링이 받은 힘은 결과의 ground_f 로 돌려주어 평형 검사에 넣는다.
        self.ground = 0.0

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
        파고들지 않음)을 저절로 만족한다. 뉴턴 방향 + 정확한 선 탐색으로 최솟점을 찾는다.

        받침이 모자라면 (메커니즘에 하중이 걸리면) Π 가 아래로 끝없이 내려가 변위가 발산한다 → Unstable.
        """
        K0 = self._base()
        F = np.array(self.F, float)
        free = np.array([i for i in range(self.n) if i not in self.fixed], int)
        ns = len(self.springs)
        kg = np.zeros(self.n)
        if self.ground:
            dall = np.diag(K0).copy()
            for s in self.springs:
                for d1, c1 in s['terms'].items():
                    dall[d1] += s['k'] * c1 * c1
            kg[free] = self.ground * np.maximum(np.abs(dall[free]), 1e-30)
            K0[free, free] += kg[free]
        # 접촉 행렬 B (스프링 × 자유도)는 아주 성기다 (스프링마다 자유도 7개 이하). 색인 배열로 다룬다.
        mt = max((len(s['terms']) for s in self.springs), default=1)
        IDX = np.zeros((ns, mt), int); VAL = np.zeros((ns, mt))
        for i, s in enumerate(self.springs):
            for j, (d, c) in enumerate(s['terms'].items()):
                IDX[i, j] = d; VAL[i, j] = c
        PAIR = (IDX[:, :, None] * self.n + IDX[:, None, :]).reshape(ns, mt * mt)   # (i, j) 쌍의 평탄 색인
        VV = (VAL[:, :, None] * VAL[:, None, :]).reshape(ns, mt * mt)

        class _B:
            """B @ u, B.T @ v, B.T diag(w) B 만 쓴다."""
            T = None

            def __matmul__(self, u):
                return (VAL * u[IDX]).sum(1)
        Bm = _B()

        def BT(v):
            return np.bincount(IDX.ravel(), weights=(VAL * v[:, None]).ravel(), minlength=self.n)

        def BtWB(w):
            return np.bincount(PAIR.ravel(), weights=(VV * w[:, None]).ravel(),
                               minlength=self.n * self.n).reshape(self.n, self.n)
        B = Bm
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

        def line_min(u, s):
            """u + t·s 위에서 에너지의 정확한 최솟점 t (≥ 0). 에너지는 t 에 대해 조각별 2차식이고,
            기울기 D(t) 는 단조 증가하는 조각별 1차식이다. 접촉이 열리고 닫히는 점을 차례로 지나며 D = 0 을 찾는다."""
            p, _ = parts(u)
            q = -(B @ s)
            A = s @ (K0 @ u - F)
            C = s @ (K0 @ s)
            bil = ~comp
            A += np.sum(kk[bil] * p[bil] * q[bil]); C += np.sum(kk[bil] * q[bil] ** 2)
            on = comp & ((p > 0) | ((p == 0) & (q > 0)))
            A += np.sum(kk[on] * p[on] * q[on]); C += np.sum(kk[on] * q[on] ** 2)
            tb = np.full(ns, np.inf)
            mk = comp & (q != 0)
            tb[mk] = -p[mk] / q[mk]
            ev = np.where(mk & (tb > 0))[0]
            Cscale = abs(C) + np.sum(kk * q * q) + 1e-300
            t_prev = 0.0
            for i in ev[np.argsort(tb[ev])]:
                ti = tb[i]
                if A + C * t_prev >= 0:              # 구간 시작에서 이미 오르막: 최솟점은 구간 시작
                    return t_prev
                if A + C * ti >= 0:                  # 이 구간 안에서 D = 0 (C > 0 일 수밖에 없다)
                    return -A / C
                if q[i] < 0:                          # 닫혀 있던 접촉이 열린다
                    A -= kk[i] * p[i] * q[i]; C -= kk[i] * q[i] ** 2
                else:                                 # 열려 있던 접촉이 닫힌다
                    A += kk[i] * p[i] * q[i]; C += kk[i] * q[i] ** 2
                if abs(C) < 1e-12 * Cscale:           # 빼고 더하며 생긴 반올림
                    C = 0.0
                t_prev = ti
            if A + C * t_prev >= 0:
                return t_prev
            if C > 0:
                return -A / C
            raise Unstable("energy unbounded along the search direction: a part has no support")

        u = np.zeros(self.n)
        prev_set, prev_exact, last_t = None, False, 0.0
        Ehist, flat = [], False
        scaleF = np.abs(F).max() + 1e-30
        for it in range(max_iter):
            p, phi = parts(u)
            grad = K0 @ u - F - BT(kk * phi)
            # 에너지의 조각 경계(p = 0)와 똑같이 나눈다
            act = np.where(comp, p >= 0.0, True)
            # 끝: 바로 앞 걸음이 그 접촉 상태의 정확한 뉴턴 걸음이었고 (정확한 선 탐색에서 t = 1),
            # 걸음 뒤에도 접촉 상태가 그대로면 지금 점은 그 2차 조각의 정확한 최솟점이다 (유한 종료).
            if prev_exact and abs(last_t - 1.0) < 1e-9 and np.array_equal(act, prev_set):
                break
            # 무차별 평형 (접지 스프링을 끈 경우에만 생긴다): 강체가 대각선 두 점에만 닿고 무게중심이 그 대각선
            # 위에 있으면 그 축 회전은 에너지 0 이다. 접촉 길이·막대 변형이 그대로라 힘과 응력은 같다.
            # 에너지가 더 줄지 않고 잔차가 충분히 작으면 해로 받아들이고 표시한다.
            Ehist.append(energy(u))
            if len(Ehist) > 20:
                dE = Ehist[-21] - Ehist[-1]
                Hd0 = np.abs(np.diag(K0 + BtWB(kk * act))[free]).max()
                if dE <= 1e-12 * abs(Ehist[-1]) and \
                        np.abs(grad[free]).max() <= 1e-8 * (Hd0 * np.abs(u).max() + scaleF):
                    flat = True
                    break
            # 걸음 방향.
            # - 첫 걸음: 모든 접촉이 닿았다고 본다 (초기 틈이 있으면 u = 0 에서 모두 떨어져 있어 부재가 허공에 뜬다).
            # - 접촉 상태가 바뀌는 중: 떨어진 접촉의 강성을 1e-3 배로 살짝 넣어 '곧 닿을 곳' 쪽으로 방향을 잡는다.
            # - 접촉 상태가 그대로: 정확한 헤세 행렬 (종료 판정에 필요).
            if it == 0:
                Hset, w = np.ones_like(act), kk.copy()
            elif prev_set is not None and not np.array_equal(act, prev_set):
                Hset, w = act, kk * act + 1e-3 * kk * (comp & ~act)
            else:
                Hset, w = act, kk * act
            exact = it > 0 and np.array_equal(w, kk * act)
            H = K0 + BtWB(w)
            gf, Hf = grad[free], H[np.ix_(free, free)]
            try:
                Lc = np.linalg.cholesky(Hf)
                if ((np.diag(Lc) ** 2) / np.maximum(np.diag(Hf), 1e-300)).min() < 1e-14:
                    raise np.linalg.LinAlgError
                sf = np.linalg.solve(Hf, -gf)
            except np.linalg.LinAlgError:
                Hr = (H + BtWB(1e-3 * kk * (comp & ~act)))[np.ix_(free, free)]
                reg = 1e-12 * max(np.abs(np.diag(Hr)).max(), 1.0)
                sf = np.linalg.solve(Hr + reg * np.eye(len(free)), -gf); exact = False
            if gf @ sf >= 0:                      # 수치적으로 하강 방향이 아니면 경사 방향
                sf, exact = -gf, False
            s = np.zeros(self.n); s[free] = sf
            t = line_min(u, s)
            u = u + t * s
            prev_set, prev_exact, last_t = Hset, exact, t
            # 이 책장에서 실제 변위는 수 mm, 회전은 0.01 rad 수준이다. 100 (mm 또는 rad) 을 넘으면 받침이 모자란 것이다.
            if not np.all(np.isfinite(u)) or np.abs(u).max() > 100.0:
                raise Unstable(f"no stable support (iteration {it}, max |u| {np.abs(u).max():.3g})")
        else:
            raise RuntimeError("Newton did not converge")
        p, phi = parts(u)
        f = kk * phi
        act = np.where(comp, p > 0.0, True)
        # 잔차 검사
        grad = K0 @ u - F - BT(f)
        Hd = np.abs(np.diag(K0 + BtWB(kk))[free]).max() if len(free) else 1.0
        if np.abs(grad[free]).max() > 1e-8 * (Hd * np.abs(u).max() + scaleF):
            raise RuntimeError(f"residual {np.abs(grad[free]).max():.3e}")
        # 무차별 평형(하중이 없는 방향으로 강성 0) 여부: 경고용
        Hf = (K0 + BtWB(kk * act))[np.ix_(free, free)]
        try:
            Lc = np.linalg.cholesky(Hf)
            indifferent = bool(((np.diag(Lc) ** 2) / np.maximum(np.diag(Hf), 1e-300)).min() < 1e-14)
        except np.linalg.LinAlgError:
            indifferent = True
        gf = np.zeros(self.n)
        gf[free] = -kg[free] * u[free]            # 접지 스프링이 구조를 받치는 힘 (위로 +). 아래로 처지면(u<0) 위로 민다
        return dict(u=u, f=f, active=act, iterations=it + 1, indifferent=indifferent or flat, ground_f=gf)

    def beam_forces(self, u):
        """요소마다 (tag, L, V1, M1, V2, M2). 부재 끝에서 요소에 작용하는 힘."""
        out = []
        for d, L, EI, phi, tag in self.beams:
            f = self.k_beam(L, EI, phi) @ u[d]
            out.append((tag, L, *f))
        return out

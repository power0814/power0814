"""엇갈려 쌓은 2안: 책이 기둥, 막대가 줄눈 보, 줄 끝마다 출력 기둥.

runs.py 와 같은 계(책 + 받침 + 덮개 + 이어진 막대)에 세 가지를 더한다.
- 기둥(pier): 줄의 양 끝에 책이 아닌 얇은 출력 기둥을 세운다. 막대 끝을 늘 받치므로 맨 바깥 책도 뺄 수 있다.
  이웃한 두 줄 사이에는 기둥 하나를 같이 쓰고, 윗면은 두 줄 높이에 맞춘 계단이 된다.
- 엇갈림: 위 단의 책이 아래 단 줄들의 경계를 걸쳐 앉는다. 그런 책의 받침은 바닥이 계단형이다 (책마다 출력).
- 단마다 좌우로 어긋나게 시작한다.

출력: out/stagger/layout.json — runs.py 와 같은 형식에 piers 와 책마다 supports(아래에서 딛는 구간들)가 붙는다.
사용법: python3 stagger.py [--out out/stagger] [--target 520] [--seed 3]   (out/bond 는 예전 출력형 모듈의 엇쌓기 배치다)
"""
import argparse
import json
import random
from pathlib import Path

import runs as R
from layout import book_kg

ROOT = Path(__file__).parent
P = dict(R.P)
P.update(
    dmax=60.0,             # 한 줄 안에서 받침이 흡수하는 높이 차 최대
    s_max=90.0,            # 받침 최대 높이 (계단형 받침의 낮은 쪽 포함)
    pier_w=14.0,           # 기둥 폭 (x)
    run_min=3, run_max=6,  # 한 줄의 책 수
    stagger=60.0,          # 단마다 어긋나는 거리 (mm)
    joint_gap=25.0,        # 위 단 기둥은 아래 단 기둥에서 이만큼 떨어진다 (세로 이음이 겹치지 않게: 엇갈려 쌓기)
    pick=3,                # 맞는 책 후보 중 앞쪽 몇 권에서 무작위로 고른다
    rod_ext=0.0,
    # 책마다 골조: 받침과 덮개를 네 모서리의 가는 기둥으로 잇는다. 기둥은 받침에 고정되고 덮개 구멍으로
    # slip 만큼 미끄러져 들어가 평소에는 하중을 받지 않는다 (책이 기둥). 칸 옆 두께 = 기둥 + 틈.
    post=[3.0, 8.0],       # 모서리 기둥 단면 (x 두께, y 깊이) mm
    slip=1.5,              # 기둥이 덮개 속에서 미끄러지는 거리 mm
    side=3.5,
)
R.P.update({k: P[k] for k in ("y0", "rows", "edge", "cg_margin", "side")})


def pitch(b):
    return b["t"] + 2 * P["side"]


def rows_for(width_min):
    return [y for y in P["rows"] if y <= P["y0"] + width_min - P["edge"]]


class Course:
    """한 단: 기둥과 책을 왼쪽부터 놓는다. 줄은 기둥 사이의 책들."""

    def __init__(self, idx, below=None):
        self.idx, self.below = idx, below
        self.items = []        # ("pier", x0, x1) 또는 ("book", b, x0, x1)
        self.runs = []

    def supports(self, x0, x1):
        """[x0, x1] 아래에서 딛는 구간들: [(run, sx0, sx1)]. 아래 단이 없으면 바닥. 막대 없는 곳이면 None."""
        if self.below is None:
            return [(None, x0, x1)]
        out = []
        for r, ra, rb in self.below.spans():
            a, b = max(x0, ra), min(x1, rb)
            if b - a > 1e-9:
                out.append((r, a, b))
        covered = sum(b - a for _, a, b in out)
        return out if abs(covered - (x1 - x0)) < 1e-6 else None

    def spans(self):
        """막대가 있는 줄들이 받치는 구간. 같이 쓰는 기둥은 가운데에서 나눈다 (두 번 세지 않게)."""
        rs = sorted((r for r in self.runs if r["rows"]), key=lambda r: r["x0"])
        out = []
        for i, r in enumerate(rs):
            a, b = r["x0"], r["x1"]
            if i > 0 and rs[i - 1]["x1"] > a:
                a = (a + rs[i - 1]["x1"]) / 2
            if i + 1 < len(rs) and rs[i + 1]["x0"] < b:
                b = (b + rs[i + 1]["x0"]) / 2
            out.append((r, a, b))
        return out


def seg_rows(book, segs):
    """계단형 받침이 딛는 막대 줄: 구간마다 둘 이상, 무게중심이 그 사이."""
    out = []
    for r, a, b in segs:
        if r is None:
            out.append(None); continue
        rows = R.contact_rows(book, r["rows"])
        if rows is None:
            return False
        out.append(rows)
    return out


def close_run(course, books, x_start, x_end, piers):
    """책 목록으로 줄을 만든다. 높이(level)는 계단형 받침까지 고려해 가장 높은 요구에 맞춘다."""
    rid = f"R{course.idx}{chr(97 + len(course.runs))}"
    need = []
    for b, x0, x1, segs in books:
        top = max(0.0 if r is None else r["level"] for r, _, _ in segs)
        need.append(top + P["s_min"] + b["h"] + P["cap_t"])
    level = max(need)
    has_rods = len(books) >= P["run_min"]
    run = dict(id=rid, course=course.idx, level=level, x0=x_start, x1=x_end,
               cells=[b["id"] for b, *_ in books], upper=[], piers=piers,
               rows=rows_for(min(b["w"] for b, *_ in books)) if has_rods else [])
    course.runs.append(run)
    return run


def place_course(course, cands, start, stop, rng, max_h):
    """start 에서 stop 까지 책을 고르며 놓는다. 반환: 놓은 책 id."""
    placed, x = [], start

    def heights_ok(books, b, segs):
        top = max(0.0 if r is None else r["level"] for r, _, _ in segs)
        hs = [bb["h"] for bb, *_ in books] + [b["h"]]
        if max(hs) - min(hs) > P["dmax"]:
            return False
        need = [max(0.0 if r is None else r["level"] for r, _, _ in s) + P["s_min"] + bb["h"] + P["cap_t"]
                for bb, _, _, s in books] + [top + P["s_min"] + b["h"] + P["cap_t"]]
        level = max(need)
        if level + P["rod_r"] > max_h:
            return False
        for bb, _, _, s in books + [(b, 0, 0, segs)]:
            for r, _, _ in s:
                base = 0.0 if r is None else r["level"]
                sh = level - P["cap_t"] - bb["h"] - base
                if sh > P["s_max"] + 1e-9:
                    return False
        return True

    pool = list(cands)
    pw = P["pier_w"]
    below_piers = [] if course.below is None else [r[k] for r in course.below.runs if r["rows"]
                                                   for k in ("x0", "x1")]

    def pier_ok(xp):
        """기둥 [xp, xp + pw] 가 아래 단 기둥과 일직선이 아닌가 (아래 단 줄의 양 끝 = 기둥 바깥면)."""
        c = xp + pw / 2
        return all(abs(c - (e + pw / 2 if i % 2 == 0 else e - pw / 2)) >= P["joint_gap"]
                   for i, e in enumerate(below_piers))

    def fits(books_run, xb, b):
        x0, x1 = xb, xb + pitch(b)
        if x1 + pw > stop:
            return None
        segs = course.supports(x0, x1)
        if segs is None or course.supports(x1, x1 + pw) is None:
            return None
        if any(r is not None for r, _, _ in segs) and not seg_rows(b, segs):
            return None
        if not heights_ok(books_run, b, segs):
            return None
        return (b, x0, x1, segs)

    while pool and x + pw <= stop:
        # 줄 시작: 왼쪽 기둥 [x, x + pw]
        if course.supports(x, x + pw) is None or not pier_ok(x):
            x += 5.0
            continue
        books_run, xb = [], x + pw
        while len(books_run) < P["run_max"]:
            ok = []
            for b in pool:
                f = fits(books_run, xb, b)
                if f:
                    ok.append(f)
                    if len(ok) >= P["pick"]:
                        break
            if not ok:
                break
            chosen = rng.choice(ok)
            books_run.append(chosen); pool.remove(chosen[0])
            xb = chosen[2]
            # 줄 길이를 들쭉날쭉하게: run_min 이상이고 이음이 어긋나는 자리면 일정 확률로 끊는다
            if len(books_run) >= P["run_min"] and pier_ok(xb) and rng.random() < 0.35:
                break
        # 오른쪽 기둥이 아래 기둥과 일직선이면 끝 책을 하나씩 돌려놓아 본다
        while len(books_run) > P["run_min"] and not pier_ok(xb):
            b = books_run.pop(); pool.insert(0, b[0]); xb = b[1]
        if not books_run:
            x += 5.0
            continue
        placed += [b["id"] for b, *_ in books_run]
        run = close_run(course, books_run, x, xb + pw, piers=[])
        for b, x0, x1, segs in books_run:
            course.items.append(("book", b, x0, x1, segs, run["id"]))
        x = xb                    # 다음 줄은 이 줄의 오른쪽 기둥을 같이 쓴다
    return placed


def build(books, target_w, seed, max_h):
    rng = random.Random(seed)
    order = sorted(books, key=lambda b: (-b["kg"], b.get("date", "")))
    courses, k = [], 0
    below = None
    while order:
        c = Course(k, below)
        if below is None:
            lo, hi = 0.0, target_w
        else:
            spans = [r for r in below.runs if r["rows"]]
            if not spans:
                break
            lo, hi = min(r["x0"] for r in spans), max(r["x1"] for r in spans)
            # 단마다 반대쪽으로 어긋나게
            if k % 2 == 1:
                lo += P["stagger"]
            else:
                hi -= P["stagger"]
        if hi - lo < 3 * 20 + 2 * P["pier_w"]:
            break
        # 아래 단은 높이가 다른 줄들이 섞이도록 높이순으로 몇 덩어리로 나눠 번갈아 놓는다
        cands = order
        if below is None:
            take, w = [], 0.0
            for b in order:
                if w + pitch(b) + P["pier_w"] > target_w:
                    continue
                take.append(b); w += pitch(b) + P["pier_w"] / P["run_min"]
            take.sort(key=lambda b: b["h"])
            n = max(2, round(len(take) / 4))
            chunks = [take[i * len(take) // n:(i + 1) * len(take) // n] for i in range(n)]
            alt = []
            for i in range(n):
                alt += chunks[(i * 2) % n if n % 2 else (i * 2 + i // (n // 2)) % n]
            cands = alt
        placed = place_course(c, cands, lo, hi, rng, max_h)
        if not placed:
            break
        order = [b for b in order if b["id"] not in set(placed)]
        courses.append(c); below = c; k += 1
    return courses, order


def export(courses, books):
    placed, runs, piers = {}, [], []
    for c in courses:
        for it in c.items:
            _, b, x0, x1, segs, rid = it
            run = next(r for r in c.runs if r["id"] == rid)
            sup = []
            for r, a, bb in segs:
                base = 0.0 if r is None else r["level"]
                sup.append(dict(run=None if r is None else r["id"], x0=a, x1=bb, base=base,
                                shoe=run["level"] - P["cap_t"] - b["h"] - base,
                                rows=None if r is None else R.contact_rows(b, r["rows"])))
                if r is not None:
                    r["upper"].append(b["id"])
            shoe_top = run["level"] - P["cap_t"] - b["h"]
            placed[b["id"]] = dict(
                id=b["id"], label=b.get("label", ""), kind=b.get("kind"), date=b.get("date"), color=b.get("color"),
                h=b["h"], w=b["w"], t=b["t"], kg=b["kg"], course=c.idx, x0=x0, x1=x1, xc=(x0 + x1) / 2,
                z_foot=shoe_top, z_head=shoe_top + b["h"], cg_y=P["y0"] + b["w"] / 2, run=rid, supports=sup,
                shoe=sum(s["shoe"] * (s["x1"] - s["x0"]) for s in sup) / (x1 - x0),
                base=sup[0]["run"], rows_below=sup[0]["rows"])
        # 기둥: 막대가 있는 줄의 양 끝. 이웃 줄과 맞닿은 곳은 하나를 같이 쓴다
        ends = {}
        for r in c.runs:
            if not r["rows"]:
                continue
            for side, x in (("L", r["x0"]), ("R", r["x1"] - P["pier_w"])):
                key = round(x, 6)
                ends.setdefault(key, []).append(r)
        for x, rs in sorted(ends.items()):
            x0, x1 = x, x + P["pier_w"]
            segs = c.supports(x0, x1)
            pid = f"P{len(piers)}"
            sup = [dict(run=None if r is None else r["id"], x0=a, x1=b, base=0.0 if r is None else r["level"])
                   for r, a, b in segs]
            top = max(r["level"] for r in rs)
            rows = sorted(set(y for r in rs for y in r["rows"]))
            piers.append(dict(id=pid, course=c.idx, x0=x0, x1=x1, xc=(x0 + x1) / 2, runs=[r["id"] for r in rs],
                              top=top, supports=sup, rows=rows,
                              depth=max(rows) + P["edge"] + 10.0 - P["y0"]))
            for r in rs:
                r["piers"].append(pid)
            for s in segs:
                if s[0] is not None:
                    s[0]["upper_piers"] = s[0].get("upper_piers", []) + [pid]
        runs += c.runs
    for r in runs:
        r.setdefault("upper_piers", [])
    return placed, runs, piers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", default=str(ROOT / "books.json"))
    ap.add_argument("--out", default=str(ROOT / "out/stagger"))
    ap.add_argument("--target", type=float, default=520.0)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--max-height", type=float, default=P["max_h"])
    a = ap.parse_args()
    books = json.load(open(a.books))["books"]
    for b in books:
        b["kg"] = round(book_kg(b), 3)
    tw = a.target
    while True:
        courses, left = build(books, tw, a.seed, a.max_height)
        if not left:
            break
        tw += 10
        if tw > 2000:
            raise SystemExit("could not place all books")
    placed, runs, piers = export(courses, books)
    width = max(r["x1"] for r in runs) - min(r["x0"] for r in runs)
    height = max(r["level"] for r in runs) + P["rod_r"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    data = dict(system="bond", params=P, width=width, height=height,
                books=[placed[b["id"]] for b in books], runs=runs, piers=piers)
    (out / "layout.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"width {width:.0f} mm, height {height:.0f} mm, courses {len(courses)}, runs {len(runs)}, piers {len(piers)}")
    for r in runs:
        print(f"  {r['id']:>5} level {r['level']:6.0f} x {r['x0']:6.0f}–{r['x1']:6.0f} rows {[int(y) for y in r['rows']]} "
              f"cells {r['cells']} upper {sorted(set(r['upper']))}")
    straddle = [b["id"] for b in placed.values() if len(b["supports"]) > 1]
    print("books on stepped shoes (straddling two runs):", straddle)
    print("shoe range", round(min(s["shoe"] for b in placed.values() for s in b["supports"])),
          "–", round(max(s["shoe"] for b in placed.values() for s in b["supports"])))


if __name__ == "__main__":
    main()

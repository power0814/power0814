"""책이 기둥, 막대가 줄눈 보인 배치 (2안).

책마다 출력한 받침(아래)과 머리 덮개(위)가 붙고, 높이가 비슷한 이웃 책들이 한 '줄'(run)을 이룬다.
한 줄의 덮개 위에는 앞뒤 방향으로 몇 가닥의 막대가 x 방향으로 길게 이어지고(줄눈 보),
위 줄의 책 받침이 그 막대 위에 선다. 책 높이 차이는 받침 높이가 흡수한다.

좌표: x 벽을 따라 왼→오, y 벽에서 앞으로, z 위로. 단위 mm.
사용법: python3 runs.py [--out out/runs] [--target 480] [--end-rule half]
"""
import argparse
import json
from collections import deque
from pathlib import Path

from layout import book_kg

ROOT = Path(__file__).parent
P = dict(
    y0=5.0,                       # 책 뒤끝 (벽 쪽)
    rows=[15.0, 95.0, 175.0, 255.0],  # 막대 줄의 y (벽에서)
    edge=10.0,                    # 막대 줄은 책 앞끝에서 이만큼 안쪽까지만
    cg_margin=10.0,               # 위 책 무게중심은 바깥 막대 줄보다 이만큼 안쪽
    side=2.0,                     # 받침·덮개의 한쪽 옆 두께 + 틈. 칸 폭 = t + 2·side
    s_min=14.0,                   # 받침 최소 높이 (바닥 4 + 쐐기 8 + 내림 2)
    dmax=40.0,                    # 한 줄 안에서 받침이 흡수하는 높이 차 최대
    cap_t=10.0,                   # 책 머리 → 막대 중심
    rod_r=6.0,
    rod_ext=-1.0,                 # 막대 끝 위치: 끝 칸 바깥면에서 1 mm 안쪽 (옆 줄의 책과 부딪히지 않게)
    max_h=1500.0,
    end_rule="half",              # 위 칸이 놓일 수 있는 범위: none | half | inner
    min_rod_cells=3,              # 막대를 거는 줄의 최소 책 수. 둘 이하면 한 권을 뺐을 때 남은 한 권 위에서
                                  # 막대와 덮개가 시소처럼 넘어간다 (구조 해석으로 확인). 그런 줄은 덮개만 얹는다.
)


def pitch(b):
    return b["t"] + 2 * P["side"]


def run_rows(books):
    """줄의 막대 줄: 줄 안의 모든 책 깊이에 들어가는 줄."""
    wmin = min(b["w"] for b in books)
    return [y for y in P["rows"] if y <= P["y0"] + wmin - P["edge"]]


def contact_rows(book, rows):
    """위 책이 아래 막대 중 실제로 딛는 줄. 둘 이상이고 무게중심이 그 사이에 있어야 선다."""
    r = [y for y in rows if y <= P["y0"] + book["w"] - P["edge"]]
    cg = P["y0"] + book["w"] / 2
    if len(r) >= 2 and r[0] + P["cg_margin"] <= cg <= r[-1] - P["cg_margin"]:
        return r
    return None


def group_by_height(books):
    """높이순으로 정렬해 높이 차 dmax 이내로 묶는다."""
    groups, cur = [], []
    for b in sorted(books, key=lambda b: b["h"]):
        if cur and b["h"] - cur[0]["h"] > P["dmax"]:
            groups.append(cur); cur = []
        cur.append(b)
    if cur:
        groups.append(cur)
    return groups


def heavy_middle(books):
    """무거운 책을 가운데로."""
    d = deque()
    for i, b in enumerate(sorted(books, key=lambda b: -b["kg"])):
        (d.append if i % 2 == 0 else d.appendleft)(b)
    return list(d)


def mountain(groups):
    """높은 줄을 가운데로."""
    d = deque()
    for i, g in enumerate(sorted(groups, key=lambda g: -max(b["h"] for b in g))):
        (d.append if i % 2 == 0 else d.appendleft)(g)
    return list(d)


def make_runs(groups, x_start, base, course, runs, placed):
    x = x_start
    base_level = base["level"] if base else 0.0
    for g in groups:
        g = heavy_middle(g)
        level = base_level + max(b["h"] for b in g) + P["s_min"] + P["cap_t"]
        rid = f"R{len(runs)}"
        cells = []
        for b in g:
            x0, x1 = x, x + pitch(b)
            shoe = level - P["cap_t"] - b["h"] - base_level
            assert P["s_min"] - 1e-9 <= shoe <= P["s_min"] + P["dmax"] + 1e-9, (b["id"], shoe)
            placed[b["id"]] = dict(
                id=b["id"], label=b.get("label", ""), kind=b.get("kind"), date=b.get("date"), color=b.get("color"),
                h=b["h"], w=b["w"], t=b["t"], kg=b["kg"], course=course,
                x0=x0, x1=x1, xc=(x0 + x1) / 2, shoe=shoe, z_foot=base_level + shoe,
                z_head=base_level + shoe + b["h"], cg_y=P["y0"] + b["w"] / 2,
                base=base["id"] if base else None, run=rid,
                rows_below=contact_rows(b, base["rows"]) if base else None)
            cells.append(b["id"]); x = x1
        runs.append(dict(id=rid, course=course, base=base["id"] if base else None, base_level=base_level,
                         level=level, x0=placed[cells[0]]["x0"] - P["rod_ext"],
                         x1=placed[cells[-1]]["x1"] + P["rod_ext"], cells=cells,
                         rows=run_rows(g) if len(cells) >= P["min_rod_cells"] else [], upper=[]))
    return x


def allowed(run, placed):
    first, last = placed[run["cells"][0]], placed[run["cells"][-1]]
    if P["end_rule"] == "none":
        return first["x0"], last["x1"]
    if P["end_rule"] == "half":
        return first["xc"], last["xc"]
    return first["x1"], last["x0"]        # inner: 끝 칸 위에는 놓지 않는다


def build(books, target_w):
    order = sorted(books, key=lambda b: (-b["kg"], b.get("date", "")))
    floor, w = [], 0.0
    while order and w < target_w:
        b = order.pop(0); floor.append(b); w += pitch(b)
    runs, placed = [], {}
    make_runs(mountain(group_by_height(floor)), 0.0, None, 0, runs, placed)
    bases, course = list(runs), 1
    while order and bases:
        new = []
        for base in sorted(bases, key=lambda r: r["x0"]):
            if not base["rows"]:
                continue                      # 막대가 없는 줄(책 둘 이하) 위에는 올리지 않는다
            a, b_ = allowed(base, placed)
            chosen, used = [], 0.0
            for bk in order:
                if contact_rows(bk, base["rows"]) is None:
                    continue
                if base["level"] + P["s_min"] + bk["h"] + P["cap_t"] + P["rod_r"] > P["max_h"]:
                    continue
                if used + pitch(bk) > b_ - a + 1e-9:
                    continue
                chosen.append(bk); used += pitch(bk)
            if not chosen:
                continue
            ids = {c["id"] for c in chosen}
            order = [o for o in order if o["id"] not in ids]
            before = len(runs)
            make_runs(mountain(group_by_height(chosen)), a + (b_ - a - used) / 2, base, course, runs, placed)
            base["upper"] = [c for r in runs[before:] for c in r["cells"]]
            new += runs[before:]
        bases, course = new, course + 1
    return runs, placed, order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", default=str(ROOT / "books.json"))
    ap.add_argument("--out", default=str(ROOT / "out/runs"))
    ap.add_argument("--target", type=float, default=400.0, help="바닥 줄 폭의 시작값. 다 못 놓으면 늘린다")
    ap.add_argument("--end-rule", default=P["end_rule"], choices=["none", "half", "inner"])
    ap.add_argument("--max-height", type=float, default=P["max_h"])
    a = ap.parse_args()
    P["end_rule"], P["max_h"] = a.end_rule, a.max_height
    books = json.load(open(a.books))["books"]
    for b in books:
        b["kg"] = round(book_kg(b), 3)
    tw = a.target
    while True:
        runs, placed, left = build(books, tw)
        if not left:
            break
        tw += 10
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    width = max(r["x1"] for r in runs) - min(r["x0"] for r in runs)
    height = max(r["level"] for r in runs) + P["rod_r"]
    data = dict(system="runs", params=P, width=width, height=height,
                books=[placed[b["id"]] for b in books], runs=runs)
    (out / "layout.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"width {width:.0f} mm, height {height:.0f} mm, runs {len(runs)}, courses {1 + max(r['course'] for r in runs)}")
    for r in runs:
        print(f"  {r['id']:>4} course {r['course']} level {r['level']:6.0f} x {r['x0']:6.0f}–{r['x1']:6.0f} "
              f"rows {[int(y) for y in r['rows']]} cells {r['cells']} upper {r['upper']}")


if __name__ == "__main__":
    main()

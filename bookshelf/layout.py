#!/usr/bin/env python3
"""책 목록 → 모듈 치수 → 쌓는 위치 → layout.json / assembly.scad / STL.

쌓는 규칙 (중력 + 받침 + 무게 + 높이 한계):
  1. 책은 들어온 순서대로 하나씩 놓는다. 모든 모듈은 뒷면을 벽에 붙인다.
  2. 놓을 수 있는 자리 중 가장 낮은 곳에 놓는다. 높이가 같으면 왼쪽부터.
  3. 바닥이 아닌 곳에 놓으려면 아래 모듈이 받쳐야 한다.
     - 닿는 면의 좌우 범위 안에 모듈의 중심이 들어갈 것
     - 닿는 면이 모듈 깊이의 75% 이상일 것 (앞으로 크게 내밀지 않기)
     - 닿는 면적이 바닥 면적의 40% 이상일 것
  4. 책은 자기보다 무겁거나 같은 책 위에만 올라간다 (받치는 모듈 모두가 더 무거울 것).
  5. 무거울수록 낮은 곳에서만 시작할 수 있다: 0.1 kg은 최대 높이까지, 7 kg은 바닥만 (로그 척도).
  6. 모듈 윗면이 최대 높이(기본 1500 mm)를 넘으면 안 된다.
  7. 정해 둔 폭 안에 자리가 없으면 오른쪽으로 한 칸 넓힌다.

무게는 books.json의 "kg"이 있으면 그 값을, 없으면 판형 부피로 추정한다
(미술책 1.0 g/cm³, 페이퍼백 0.65 g/cm³). 실제 책은 저울로 재서 "kg"을 넣는 게 정확하다.

사용법:
  python3 layout.py                  # layout.json, assembly.scad
  python3 layout.py --stl out/stl    # 모듈·받침·쐐기 STL까지
"""
import argparse
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SCAD = HERE / "book_module.scad"
GRID = 10


def scad_args(b, part):
    return [
        "-D", f"book_h={b['h']}", "-D", f"book_w={b['w']}", "-D", f"book_t={b['t']}",
        "-D", f'idx="{b["id"]}"', "-D", f'note="{b["date"]}"', "-D", f'part="{part}"',
        "-D", f"lay={'true' if b.get('lay') else 'false'}",
        "-D", f"skeletal={'true' if b.get('skeletal') else 'false'}",
    ]


def module_dims(b):
    """OpenSCAD가 계산한 치수를 그대로 읽는다 (계산식은 .scad 한 곳에만)."""
    with tempfile.NamedTemporaryFile(suffix=".echo") as f:
        subprocess.run(["openscad", "-o", f.name, *scad_args(b, "pin"), str(SCAD)],
                       check=True, capture_output=True)
        text = Path(f.name).read_text()
    nums = re.search(r'"DIMS ([^"]+)"', text).group(1).split()
    fits = re.search(r'"FITS_BED (\w+)"', text).group(1) == "true"
    X, Y, Z, sx, by, pz, cav = map(float, nums)
    return dict(X=X, Y=Y, Z=Z, sx=sx, by=by, pz=pz, cav=cav, fits_bed=fits)


DENSITY = {"art": 1.0, "pb": 0.65}           # g/cm³, 책 종류별 대략값


def book_kg(b):
    if "kg" in b:
        return float(b["kg"])
    return b["h"] * b["w"] * b["t"] / 1000 * DENSITY.get(b.get("kind"), 0.8) / 1000


def base_cap(kg, max_h, kg0=0.1, kg1=7.0):
    """무거울수록 낮은 곳에서만 시작할 수 있다 (로그 척도). 0.1 kg → max_h, 7 kg → 바닥."""
    t = min(1.0, max(0.0, np.log(kg / kg0) / np.log(kg1 / kg0)))
    return max_h * (1 - t)


def place(books, width_mm, max_h=1500, heavy_low=True):
    nx = 400                                  # 넉넉한 좌우 칸 수
    ny = int(max(b["dims"]["Y"] for b in books) // GRID)
    hmap = np.zeros((nx, ny), dtype=int)      # 각 격자 칸의 현재 높이(mm), y=0이 벽
    top = np.full((nx, ny), -1, dtype=int)    # 각 격자 칸 맨 위에 있는 모듈 번호
    limit = width_mm // GRID
    placed = []
    for i, b in enumerate(books):
        d = b["dims"]
        X, Y, Z = int(d["X"] // GRID), int(d["Y"] // GRID), int(d["Z"])
        while True:
            best = None
            for x0 in range(0, limit - X + 1):
                foot = hmap[x0:x0 + X, 0:Y]
                base = int(foot.max())
                if base + Z > max_h:
                    continue
                if base > 0:
                    contact = foot == base
                    xs = np.where(contact.any(axis=1))[0]
                    ys = np.where(contact.any(axis=0))[0]
                    centred = xs.min() + 0.25 <= X / 2 <= xs.max() + 1 - 0.25
                    deep = (ys.max() + 1) >= 0.75 * Y
                    area = contact.sum() >= 0.4 * X * Y
                    if not (centred and deep and area):
                        continue
                    if heavy_low:
                        below = set(top[x0:x0 + X, 0:Y][contact].tolist())
                        if any(placed[j]["kg"] < b["kg"] for j in below):
                            continue
                        if base > base_cap(b["kg"], max_h):
                            continue
                if best is None or base < best[0]:
                    best = (base, x0)
            if best:
                break
            limit += X                        # 자리가 없으면 옆으로 넓힌다
        base, x0 = best
        hmap[x0:x0 + X, 0:Y] = base + Z
        top[x0:x0 + X, 0:Y] = i
        placed.append({**b, "pos": [x0 * GRID, -d["Y"], base]})
    return placed


def place_bond(books, width_mm, max_h=1500, heavy_low=True, max_shim=40, min_share=0.25,
               deep_min=0.75, weight_ratio=0.5):
    """엇쌓기: 바닥이 아닌 곳의 칸은 아래 칸 두 개 이상에 걸쳐야 한다.

    벽돌을 엇갈려 쌓듯, 위 칸이 아래 칸 사이 줄눈을 덮게 한다. 그러면 아래 책 하나가 빠져도
    위 칸이 빈자리를 건너 옆 칸으로 하중을 넘긴다. 아래 칸들의 윗면 높이가 다르면, 차이가
    max_shim 이하일 때 10 mm 단위 괴임 블록으로 메운다. 받치는 칸마다 위 칸 폭의 min_share
    이상을 받쳐야 하고, 받치는 칸은 위 칸 무게의 절반 이상이어야 한다.
    """
    nx = 400
    ny = int(max(b["dims"]["Y"] for b in books) // GRID)
    hmap = np.zeros((nx, ny), dtype=int)
    top = np.full((nx, ny), -1, dtype=int)            # -1 = 바닥
    limit = width_mm // GRID
    placed, shims = [], []
    for i, b in enumerate(books):
        d = b["dims"]
        X, Y, Z = int(d["X"] // GRID), int(d["Y"] // GRID), int(d["Z"])
        while True:
            best = None
            for x0 in range(0, limit - X + 1):
                foot = hmap[x0:x0 + X, 0:Y]
                own = top[x0:x0 + X, 0:Y]
                base = int(foot.max())
                if base + Z > max_h:
                    continue
                sup, cost = [], 0
                if base > 0:
                    if heavy_low and base > base_cap(b["kg"], max_h):
                        continue
                    contact = foot >= base - max_shim
                    xs = np.where(contact.any(axis=1))[0]
                    ys = np.where(contact.any(axis=0))[0]
                    if not (xs.min() + 0.25 <= X / 2 <= xs.max() + 1 - 0.25
                            and ys.max() + 1 >= deep_min * Y and contact.sum() >= 0.4 * X * Y):
                        continue
                    ok = True
                    for o in np.unique(own[contact]):
                        cells = (own == o) & contact
                        cols = np.where(cells.any(axis=1))[0]
                        rows = np.where(cells.any(axis=0))[0]
                        share = len(cols) / X
                        h_o = int(foot[cells].max())
                        if share < min_share:
                            continue
                        if heavy_low and o >= 0 and placed[o]["kg"] < weight_ratio * b["kg"]:
                            ok = False
                            break
                        sup.append((int(o), cols, rows, h_o))
                        cost += (base - h_o) * int(cells.sum())
                    if not ok or len(sup) < 2:
                        continue
                cand = (base, cost, x0, sup)
                if best is None or cand[:3] < best[:3]:
                    best = cand
            if best:
                break
            limit += X
        base, cost, x0, sup = best
        for o, cols, rows, h_o in sup:
            if h_o < base:
                shims.append({"x": (x0 + int(cols.min())) * GRID, "X": len(cols) * GRID,
                              "Y": (int(rows.max()) + 1) * GRID, "z": h_o, "H": base - h_o,
                              "under": placed[o]["id"] if o >= 0 else "floor", "over": b["id"]})
        hmap[x0:x0 + X, 0:Y] = base + Z
        top[x0:x0 + X, 0:Y] = i
        placed.append({**b, "pos": [x0 * GRID, -d["Y"], base],
                       "supports": [placed[o]["id"] if o >= 0 else "floor" for o, *_ in sup]})
    return placed, shims


def place_spacer(books, width_mm, max_h=1500, heavy_low=True, spacer_t=10, max_leg=120, min_leg_mm=20,
                 target_mm=None, max_ext_mm=40):
    """스페이서 받침: 위 칸마다 계단형 받침 하나를 깐다.

    받침 윗면은 평평한 판(spacer_t)이고, 밑은 아래 칸들의 윗면 높이에 맞춰 다리가 내려간다.
    받침은 위 칸보다 양옆으로 max_ext_mm까지 넓어질 수 있어서, 좁은 칸도 이웃 칸까지 걸친다.
    받침은 아래 칸 두 개 이상에 걸쳐야 하고(다리마다 폭 min_leg_mm 이상), 다리 길이는 max_leg 이하.
    받침이 아래 칸들을 핀으로 묶어 짧은 보처럼 줄눈을 건너므로, 아래 책 하나가 빠져도
    위 칸의 하중이 옆 칸으로 간다. target_mm 폭 안을 먼저 채우고, 자리가 없을 때만 넓힌다.
    """
    nx = 400
    ny = int(max(b["dims"]["Y"] for b in books) // GRID)
    hmap = np.zeros((nx, ny), dtype=int)
    top = np.full((nx, ny), -1, dtype=int)
    limit = width_mm // GRID
    target = (target_mm or width_mm) // GRID
    min_cols = max(1, min_leg_mm // GRID)
    E = max_ext_mm // GRID
    placed, parts = [], []
    for i, b in enumerate(books):
        d = b["dims"]
        X, Y, Z = int(d["X"] // GRID), int(d["Y"] // GRID), int(d["Z"])
        while True:
            best = None
            for x0 in range(0, limit - X + 1):
                if int(hmap[x0:x0 + X, 0:Y].max()) == 0:      # 바닥
                    cand = (int(x0 + X > target), 0, 0, 0, x0, None)
                    if best is None or cand[:5] < best[:5]:
                        best = cand
                    continue
                for el in range(0, E + 1):
                    for er in range(0, E + 1):
                        s0, s1 = x0 - el, x0 + X + er
                        if s0 < 0 or s1 > limit:
                            continue
                        foot = hmap[s0:s1, 0:Y]
                        own = top[s0:s1, 0:Y]
                        hi = int(foot.max())
                        base = hi + spacer_t
                        if base + Z > max_h or (heavy_low and base > base_cap(b["kg"], max_h)):
                            continue
                        contact = foot >= hi - max_leg
                        ys = np.where(contact.any(axis=0))[0]
                        if ys.max() + 1 < 0.6 * Y or contact.sum() < 0.4 * (s1 - s0) * Y:
                            continue
                        legs, vol = [], 0
                        for o in np.unique(own[contact]):
                            cells = (own == o) & contact
                            cols = np.where(cells.any(axis=1))[0]
                            if len(cols) < min_cols:
                                continue
                            rows = np.where(cells.any(axis=0))[0]
                            h_o = int(foot[cells].max())
                            legs.append((int(o), cols + s0, rows, h_o))
                            vol += (hi - h_o) * int(cells.sum())
                        if len(legs) < 2:
                            continue
                        lx0 = min(int(c.min()) for _, c, _, _ in legs)
                        lx1 = max(int(c.max()) + 1 for _, c, _, _ in legs)
                        if not (lx0 + 0.25 <= x0 + X / 2 <= lx1 - 0.25):   # 위 칸 중심이 다리 사이에
                            continue
                        cand = (int(max(s1, x0 + X) > target), base, el + er, vol, x0, (s0, s1, legs))
                        if best is None or cand[:5] < best[:5]:
                            best = cand
            if best:
                break
            limit += X
        _, base, _, _, x0, sp = best
        legs = []
        if sp:
            s0, s1, legs = sp
            parts.append({"kind": "plate", "x": s0 * GRID, "X": (s1 - s0) * GRID, "Y": Y * GRID,
                          "z": base - spacer_t, "H": spacer_t, "over": b["id"]})
            for o, cols, rows, h_o in legs:
                if base - spacer_t > h_o:
                    parts.append({"kind": "leg", "x": int(cols.min()) * GRID, "X": len(cols) * GRID,
                                  "Y": (int(rows.max()) + 1) * GRID, "z": h_o, "H": base - spacer_t - h_o,
                                  "over": b["id"], "under": placed[o]["id"] if o >= 0 else "floor"})
            hmap[s0:s1, 0:Y] = np.maximum(hmap[s0:s1, 0:Y], base)   # 받침 윗면도 다음 칸이 쓸 수 있다
        hmap[x0:x0 + X, 0:Y] = base + Z
        top[x0:x0 + X, 0:Y] = i
        placed.append({**b, "pos": [x0 * GRID, -d["Y"], base],
                       "supports": [placed[o]["id"] if o >= 0 else "floor" for o, *_ in legs]})
    return placed, parts

def write_assembly(placed, path):
    lines = [
        "// layout.py가 만든 파일. 수정은 books.json에서.",
        "use <book_module.scad>",
        "",
        "color(\"#D9D6D0\") translate([-60, 0, -1]) cube([1600, 10, 1400]);   // 벽",
    ]
    for p in placed:
        x, y, z = p["pos"]
        ch, ct = (p["t"], p["h"]) if p.get("lay") else (p["h"], p["t"])   # 칸 기준 높이·두께
        lines.append(
            f'translate([{x}, {y}, {z}]) preview({ch}, {p["w"]}, {ct}, '
            f'"{p["id"]}", "{p["date"]}", "{p["color"]}");  // {p["label"]}'
            + (" (눕힘)" if p.get("lay") else "")
        )
    path.write_text("\n".join(lines) + "\n")


def export_stls(b, outdir):
    for part in ("module", "shoe", "wedge"):
        out = outdir / f"{b['id']}_{part}.stl"
        subprocess.run(["openscad", "-o", str(out), *scad_args(b, part), str(SCAD)],
                       check=True, capture_output=True)
    return b["id"]


def stl_volume_cm3(path):
    """ASCII STL의 부피 (삼각형마다 원점과 이루는 사면체 부피의 합)."""
    v = np.array([list(map(float, ln.split()[1:4]))
                  for ln in Path(path).read_text().splitlines() if ln.lstrip().startswith("vertex")])
    a, b, c = v[0::3], v[1::3], v[2::3]
    return abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6 / 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", default=str(HERE / "books.json"))
    ap.add_argument("--width", type=int, default=340, help="처음 바닥 폭 (mm)")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--stl", help="STL을 내보낼 폴더")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--max-height", type=int, default=1500, help="최대 높이 (mm)")
    ap.add_argument("--no-heavy-low", action="store_true", help="무게 규칙(4번)을 끈다")
    ap.add_argument("--lay-landscape", action="store_true", help="가로형(w > h) 책을 모두 눕혀 꽂는다")
    ap.add_argument("--assembly", default=str(HERE / "assembly.scad"))
    ap.add_argument("--skeletal", action="store_true", help="골조형 모듈 (윗판·바닥판·뒷벽에 갈빗대만)")
    ap.add_argument("--bond", action="store_true", help="엇쌓기: 위 칸은 아래 칸 두 개 이상에 걸친다")
    ap.add_argument("--spacer", action="store_true", help="스페이서 받침: 위 칸마다 계단형 받침으로 두 칸 이상을 묶는다")
    ap.add_argument("--max-leg", type=int, default=120, help="스페이서 다리 최대 길이 (mm)")
    ap.add_argument("--target", type=int, help="이 폭 안을 먼저 채운다 (mm, 벽에 쓸 수 있는 폭)")
    ap.add_argument("--max-shim", type=int, default=40, help="괴임 블록 최대 높이 (mm)")
    ap.add_argument("--deep-min", type=float, default=0.75, help="받침이 덮어야 할 깊이 비율")
    ap.add_argument("--weight-ratio", type=float, default=0.5, help="엇쌓기: 받치는 칸의 최소 무게 비율")
    args = ap.parse_args()

    books = json.loads(Path(args.books).read_text())["books"]
    for b in books:
        if args.lay_landscape and b["w"] > b["h"]:
            b["lay"] = True
        b["kg"] = round(book_kg(b), 2)
        if args.skeletal:
            b["skeletal"] = True
    with ThreadPoolExecutor(args.jobs) as ex:
        for b, d in zip(books, ex.map(module_dims, books)):
            b["dims"] = d

    shims = []
    if args.spacer:
        placed, shims = place_spacer(books, args.width, args.max_height, not args.no_heavy_low,
                                     max_leg=args.max_leg, target_mm=args.target)
    elif args.bond:
        placed, shims = place_bond(books, args.width, args.max_height, not args.no_heavy_low,
                                   args.max_shim, deep_min=args.deep_min, weight_ratio=args.weight_ratio)
    else:
        placed = place(books, args.width, args.max_height, not args.no_heavy_low)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "layout.json").write_text(json.dumps(
        {"grid": GRID, "max_height": args.max_height, "heavy_low": not args.no_heavy_low,
         "bond": args.bond or args.spacer, "spacer": args.spacer, "books": placed, "shims": shims}, ensure_ascii=False, indent=1))
    write_assembly(placed, Path(args.assembly))

    for p in placed:
        d = p["dims"]
        flag = "" if d["fits_bed"] else "  ← 출력 범위 초과, 나눠 뽑아야 함"
        flag += "  (눕힘)" if p.get("lay") else ""
        print(f'{p["id"]} {p["label"]:<18} 책 {p["h"]}x{p["w"]}x{p["t"]} {p["kg"]:4.1f}kg  '
              f'모듈 {d["X"]:.0f}x{d["Y"]:.0f}x{d["Z"]:.0f}  위치 x={p["pos"][0]} z={p["pos"][2]}{flag}')
    xmax = max(p["pos"][0] + p["dims"]["X"] for p in placed)
    zmax = max(p["pos"][2] + p["dims"]["Z"] for p in placed)
    kg = sum(p["kg"] for p in placed)
    com = sum(p["kg"] * (p["pos"][2] + p["dims"]["Z"] / 2) for p in placed) / kg
    print(f"전체 폭 {xmax:.0f} mm, 높이 {zmax:.0f} mm, 책 무게 합 {kg:.1f} kg, "
          f"책 무게중심 높이 {com:.0f} mm")
    if args.spacer:
        ups = [p for p in placed if p["pos"][2] > 0]
        legs = [s for s in shims if s["kind"] == "leg"]
        vol = sum(s["X"] * s["Y"] * s["H"] for s in shims) / 1000
        print(f"위 칸 {len(ups)}개 모두 스페이서로 두 칸 이상에 걸침, 스페이서 {len(ups)}개 "
              f"(다리 {len(legs)}개, 다리 최대 {max([s['H'] for s in legs] or [0])} mm, 꽉 채운 부피 {vol:.0f} cm³)")
    elif args.bond:
        ups = [p for p in placed if p["pos"][2] > 0]
        print(f"위 칸 {len(ups)}개 모두 두 칸 이상에 걸침, 괴임 {len(shims)}개 "
              f"(높이 {sorted(set(s['H'] for s in shims))} mm)")

    if args.stl:
        stl = Path(args.stl)
        stl.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(args.jobs) as ex:
            for i in ex.map(lambda b: export_stls(b, stl), books):
                print("STL", i)
        # 꽉 채운 부피 기준이라 실제 출력(벽 몇 겹 + 채움)은 이보다 가볍다
        vols = {p: sum(stl_volume_cm3(stl / f"{b['id']}_{p}.stl") for b in books)
                for p in ("module", "shoe", "wedge")}
        total = sum(vols.values())
        print("부피(cm³): " + ", ".join(f"{k} {v:.0f}" for k, v in vols.items()) +
              f" → PETG 최대 {total * 1.27 / 1000:.1f} kg (권당 평균 {total * 1.27 / len(books):.0f} g)")


if __name__ == "__main__":
    main()

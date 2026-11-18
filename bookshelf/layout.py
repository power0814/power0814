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
    args = ap.parse_args()

    books = json.loads(Path(args.books).read_text())["books"]
    for b in books:
        if args.lay_landscape and b["w"] > b["h"]:
            b["lay"] = True
        b["kg"] = round(book_kg(b), 2)
    with ThreadPoolExecutor(args.jobs) as ex:
        for b, d in zip(books, ex.map(module_dims, books)):
            b["dims"] = d

    placed = place(books, args.width, args.max_height, not args.no_heavy_low)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "layout.json").write_text(json.dumps(
        {"grid": GRID, "max_height": args.max_height, "heavy_low": not args.no_heavy_low,
         "books": placed}, ensure_ascii=False, indent=1))
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

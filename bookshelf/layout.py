#!/usr/bin/env python3
"""책 목록 → 모듈 치수 → 쌓는 위치 → layout.json / assembly.scad / STL.

쌓는 규칙 (중력 + 받침):
  1. 책은 들어온 순서대로 하나씩 놓는다. 모든 모듈은 뒷면을 벽에 붙인다.
  2. 놓을 수 있는 자리 중 가장 낮은 곳에 놓는다. 높이가 같으면 왼쪽부터.
  3. 바닥이 아닌 곳에 놓으려면 아래 모듈이 받쳐야 한다.
     - 닿는 면의 좌우 범위 안에 모듈의 중심이 들어갈 것
     - 닿는 면이 모듈 깊이의 75% 이상일 것 (앞으로 크게 내밀지 않기)
     - 닿는 면적이 바닥 면적의 40% 이상일 것
  4. 정해 둔 폭 안에 자리가 없으면 오른쪽으로 한 칸 넓힌다.

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


def place(books, width_mm):
    nx = 400                                  # 넉넉한 좌우 칸 수
    ny = int(max(b["dims"]["Y"] for b in books) // GRID)
    hmap = np.zeros((nx, ny), dtype=int)      # 각 격자 칸의 현재 높이(mm), y=0이 벽
    limit = width_mm // GRID
    placed = []
    for b in books:
        d = b["dims"]
        X, Y, Z = int(d["X"] // GRID), int(d["Y"] // GRID), int(d["Z"])
        while True:
            best = None
            for x0 in range(0, limit - X + 1):
                foot = hmap[x0:x0 + X, 0:Y]
                base = int(foot.max())
                if base > 0:
                    contact = foot == base
                    xs = np.where(contact.any(axis=1))[0]
                    ys = np.where(contact.any(axis=0))[0]
                    centred = xs.min() + 0.25 <= X / 2 <= xs.max() + 1 - 0.25
                    deep = (ys.max() + 1) >= 0.75 * Y
                    area = contact.sum() >= 0.4 * X * Y
                    if not (centred and deep and area):
                        continue
                if best is None or base < best[0]:
                    best = (base, x0)
            if best:
                break
            limit += X                        # 자리가 없으면 옆으로 넓힌다
        base, x0 = best
        hmap[x0:x0 + X, 0:Y] = base + Z
        placed.append({**b, "pos": [x0 * GRID, -d["Y"], base]})
    return placed


def write_assembly(placed, path):
    lines = [
        "// layout.py가 만든 파일. 수정은 books.json에서.",
        "use <book_module.scad>",
        "",
        "color(\"#D9D6D0\") translate([-60, 0, -1]) cube([1000, 10, 1400]);   // 벽",
    ]
    for p in placed:
        x, y, z = p["pos"]
        lines.append(
            f'translate([{x}, {y}, {z}]) preview({p["h"]}, {p["w"]}, {p["t"]}, '
            f'"{p["id"]}", "{p["date"]}", "{p["color"]}");  // {p["label"]}'
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
    args = ap.parse_args()

    books = json.loads(Path(args.books).read_text())["books"]
    with ThreadPoolExecutor(args.jobs) as ex:
        for b, d in zip(books, ex.map(module_dims, books)):
            b["dims"] = d

    placed = place(books, args.width)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "layout.json").write_text(json.dumps({"grid": GRID, "books": placed},
                                                ensure_ascii=False, indent=1))
    write_assembly(placed, HERE / "assembly.scad")

    for p in placed:
        d = p["dims"]
        flag = "" if d["fits_bed"] else "  ← 출력 범위 초과, 나눠 뽑아야 함"
        print(f'{p["id"]} {p["label"]:<18} 책 {p["h"]}x{p["w"]}x{p["t"]}  '
              f'모듈 {d["X"]:.0f}x{d["Y"]:.0f}x{d["Z"]:.0f}  위치 x={p["pos"][0]} z={p["pos"][2]}{flag}')
    xmax = max(p["pos"][0] + p["dims"]["X"] for p in placed)
    zmax = max(p["pos"][2] + p["dims"]["Z"] for p in placed)
    print(f"전체 폭 {xmax:.0f} mm, 높이 {zmax:.0f} mm")

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

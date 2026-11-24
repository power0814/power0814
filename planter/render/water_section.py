"""물길 그림: 한 층의 단면과 물받이 평면에 물 흐름을 그린다.

python3 planter/render/water_section.py   →  planter/renders/cross_water.png
"""
import re, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCAD = ROOT / "cross_floor.scad"
tmp = Path(tempfile.mkdtemp())

def section(name, body):
    f = tmp / f"{name}.scad"
    f.write_text(f'include <{SCAD}>\npart = "none";\n$fn = 120;\n{body};\n')
    subprocess.run(["openscad", "-o", str(tmp / f"{name}.svg"), str(f)], check=True, capture_output=True)
    return re.findall(r'<path d="([^"]+)"', (tmp / f"{name}.svg").read_text())

WATER = "#1F6FD1"
INK = "#2B2B2B"

def panel(title, paths, box, scale, arrows=(), labels=(), dashed=(), note=None):
    """box = (x0, x1, v0, v1) 모델 좌표 (v 위). arrows: [(x, v), ...] 꺾은선. labels: (x, v, text, anchor)."""
    x0, x1, v0, v1 = box
    W, H = (x1 - x0) * scale, (v1 - v0) * scale
    fs = 15 / scale
    out = [f'<figure><figcaption>{title}</figcaption>'
           f'<svg width="{W:.0f}" height="{H:.0f}" viewBox="{x0} {-v1} {x1 - x0} {v1 - v0}">',
           f'<defs><marker id="a{id(paths)}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
           f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{WATER}"/></marker></defs>',
           f'<g fill="#BFDCF7" stroke="#24507F" stroke-width="{0.9 / scale}">',
           *[f'<path d="{d}"/>' for d in paths], '</g>']
    for pts in dashed:
        out.append(f'<polyline points="{" ".join(f"{x},{-v}" for x, v in pts)}" fill="none" stroke="{WATER}" '
                   f'stroke-width="{2.2 / scale}" stroke-dasharray="{5 / scale} {4 / scale}" marker-end="url(#a{id(paths)})"/>')
    for pts in arrows:
        out.append(f'<polyline points="{" ".join(f"{x},{-v}" for x, v in pts)}" fill="none" stroke="{WATER}" '
                   f'stroke-width="{3 / scale}" stroke-linejoin="round" marker-end="url(#a{id(paths)})"/>')
    for lab in labels:                  # (x, v, 글, 정렬[, (가리키는 x, v)])
        x, v, t, anc = lab[:4]
        if len(lab) > 4:
            tx, tv = lab[4]
            out.append(f'<line x1="{x}" y1="{-v - fs * 0.35}" x2="{tx}" y2="{-tv}" stroke="{INK}" stroke-width="{1 / scale}"/>'
                       f'<circle cx="{tx}" cy="{-tv}" r="{2 / scale}" fill="{INK}"/>')
        out.append(f'<text x="{x}" y="{-v}" font-size="{fs}" fill="{INK}" text-anchor="{anc}" '
                   f'paint-order="stroke" stroke="#FBFAF7" stroke-width="{3 / scale}">{t}</text>')
    out.append('</svg>')
    if note:
        out.append(f'<p>{note}</p>')
    out.append('</figure>')
    return "\n".join(out)

# A. 팔 축을 지나는 세로 단면 (y = 0)
A = section("A", "projection(cut = true) rotate([-90, 0, 0]) union() { core(); arm(); tray_full(); gate(); "
                 "translate([0, 0, Hf]) core(); }")
pA = panel("① 팔 축 단면 — 위에서 떨어진 물이 받이 지붕을 타고 팔 쪽 구멍으로 나가 물받이 가운데 물길로 떨어진다",
           A, (-45, 330, -78, 110), 3.6,
           arrows=[[(10, 108), (10, 64)], [(14, 58), (40, 32.5), (64, 29.5)], [(66, 22), (66, -45)],
                   [(70, -58), (300, -58)]],
           labels=[(-40, 70, "받이 지붕 (45°)", "start"), (70, 36, "홈통", "start"),
                   (12, 100, "윗층에서 내려온 물", "start"), (100, -52, "가운데 물길 → 바깥 끝", "start"),
                   (270, 30, "마개 손잡이", "start", (247, 35)),
                   (195, 80, "심는 창", "middle")])

# B. 물받이 평면 (z = −45 에서 자른 모습)
B = section("B", "projection(cut = true) translate([0, 0, 45]) union() { core(); arm(); tray_full(); gate(); }")
pB = panel("② 물받이 평면 — 가운데 물길로 바깥 끝까지 가서 양쪽 칸(뿌리 자리)을 거슬러 오고, 넘침 둑을 넘어 골과 주둥이로 나간다",
           B, (-45, 330, -62, 62), 3.6,
           arrows=[[(68, 0), (296, 0)], [(300, 4), (306, 30), (100, 30)], [(300, -4), (306, -30), (100, -30)],
                   [(82, 30), (66, 26), (52, 16)], [(82, -30), (66, -26), (52, -16)]],
           dashed=[[(62, 3), (62, 14)]],
           labels=[(200, 6, "가운데 물길", "middle"), (200, 36, "칸 (뿌리)", "middle"), (200, -40, "칸 (뿌리)", "middle"),
                   (100, 46, "넘침 둑", "start", (75, 34)), (40, 58, "골", "end", (62, 30)),
                   (-5, 56, "주둥이", "end", (50, 20)), (262, -20, "마개", "start", (247, -6)),
                   (-5, -56, "받침 링 홈통 구멍", "end", (41, -16))],
           note="마개를 끼우면 물길이 막혀 머리의 칸막이(점선)를 넘쳐 바로 골로 간다. 그 팔은 윗물을 받지 않는다.")

# C. 주둥이 쪽 세로 단면 (y = 16)
C = section("C", "projection(cut = true) rotate([-90, 0, 0]) translate([0, -16, 0]) union() { core(); arm(); tray_full(); }")
pC = panel("③ 주둥이 단면 — 넘친 물이 받침 링 홈통에 떨어져 코어 벽 구멍으로 들어가, 아래층 받이 지붕으로 떨어진다",
           C, (-10, 110, -80, -20), 9,
           arrows=[[(70, -46), (48, -46), (47, -51)], [(44, -52.5), (36, -52.5), (36, -78)]],
           labels=[(85, -38, "골", "middle"), (60, -30, "주둥이", "middle", (52, -47)), (80, -76, "발꿈치", "middle", (66, -64)),
                   (20, -62, "받침 링 홈통", "end", (47, -53.5)), (30, -30, "코어 속 → 아래층", "end"),
                   (20, -44, "코어 벽 구멍", "end", (42, -51))])

# D. 배수 밸브 (맨 아래 마디, 대각선 단면)
D = section("D", "projection(cut = true) rotate([-90, 0, 0]) rotate(-45) union() { core(-R, true); "
                 "rotate(45) translate([0, 0, sump_z]) { valve_body(); translate([vx, 0, 0]) valve_plug(); } }")
pD = panel("④ 맨 아래 마디 — 집수 바닥과 배수 밸브. 손잡이가 관과 나란하면 열림, 직각이면 닫힘",
           D, (-45, 125, 40, 140), 4.6,
           arrows=[[(10, 136), (10, 88)], [(14, 82), (40, 70), (110, 69)]],
           labels=[(-40, 100, "집수 바닥", "start"), (60, 92, "밸브 마개", "middle"),
                   (112, 80, "호스", "middle"), (12, 128, "맨 아래까지 내려온 물", "start")])

html = f"""<!doctype html><meta charset="utf-8">
<style>
 body {{ margin: 0; background: #FBFAF7; font-family: Pretendard, 'Noto Sans CJK KR', sans-serif; color: {INK}; }}
 main {{ padding: 28px 32px; display: grid; grid-template-columns: auto auto; gap: 18px 36px; align-items: start; }}
 figure {{ margin: 0; }} figcaption {{ font-size: 15px; margin-bottom: 6px; max-width: 1350px; }}
 p {{ font-size: 14px; margin: 4px 0 0; color: #555; }}
 h1 {{ font-size: 20px; margin: 0 0 4px; grid-column: 1 / -1; font-weight: 600; }}
 .wide {{ grid-column: 1 / -1; }}
</style>
<main>
<h1>같이 쓰는 물길 — 맨 위 코어에 부은 물이 층마다 네 팔을 거쳐 아래층으로</h1>
<div class="wide">{pA}</div>
<div class="wide">{pB}</div>
<div>{pC}</div>
<div>{pD}</div>
</main>"""
(tmp / "w.html").write_text(html)
out = ROOT / "renders/cross_water.png"
subprocess.run(["node", "-e", f"""
const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();
const p=await b.newPage({{viewport:{{width:1420,height:800}},deviceScaleFactor:2}});
await p.goto('file://{tmp / "w.html"}');await p.screenshot({{path:'{out}',fullPage:true}});await b.close();}})()"""],
               check=True, cwd=ROOT.parent)
print("wrote", out)

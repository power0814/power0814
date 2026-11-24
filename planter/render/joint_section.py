"""팔과 코어 이음 단면 그림 (팔 축을 지나는 세로 단면, 코어 오른쪽 절반).

python3 planter/render/joint_section.py   →  planter/renders/cross_joint.png
"""
import re, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
tmp = Path(tempfile.mkdtemp())
scad = tmp / "sec.scad"
scad.write_text(f'''use <{ROOT}/cross_floor.scad>
Hf = 270;
intersection() {{
  projection(cut = true) rotate([-90, 0, 0]) union() {{ core(); arm(); translate([0, 0, Hf]) core(); }}
  translate([-5, -90]) square([150, 260]);
}}
''')
subprocess.run(["openscad", "-o", str(tmp / "sec.svg"), str(scad)], check=True, capture_output=True)
paths = re.findall(r'<path d="([^"]+)"', (tmp / "sec.svg").read_text())

X0, X1, Z0, Z1 = -5, 145, -88, 168          # 보이는 범위 (mm)
S = 6                                       # px / mm
W, H = (X1 - X0) * S + 300, (Z1 - Z0) * S
def p(x, z): return f"{(x - X0) * S:.1f},{(Z1 - z) * S:.1f}"
labels = [  # (점 x, z, 글자 x, z, 글)
    (44, 20, 6, 20, "코어 (벽 2.5)"),
    (50, 50, 6, 62, "걸이 턱 (45°)"),
    (58, 64, 96, 100, "갈고리: 팔 위 벽이 넘어와 턱에 걸린다"),
    (49, -60, 6, -40, "받침 링"),
    (60, -62, 96, -30, "발꿈치: 받침 링을 0.6 mm 틈 두고 마주 봄"),
    (130, 69, 96, 82, "팔 벽 1.6"),
    (43, 125, 60, 150, "위 층 코어: 꽂이가 이 마디 속으로, 어깨(45°)가 위 끝 모따기에 앉는다"),
    (54, 22, 96, 122, "받이 지붕과 홈통 (물길 그림)"),
]
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Pretendard, Noto Sans CJK KR, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#FBFAF7"/>',
       f'<g transform="translate({-X0 * S},{Z1 * S}) scale({S},{S})"><g fill="#9CC8F2" stroke="#1D4F86" stroke-width="0.12">',
       *[f'<path d="{d}"/>' for d in paths], '</g></g>',
       f'<line x1="{p(X0, 0).split(",")[0]}" y1="{p(0, 0).split(",")[1]}" x2="{(X1 - X0) * S}" y2="{p(0, 0).split(",")[1]}" stroke="#B9B2A6" stroke-dasharray="6 5"/>',
       f'<text x="{(X1 - X0) * S - 6}" y="{p(0, 0).split(",")[1]}" dy="-6" text-anchor="end" font-size="15" fill="#8A8276">팔 축</text>']
for x, z, tx, tz, t in labels:
    a, b = p(x, z).split(","); c, d = p(tx, tz).split(",")
    svg.append(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="#3A3A3A" stroke-width="1"/><circle cx="{a}" cy="{b}" r="3" fill="#3A3A3A"/>')
    svg.append(f'<text x="{c}" y="{d}" dx="4" dy="-5" font-size="17" fill="#222">{t}</text>')
# 짝힘 화살표: 갈고리는 팔 위를 코어 쪽으로 당기고, 받침 링은 팔 아래를 밖으로 민다
def arrow(x, z, dx, dz, col):
    a, b = p(x, z).split(","); c, d = p(x + dx, z + dz).split(",")
    return (f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="{col}" stroke-width="3" marker-end="url(#h)"/>')
svg.insert(1, '<defs><marker id="h" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#C2410C"/></marker></defs>')
svg += [arrow(82, 40, -22, 0, "#C2410C"), arrow(82, -46, 22, 0, "#C2410C"), arrow(128, 20, 0, -36, "#C2410C"),
        f'<text x="{p(70, 33).split(",")[0]}" y="{p(70, 33).split(",")[1]}" font-size="15" fill="#C2410C">당김</text>',
        f'<text x="{p(84, -53).split(",")[0]}" y="{p(84, -53).split(",")[1]}" font-size="15" fill="#C2410C">누름</text>',
        f'<text x="{p(116, -22).split(",")[0]}" y="{p(116, -22).split(",")[1]}" font-size="15" fill="#C2410C">흙 무게</text>',
        '</svg>']
html = tmp / "sec.html"
html.write_text('<!doctype html><meta charset="utf-8"><body style="margin:0">' + "\n".join(svg))
out = ROOT / "renders/cross_joint.png"
subprocess.run(["node", "-e", f"""
const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();
const p=await b.newPage({{viewport:{{width:{W},height:{H}}},deviceScaleFactor:2}});
await p.goto('file://{html}');await p.screenshot({{path:'{out}'}});await b.close();}})()"""], check=True)
print("wrote", out)

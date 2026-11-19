"""줄눈 단면 (해석한 클립 상세). 벽에서 앞쪽으로 자른 단면, 축척 그대로.

python3 structure/joint.py → out/runs/fig_joint.html
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
L = json.load(open(ROOT / "out/runs/layout.json"))
P = L["params"]
S = 2.6                      # px / mm
OX, OY = 90, 300             # 원점 (y = 0 벽, z = 0 아래 책 머리)
Y = lambda y: OX + y * S     # noqa: E731
Z = lambda z: OY - z * S     # noqa: E731
r = P["rod_r"]
zc = P["cap_t"]              # 막대 중심
w_low, w_up = 220.0, 152.0   # 아래 책 (예: 04), 위 책 (예: 18)
y0 = P["y0"]
rows_low = [y for y in P["rows"] if y <= y0 + w_low - P["edge"]]
rows_up = [y for y in rows_low if y <= y0 + w_up - P["edge"]]
z_shoe0 = zc + r                      # 받침 바닥 = 막대 윗면
z_floor = z_shoe0 + 4                 # 받침 판
wedge = 6.0                           # 쐐기 두께 (그림용)
z_book = z_floor + wedge

o = []
part = "#D8D2C7"; partline = "#8E877B"; rod = "#6F6455"; book = "#4A5552"; acc = "#C9663D"
# 벽
o.append(f'<rect x="{Y(-12)}" y="{Z(70)}" width="{12 * S}" height="{125 * S}" fill="#CFC9BF"/>')
o.append(f'<line x1="{Y(0)}" y1="{Z(70)}" x2="{Y(0)}" y2="{Z(-55)}" stroke="var(--ink)" stroke-width="1.2"/>')
# 아래 책
o.append(f'<rect x="{Y(y0)}" y="{Z(0)}" width="{w_low * S}" height="{50 * S}" fill="{book}"/>')
# 덮개: 판 + 막대마다 아래에서 감싸는 클립
o.append(f'<rect x="{Y(y0)}" y="{Z(4)}" width="{w_low * S}" height="{4 * S}" fill="{part}" stroke="{partline}"/>')
for yr in rows_low:
    R = r + 2.6
    # 아래쪽 220° 를 감싸는 C
    import math
    a0, a1 = math.radians(-20), math.radians(200)
    p0 = (Y(yr + R * math.cos(a0)), Z(zc + R * math.sin(a0)))
    p1 = (Y(yr + R * math.cos(a1)), Z(zc + R * math.sin(a1)))
    o.append(f'<path d="M {p0[0]:.1f} {p0[1]:.1f} A {R * S:.1f} {R * S:.1f} 0 1 1 {p1[0]:.1f} {p1[1]:.1f}" '
             f'fill="none" stroke="{part}" stroke-width="{2.6 * S:.1f}"/>')
    o.append(f'<rect x="{Y(yr - 5)}" y="{Z(zc)}" width="{10 * S}" height="{(zc - 4) * S}" fill="{part}"/>')
# 받침 (위 책 깊이만큼) + 막대 위에 앉는 홈
o.append(f'<rect x="{Y(y0)}" y="{Z(z_floor)}" width="{w_up * S}" height="{4 * S}" fill="{part}" stroke="{partline}"/>')
for yr in rows_up:
    R = r + 2.0
    a0, a1 = math.radians(200), math.radians(340)
    p0 = (Y(yr + R * math.cos(a0)), Z(zc - R * math.sin(a0)))
    p1 = (Y(yr + R * math.cos(a1)), Z(zc - R * math.sin(a1)))
    o.append(f'<path d="M {Y(yr - 9):.1f} {Z(z_shoe0):.1f} L {Y(yr + 9):.1f} {Z(z_shoe0):.1f}" stroke="{part}" stroke-width="{4 * S}"/>')
    o.append(f'<path d="M {p0[0]:.1f} {p0[1]:.1f} A {R * S:.1f} {R * S:.1f} 0 0 1 {p1[0]:.1f} {p1[1]:.1f}" '
             f'fill="none" stroke="{part}" stroke-width="{2.4 * S:.1f}"/>')
# 막대
for yr in rows_low:
    o.append(f'<circle cx="{Y(yr)}" cy="{Z(zc)}" r="{r * S}" fill="{rod}"/>')
# 쐐기 (앞으로 당겨 뺀다)
o.append(f'<path d="M {Y(y0 + 4)} {Z(z_floor)} L {Y(y0 + w_up + 14)} {Z(z_floor)} L {Y(y0 + w_up + 14)} {Z(z_floor + wedge)} '
         f'L {Y(y0 + 4)} {Z(z_floor + 2)} Z" fill="{acc}"/>')
o.append(f'<rect x="{Y(y0 + w_up + 6)}" y="{Z(z_floor + wedge + 8)}" width="{8 * S}" height="{(wedge + 8) * S}" fill="{acc}"/>')
# 위 책
o.append(f'<rect x="{Y(y0)}" y="{Z(z_book + 45)}" width="{w_up * S}" height="{45 * S}" fill="{book}"/>')


def label(x, y, tx, ty, text, sub=None):
    o.append(f'<line x1="{x}" y1="{y}" x2="{tx}" y2="{ty}" stroke="var(--muted)" stroke-width="1"/>')
    o.append(f'<circle cx="{x}" cy="{y}" r="2.4" fill="var(--ink)"/>')
    o.append(f'<text x="{tx + 6}" y="{ty + 4}" class="leg">{text}</text>')
    if sub:
        o.append(f'<text x="{tx + 6}" y="{ty + 21}" class="legm">{sub}</text>')


RX = Y(270)
label(Y(120), Z(z_book + 20), RX, Z(z_book + 32), "위 책", "발이 쐐기 위에 선다")
label(Y(y0 + w_up + 10), Z(z_floor + 10), RX, Z(z_floor + 12), "쐐기 · 앞으로 당겨 뺀다", "빼면 책이 2 mm 내려가 덮개에서 떨어진다")
label(Y(60), Z(z_floor + 2), RX, Z(z_floor - 6), "받침 · 막대 위에 끼운다 (같은 클립)", "책을 빼도 남는다")
label(Y(rows_low[-1]), Z(zc), RX, Z(zc - 18), "막대 · 줄눈 보 (출력이면 PETG Ø16)", f"벽에서 {', '.join(str(int(v)) for v in rows_low)} mm · 그림은 Ø{2 * r:.0f}")
label(Y(130), Z(2), RX, Z(-26), "덮개 · 막대를 감싸는 클립, 위아래 유격 0.2 mm", "누를 땐 홈에 앉고, 0.2 mm 넘게 들리면 걸린다 · 책을 빼도 남는다")
label(Y(150), Z(-25), RX, Z(-50), "아래 책", "머리가 덮개를 받친다 (압축만)")
o.append(f'<text x="{Y(-6)}" y="{Z(-55) + 18}" class="legm" text-anchor="middle">벽</text>')

W, H = int(RX + 360), int(Z(-55) + 60)
doc = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Joint Section</title>
<style>
:root {{ --bg:#F3F0EA; --ink:#1D1D1B; --muted:#77726A; --accent:#C9663D; }}
html,body {{ margin:0; background:var(--bg); }}
body {{ font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif; color:var(--ink); }}
.t1 {{ font-size:24px; font-weight:700; }} .t2 {{ font-size:14px; fill:var(--muted); }}
.leg {{ font-size:14px; font-weight:700; }} .legm {{ font-size:12.5px; fill:var(--muted); }}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
<text x="40" y="44" class="t1">줄눈 단면 · 해석한 상세</text>
<text x="40" y="68" class="t2">벽에서 앞으로 자른 단면, 실제 축척. 책을 뺄 때 빠지는 것은 책과 쐐기뿐이고 덮개·막대·받침은 남는다.</text>
{chr(10).join(o)}
</svg><script>window.__done = true;</script></body></html>'''
(ROOT / "out/runs/fig_joint.html").write_text(doc)
print("wrote out/runs/fig_joint.html", W, H)

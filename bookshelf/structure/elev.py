"""배치 정면도 (runs / bond 공통). 책은 책 색, 받침(계단형 포함)·덮개·기둥은 출력 부품 색, 막대는 짙은 색.

python3 structure/elev.py out/runs/layout.json:지금 out/bond/layout.json:엇갈림 ... --out out/bond/elev.html
"""
import argparse
import html
import json
from pathlib import Path

S = 0.5


def draw(L, ox, oy, title, Hmax, removed=(), note=None):
    P = L["params"]
    o = []
    X = lambda x: ox + x * S                 # noqa: E731
    Z = lambda z: oy + (Hmax - z) * S        # noqa: E731
    o.append(f'<text x="{ox}" y="{oy - 18}" class="cap">{html.escape(title)}</text>')
    o.append(f'<line x1="{X(-15)}" y1="{Z(0)}" x2="{X(L["width"] + 15)}" y2="{Z(0)}" stroke="var(--ink)" stroke-width="1.2"/>')
    part, rod, pier = "#D8D2C7", "#6F6455", "#BFB6A8"
    runs = {r["id"]: r for r in L["runs"]}
    for p in L.get("piers", []):
        for s in p["supports"]:
            o.append(f'<rect x="{X(s["x0"])}" y="{Z(p["top"])}" width="{(s["x1"] - s["x0"]) * S}" '
                     f'height="{(p["top"] - s["base"]) * S}" fill="{pier}"/>')
        # 계단형 윗면: 이 기둥을 쓰는 줄 중 낮은 쪽
        for rid in p["runs"]:
            lv = runs[rid]["level"]
            if lv < p["top"]:
                left = runs[rid]["x1"] - P["pier_w"] <= p["x0"] + 1e-6
                xa, xb = (p["xc"], p["x1"]) if left else (p["x0"], p["xc"])
                if xb - xa > 0 and p["top"] - lv - P["rod_r"] > 0:
                    o.append(f'<rect x="{X(xa)}" y="{Z(p["top"])}" width="{(xb - xa) * S}" height="{(p["top"] - lv - P["rod_r"]) * S}" fill="#F3F0EA"/>')
    for b in L["books"]:
        sups = b.get("supports") or [dict(x0=b["x0"], x1=b["x1"], base=(runs[b["base"]]["level"] if b["base"] else 0.0))]
        for s in sups:
            o.append(f'<rect x="{X(s["x0"] + 0.6)}" y="{Z(b["z_foot"])}" width="{max(0.0, s["x1"] - s["x0"] - 1.2) * S}" '
                     f'height="{(b["z_foot"] - s["base"]) * S}" fill="{part}"/>')
        o.append(f'<rect x="{X(b["x0"] + 0.6)}" y="{Z(b["z_head"] + 4)}" width="{(b["x1"] - b["x0"] - 1.2) * S}" height="{4 * S}" fill="{part}"/>')
        if P.get("post"):   # 책마다 골조: 책등 양옆의 앞 기둥 (받침 바닥에서 덮개 위까지)
            px = P["post"][0]
            for xa in (b["x0"] + 0.5, b["x1"] - 0.5 - px):
                base = min(s["base"] for s in sups if s["x0"] - 1e-6 <= xa + px / 2 <= s["x1"] + 1e-6) \
                    if any(s["x0"] - 1e-6 <= xa + px / 2 <= s["x1"] + 1e-6 for s in sups) else sups[0]["base"]
                o.append(f'<rect x="{X(xa)}" y="{Z(b["z_head"] + 4)}" width="{px * S}" height="{(b["z_head"] + 4 - base) * S}" fill="#CFC6B8"/>')
        bx0, bx1 = b["x0"] + P["side"], b["x1"] - P["side"]
        if b["id"] in removed:
            o.append(f'<rect x="{X(bx0)}" y="{Z(b["z_head"])}" width="{(bx1 - bx0) * S}" height="{b["h"] * S}" fill="none" '
                     f'stroke="var(--accent)" stroke-width="1.4" stroke-dasharray="4 3"/>')
        else:
            o.append(f'<rect x="{X(bx0)}" y="{Z(b["z_head"])}" width="{(bx1 - bx0) * S}" height="{b["h"] * S}" fill="{b.get("color") or "#888"}"/>')
    for r in L["runs"]:
        if r["rows"]:
            o.append(f'<rect x="{X(r["x0"])}" y="{Z(r["level"] + P["rod_r"])}" width="{(r["x1"] - r["x0"]) * S}" '
                     f'height="{2 * P["rod_r"] * S}" rx="{P["rod_r"] * S}" fill="{rod}"/>')
    o.append(f'<text x="{ox}" y="{Z(0) + 22}" class="capm">{L["width"]:.0f} × {L["height"]:.0f} mm'
             + (f' · {html.escape(note)}' if note else "") + '</text>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+", help="layout.json:제목")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="배치 비교")
    a = ap.parse_args()
    Ls = []
    for it in a.items:
        path, _, title = it.partition(":")
        Ls.append((json.load(open(path)), title or path))
    Hmax = max(L["height"] for L, _ in Ls) + 30
    gap, x, panels = 70, 50, []
    for L, title in Ls:
        panels.append(draw(L, x, 110, title, Hmax)); x += L["width"] * S + gap
    W, H = int(x), int(110 + Hmax * S + 50)
    doc = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Layouts</title>
<style>
:root {{ --bg:#F3F0EA; --ink:#1D1D1B; --muted:#77726A; --accent:#C9663D; }}
html,body {{ margin:0; background:var(--bg); }}
body {{ font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif; color:var(--ink); }}
.cap {{ font-size:16px; font-weight:700; }} .capm {{ font-size:12.5px; fill:var(--muted); }} .t1 {{ font-size:22px; font-weight:700; }}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
<text x="50" y="44" class="t1">{html.escape(a.title)}</text>
{chr(10).join(panels)}
</svg><script>window.__done = true;</script></body></html>'''
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(doc)
    print("wrote", a.out, W, H)


if __name__ == "__main__":
    main()

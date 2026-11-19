"""2안 하중 그림: 정면도에 책마다 받는 하중(위에서 내려오는 힘)과, 한 권을 뺐을 때의 변화를 그린다.

python3 structure/figure.py [--mat petg12] [--remove 04,20] → out/runs/fig_load.html (PNG 는 render/shoot.mjs 로)
"""
import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import model as MD  # noqa: E402
from analyze import case, cap_drop, DROP, CLEAR  # noqa: E402

ROOT = Path(__file__).parent.parent
S = 0.62            # px / mm
EXAG = 150          # 처짐 과장 배율


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def panel(L, ox, oy, title, sub, fill, labels, removed=(), defl=None, note=None):
    P = L["params"]
    H = L["height"]
    out = []
    X = lambda x: ox + x * S            # noqa: E731
    Z = lambda z: oy + (H - z) * S      # noqa: E731
    out.append(f'<text x="{ox}" y="{oy - 46}" class="cap">{html.escape(title)}</text>')
    out.append(f'<text x="{ox}" y="{oy - 26}" class="capm">{html.escape(sub)}</text>')
    out.append(f'<line x1="{X(-20)}" y1="{Z(0)}" x2="{X(L["width"] + 20)}" y2="{Z(0)}" stroke="var(--ink)" stroke-width="1.2"/>')
    runs = {r["id"]: r for r in L["runs"]}
    for b in L["books"]:
        base = runs[b["base"]]["level"] if b["base"] else 0.0
        x0, x1 = b["x0"] + 0.6, b["x1"] - 0.6
        # 받침
        out.append(f'<rect x="{X(x0)}" y="{Z(b["z_foot"])}" width="{(x1 - x0) * S}" height="{(b["z_foot"] - base) * S}" '
                   f'fill="#D8D2C7"/>')
        # 덮개 (머리 위 4 mm)
        out.append(f'<rect x="{X(x0)}" y="{Z(b["z_head"] + 4)}" width="{(x1 - x0) * S}" height="{4 * S}" fill="#D8D2C7"/>')
        bx0, bx1 = b["x0"] + P["side"], b["x1"] - P["side"]
        if b["id"] in removed:
            out.append(f'<rect x="{X(bx0)}" y="{Z(b["z_head"])}" width="{(bx1 - bx0) * S}" height="{b["h"] * S}" '
                       f'fill="none" stroke="var(--ink)" stroke-width="1.2" stroke-dasharray="5 3"/>')
        else:
            out.append(f'<rect x="{X(bx0)}" y="{Z(b["z_head"])}" width="{(bx1 - bx0) * S}" height="{b["h"] * S}" '
                       f'fill="{fill(b)}"/>')
        lab = labels(b)
        if lab:   # 책 안쪽 위에서부터 세로로
            cx, cy = X((bx0 + bx1) / 2) + 3.5, Z(b["z_head"]) + 6
            out.append(f'<text x="{cx:.1f}" y="{cy:.1f}" class="num" transform="rotate(90 {cx:.1f} {cy:.1f})">'
                       f'{html.escape(lab)}</text>')
    # 막대 (정면에서 보이는 가장 앞 줄)
    for r in L["runs"]:
        if not r["rows"]:
            continue
        out.append(f'<rect x="{X(r["x0"])}" y="{Z(r["level"] + P["rod_r"])}" width="{(r["x1"] - r["x0"]) * S}" '
                   f'height="{2 * P["rod_r"] * S}" rx="{P["rod_r"] * S}" fill="#6F6455"/>')
    if defl:
        for pts in defl:
            d = " ".join(f'{"M" if i == 0 else "L"} {X(x):.1f} {Z(z):.1f}' for i, (x, z) in enumerate(pts))
            out.append(f'<path d="{d}" fill="none" stroke="var(--accent)" stroke-width="1.6"/>')
    if note:
        for i, line in enumerate(note):
            out.append(f'<text x="{ox}" y="{Z(0) + 28 + 18 * i}" class="capm">{html.escape(line)}</text>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default=str(ROOT / "out/runs/layout.json"))
    ap.add_argument("--mat", default="petg12")
    ap.add_argument("--remove", default="04,20")
    ap.add_argument("--out", default=str(ROOT / "out/runs/fig_load.html"))
    a = ap.parse_args()
    L = json.load(open(a.layout))
    base = case(L, a.mat)
    F0 = base["head_force"]
    fmax = max(F0.values())
    panels = []
    W = L["width"] * S
    gap = 120
    oy = 120
    panels.append(panel(
        L, 60, oy, "책이 받는 하중 · 전부 꽂혔을 때",
        f"위에서 내려오는 힘, 최대 {fmax:.0f} N ({max(F0, key=F0.get)}번)",
        fill=lambda b: mix("#ECE8E0", "#2F3A37", min(1.0, F0.get(b["id"], 0) / fmax) ** 0.7),
        labels=lambda b: f'{F0.get(b["id"], 0):.0f} N' if F0.get(b["id"], 0) >= 8 else "",
        note=[f"책·받침·덮개·막대 합계 {base['load_total'] / 9.81:.1f} kg",
              f"막대 최대 휨응력 {base['sigma_max']:.2f} MPa"]))
    for k, rid in enumerate(a.remove.split(",")):
        res = case(L, a.mat, removed={rid})
        F1 = res["head_force"]
        dF = {b: F1.get(b, 0.0) - F0.get(b, 0.0) for b in F0 if b != rid}
        dmax = max(abs(v) for v in dF.values())
        drop = cap_drop(L, base, res, [rid])
        info, u = res["_info"], res["_u"]
        book = next(b for b in L["books"] if b["id"] == rid)
        run = next(r for r in L["runs"] if r["id"] == book["run"])
        defl = []
        for (rr, y), rod in info["rods"].items():
            if rr != run["id"] or y != max(run["rows"]):
                continue
            defl.append([(x, run["level"] + EXAG * u[n[0]]) for x, n in zip(rod["xs"], rod["nodes"])])

        def fill(b, dF=dF, dmax=dmax):
            v = dF.get(b["id"], 0.0)
            if abs(v) < 0.5:
                return "#E4DFD6"
            return mix("#E4DFD6", "#C9663D" if v > 0 else "#4F7393", min(1.0, abs(v) / dmax) ** 0.6)

        panels.append(panel(
            L, 60 + (k + 1) * (W + gap), oy, f"{rid}번을 뺐을 때",
            f"실려 있던 {F0.get(rid, 0):.0f} N 이 이웃으로 · 붉은색 = 더 받음",
            fill=fill,
            labels=lambda b, dF=dF: (f'{dF[b["id"]]:+.0f} N' if abs(dF.get(b["id"], 0)) >= 2 else ""),
            removed={rid}, defl=defl,
            note=[f"덮개가 따라 내려온 거리 {drop:.2f} mm (꺼낼 수 있는 한도 {DROP - CLEAR:.1f})",
                  f"막대 최대 휨응력 {res['sigma_max']:.2f} MPa · 막대 처짐 ×{EXAG} (주황 선)"]))
    width = 60 + (1 + len(a.remove.split(","))) * (W + gap)
    height = oy + L["height"] * S + 90
    doc = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Load Paths</title>
<style>
:root {{ --bg:#F3F0EA; --ink:#1D1D1B; --muted:#77726A; --accent:#C9663D; }}
html,body {{ margin:0; background:var(--bg); }}
body {{ font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif; color:var(--ink); }}
.cap {{ font-size:17px; font-weight:700; }} .capm {{ font-size:13px; fill:var(--muted); }}
.num {{ font-size:10px; font-weight:700; fill:var(--ink); font-family:"DejaVu Sans Mono",monospace;
        paint-order:stroke; stroke:#F3F0EA; stroke-width:2.4px; }}
.t1 {{ font-size:24px; font-weight:700; }}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}">
<text x="60" y="44" class="t1">책이 기둥, 막대가 줄눈 보 · 하중이 가는 길</text>
{chr(10).join(panels)}
</svg>
<script>window.__done = true;</script>
</body></html>'''
    Path(a.out).write_text(doc)
    print(f"wrote {a.out} ({width:.0f} × {height:.0f})")


if __name__ == "__main__":
    main()

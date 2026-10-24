#!/usr/bin/env python3
"""Build the recipe pages and the share-card images for the First Spoon site.

Usage:
  python3 tools/build.py [--photos "/path/to/Assets/Food photos/dishes"]

Reads data/plan-and-recipes.json (a copy of the app's content file), writes
  recipe/<id>.html      one page per recipe, noindex, not linked from the site
  img/dishes/<id>.png   the dish cut-out, when a photo exists (330 px)
  img/og/<id>.jpg       the 1200 x 630 share card (Open Graph image) per recipe
  img/og/list.jpg       the share card for list.html
Photos are copied from --photos (files named <id>-spoon.png or <id>-finger.png);
without the flag the photos already in img/dishes are reused.
"""
import argparse, html, json, os, re, shutil, sys
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://boyantasevski.github.io/first-spoon-site"
DATA = ROOT / "data" / "plan-and-recipes.json"

STAGE = {"FT": ("First tastes", "from 6 months"), "S1": ("Stage 1", "from 6 months"),
         "S2": ("Stage 2", "from 9 months"), "S3": ("Stage 3", "from 12 months")}
STAGE_ORDER = ["FT", "S1", "S2", "S3"]


def name_fill(s):
    if not s:
        return s
    return s.replace("{name}'s", "your baby's").replace("{name}", "your baby")


def esc(s):
    return html.escape(name_fill(s or ""), quote=True)


def stage_line(r):
    first = min(r["st"], key=STAGE_ORDER.index)
    label, frm = STAGE[first]
    return f"{label} · {frm}" if first == "FT" else frm.capitalize()


def allergen_text(r, names):
    if not r["al"]:
        return "No common allergens"
    return "Contains: " + ", ".join(names.get(a, a).lower() for a in r["al"])


def facts(r):
    out = []
    if r.get("t"):
        out.append(f"{r['t']} min")
    if r.get("y"):
        y = r["y"]
        out.append(("Makes " + y) if y[0].isdigit() else y)
    if r.get("fz"):
        out.append("Freezes well" if r["fz"].lower().startswith("freezes well") else "Can be frozen")
    if r.get("iron"):
        out.append("Iron-rich")
    return "  ·  ".join(out)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>{title} — First Spoon</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="First Spoon">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{title}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og}">
<style>
  :root {{ color-scheme: light dark; --ink: #000; --ink2: #6e6e73; --bg: #fff; --tile: #f2f2f7; --line: #e5e5ea; --accent: #0a84ff; --card: #fff; --shadow: 0 12px 24px rgba(0,0,0,.08); }}
  @media (prefers-color-scheme: dark) {{ :root {{ --ink: #fff; --ink2: #98989d; --bg: #000; --tile: #1c1c1e; --line: #2c2c2e; --card: #1c1c1e; --shadow: none; }} }}
  body {{ margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.45 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Roboto, Arial, sans-serif; -webkit-text-size-adjust: 100%; }}
  main {{ max-width: 560px; margin: 0 auto; padding: 24px 16px 64px; padding-left: max(16px, env(safe-area-inset-left)); padding-right: max(16px, env(safe-area-inset-right)); }}
  .brand {{ font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink2); margin: 0 0 16px; }}
  .hero {{ margin: 0 0 8px; text-align: center; }}
  .hero img {{ width: 247px; height: 247px; object-fit: contain; filter: drop-shadow(0 12px 18px rgba(0,0,0,.12)); }}
  .stage {{ font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink2); margin: 0 0 4px; }}
  h1 {{ font-size: 28px; line-height: 1.15; margin: 0 0 6px; letter-spacing: -.01em; }}
  .facts {{ color: var(--ink2); margin: 0 0 20px; font-size: 15px; }}
  .tile {{ background: var(--tile); border-radius: 20px; padding: 14px 16px; margin: 0 0 12px; }}
  .tile h2 {{ font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink2); margin: 0 0 6px; }}
  .tile p {{ margin: 0 0 8px; }}
  .tile p:last-child {{ margin-bottom: 0; }}
  .tile.allergens p {{ font-weight: 600; }}
  .tile .note {{ color: var(--ink2); font-size: 15px; font-weight: 400; }}
  h2.section {{ font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink2); margin: 28px 0 8px; }}
  ul.ing {{ list-style: none; margin: 0; padding: 0; background: var(--card); border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow); }}
  ul.ing li {{ display: flex; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--line); }}
  ul.ing li:last-child {{ border-bottom: 0; }}
  ul.ing .q {{ flex: none; min-width: 72px; color: var(--ink2); font-variant-numeric: tabular-nums; }}
  ol.steps {{ margin: 0; padding: 0; list-style: none; counter-reset: step; }}
  ol.steps li {{ position: relative; padding: 10px 0 10px 44px; border-bottom: 1px solid var(--line); counter-increment: step; }}
  ol.steps li:last-child {{ border-bottom: 0; }}
  ol.steps li::before {{ content: counter(step); position: absolute; left: 0; top: 10px; width: 28px; height: 28px; border-radius: 50%; background: var(--ink); color: var(--bg); font-weight: 600; font-size: 14px; display: grid; place-items: center; }}
  ol.steps li.portion {{ padding-left: 44px; font-weight: 600; counter-increment: none; }}
  ol.steps li.portion::before {{ content: "✓"; background: transparent; color: var(--ink); border: 1.5px solid var(--ink); }}
  .foot {{ color: var(--ink2); font-size: 14px; margin: 24px 0 0; }}
  .foot a {{ color: var(--accent); text-decoration: none; }}
  .cta {{ margin: 28px 0 0; padding: 16px; background: var(--tile); border-radius: 20px; font-size: 15px; }}
  .cta b {{ display: block; margin-bottom: 4px; font-size: 17px; }}
</style>
</head>
<body>
<main>
  <p class="brand">First Spoon · Recipe</p>
{hero}  <p class="stage">{stage}</p>
  <h1>{title}</h1>
  <p class="facts">{facts}</p>
  <section class="tile allergens"><h2>Allergens</h2><p>{allergens}</p>{info}</section>
{serve}{intro}{freeze}  <h2 class="section">Ingredients{ing_count}</h2>
  <ul class="ing">
{ingredients}  </ul>
  <h2 class="section">Method{step_count}</h2>
  <ol class="steps">
{steps}  </ol>
{note}  <div class="cta"><b>Made with First Spoon</b>A daily plan for your baby, from the first taste of solid food to the family table at two: what to cook, what comes from the freezer, and when a new allergen is introduced. <a href="../index.html">About First Spoon</a></div>
  <p class="foot">First Spoon follows NHS guidance on <a href="{src_avoid}">foods to avoid</a>, <a href="{src_allergy}">food allergies</a> and <a href="{src_hygiene}">preparing and freezing baby food</a>. It is not medical advice: if your baby has a health condition or a diagnosed allergy, follow your doctor's advice.</p>
</main>
</body>
</html>
"""


def build_page(r, names, sources, has_photo):
    title = r["n"]
    desc_bits = [stage_line(r)]
    if r.get("t"):
        desc_bits.append(f"{r['t']} min")
    desc_bits.append(allergen_text(r, names))
    desc = " · ".join(desc_bits) + ". A First Spoon recipe."
    hero = f'  <figure class="hero"><img src="../img/dishes/{r["id"]}.png" alt=""></figure>\n' if has_photo else ""
    info = ""
    if r.get("info"):
        info = "".join(f'<p class="note">{esc(i)}</p>' for i in r["info"])
    serve = ""
    if r.get("spoon") or r.get("finger"):
        parts = []
        if r.get("spoon"):
            parts.append(f"<p><b>Spoon-fed:</b> {esc(r['spoon'])}</p>")
        if r.get("finger"):
            parts.append(f"<p><b>Baby-led:</b> {esc(r['finger'])}</p>")
        serve = '  <section class="tile"><h2>How to serve</h2>' + "".join(parts) + "</section>\n"
    intro = ""
    if r.get("intro") and r["intro"].get("dose"):
        a = names.get(r["intro"]["allergen"], r["intro"]["allergen"]).lower()
        intro = f'  <section class="tile"><h2>First time with {esc(a)}</h2><p>{esc(r["intro"]["dose"])}</p></section>\n'
    freeze = ""
    if r.get("fz"):
        freeze = f'  <section class="tile"><h2>Freezing</h2><p>{esc(r["fz"])}</p></section>\n'
    ingredients = "".join(f'    <li><span class="q">{esc(q)}</span><span>{esc(n)}</span></li>\n' for q, n in r["ing"])
    steps = ""
    for i, s in enumerate(r["steps"], 1):
        steps += f"    <li>{esc(s)}</li>\n"
        if r.get("fam") and r.get("bs") == i:
            steps += '    <li class="portion">Take your baby\'s portion out here, before any salt.</li>\n'
    note = f'  <p class="foot">{esc(r["note"])}</p>\n' if r.get("note") else ""
    return PAGE.format(
        title=esc(title), desc=esc(desc), url=f"{SITE}/recipe/{r['id']}.html", og=f"{SITE}/img/og/{r['id']}.jpg",
        hero=hero, stage=esc(stage_line(r)), facts=esc(facts(r)), allergens=esc(allergen_text(r, names)), info=info,
        serve=serve, intro=intro, freeze=freeze, ing_count=f" · {len(r['ing'])} items", ingredients=ingredients,
        step_count=f" · {len(r['steps'])} steps", steps=steps, note=note,
        src_avoid=sources["nhs_avoid"]["u"], src_allergy=sources["nhs_allergy"]["u"], src_hygiene=sources["nhs_hygiene"]["u"],
    )


OG_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{{margin:0;width:1200px;height:630px;background:#fff;font-family:Inter,-apple-system,"SF Pro Text",Helvetica,Arial,sans-serif;color:#000;overflow:hidden}}
  .wrap{{position:relative;width:1200px;height:630px}}
  .brand{{position:absolute;left:64px;top:56px;font-size:26px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#6e6e73}}
  .photo{{position:absolute;left:0;top:0;width:1200px;height:630px;display:flex;align-items:center;justify-content:center}}
  .photo img{{width:480px;height:480px;object-fit:contain;filter:drop-shadow(0 24px 32px rgba(0,0,0,.14))}}
  .name{{position:absolute;left:64px;right:64px;top:200px;font-size:88px;line-height:1.08;font-weight:700;letter-spacing:-.02em}}
  .sub{{position:absolute;left:64px;bottom:64px;font-size:30px;color:#6e6e73}}
  .basket{{position:absolute;left:0;top:0;width:1200px;height:630px;display:flex;align-items:center;justify-content:center}}
</style></head><body><div class="wrap">{body}</div></body></html>"""

BASKET_SVG = """<svg width="420" height="420" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h18l-1.6 9.2a1.5 1.5 0 0 1-1.48 1.3H6.08a1.5 1.5 0 0 1-1.48-1.3L3 10z"/><path d="M8 10l2.6-5.5M16 10l-2.6-5.5"/><path d="M9 14v3M12 14v3M15 14v3"/></svg>"""


def knock_out(im, thresh=24, band=40):
    """Make a flat near-white background transparent (for the draft photos, which
    are opaque; Boyan's final cut-outs are transparent already and are left alone)."""
    import numpy as np
    from scipy import ndimage
    im = im.convert("RGBA")
    a = np.asarray(im).astype(np.int16)
    if a[..., 3].min() < 255:
        return im
    rgb = a[..., :3]
    h, w = rgb.shape[:2]
    corners = np.array([rgb[0, 0], rgb[0, w - 1], rgb[h - 1, 0], rgb[h - 1, w - 1]])
    bg = corners.mean(axis=0)
    diff = np.abs(rgb - bg).max(axis=2)
    near = diff < thresh
    labels, n = ndimage.label(near)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    border.discard(0)
    background = np.isin(labels, list(border))
    alpha = np.full((h, w), 255, dtype=np.int16)
    alpha[background] = 0
    ring = ndimage.binary_dilation(background, iterations=6) & ~background
    alpha[ring] = np.clip(diff[ring] * 255 // band, 0, 255)
    out = a.copy()
    out[..., 3] = alpha
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def render_og(pages, out_dir):
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        for name, body in pages:
            page.set_content(OG_HTML.format(body=body), wait_until="load")
            page.screenshot(path=str(out_dir / f"{name}.jpg"), type="jpeg", quality=86, clip={"x": 0, "y": 0, "width": 1200, "height": 630})
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", help="folder with <id>-spoon.png / <id>-finger.png cut-outs")
    ap.add_argument("--no-og", action="store_true", help="skip the share-card images")
    args = ap.parse_args()

    d = json.load(open(DATA, encoding="utf-8"))
    names = d["allergenNames"]
    sources = d["sources"]
    recipes = d["recipes"]

    dishes = ROOT / "img" / "dishes"
    dishes.mkdir(parents=True, exist_ok=True)
    if args.photos:
        from PIL import Image
        src = Path(args.photos)
        for r in recipes:
            for form in ("spoon", "finger"):
                f = src / f"{r['id']}-{form}.png"
                if f.exists():
                    im = knock_out(Image.open(f))
                    if max(im.size) > 660:
                        im.thumbnail((660, 660))
                    im.save(dishes / f"{r['id']}.png", optimize=True)
                    break

    rec_dir = ROOT / "recipe"
    rec_dir.mkdir(exist_ok=True)
    og_pages = []
    with_photo = 0
    for r in recipes:
        has_photo = (dishes / f"{r['id']}.png").exists()
        with_photo += has_photo
        (rec_dir / f"{r['id']}.html").write_text(build_page(r, names, sources, has_photo), encoding="utf-8")
        if has_photo:
            import base64
            img = "data:image/png;base64," + base64.b64encode((dishes / f"{r['id']}.png").read_bytes()).decode()
            body = f'<div class="photo"><img src="{img}"></div><div class="brand">First Spoon · Recipe</div>'
        else:
            body = f'<div class="brand">First Spoon · Recipe</div><div class="name">{esc(r["n"])}</div><div class="sub">{esc(stage_line(r))}</div>'
        og_pages.append((r["id"], body))
    og_pages.append(("list", f'<div class="basket">{BASKET_SVG}</div><div class="brand">First Spoon · Shopping list</div><div class="sub">Tick things off as you shop</div>'))
    if not args.no_og:
        render_og(og_pages, ROOT / "img" / "og")
    print(f"{len(recipes)} recipe pages, {with_photo} with a photo, {len(og_pages)} share cards")


if __name__ == "__main__":
    main()

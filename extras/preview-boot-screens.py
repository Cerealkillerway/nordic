#!/usr/bin/env python3
"""Render offline previews of the boot splash and login screen.

Neither screen can be seen without rebooting or logging out, which makes
iterating on them tedious. This composites what they will look like using the
same assets and the same geometry the real ones use, so you can tweak
extras/render-boot-assets.py and check the result in a couple of seconds.

    ./extras/render-boot-assets.py && ./extras/preview-boot-screens.py

Writes preview-*.png into the directory given as argv[1] (default: /tmp).

CAVEAT: this is a mock-up, not a run. It reproduces nordic.script's layout
arithmetic in Python; it does not execute the theme. The geometry constants
below must be kept in step with nordic.script — they are read from it where
possible, and flagged where they are not.
"""
import math
import os
import re
import sys

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
THEME = os.path.join(HERE, "plymouth", "nordic")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp"

W, H = 1920, 1080          # plymouth draws on one output, not the whole desktop
FONT = "Ubuntu"
FONT_PX = 15               # "Ubuntu 11" in pango points, roughly


def script_const(name, default):
    """Pull a numeric constant out of nordic.script so the two cannot drift."""
    src = open(os.path.join(THEME, "nordic.script")).read()
    m = re.search(rf"^{name}\s*=\s*(\d+)\s*;", src, re.M)
    return int(m.group(1)) if m else default


DOTS = script_const("DOTS", 6)
DOT_GAP = script_const("DOT_GAP", 26)

# Not expressed as bare constants in the script, so mirrored by hand.
# Keep in sync with nordic.script if you move things around.
LOGO_Y_OFFSET = -70        # logo.y = H/2 - logo.h/2 - 70
DOTS_Y_GAP = 46            # dots_y = logo.y + logo.h + 46
FIELD_Y_GAP = 54           # field.y = dots_y + 54


def png(name):
    return cairo.ImageSurface.create_from_png(os.path.join(THEME, name))


def background(ctx):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0.0, 0.137, 0.157, 0.192)   # #232831
    g.add_color_stop_rgb(1.0, 0.231, 0.263, 0.322)   # #3b4252
    ctx.set_source(g)
    ctx.paint()

    # nordic.script draws background.png over the gradient, scaled to cover.
    # Mirror that here or the preview shows a splash nobody will ever see.
    art = os.path.join(THEME, "background.png")
    if not os.path.exists(art):
        return
    bg = cairo.ImageSurface.create_from_png(art)
    scale = max(W / bg.get_width(), H / bg.get_height())
    ctx.save()
    ctx.translate((W - bg.get_width() * scale) / 2,
                  (H - bg.get_height() * scale) / 2)
    ctx.scale(scale, scale)
    ctx.set_source_surface(bg, 0, 0)
    ctx.paint()
    ctx.restore()


def paste(ctx, surf, x, y, alpha=1.0):
    ctx.save()
    ctx.set_source_surface(surf, x, y)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def measure(ctx, s):
    """Width and full line height of `s`, without drawing anything."""
    ctx.save()
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(FONT_PX)
    ascent, descent, _, _, _ = ctx.font_extents()
    _, _, tw, _, _, _ = ctx.text_extents(s)
    ctx.restore()
    return tw, ascent + descent


def text(ctx, s, cx, top, rgb=(0.847, 0.871, 0.914)):
    """Draw centred on cx with `top` as the TOP edge.

    Plymouth's Sprite.SetPosition places an image by its top-left corner,
    whereas cairo's show_text draws from the baseline. Converting via the font
    ascent keeps this preview honest — otherwise every label sits lower here
    than it will on screen.
    """
    ctx.save()
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(FONT_PX)
    ctx.set_source_rgb(*rgb)
    ascent, descent, _, _, _ = ctx.font_extents()
    xb, _, tw, _, _, _ = ctx.text_extents(s)
    ctx.move_to(cx - tw / 2 - xb, top + ascent)
    ctx.show_text(s)
    ctx.restore()
    return tw, ascent + descent


def splash(tick, password=False, bullet_count=0):
    logo, dot, field = png("logo.png"), png("dot.png"), png("field.png")
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    c = cairo.Context(s)
    background(c)

    lw, lh = logo.get_width(), logo.get_height()
    lx, ly = W / 2 - lw / 2, H / 2 - lh / 2 + LOGO_Y_OFFSET
    paste(c, logo, lx, ly)

    dots_y = ly + lh + DOTS_Y_GAP
    dots_left = W / 2 - (DOTS * DOT_GAP) / 2 + (DOT_GAP - dot.get_width()) / 2

    if not password:
        for i in range(DOTS):
            wave = math.sin(tick * 0.10 - i * 0.65)
            paste(c, dot, dots_left + i * DOT_GAP, dots_y,
                  0.18 + 0.72 * (0.5 + 0.5 * wave))
    else:
        fw, fh = field.get_width(), field.get_height()
        fx, fy = W / 2 - fw / 2, dots_y + FIELD_Y_GAP
        # matches nordic.script: label top = field.y - label.height - 14
        label = "Unlock the disk"
        _, lh = measure(c, label)
        text(c, label, W / 2, fy - lh - 14)
        paste(c, field, fx, fy)
        if bullet_count:
            marks = "•" * bullet_count
            _, bh = measure(c, marks)
            text(c, marks, W / 2, fy + fh / 2 - bh / 2)

    return s


def login():
    bg = cairo.ImageSurface.create_from_png(
        os.path.join(HERE, "gdm", "nordic-login.png"))
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    c = cairo.Context(s)
    sx, sy = W / bg.get_width(), H / bg.get_height()
    c.save()
    c.scale(sx, sy)                       # background-size='cover'
    c.set_source_surface(bg, 0, 0)
    c.paint()
    c.restore()

    # Rough stand-in for the greeter, to check nothing important is obscured.
    cx, cy = W / 2, H * 0.36
    c.set_source_rgba(0.847, 0.871, 0.914, 0.30)
    c.set_line_width(2)
    c.arc(cx, cy, 64, 0, math.tau)
    c.stroke()
    text(c, "cerealkiller", cx, cy + 108, (0.847, 0.871, 0.914))
    c.rectangle(cx - 170, cy + 132, 340, 44)
    c.stroke()
    text(c, "Password", cx, cy + 160, (0.557, 0.584, 0.643))
    return s


if __name__ == "__main__":
    # cairo reports a missing output directory as a bare "error while writing
    # to output stream", with no hint of which path failed, so make it first.
    os.makedirs(OUT, exist_ok=True)

    jobs = [
        ("preview-splash-a.png", splash(0)),
        ("preview-splash-b.png", splash(16)),
        ("preview-splash-password.png", splash(0, password=True, bullet_count=7)),
        ("preview-login.png", login()),
    ]
    for name, surf in jobs:
        path = os.path.join(OUT, name)
        surf.write_to_png(path)
        print("  " + path)

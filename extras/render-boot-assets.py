#!/usr/bin/env python3
"""Render the boot-splash and login-screen artwork from the Nordic palette.

Everything the Plymouth theme and the GDM background need is generated here,
so tweaking the look means editing this file and re-running it rather than
hand-editing PNGs:

    ./extras/render-boot-assets.py

Outputs
    extras/plymouth/nordic/logo.png    snowflake mark shown while booting
    extras/plymouth/nordic/dot.png     one throbber dot, drawn six times
    extras/plymouth/nordic/field.png   entry box for the LUKS password prompt
    extras/gdm/nordic-login.png        login-screen background

Palette is transcribed from gtk-3.0/gtk.css — see PALETTE below.
"""
import math
import os

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
#  Palette — the same values the GTK theme uses.
# ---------------------------------------------------------------------------
PALETTE = {
    "deepest":  "#1d2128",
    "border":   "#232831",
    "headerbar": "#2b313c",
    "popover":  "#2e3440",
    "base":     "#3b4252",
    "raised":   "#434c5e",
    "hover":    "#4c566a",
    "fg":       "#d8dee9",
    "subtle":   "#8e95a4",
    "teal":     "#8fbcbb",
    "cyan":     "#88c0d0",
}


def rgb(name, alpha=1.0):
    h = PALETTE[name].lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (r, g, b, alpha)


def snowflake(ctx, cx, cy, radius, colour, width_ratio=0.05):
    """Six-arm snowflake, thin strokes, round caps."""
    ctx.save()
    ctx.set_source_rgba(*colour)
    ctx.set_line_width(radius * width_ratio)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    for i in range(6):
        a = math.radians(i * 60)
        dx, dy = math.cos(a), math.sin(a)

        # main arm
        ctx.move_to(cx + dx * radius * 0.16, cy + dy * radius * 0.16)
        ctx.line_to(cx + dx * radius, cy + dy * radius)
        ctx.stroke()

        # side branches, angled 40 degrees off the arm
        for at, length in ((0.48, 0.26), (0.74, 0.18)):
            bx, by = cx + dx * radius * at, cy + dy * radius * at
            for sign in (1, -1):
                b = a + sign * math.radians(40)
                ctx.move_to(bx, by)
                ctx.line_to(bx + math.cos(b) * radius * length,
                            by + math.sin(b) * radius * length)
                ctx.stroke()

    # hexagonal hub
    ctx.set_line_width(radius * width_ratio * 0.9)
    for i in range(6):
        a = math.radians(i * 60)
        x, y = cx + math.cos(a) * radius * 0.15, cy + math.sin(a) * radius * 0.15
        ctx.line_to(x, y) if i else ctx.move_to(x, y)
    ctx.close_path()
    ctx.stroke()
    ctx.restore()


def write(surface, *parts):
    path = os.path.join(REPO, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    surface.write_to_png(path)
    print("  %-44s %s" % (os.path.relpath(path, REPO),
                          "%dx%d" % (surface.get_width(), surface.get_height())))


# ---------------------------------------------------------------------------
#  Plymouth assets
# ---------------------------------------------------------------------------
def plymouth_logo(size=256):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    c = cairo.Context(s)
    snowflake(c, size / 2, size / 2, size * 0.42, rgb("teal"))
    write(s, "extras", "plymouth", "nordic", "logo.png")


def plymouth_dot(size=14):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    c = cairo.Context(s)
    c.set_source_rgba(*rgb("teal"))
    c.arc(size / 2, size / 2, size / 2 - 1, 0, math.tau)
    c.fill()
    write(s, "extras", "plymouth", "nordic", "dot.png")


def plymouth_field(w=460, h=48, r=8):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(s)
    # rounded rectangle, inset by 1px so the stroke stays inside the surface
    x0, y0, x1, y1 = 1, 1, w - 1, h - 1
    c.new_sub_path()
    c.arc(x1 - r, y0 + r, r, math.radians(-90), 0)
    c.arc(x1 - r, y1 - r, r, 0, math.radians(90))
    c.arc(x0 + r, y1 - r, r, math.radians(90), math.radians(180))
    c.arc(x0 + r, y0 + r, r, math.radians(180), math.radians(270))
    c.close_path()
    c.set_source_rgba(*rgb("base"))
    c.fill_preserve()
    c.set_source_rgba(*rgb("border"))
    c.set_line_width(2)
    c.stroke()
    write(s, "extras", "plymouth", "nordic", "field.png")


# ---------------------------------------------------------------------------
#  Login background
# ---------------------------------------------------------------------------
def login_background(w=2560, h=1440):
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    c = cairo.Context(s)

    # Polar Night, darkest at the top so the greeter's white text stays legible
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgba(0.0, *rgb("deepest"))
    g.add_color_stop_rgba(0.55, *rgb("popover"))
    g.add_color_stop_rgba(1.0, *rgb("base"))
    c.set_source(g)
    c.paint()

    # soft frost glow behind where the login dialog sits
    glow = cairo.RadialGradient(w / 2, h * 0.42, 0, w / 2, h * 0.42, w * 0.42)
    glow.add_color_stop_rgba(0.0, *rgb("teal", 0.10))
    glow.add_color_stop_rgba(1.0, *rgb("teal", 0.0))
    c.set_source(glow)
    c.paint()

    # Watermark, pushed off to the right. GDM centres the login dialog, so a
    # centred mark sits directly behind the avatar and entry box and fights
    # them however faint it is.
    snowflake(c, w * 0.78, h * 0.30, h * 0.36, rgb("teal", 0.055), width_ratio=0.03)

    # vignette
    vg = cairo.RadialGradient(w / 2, h / 2, h * 0.25, w / 2, h / 2, w * 0.72)
    vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.35)
    c.set_source(vg)
    c.paint()

    write(s, "extras", "gdm", "nordic-login.png")


if __name__ == "__main__":
    print("rendering boot assets from the Nordic palette:")
    plymouth_logo()
    plymouth_dot()
    plymouth_field()
    login_background()
    print("done")

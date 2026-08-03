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
    extras/gdm/login-logo.svg          badge under the login password box

Palette is transcribed from gtk-3.0/gtk.css — see PALETTE below.
"""
import math
import re
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
    #
    # Geometry is constrained: the mark's left arm reaches cx - r, and the
    # dialog's right edge is about 0.59*w. Keep (cx - r) clear of that.
    #   0.82*w - 0.32*h = 0.82*2560 - 0.32*1440 = 1638, vs a 1507 dialog edge.
    snowflake(c, w * 0.82, h * 0.30, h * 0.32, rgb("teal", 0.055), width_ratio=0.03)

    # vignette
    vg = cairo.RadialGradient(w / 2, h / 2, h * 0.25, w / 2, h / 2, w * 0.72)
    vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.35)
    c.set_source(vg)
    c.paint()

    write(s, "extras", "gdm", "nordic-login.png")


# ---------------------------------------------------------------------------
#  Login-screen vendor logo
# ---------------------------------------------------------------------------
def login_logo():
    """Replacement for the Ubuntu badge GDM draws below the password box.

    Geometry matches /usr/share/pixmaps/ubuntu-logo-text-dark.svg exactly —
    187x72 with a 1039.44678x400 viewBox — so GDM lays it out identically.
    The original is kept alongside as login-logo-original.svg.

    The wordmark is converted to outlines with text_path() rather than left as
    an SVG <text> element: the greeter runs as user `gdm` and there is no
    guarantee about which fonts it can resolve, and a missing font would
    silently fall back to something else or vanish.
    """
    VB_W, VB_H = 1039.44678, 400.0
    path = os.path.join(REPO, "extras", "gdm", "login-logo.svg")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    s = cairo.SVGSurface(path, VB_W, VB_H)
    c = cairo.Context(s)

    snowflake(c, 170, VB_H / 2, 150, rgb("teal"), width_ratio=0.09)

    # Fit the wordmark to the space left of the viewBox edge rather than
    # trusting a hardcoded size — the width depends on whichever font actually
    # resolves, and at 230pt "nordic" in Ubuntu Regular overruns 1039 outright.
    WORD = "nordic"
    TEXT_X, PAD = 380.0, 40.0
    avail = VB_W - TEXT_X - PAD

    c.select_font_face("Ubuntu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(230)
    ext = c.text_extents(WORD)
    c.set_font_size(230 * min(1.0, avail / ext.width))

    # Optically centre on the viewBox using the inked extents, not the font
    # metrics — "nordic" has no ascenders beyond the 'd' and no descenders.
    ext = c.text_extents(WORD)
    c.set_source_rgba(*rgb("fg"))
    c.move_to(TEXT_X - ext.x_bearing, VB_H / 2 - ext.y_bearing - ext.height / 2)
    c.text_path(WORD)
    c.fill()

    s.finish()

    # cairo writes the surface size as the width/height, so the file would
    # render at 1039x400 instead of the 187x72 the original declares. Rewrite
    # just those two attributes.
    #
    # Only add a viewBox if cairo did not already emit one — appending a second
    # makes the document invalid XML ("Attribute viewBox redefined") and
    # librsvg refuses to render it at all, which shows up as a blank logo
    # rather than an error.
    svg = open(path).read()
    tag = re.search(r"<svg[^>]*>", svg).group(0)
    patched = re.sub(r'\swidth="[^"]*"', ' width="187"', tag, count=1)
    patched = re.sub(r'\sheight="[^"]*"', ' height="72"', patched, count=1)
    if "viewBox" not in patched:
        patched = patched[:-1] + f' viewBox="0 0 {VB_W} {VB_H}">'
    open(path, "w").write(svg.replace(tag, patched, 1))
    print("  %-44s %s" % ("extras/gdm/login-logo.svg", "187x72"))


if __name__ == "__main__":
    print("rendering boot assets from the Nordic palette:")
    plymouth_logo()
    plymouth_dot()
    plymouth_field()
    login_background()
    login_logo()
    print("done")

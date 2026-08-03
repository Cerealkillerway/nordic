#!/usr/bin/env python3
"""Render the boot-splash and login-screen artwork from the Nordic palette.

Everything the Plymouth theme and the GDM background need is generated here,
so tweaking the look means editing this file and re-running it rather than
hand-editing PNGs:

    ./extras/render-boot-assets.py

Outputs
    extras/plymouth/nordic/logo.png        snowflake mark shown while booting
    extras/plymouth/nordic/dot.png         one throbber dot, drawn six times
    extras/plymouth/nordic/field.png       entry box for the LUKS prompt
    extras/plymouth/nordic/background.png  boot-splash artwork
    extras/gdm/nordic-login.png            login background, plain gradient
    extras/gdm/nordic-login-storm.png      login background, drawn storm
    extras/gdm/nordic-login-jormungandr.png  login background, from artwork
    extras/gdm/login-logo.svg              badge under the login password box

The two artwork-derived files come from extras/gdm/jormungandr-source.jpg and
need python3-pil and python3-numpy; without them those two are skipped and the
rest still render.

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


# ---------------------------------------------------------------------------
#  Alternate login background — storm
# ---------------------------------------------------------------------------
#  Inspired by the Jörmungandr painting, but atmosphere only: storm cloud,
#  lightning, rain and a hatched sea, with no figures in it.
#
#  Drawing the serpent, longship and breaking wave was tried twice. Cairo
#  primitives at this scale gave a blob, a bent pipe and a top hat — the method
#  is fine for gradients and line-work and poor at representational art. If you
#  want the creature, composite a real image instead (see FORK-NOTES).
# ---------------------------------------------------------------------------
def login_background_storm(w=2560, h=1440):
    sea = h * 0.66
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    c = cairo.Context(s)

    # Same Polar Night gradient as the plain version — this is what the scene
    # fades back into.
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgba(0.0, *rgb("deepest"))
    g.add_color_stop_rgba(0.55, *rgb("popover"))
    g.add_color_stop_rgba(1.0, *rgb("base"))
    c.set_source(g)
    c.paint()

    # Cloud mass: overlapping soft radials at varying scale. Deterministic
    # offsets rather than an RNG so successive runs are byte-identical.
    for i in range(22):
        fx = (i * 0.137 + 0.05) % 1.0
        fy = 0.02 + 0.16 * ((i * 0.31) % 1.0)
        r = w * (0.07 + 0.10 * ((i * 0.53) % 1.0))
        cl = cairo.RadialGradient(w * fx, h * fy, 0, w * fx, h * fy, r)
        cl.add_color_stop_rgba(0.0, *rgb("deepest", 0.34))
        cl.add_color_stop_rgba(1.0, *rgb("deepest", 0.0))
        c.set_source(cl)
        c.paint()

    # A break in the cloud, lit from behind, upper left as in the reference.
    br = cairo.RadialGradient(w * 0.19, h * 0.13, 0, w * 0.19, h * 0.13, w * 0.15)
    br.add_color_stop_rgba(0.0, *rgb("subtle", 0.20))
    br.add_color_stop_rgba(0.45, *rgb("hover", 0.10))
    br.add_color_stop_rgba(1.0, *rgb("hover", 0.0))
    c.set_source(br)
    c.paint()

    # Lightning, right-hand side, well clear of the dialog.
    for x, ln, seed in ((0.845, 0.42, 1.0), (0.935, 0.30, 2.4), (0.775, 0.22, 5.1)):
        pts, cx, cy = [(w * x, h * 0.02)], w * x, h * 0.02
        for i in range(16):
            cy += h * ln / 16
            cx += math.sin(seed * 3.7 + i * 2.3) * w * 0.009
            pts.append((cx, cy))
        for width, alpha in ((w * 0.010, 0.10), (w * 0.0035, 0.38), (w * 0.0012, 1.0)):
            c.save()
            c.set_source_rgba(*rgb("cyan")[:3], alpha)
            c.set_line_width(width)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.move_to(*pts[0])
            for p in pts[1:]:
                c.line_to(*p)
            c.stroke()
            c.restore()
        # glow where the bolt meets the water
        gl = cairo.RadialGradient(pts[-1][0], pts[-1][1], 0, pts[-1][0], pts[-1][1], w * 0.10)
        gl.add_color_stop_rgba(0.0, *rgb("cyan", 0.11))
        gl.add_color_stop_rgba(1.0, *rgb("cyan", 0.0))
        c.set_source(gl)
        c.paint()

    # Sea: engraving hatching, denser and brighter toward the bottom.
    for i in range(52):
        t = i / 51
        y = sea + (h - sea) * (t ** 1.5)
        c.save()
        c.set_source_rgba(*rgb("hover", 0.05 + 0.17 * t))
        c.set_line_width(h * (0.0011 + 0.0030 * t))
        c.move_to(0, y)
        for xx in range(0, w + 28, 28):
            c.line_to(xx, y + math.sin(xx * 0.0031 + i * 1.9) * h * (0.0012 + 0.0055 * t)
                         + math.sin(xx * 0.0009 + i) * h * 0.0025)
        c.stroke()
        c.restore()

    # Horizon haze, so the hatching does not start abruptly.
    hz = cairo.LinearGradient(0, sea - h * 0.06, 0, sea + h * 0.10)
    hz.add_color_stop_rgba(0.0, *rgb("popover", 0.85))
    hz.add_color_stop_rgba(1.0, *rgb("popover", 0.0))
    c.set_source(hz)
    c.paint()

    # Rain.
    c.save()
    c.set_source_rgba(*rgb("subtle", 0.06))
    c.set_line_width(1.3)
    for i in range(520):
        x = (i * 137.508) % w
        y = (i * 271.3) % (h * 0.72)
        c.move_to(x, y)
        c.line_to(x - h * 0.013, y + h * 0.032)
    c.stroke()
    c.restore()

    # Fade back to the plain background where the greeter's dialog sits.
    calm = cairo.RadialGradient(w / 2, h * 0.34, 0, w / 2, h * 0.34, w * 0.33)
    calm.add_color_stop_rgba(0.0, *rgb("popover", 0.88))
    calm.add_color_stop_rgba(0.55, *rgb("popover", 0.48))
    calm.add_color_stop_rgba(1.0, *rgb("popover", 0.0))
    c.set_source(calm)
    c.paint()

    # No snowflake watermark on this variant. It occupies the same upper-right
    # corner as the lightning, and the two together read as noise rather than
    # as either a mark or a storm.

    vg = cairo.RadialGradient(w / 2, h / 2, h * 0.25, w / 2, h / 2, w * 0.72)
    vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.38)
    c.set_source(vg)
    c.paint()

    write(s, "extras", "gdm", "nordic-login-storm.png")


# ---------------------------------------------------------------------------
#  Alternate login background — Jörmungandr, from artwork
# ---------------------------------------------------------------------------
#  Recolours a source painting into the Nord palette by gradient-mapping its
#  luminance, then fades the middle back into the plain gradient so the
#  greeter's dialog stays legible.
#
#  This is image processing, not illustration — see login_background_storm()
#  for why the drawn version was abandoned.
#
#  Source: extras/gdm/jormungandr-source.jpg. Swap that file to use your own;
#  anything roughly landscape works, it is cropped to 16:9 keeping the top.
# ---------------------------------------------------------------------------
JORM_SRC = "jormungandr-source.jpg"

# Luminance -> palette. The last two stops lift highlights toward Frost so
# lightning reads as cold rather than white.
JORM_RAMP = [(0.00, "#151920"), (0.22, "#1d2128"), (0.42, "#2e3440"),
             (0.60, "#3b4252"), (0.76, "#4c566a"), (0.88, "#8e95a4"),
             (0.96, "#a9c6cf"), (1.00, "#e5e9f0")]


def _duotone_surface(w, h, crop_bias=0.35):
    """Source artwork, cropped to w:h and gradient-mapped onto the palette.

    Returns a cairo surface, or None if the source or the imaging libraries
    are missing. Shared by the login background and the boot splash so both
    are cut from the same cloth.
    """
    src = os.path.join(HERE, "gdm", JORM_SRC)
    if not os.path.exists(src):
        return None
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    import io

    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    want_h = int(round(sw / (w / h)))
    if want_h <= sh:
        top = int((sh - want_h) * crop_bias)
        im = im.crop((0, top, sw, top + want_h))
    else:
        want_w = int(round(sh * (w / h)))
        left = (sw - want_w) // 2
        im = im.crop((left, 0, left + want_w, sh))

    xs = np.array([s[0] for s in JORM_RAMP])
    cols = np.array([[int(s[1][i:i + 2], 16) for i in (1, 3, 5)] for s in JORM_RAMP], float)
    t = np.linspace(0, 1, 256)
    lut = np.stack([np.interp(t, xs, cols[:, k]) for k in range(3)], axis=1)

    im = Image.fromarray(lut[np.asarray(im.convert("L"))].astype(np.uint8))
    im = im.resize((w, h), Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return cairo.ImageSurface.create_from_png(buf)


def login_background_jormungandr(w=2560, h=1440):
    art = _duotone_surface(w, h)
    if art is None:
        print("  %-44s %s" % ("extras/gdm/nordic-login-jormungandr.png",
                              "skipped — needs " + JORM_SRC + " + pil/numpy"))
        return

    s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    c = cairo.Context(s)
    c.set_source_surface(art, 0, 0)
    c.paint()

    # Knock it back so it reads as a background rather than a poster.
    c.set_source_rgba(*rgb("deepest", 0.34))
    c.paint()

    # Fade into the plain gradient behind the dialog. Kept tight: the dialog
    # only spans roughly 0.41-0.59w, and a wider radius reaches the serpent's
    # head at ~0.35w and washes out the one thing worth looking at.
    calm = cairo.RadialGradient(w / 2, h * 0.34, 0, w / 2, h * 0.34, w * 0.235)
    calm.add_color_stop_rgba(0.0, *rgb("popover", 0.92))
    calm.add_color_stop_rgba(0.45, *rgb("popover", 0.70))
    calm.add_color_stop_rgba(1.0, *rgb("popover", 0.0))
    c.set_source(calm)
    c.paint()

    # Light touch at the top — the serpent's head and the lit break in the
    # cloud both sit in the upper third, and a heavy fade there buries them.
    top_g = cairo.LinearGradient(0, 0, 0, h * 0.22)
    top_g.add_color_stop_rgba(0.0, *rgb("deepest", 0.32))
    top_g.add_color_stop_rgba(1.0, *rgb("deepest", 0.0))
    c.set_source(top_g)
    c.paint()

    vg = cairo.RadialGradient(w / 2, h / 2, h * 0.25, w / 2, h / 2, w * 0.72)
    vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.40)
    c.set_source(vg)
    c.paint()

    write(s, "extras", "gdm", "nordic-login-jormungandr.png")


# ---------------------------------------------------------------------------
#  Boot splash background
# ---------------------------------------------------------------------------
#  The same artwork behind the Plymouth splash. Rendered at 1920x1080 rather
#  than 2560x1440 on purpose: this file goes into the initramfs, which is
#  rebuilt and read on every boot, and the theme scales it to fit anyway.
#
#  Treated harder than the login version — the snowflake and the throbber sit
#  dead centre and have to stay readable against it.
# ---------------------------------------------------------------------------
def plymouth_background(w=1920, h=1080):
    art = _duotone_surface(w, h)
    if art is None:
        print("  %-44s %s" % ("extras/plymouth/nordic/background.png",
                              "skipped — needs " + JORM_SRC + " + pil/numpy"))
        return

    s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    c = cairo.Context(s)
    c.set_source_surface(art, 0, 0)
    c.paint()

    # Push it further back than the login screen: at boot the artwork is
    # scenery, and the mark in front of it is the thing being looked at.
    c.set_source_rgba(*rgb("deepest", 0.46))
    c.paint()

    # Calm field centred on the logo/throbber stack rather than on the
    # greeter's dialog. nordic.script puts the logo at H/2 - logo.h/2 - 70 and
    # the dots below it, so the group straddles the middle of the screen.
    calm = cairo.RadialGradient(w / 2, h * 0.46, 0, w / 2, h * 0.46, w * 0.30)
    calm.add_color_stop_rgba(0.0, *rgb("popover", 0.88))
    calm.add_color_stop_rgba(0.45, *rgb("popover", 0.62))
    calm.add_color_stop_rgba(1.0, *rgb("popover", 0.0))
    c.set_source(calm)
    c.paint()

    vg = cairo.RadialGradient(w / 2, h / 2, h * 0.22, w / 2, h / 2, w * 0.70)
    vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.45)
    c.set_source(vg)
    c.paint()

    write(s, "extras", "plymouth", "nordic", "background.png")


if __name__ == "__main__":
    print("rendering boot assets from the Nordic palette:")
    plymouth_logo()
    plymouth_dot()
    plymouth_field()
    plymouth_background()
    login_background()
    login_logo()
    login_background_storm()
    login_background_jormungandr()
    print("done")

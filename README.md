
![](Art/_banner-github.jpg)

> Nordic is a Gtk3.20+ theme created using the awesome [Nord](https://github.com/arcticicestudio/nord) color palette.

#### Installation

Extract the zip file to the themes directory i.e. `/usr/share/themes/` or `~/.themes/` (create it if necessary).

To set the theme on Gnome, run the following commands in Terminal:

```
gsettings set org.gnome.desktop.interface gtk-theme "Nordic"
gsettings set org.gnome.desktop.wm.preferences theme "Nordic"
```
or Change via distribution specific tweak tool.

## Previewing the boot splash and login screen

Neither screen is visible without rebooting or logging out, so there are three
ways to look at them first — cheapest and least invasive at the top.

**1. Offline mock-up.** Installs nothing, takes about a second, and is the one
to use while iterating on the artwork. It composites both screens from the same
images and layout arithmetic the real ones use, and writes `preview-*.png` into
whatever directory you give it (default `/tmp`):

```sh
./extras/render-boot-assets.py && ./extras/preview-boot-screens.py ~/preview
```

You get four files: two frames of the boot splash showing the throbber at
different points in its cycle, the splash with the LUKS password prompt, and
the login screen with a stand-in for the greeter's dialog.

It is a mock-up, not a run — it reproduces `nordic.script`'s geometry in Python
rather than executing it, so it will **not** catch an error in the theme
script.

**2. The real Plymouth, in a window.** This runs the actual theme, so it is
what catches script errors. Worth doing once before trusting it at boot, since
a broken splash is awkward to debug from a black screen:

```sh
sudo apt install plymouth-x11          # provides the X11 renderer
sudo -E plymouthd --debug --debug-file=/tmp/plymouth.log
sudo -E plymouth --show-splash
sleep 15
sudo plymouth --quit
```

To exercise the encrypted-disk prompt while it is up:

```sh
sudo -E plymouth ask-for-password --prompt "Unlock the disk"
```

Two things that are easy to get wrong here. `plymouthd` has **no `--renderer`
option** — it chooses among the plugins in
`/usr/lib/x86_64-linux-gnu/plymouth/renderers/`, and installing `plymouth-x11`
is what puts `x11.so` there next to `drm.so`. And `sudo -E` matters: without it
`DISPLAY` and `XAUTHORITY` are stripped and the X11 renderer cannot be used. If
it takes over a console instead of opening a window, switch to a VT with
Ctrl+Alt+F3 — it is running there. Parse errors land in `/tmp/plymouth.log`.

**3. The real GDM greeter, nested in a window:**

```sh
dbus-run-session -- gnome-shell --mode=gdm --wayland
```

This shows the genuine greeter, but under *your* dconf profile rather than
`gdm`'s — so you see the layout, **not** the background from
`/etc/dconf/db/gdm.d/10-nordic`. For checking the background itself, the
mock-up in (1) is the more accurate test.

## Firefox theme

If you're a firefox user you should give a try to the awesome [Nordic theme for firefox](https://github.com/EliverLara/firefox-nordic-theme).

![](Art/firefox-preview.jpg)
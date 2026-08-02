# Nordic fork — libadwaita support

Fork of [EliverLara/Nordic](https://github.com/EliverLara/Nordic) that makes the
theme apply to **libadwaita** apps (Files, Settings, Text Editor, Software,
Calendar…), which upstream Nordic does not touch.

Install: `./install-nordic.sh` — undo with `./install-nordic.sh --uninstall`.

## Requirements

| Need | For what |
|---|---|
| `git` | already have it if you cloned this |
| Node / nvm | the script builds the compat layer with `npx sass` |
| `sudo` | **only** for the GNOME Shell theme and Flatpak — see below |

**GTK3, GTK4 and libadwaita theming need no root at all.** Everything lands in
`~/.themes` and `~/.config/gtk-4.0`. If you skip sudo entirely, every normal
app is themed; you just don't get the Shell (top bar / overview / menus),
Flatpak, root-launched apps or snaps.

Step 0 asks for sudo once, up front, and every later step runs against the warm
credential cache. Say no and it degrades gracefully, themes everything else,
and tells you what it skipped.

> Do not go back to calling `sudo` ad-hoc inside the later steps. Most of those
> calls redirect stderr to `/dev/null`, and a `sudo` whose stderr is discarded
> still waits for a password with the prompt invisible: the script looks hung,
> nothing gets typed, and the step fails silently while the rest succeeds. That
> is exactly how the schema fix and the theme snap both no-op'd once.

What sudo covers:

```sh
sudo glib-compile-schemas /usr/share/glib-2.0/schemas/  # if color-scheme is missing
sudo apt install -y gnome-shell-extensions              # User Themes extension
sudo flatpak override --filesystem=$HOME/.themes:ro
sudo flatpak override --env=GTK_THEME=Nordic
sudo ln -sfnT ~/.themes/Nordic /usr/share/themes/Nordic # root-launched apps
sudo snap install --dangerous nordic-themes_1.0_all.snap
sudo snap connect <snap>:gtk-3-themes nordic-themes:gtk-3-themes
```

**Ordering wrinkle for the Shell theme.** If `gnome-shell-extensions` was not
already installed, GNOME Shell will not see the User Themes extension until the
session restarts. So on a fresh machine it goes:

1. `./install-nordic.sh` — installs the package, themes GTK, warns that the
   shell theme could not be set yet
2. log out and back in
3. `./install-nordic.sh` again — now the extension enables and the shell theme
   applies

Step 3 is cheap and idempotent. If you would rather not re-run the whole thing,
after the re-login this is all that is left:

```sh
gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com
gsettings set org.gnome.shell.extensions.user-theme name Nordic
```

Flatpak has no such ordering constraint — those overrides can be applied at any
time and take effect the next time the app starts.

---

## The problem

Upstream `gtk-3.0/_colors-public.scss` exports only the legacy GTK named
colours (`theme_bg_color`, `theme_fg_color`, …). libadwaita reads **none** of
them, so every libadwaita app stayed default Adwaita grey no matter what the
GTK theme was set to.

Since libadwaita 1.6 the resolution chain is:

```css
/* libadwaita's own stylesheet */
:root  { --window-bg-color: @window_bg_color; }   /* custom prop ← named colour */
.background { background-color: var(--window-bg-color); }   /* widget rule */
```

So the named colours are still the way in — they just have to be the *right
names*, which upstream never defined.

## The fix

`gtk-4.0/_adw-compat.scss` maps the Nord palette onto all ~50 libadwaita
semantic tokens and emits each one twice:

1. `@define-color window_bg_color …` — feeds libadwaita's own `:root` mapping.
2. `:root { --window-bg-color: … }` — overrides the custom property directly,
   in case a future libadwaita stops going through the named colour.

Both are emitted **unconditionally** (outside any `prefers-color-scheme` media
query). A media query adds no specificity, and `~/.config/gtk-4.0/gtk.css`
loads at `GTK_STYLE_PROVIDER_PRIORITY_USER` (800) vs. the theme provider's 600,
so these win in both light and dark. Nordic is dark-only, which is what we want.

The token list was extracted from the installed library rather than guessed:

```sh
gresource extract /usr/lib/x86_64-linux-gnu/libadwaita-1.so.0 \
    /org/gnome/Adwaita/styles/default.css
```

Re-run that after a libadwaita major bump to catch added or renamed tokens.

Also mapped: Ubuntu's user-selectable accent palette (`--accent-blue`,
`--accent-teal`, …), so any accent choice stays inside the Nord palette instead
of punching a foreign colour through the theme.

## Upstream bugs fixed along the way

| Issue | Fix |
|---|---|
| [#359](https://github.com/EliverLara/Nordic/issues/359) — monospace lost in GNOME 50 Text Editor | `font-family: Monospace` → `monospace`. The capitalised fontconfig alias no longer resolves in GTK4/Pango. Note `!important` is **not** usable — GTK4's font-family parser rejects it with *"Junk at end of value for font-family"*. |
| [#356](https://github.com/EliverLara/Nordic/pull/356) — `-gtk-scaled()` removed in GTK 4.22 | Replaced all 101 `-gtk-scaled(url(a), url(b))` with `url(a)` in the GTK4 stylesheets. |
| `url("assets/color-button-auto.png")` never loaded | Missing `../`; normalised at install time. |
| gtk-4.0 had no build task | Added `styles4` to the Gulpfile. |

## Build architecture — important

**Upstream's `gtk-4.0/*.scss` tree does not compile with any current dart-sass.**
`widgets/_base-states.scss` extends compound selectors
(`@extend %selected_items:disabled`), which Sass removed years ago. Upstream
keeps `gtk-4.0/gtk.css` in sync by hand, so **that file is the real artifact**.

Consequently `install-nordic.sh` never regenerates `gtk.css`. It compiles only
the new compat layer (`build-adw-compat.scss` → `adw-compat.css`) and
concatenates it on top, preserving every upstream hand-fix for GNOME 47–50.
Fixes that must reach the running theme are applied to **both** the `.scss`
(for future correctness) and the checked-in `.css` (what actually ships).

Two gotchas the install script handles:

- Build with `--no-charset`. Sass emits `@charset "UTF-8"` which, after
  concatenation, sits mid-file where GTK rejects it as an unknown at-rule.
- `~/.config/gtk-4.0/gtk.css` must be a **real file, not a symlink** into the
  theme. GTK resolves relative `url()` against the stylesheet's own location,
  so `../assets` would resolve to `~/.config/assets` and every asset would 404.
  The script rewrites them to absolute `file://` URLs.

## Verification

`_adw-compat` was verified against libadwaita 1.8.0 / GTK 4.20.1 by rendering a
representative libadwaita UI through GTK's own CSS engine and reading back the
resolved colours:

```
window_bg_color   #434c5e ok      accent_bg_color  #8fbcbb ok
view_bg_color     #3b4252 ok      card_bg_color    #444c5e ok
headerbar_bg_color #2b313c ok     sidebar_bg_color #2e3440 ok
error_bg_color    #bf616a ok
```

Measured text contrast in the render: action-row title 4.62:1, list rows
6.70:1 — both pass WCAG AA. A real `gnome-text-editor` launch reports **0**
theme parser errors.

## Apps the GTK theme does not reach on its own

Several kinds of app stay unthemed after a normal install, each for a different
reason. Sections 4, 6, 7 and 8 of `install-nordic.sh` handle them.

**Apps that run as root** (GParted, Synaptic). `/usr/sbin/gparted` relaunches
itself through `pkexec`, which resets the environment and sets `HOME=/root`.
GTK then looks for the theme in `/root/.themes`, `/root/.local/share/themes`
and `/usr/share/themes` — never in your `~/.themes`. It finds nothing named
Nordic and falls back to Adwaita. The giveaway is a Nordic titlebar (drawn by
mutter, running as you) around an Adwaita-light window. Section 6 symlinks the
theme into `/usr/share/themes` and writes `/root/.config/gtk-3.0/settings.ini`.

GParted's partition-graph swatches do not change: those 38 colours are compiled
into `/usr/libexec/gpartedbin` and passed straight to a `Gtk::DrawingArea`, so
no stylesheet can reach them. Only a patched build would.

**Mailspring** is Electron — its entire UI is Chromium-rendered HTML/CSS driven
by its own theme packages, so no GTK theme can style it however it is packaged.
Section 7 therefore installs a real Mailspring theme package from
`extras/mailspring/ui-nordic`, with the palette transcribed from
`gtk-3.0/gtk.css` so the two stay in step. It goes into whichever of the snap,
deb and flatpak config directories exist, and is selected automatically when
Mailspring is not running. That themes the contents; the window frame around
them is a separate problem, below.

**Snap window frames.** Theming Mailspring's *contents* still leaves a pale
window frame, because that frame is drawn by GTK inside the sandbox, not by the
app. A snap cannot read `~/.themes` — inside the sandbox `/usr/share/themes`
does not even exist, and themes arrive only through the `gtk-3-themes` content
interface, wired by default to `gtk-common-themes` (53 themes, no Nordic). So
GTK finds no theme by that name and falls back to Adwaita light.

Section 8 fixes it by publishing Nordic as a content snap of its own and
connecting it alongside `gtk-common-themes`. One content plug can take several
slots — that is how `icon-theme-papirus` already coexists there — so this adds
Nordic without displacing anything. `extras/snap/build-nordic-theme-snap.sh`
builds it; no snapcraft required, since a content snap is just a squashfs with
a `meta/snap.yaml`. Every installed snap that plugs `gtk-3-themes` gets
connected, so Firefox, Discord, Steam and the rest are covered too, not only
Mailspring.

**Boot splash and login screen** are sections 9 and 10. Both draw on the same
palette as the GTK theme, and both are generated by
`extras/render-boot-assets.py` — edit that script and re-run it rather than
hand-editing the PNGs.

The splash is a Plymouth `script`-plugin theme in `extras/plymouth/nordic`.
Two things to know if you change it. `Plymouth.SetMessageFunction` does not
exist — the callback is `SetDisplayMessageFunction`, and calling the wrong one
fails silently, so fsck and systemd messages simply never appear. And the theme
is baked into the initramfs, so nothing changes until `update-initramfs -u`
runs. To preview without rebooting:

```sh
sudo plymouthd --debug --tty=/dev/tty2 ; sudo plymouth --show-splash
sleep 10 ; sudo plymouth --quit
```

The login screen is set through GDM's dconf profile. The stock profile chains
only `user-db` and the packaged `file-db` — there is no `system-db`, so
dropping a file into `/etc/dconf/db/gdm.d` does nothing until the profile is
extended. Section 10 writes `/etc/dconf/profile/gdm` (which overrides the copy
in `/usr/share`, leaving the gdm3 package alone) adding `system-db:gdm`, then
writes `/etc/dconf/db/gdm.d/10-nordic`. The background has to sit in
`/usr/share/backgrounds`: the greeter runs as user `gdm` and cannot read
`/home/<you>`.

**Google Chrome** (the deb, so it can read `~/.themes`) has two options. The
cheap one is `chrome://settings/appearance` -> theme **GTK**, which picks up
Nordic for the frame and tabstrip but maps it approximately and leaves the new
tab page alone. For an exact match, `extras/chrome/nordic-theme` is a theme
extension with the palette taken from `gtk-3.0/gtk.css`. Install it via
`chrome://extensions` -> Developer mode -> **Load unpacked**. It is not wired
into `install-nordic.sh`: Chrome only accepts packaged themes from the Web
Store, so loading it is a browser-UI step that cannot be scripted.

**Do not trust `gsettings` from inside a snap terminal.** Running this script
from VS Code's integrated terminal — VS Code being a snap — inherits
`GSETTINGS_SCHEMA_DIR=~/snap/code/<rev>/.local/share/glib-2.0/schemas`. That
directory holds the snap's own older `org.gnome.desktop.interface`, with 43
keys instead of the system's 45, and it *shadows* the real one. So
`color-scheme` and `accent-color` appear not to exist and `gsettings set` on
them fails, on a completely healthy system. It costs an afternoon if you take
the reading at face value and go hunting for a stale `gschemas.compiled`.

Section 4 pins `GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas` for that
reason. To check the real value by hand:

```sh
env -i HOME=$HOME DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" \
  /usr/bin/gsettings get org.gnome.desktop.interface color-scheme
```

## Known limits (not fixable in this repo)

- **GParted's partition graph** — see above; the swatches are compiled in.
- **GTK4 flatpaks** are unaffected — Flathub has 337 `org.gtk.Gtk3theme.*`
  extensions and **zero** `Gtk4theme` ones; no such extension point exists.
- This override is unsupported by GNOME upstream and may need revisiting when
  libadwaita changes its token set (i.e. around Ubuntu 28.04).

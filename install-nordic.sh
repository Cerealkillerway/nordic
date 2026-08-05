#!/usr/bin/env bash
#
# ============================================================================
#  install-nordic.sh — Nordic with working libadwaita support
# ============================================================================
#
#  Builds the libadwaita compatibility layer, installs the theme, and wires up
#  the GTK4 user stylesheet that libadwaita apps actually read.
#
#  Run from the repo root:   ./install-nordic.sh
#  Undo everything:          ./install-nordic.sh --uninstall
#
#  WHY IT IS BUILT THIS WAY
#  ------------------------
#  Upstream's gtk-4.0/*.scss tree does not compile with any current dart-sass
#  (widgets/_base-states.scss extends compound selectors, removed from Sass
#  years ago). Upstream keeps gtk-4.0/gtk.css in sync by hand, so THAT file is
#  the real artifact. This script therefore never regenerates it — it compiles
#  only the new _adw-compat layer and concatenates it on top, preserving every
#  upstream hand-fix for GNOME 47-50.
#
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_NAME="Nordic"
THEME_DIR="$HOME/.themes/$THEME_NAME"
CFG4="$HOME/.config/gtk-4.0"
SASS_VER="1.77.8"

# Which login-screen background to install, from extras/gdm/:
#   nordic-login.png             plain Polar Night gradient with a snowflake
#   nordic-login-storm.png       drawn storm: lightning and a hatched sea
#   nordic-login-jormungandr.png artwork recoloured to the palette
# Override for one run with:  NORDIC_LOGIN_BG=nordic-login.png ./install-nordic.sh
LOGIN_BG="${NORDIC_LOGIN_BG:-nordic-login-jormungandr.png}"

# Desktop wallpaper, from extras/wallpapers/. Set to "" to leave the current
# wallpaper alone:  NORDIC_DESKTOP_BG= ./install-nordic.sh
DESKTOP_BG="${NORDIC_DESKTOP_BG-nordic-dragon.jpg}"

# Where the installer remembers things it overwrote, so --uninstall can put
# them back.
STATE_DIR="$HOME/.local/state/nordic-theme"

step() { echo; echo "==> $*"; }
note() { echo "    ~ $*"; }

# ---------------------------------------------------------------------------
#  Uninstall
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--uninstall" ]; then
  step "Removing GTK4 user stylesheet overrides"
  rm -f "$CFG4/gtk.css" "$CFG4/gtk-dark.css"
  for f in "$CFG4/gtk.css.nordic-backup" "$CFG4/gtk-dark.css.nordic-backup"; do
    [ -f "$f" ] && mv "$f" "${f%.nordic-backup}" && note "restored ${f%.nordic-backup}"
  done
  step "Removing the root-app hookup"
  [ -L "/usr/share/themes/$THEME_NAME" ] && sudo rm -f "/usr/share/themes/$THEME_NAME" \
    && note "unlinked /usr/share/themes/$THEME_NAME"
  sudo rm -f /root/.config/gtk-3.0/settings.ini \
             /root/.config/gtk-4.0/gtk.css \
             /root/.config/gtk-4.0/gtk-dark.css 2>/dev/null

  step "Removing the Mailspring theme"
  for MS_DIR in "$HOME/snap/mailspring/common" \
                "$HOME/.config/Mailspring" \
                "$HOME/.var/app/com.getmailspring.Mailspring/config/Mailspring"; do
    [ -d "$MS_DIR/packages/ui-nordic" ] || continue
    rm -rf "$MS_DIR/packages/ui-nordic"
    note "removed $MS_DIR/packages/ui-nordic"
    # Only reset the selection if it still points at the theme we just deleted.
    [ -f "$MS_DIR/config.json" ] && python3 - "$MS_DIR/config.json" <<'PY'
import json, sys
p = sys.argv[1]
with open(p) as f:
    d = json.load(f)
core = d.get('*', {}).get('core', {})
if core.get('themes') == ['ui-nordic'] or core.get('theme') == 'ui-nordic':
    core['themes'] = ['ui-light']
    core['theme'] = 'ui-light'
    with open(p, 'w') as f:
        json.dump(d, f, indent=2)
PY
  done

  step "Restoring the previous desktop wallpaper"
  if [ -f "$STATE_DIR/desktop-background.prev" ]; then
    # Three lines, in the order they were written: uri, uri-dark, options.
    { read -r prev_uri; read -r prev_dark; read -r prev_opts; } \
      < "$STATE_DIR/desktop-background.prev"
    for pair in "picture-uri $prev_uri" "picture-uri-dark $prev_dark" \
                "picture-options $prev_opts"; do
      k="${pair%% *}"; v="${pair#* }"
      [ -n "$v" ] && GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
        gsettings set org.gnome.desktop.background "$k" "$v" 2>/dev/null
    done
    rm -f "$STATE_DIR/desktop-background.prev"
    note "restored the wallpaper that was set before Nordic"
  fi
  rm -f "$HOME/.local/share/backgrounds/nordic-dragon.jpg"

  step "Removing the Warp theme"
  WARP_SETTINGS="$HOME/.config/warp-terminal/settings.toml"
  rm -f "$HOME/.local/share/warp-terminal/themes/nordic.yaml"
  if [ -f "$WARP_SETTINGS" ] && grep -q '^theme = "nordic"$' "$WARP_SETTINGS"; then
    if pgrep -x warp >/dev/null 2>&1; then
      note "Warp is running — pick another theme in Settings > Appearance"
    else
      # Drop just the key; Warp falls back to its default rather than leaving
      # a dangling reference to a theme file we just deleted.
      sed -i '/^theme = "nordic"$/d' "$WARP_SETTINGS"
      note "removed the Nordic selection from settings.toml"
    fi
  fi

  step "Reverting the boot splash"
  if [ -e /usr/share/plymouth/themes/nordic/nordic.plymouth ]; then
    sudo update-alternatives --remove default.plymouth \
         /usr/share/plymouth/themes/nordic/nordic.plymouth >/dev/null 2>&1
    sudo rm -rf /usr/share/plymouth/themes/nordic
    note "removed the Nordic plymouth theme; rebuilding the initramfs"
    sudo update-initramfs -u >/dev/null 2>&1 \
      || note "run 'sudo update-initramfs -u' yourself"
  fi

  step "Reverting the login screen"
  if [ -f /etc/dconf/db/gdm.d/10-nordic ]; then
    sudo rm -f /etc/dconf/db/gdm.d/10-nordic
    # Only drop the profile overrides we added; leave anything else alone.
    for p in gdm Debian-gdm; do
      if [ -f "/etc/dconf/profile/$p" ] && grep -q '^system-db:gdm$' "/etc/dconf/profile/$p"; then
        sudo rm -f "/etc/dconf/profile/$p"
      fi
    done
    sudo rm -f /usr/share/backgrounds/nordic-login.png \
               /usr/share/pixmaps/nordic-login-logo.svg
    sudo dconf update 2>/dev/null
    note "login screen reverted to the packaged defaults"
  fi

  step "Removing the theme snap"
  if command -v snap >/dev/null 2>&1 && snap list nordic-themes >/dev/null 2>&1; then
    sudo snap remove nordic-themes >/dev/null 2>&1 \
      && note "removed the nordic-themes snap (connections drop with it)"
  fi

  step "Reverting theme settings to Yaru"
  gsettings set org.gnome.desktop.interface gtk-theme 'Yaru-purple-dark'
  gsettings set org.gnome.desktop.wm.preferences theme 'Yaru-purple-dark'
  gsettings set org.gnome.shell.extensions.user-theme name '' 2>/dev/null || true
  sudo flatpak override --reset 2>/dev/null || true
  note "Theme files left in $THEME_DIR — delete manually if you want them gone."
  echo; echo "Done. Log out and back in."
  exit 0
fi

# ---------------------------------------------------------------------------
#  0. Ask for sudo once, up front
# ---------------------------------------------------------------------------
#  Several later steps need root. They used to just call sudo where needed,
#  which broke badly: a sudo whose stderr is redirected to /dev/null still
#  waits for a password, but the prompt is invisible. The script looks hung,
#  nothing gets typed, and the step fails silently. Prompting once here, with
#  stderr intact, means every later sudo runs against a warm credential cache.
# ---------------------------------------------------------------------------
step "0. Checking for root access"
note "GTK3/GTK4 theming needs no root. Root is used for the GNOME Shell"
note "extension, Flatpak overrides, root-launched apps and the theme snap."
if sudo -v; then
  HAVE_SUDO=yes
  note "got it — later steps will not prompt again"
else
  HAVE_SUDO=no
  note "no sudo: skipping shell theme, Flatpak, root apps and snaps"
fi

# ---------------------------------------------------------------------------
#  1. Build the libadwaita compatibility layer
# ---------------------------------------------------------------------------
step "1. Building the libadwaita compatibility layer"
export NVM_DIR="$HOME/.nvm"
# shellcheck disable=SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1

if ! command -v npx >/dev/null 2>&1; then
  echo "npx not found — install Node (nvm) first." >&2; exit 1
fi

npx --yes "sass@$SASS_VER" --no-source-map --no-charset \
  "$REPO/gtk-4.0/build-adw-compat.scss:$REPO/gtk-4.0/adw-compat.css" 2>&1 \
  | grep -iE '^Error' && { echo "sass build FAILED" >&2; exit 1; }

[ -s "$REPO/gtk-4.0/adw-compat.css" ] || { echo "adw-compat.css not produced" >&2; exit 1; }
note "adw-compat.css: $(wc -l < "$REPO/gtk-4.0/adw-compat.css") lines"

# ---------------------------------------------------------------------------
#  2. Install the theme tree
# ---------------------------------------------------------------------------
step "2. Installing theme to $THEME_DIR"
mkdir -p "$HOME/.themes"
rm -rf "$THEME_DIR"
mkdir -p "$THEME_DIR"
# Copy everything except VCS/build cruft.
tar -C "$REPO" \
    --exclude='.git' --exclude='.claude' --exclude='node_modules' \
    --exclude='src' --exclude='Art' --exclude='extras' --exclude='*.snap' \
    --exclude='install-nordic.sh' --exclude='Gulpfile.js' \
    --exclude='package.json' --exclude='package-lock.json' \
    -cf - . | tar -C "$THEME_DIR" -xf -
note "copied $(du -sh "$THEME_DIR" | cut -f1)"

# Upstream bug: one rule references assets/ instead of ../assets/ relative to
# gtk-4.0/, so that image never loads. Normalise it.
sed -i 's|url("assets/|url("../assets/|g' \
  "$THEME_DIR/gtk-4.0/gtk.css" "$THEME_DIR/gtk-4.0/gtk-dark.css"

# Append the adw layer to the theme's own GTK4 stylesheets, for GTK4 apps that
# read the theme directory normally (relative ../assets paths still resolve).
for f in gtk.css gtk-dark.css; do
  printf '\n/* ===== libadwaita compatibility layer (Nordic fork) ===== */\n' \
    >> "$THEME_DIR/gtk-4.0/$f"
  cat "$REPO/gtk-4.0/adw-compat.css" >> "$THEME_DIR/gtk-4.0/$f"
done
note "adw layer appended to theme gtk-4.0 stylesheets"

# ---------------------------------------------------------------------------
#  3. GTK4 user stylesheet — this is what libadwaita apps read
# ---------------------------------------------------------------------------
#  ~/.config/gtk-4.0/gtk.css loads at GTK_STYLE_PROVIDER_PRIORITY_USER (800),
#  above the theme provider (600), which is the only way to reach libadwaita.
#
#  It must be a real file, not a symlink into the theme: GTK resolves relative
#  url() against the stylesheet's own location, so ../assets would resolve to
#  ~/.config/assets and every asset would 404. Rewrite them to absolute
#  file:// URLs instead.
# ---------------------------------------------------------------------------
step "3. Writing GTK4 user stylesheet"
mkdir -p "$CFG4"
for f in gtk.css gtk-dark.css; do
  # Only back up a file we did not write ourselves, otherwise re-running the
  # script would "back up" the previous Nordic output and --uninstall would
  # then restore Nordic instead of removing it.
  if [ -f "$CFG4/$f" ] && [ ! -f "$CFG4/$f.nordic-backup" ] \
     && ! grep -q 'libadwaita compatibility layer (Nordic fork)' "$CFG4/$f"; then
    cp "$CFG4/$f" "$CFG4/$f.nordic-backup"
    note "backed up existing $f -> $f.nordic-backup"
  fi
  sed "s|url(\"\.\./assets/|url(\"file://$THEME_DIR/assets/|g" \
    "$THEME_DIR/gtk-4.0/$f" > "$CFG4/$f"
done
REMAINING=$(grep -c 'url("\.\./' "$CFG4/gtk.css" || true)
note "wrote $CFG4/gtk.css ($(wc -c < "$CFG4/gtk.css") bytes, $REMAINING unresolved relative urls)"

# ---------------------------------------------------------------------------
#  4. Apply the theme
# ---------------------------------------------------------------------------
step "4. Applying theme settings"
gsettings set org.gnome.desktop.interface gtk-theme "$THEME_NAME"
gsettings set org.gnome.desktop.wm.preferences theme "$THEME_NAME"

# color-scheme is how libadwaita, and Chromium via the desktop portal, learn
# that the session is dark.
#
# Pin the schema source. If this script is run from a terminal inside a snap
# (VS Code's integrated terminal, for one) the snap exports
# GSETTINGS_SCHEMA_DIR pointing at its own bundled copy of
# org.gnome.desktop.interface. That copy is older and has no color-scheme key,
# so an unpinned `gsettings set` fails with "No such key" and — worse — an
# unpinned `gsettings get` makes a perfectly healthy system look broken.
if GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
     gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null; then
  note "color-scheme = prefer-dark"
else
  note "could not set color-scheme (key absent from the system schemas?)"
fi

# GNOME Shell theme needs the User Themes extension.
if ! gnome-extensions list 2>/dev/null | grep -q 'user-theme@gnome-shell-extensions'; then
  if [ "$HAVE_SUDO" = yes ]; then
    note "installing gnome-shell-extensions for the User Themes extension"
    sudo apt install -y gnome-shell-extensions >/dev/null 2>&1 || \
      note "could not install gnome-shell-extensions — do it manually"
  else
    note "no sudo — install gnome-shell-extensions yourself for the shell theme"
  fi
fi
gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com 2>/dev/null \
  && note "User Themes extension enabled" \
  || note "enable 'User Themes' in Extension Manager, then re-run"
gsettings set org.gnome.shell.extensions.user-theme name "$THEME_NAME" 2>/dev/null \
  || note "shell theme not set (extension not active yet)"

# ---------------------------------------------------------------------------
#  5. Flatpak
# ---------------------------------------------------------------------------
step "5. Flatpak overrides"
if ! command -v flatpak >/dev/null 2>&1; then
  note "flatpak not installed — skipped"
elif [ "$HAVE_SUDO" != yes ]; then
  note "no sudo — Flatpak apps will stay unthemed"
else
  sudo flatpak override --filesystem="$HOME/.themes:ro"
  sudo flatpak override --env=GTK_THEME="$THEME_NAME"
  note "GTK3 flatpaks (e.g. GIMP) will pick this up; libadwaita flatpaks may not"
fi

# ---------------------------------------------------------------------------
#  6. Apps that run as root
# ---------------------------------------------------------------------------
#  GParted and Synaptic relaunch themselves through pkexec, which resets the
#  environment and sets HOME=/root. GTK then searches /root/.themes,
#  /root/.local/share/themes and /usr/share/themes — never your ~/.themes — so
#  it cannot find a theme called Nordic and falls back to Adwaita. You get a
#  Nordic titlebar (drawn by mutter, as you) around an Adwaita-light window.
#
#  Exposing the theme system-wide fixes the lookup; the settings.ini is the
#  fallback for when XSETTINGS is not reachable from the elevated process.
# ---------------------------------------------------------------------------
step "6. Apps that run as root (GParted, Synaptic)"
SYS_THEME="/usr/share/themes/$THEME_NAME"
if [ -e "$SYS_THEME" ] && [ ! -L "$SYS_THEME" ]; then
  note "$SYS_THEME exists and is not our symlink — left alone"
elif [ "$HAVE_SUDO" != yes ]; then
  note "no sudo — root apps (GParted, Synaptic) will stay Adwaita"
elif sudo ln -sfnT "$THEME_DIR" "$SYS_THEME" 2>/dev/null; then
  note "linked $SYS_THEME -> $THEME_DIR"
  ICONS=$(gsettings get org.gnome.desktop.interface icon-theme | tr -d \')
  FONT=$(gsettings get org.gnome.desktop.interface font-name | tr -d \')
  sudo install -d -m 755 /root/.config/gtk-3.0 2>/dev/null
  sudo tee /root/.config/gtk-3.0/settings.ini >/dev/null 2>&1 <<EOF
[Settings]
gtk-theme-name=$THEME_NAME
gtk-icon-theme-name=$ICONS
gtk-font-name=$FONT
gtk-application-prefer-dark-theme=true
EOF
  note "wrote /root/.config/gtk-3.0/settings.ini"
  # GTK4/libadwaita apps run as root need the same user-stylesheet trick. The
  # url()s inside are already absolute file:// paths that root can read.
  if [ -f "$CFG4/gtk.css" ]; then
    sudo install -d -m 755 /root/.config/gtk-4.0 2>/dev/null
    sudo install -m 644 "$CFG4/gtk.css"      /root/.config/gtk-4.0/gtk.css      2>/dev/null
    sudo install -m 644 "$CFG4/gtk-dark.css" /root/.config/gtk-4.0/gtk-dark.css 2>/dev/null
    note "copied the GTK4 stylesheet into /root"
  fi
  note "GParted's partition-graph swatches stay as they are — those 38 colours"
  note "are compiled into /usr/libexec/gpartedbin, not drawn from the theme"
else
  note "could not link $SYS_THEME — root apps will stay Adwaita"
fi

# ---------------------------------------------------------------------------
#  7. Mailspring
# ---------------------------------------------------------------------------
#  Mailspring is Electron: the whole UI is Chromium-rendered HTML/CSS driven by
#  its own theme packages, so GTK never touches it. On the snap build it cannot
#  even see ~/.themes — snaps only get themes through the gtk-3-themes content
#  interface, which is wired to gtk-common-themes (53 themes, no Nordic).
#  So we ship a real Mailspring theme package instead.
# ---------------------------------------------------------------------------
step "7. Mailspring theme"
MS_SRC="$REPO/extras/mailspring/ui-nordic"
MS_FOUND=no
for MS_DIR in "$HOME/snap/mailspring/common" \
              "$HOME/.config/Mailspring" \
              "$HOME/.var/app/com.getmailspring.Mailspring/config/Mailspring"; do
  [ -d "$MS_DIR" ] || continue
  MS_FOUND=yes
  mkdir -p "$MS_DIR/packages"
  rm -rf "$MS_DIR/packages/ui-nordic"
  cp -r "$MS_SRC" "$MS_DIR/packages/ui-nordic"
  note "installed ui-nordic -> $MS_DIR/packages/"

  # Match the process name, or the binary path — never a bare "mailspring",
  # which would also match this script's own argv and never install anything.
  if pgrep -x mailspring >/dev/null 2>&1 || pgrep -f 'bin/mailspring' >/dev/null 2>&1; then
    note "Mailspring is running — quit it, reopen, then pick Nordic under"
    note "Preferences > Appearance (or re-run this script once it is closed)"
  elif [ -f "$MS_DIR/config.json" ]; then
    python3 - "$MS_DIR/config.json" <<'PY'
import json, sys
p = sys.argv[1]
with open(p) as f:
    d = json.load(f)
core = d.setdefault('*', {}).setdefault('core', {})
core['themes'] = ['ui-nordic']
core['theme'] = 'ui-nordic'          # legacy key, kept consistent
with open(p, 'w') as f:
    json.dump(d, f, indent=2)
PY
    note "selected Nordic in $MS_DIR/config.json"
  fi
done
if [ "$MS_FOUND" = no ]; then
  note "Mailspring not installed — skipped"
fi

# ---------------------------------------------------------------------------
#  8. Snaps
# ---------------------------------------------------------------------------
#  A snap cannot read ~/.themes. It only sees themes handed to it over the
#  gtk-3-themes content interface, wired by default to gtk-common-themes — 53
#  themes, no Nordic. The snap finds nothing by that name and falls back to
#  Adwaita light, which is what draws the pale window frame around an otherwise
#  themed app. Publishing Nordic as our own content snap and connecting it
#  alongside gtk-common-themes fixes it: one plug can take several slots, which
#  is exactly how icon-theme-papirus already coexists there.
# ---------------------------------------------------------------------------
step "8. Snaps"
if ! command -v snap >/dev/null 2>&1; then
  note "snapd not installed — skipped"
else
  SNAP_CONSUMERS=$(snap connections 2>/dev/null \
    | awk '$1 == "content[gtk-3-themes]" { split($2, a, ":"); print a[1] }' | sort -u)
  if [ -z "$SNAP_CONSUMERS" ]; then
    note "no installed snap uses gtk-3-themes — skipped"
  elif ! command -v mksquashfs >/dev/null 2>&1; then
    note "mksquashfs missing (apt install squashfs-tools) — skipped"
  else
    SNAP_PKG="$REPO/nordic-themes_1.0_all.snap"
    if "$REPO/extras/snap/build-nordic-theme-snap.sh" "$SNAP_PKG" >/dev/null 2>&1; then
      note "built $(basename "$SNAP_PKG") ($(du -h "$SNAP_PKG" | cut -f1))"
      if [ "$HAVE_SUDO" = yes ] && SNAP_ERR=$(sudo snap install --dangerous "$SNAP_PKG" 2>&1); then
        note "installed the nordic-themes content snap"
        for s in $SNAP_CONSUMERS; do
          sudo snap connect "$s:gtk-3-themes" nordic-themes:gtk-3-themes 2>/dev/null \
            && note "connected $s -> nordic-themes" \
            || note "could not connect $s (already connected?)"
        done
        note "fully quit each of those snaps (check the tray) and reopen them"
        rm -f "$SNAP_PKG"
      else
        # Keep the .snap around — it is what the manual command needs.
        [ -n "${SNAP_ERR:-}" ] && note "snapd said: $SNAP_ERR"
        note "snap install failed. Finish by hand with:"
        note "   sudo snap install --dangerous $SNAP_PKG"
        for s in $SNAP_CONSUMERS; do
          note "   sudo snap connect $s:gtk-3-themes nordic-themes:gtk-3-themes"
        done
      fi
    else
      note "could not build the theme snap — skipped"
    fi
  fi
fi

# ---------------------------------------------------------------------------
#  9. Boot splash (Plymouth)
# ---------------------------------------------------------------------------
#  A `script`-plugin theme: snowflake on Polar Night, a travelling row of dots,
#  and a password prompt for encrypted disks. Artwork is generated by
#  extras/render-boot-assets.py from the same palette as the GTK theme.
# ---------------------------------------------------------------------------
step "9. Boot splash (Plymouth)"
if [ "$HAVE_SUDO" != yes ]; then
  note "no sudo — boot splash skipped"
elif [ ! -d /usr/share/plymouth/themes ]; then
  note "plymouth not installed — skipped"
elif [ ! -f /usr/lib/x86_64-linux-gnu/plymouth/script.so ]; then
  note "plymouth 'script' plugin missing (apt install plymouth-themes) — skipped"
elif [ ! -f "$REPO/extras/plymouth/nordic/logo.png" ]; then
  # A theme with missing images fails at boot, which is a bad place to find out.
  note "artwork missing — run ./extras/render-boot-assets.py first; skipped"
else
  sudo rm -rf /usr/share/plymouth/themes/nordic
  sudo cp -r "$REPO/extras/plymouth/nordic" /usr/share/plymouth/themes/nordic
  sudo chmod -R a+rX /usr/share/plymouth/themes/nordic
  note "installed /usr/share/plymouth/themes/nordic"

  sudo update-alternatives --install /usr/share/plymouth/themes/default.plymouth \
       default.plymouth /usr/share/plymouth/themes/nordic/nordic.plymouth 200 >/dev/null
  sudo update-alternatives --set default.plymouth \
       /usr/share/plymouth/themes/nordic/nordic.plymouth >/dev/null 2>&1
  note "set as the default plymouth theme"

  # The theme lives in the initramfs, so it does not take effect until this
  # runs. It is slow — tens of seconds — and is the reason this step is last.
  note "theme is $(du -sh "$REPO/extras/plymouth/nordic" | cut -f1), mostly the"
  note "background artwork — that much is added to the initramfs"
  note "rebuilding the initramfs (this takes a while)"
  if sudo update-initramfs -u >/dev/null 2>&1; then
    note "initramfs rebuilt — the splash appears on next boot"
  else
    note "update-initramfs failed; run 'sudo update-initramfs -u' yourself"
  fi
fi

# ---------------------------------------------------------------------------
#  10. Login screen (GDM)
# ---------------------------------------------------------------------------
#  GDM reads its settings through the dconf profile named `gdm`. The stock
#  profile only chains user-db + the packaged file-db, with no system-db, so
#  dropping a file in /etc/dconf/db/gdm.d has no effect until the profile is
#  extended. A profile in /etc overrides the one in /usr/share, which is how
#  this stays out of the way of the gdm3 package.
#
#  The background must live outside $HOME: the greeter runs as user `gdm`,
#  which cannot read /home/<you>.
# ---------------------------------------------------------------------------
step "10. Login screen (GDM)"
if [ "$HAVE_SUDO" != yes ]; then
  note "no sudo — login screen skipped"
elif ! command -v dconf >/dev/null 2>&1 || [ ! -d /usr/share/gdm ]; then
  note "GDM or dconf not present — skipped"
elif [ ! -f "$REPO/extras/gdm/$LOGIN_BG" ]; then
  note "$LOGIN_BG missing — run ./extras/render-boot-assets.py first; skipped"
else
  # Always installed under one fixed name, so switching LOGIN_BG does not
  # leave the previous choice behind in /usr/share/backgrounds.
  sudo install -D -m 644 "$REPO/extras/gdm/$LOGIN_BG" \
       /usr/share/backgrounds/nordic-login.png
  note "background -> /usr/share/backgrounds/nordic-login.png (from $LOGIN_BG)"

  # The badge under the password box. Stock is the Ubuntu wordmark at
  # /usr/share/pixmaps/ubuntu-logo-text-dark.svg, pointed at by
  # org.gnome.login-screen logo; a copy of it is kept in extras/gdm as
  # login-logo-original.svg.
  if [ -f "$REPO/extras/gdm/login-logo.svg" ]; then
    sudo install -D -m 644 "$REPO/extras/gdm/login-logo.svg" \
         /usr/share/pixmaps/nordic-login-logo.svg
    note "vendor logo -> /usr/share/pixmaps/nordic-login-logo.svg"
  fi

  for p in gdm Debian-gdm; do
    sudo install -d -m 755 /etc/dconf/profile
    printf 'user-db:user\nsystem-db:gdm\nfile-db:/var/lib/gdm3/greeter-dconf-defaults\n' \
      | sudo tee "/etc/dconf/profile/$p" >/dev/null
  done
  note "extended the gdm dconf profile with system-db:gdm"

  sudo install -d -m 755 /etc/dconf/db/gdm.d
  sudo tee /etc/dconf/db/gdm.d/10-nordic >/dev/null <<'EOF'
# Nordic login screen. Managed by install-nordic.sh — edit
# extras/gdm/ in the Nordic repo instead of this file.
[com/ubuntu/login-screen]
background-picture-uri='file:///usr/share/backgrounds/nordic-login.png'
background-size='cover'
background-repeat='no-repeat'
background-color='#2e3440'
EOF

  # Repoint the vendor logo only if one was actually installed above. Setting
  # the key unconditionally would leave GDM referencing a file that is not
  # there, and it renders nothing at all rather than falling back to Ubuntu's.
  if [ -f /usr/share/pixmaps/nordic-login-logo.svg ]; then
    printf "\n[org/gnome/login-screen]\nlogo='%s'\n" \
           /usr/share/pixmaps/nordic-login-logo.svg \
      | sudo tee -a /etc/dconf/db/gdm.d/10-nordic >/dev/null
    note "vendor logo repointed at the Nordic one"
  else
    note "no Nordic logo installed — leaving the Ubuntu badge in place"
  fi
  if sudo dconf update 2>/dev/null; then
    note "wrote /etc/dconf/db/gdm.d/10-nordic and rebuilt the db"
    note "visible at the next login screen (reboot, or restart gdm)"
  else
    note "dconf update failed — run 'sudo dconf update' yourself"
  fi
fi

# ---------------------------------------------------------------------------
#  11. Warp terminal
# ---------------------------------------------------------------------------
#  Warp reads custom themes from ~/.local/share/warp-terminal/themes and names
#  them after the file, so nordic.yaml becomes theme = "nordic".
#
#  settings.toml is edited as text on purpose. Warp writes multi-line inline
#  tables with trailing commas (TOML 1.1 draft), which Python's tomllib rejects
#  outright — a parse-and-rewrite would fail on a perfectly good file, or worse,
#  drop what it could not represent.
# ---------------------------------------------------------------------------
step "11. Warp terminal theme"
WARP_DATA="$HOME/.local/share/warp-terminal"
WARP_SETTINGS="$HOME/.config/warp-terminal/settings.toml"
if [ ! -d "$WARP_DATA" ] && ! command -v warp-terminal >/dev/null 2>&1; then
  note "Warp not installed — skipped"
else
  mkdir -p "$WARP_DATA/themes"
  cp "$REPO/extras/warp/nordic.yaml" "$WARP_DATA/themes/nordic.yaml"
  note "installed $WARP_DATA/themes/nordic.yaml"

  if pgrep -x warp >/dev/null 2>&1; then
    note "Warp is running — it rewrites settings.toml from memory on exit, so"
    note "pick Nordic under Settings > Appearance > Themes (or quit and re-run)"
  elif [ -f "$WARP_SETTINGS" ]; then
    # Back up once, not on every run — otherwise the second run "backs up"
    # our own output and the original is gone.
    [ -f "$WARP_SETTINGS.nordic-backup" ] || cp "$WARP_SETTINGS" "$WARP_SETTINGS.nordic-backup"
    python3 - "$WARP_SETTINGS" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()
want = [('system_theme', 'false'), ('theme', '"nordic"')]
m = re.search(r'^\[appearance\.themes\]\s*$', src, re.M)
if m:
    start = m.end()
    nxt = re.search(r'^\[', src[start:], re.M)
    end = start + (nxt.start() if nxt else len(src) - start)
    body = src[start:end]
    for k, v in want:
        if re.search(rf'^{k}\s*=', body, re.M):
            body = re.sub(rf'^{k}\s*=.*$', f'{k} = {v}', body, flags=re.M)
        else:
            body = body.rstrip('\n') + f'\n{k} = {v}\n'
    src = src[:start] + body + src[end:]
else:
    src = src.rstrip('\n') + '\n\n[appearance.themes]\n' + \
          ''.join(f'{k} = {v}\n' for k, v in want)
open(path, 'w').write(src)
PY
    note "selected Nordic in settings.toml (backup: settings.toml.nordic-backup)"
  else
    note "no settings.toml yet — pick Nordic under Settings > Appearance > Themes"
  fi
fi

# ---------------------------------------------------------------------------
#  12. Desktop wallpaper
# ---------------------------------------------------------------------------
#  Per-user, so no root needed — the file goes in ~/.local/share/backgrounds
#  and gsettings points at it. The previous wallpaper is remembered once so
#  --uninstall can restore it.
#
#  GSETTINGS_SCHEMA_DIR is pinned for the same reason as in section 4: run from
#  a terminal inside a snap, gsettings otherwise resolves against the snap's
#  own bundled schemas.
# ---------------------------------------------------------------------------
step "12. Desktop wallpaper"
if [ -z "$DESKTOP_BG" ]; then
  note "NORDIC_DESKTOP_BG empty — leaving the current wallpaper alone"
elif [ ! -f "$REPO/extras/wallpapers/$DESKTOP_BG" ]; then
  note "extras/wallpapers/$DESKTOP_BG not found — skipped"
else
  WALL_DIR="$HOME/.local/share/backgrounds"
  mkdir -p "$WALL_DIR" "$STATE_DIR"
  install -m 644 "$REPO/extras/wallpapers/$DESKTOP_BG" "$WALL_DIR/$DESKTOP_BG"
  WALL_URI="file://$WALL_DIR/$DESKTOP_BG"

  # Remember what was there first — but only the first time, or re-running
  # would record our own wallpaper as the thing to restore.
  if [ ! -f "$STATE_DIR/desktop-background.prev" ]; then
    {
      GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
        gsettings get org.gnome.desktop.background picture-uri
      GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
        gsettings get org.gnome.desktop.background picture-uri-dark
      GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
        gsettings get org.gnome.desktop.background picture-options
    } > "$STATE_DIR/desktop-background.prev" 2>/dev/null
    note "remembered the previous wallpaper for --uninstall"
  fi

  for k in picture-uri picture-uri-dark; do
    GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
      gsettings set org.gnome.desktop.background "$k" "$WALL_URI" 2>/dev/null
  done
  GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
    gsettings set org.gnome.desktop.background picture-options 'zoom' 2>/dev/null
  note "wallpaper -> $WALL_DIR/$DESKTOP_BG"
  note "the lock screen follows it automatically — GNOME blurs this same image"
fi

echo
echo "============================================================"
echo " Done. Log out and back in for the shell theme to load."
echo
echo " GTK4/libadwaita apps pick up the new colours immediately —"
echo " just restart the app (e.g. 'nautilus -q' then reopen)."
echo "============================================================"

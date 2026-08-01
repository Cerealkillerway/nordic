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
    --exclude='.git' --exclude='node_modules' --exclude='src' --exclude='Art' \
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

# GNOME Shell theme needs the User Themes extension.
if ! gnome-extensions list 2>/dev/null | grep -q 'user-theme@gnome-shell-extensions'; then
  note "installing gnome-shell-extensions for the User Themes extension"
  sudo apt install -y gnome-shell-extensions >/dev/null 2>&1 || \
    note "could not install gnome-shell-extensions — do it manually"
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
if command -v flatpak >/dev/null 2>&1; then
  sudo flatpak override --filesystem="$HOME/.themes:ro"
  sudo flatpak override --env=GTK_THEME="$THEME_NAME"
  note "GTK3 flatpaks (e.g. GIMP) will pick this up; libadwaita flatpaks may not"
fi

echo
echo "============================================================"
echo " Done. Log out and back in for the shell theme to load."
echo
echo " GTK4/libadwaita apps pick up the new colours immediately —"
echo " just restart the app (e.g. 'nautilus -q' then reopen)."
echo "============================================================"

#!/usr/bin/env bash
# build-nordic-theme-snap.sh — export Nordic to confined snaps.
#
# Snaps cannot read ~/.themes. They only see themes handed to them over the
# `gtk-3-themes` content interface, which on a stock Ubuntu box is wired to
# gtk-common-themes — 53 themes, none of them Nordic. So a snap like Mailspring
# finds no theme by that name and draws its window frame with Adwaita light.
#
# The fix is to publish Nordic as a content snap of our own and connect it
# alongside gtk-common-themes. Multiple slots can feed one content plug (that
# is how icon-theme-papirus coexists with gtk-common-themes), so this adds
# Nordic without displacing anything.
#
# No snapcraft needed: a content snap is just a squashfs with a meta/snap.yaml.
#
# Usage:  ./extras/snap/build-nordic-theme-snap.sh [output.snap]
set -euo pipefail

THEME_NAME="Nordic"
SRC="${NORDIC_THEME_DIR:-$HOME/.themes/$THEME_NAME}"
OUT="${1:-$PWD/nordic-themes_1.0_all.snap}"

[ -d "$SRC" ] || { echo "No theme at $SRC — run ./install-nordic.sh first." >&2; exit 1; }
command -v mksquashfs >/dev/null || { echo "mksquashfs not found (apt install squashfs-tools)" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/meta" "$STAGE/share/themes"
cp -a "$SRC" "$STAGE/share/themes/$THEME_NAME"

# snapd refuses any snap whose contents are not world-readable:
#   container.go: "." should be world-readable and executable, and isn't: drwx------
# mktemp -d gives 0700, and mksquashfs -all-root rewrites ownership but not
# permissions, so the staged tree has to be opened up before packing. ~/.themes
# may also carry restrictive modes from wherever the theme was unpacked.
chmod -R a+rX "$STAGE"

# base: bare — nothing is executed from this snap, it only exports files.
cat > "$STAGE/meta/snap.yaml" <<EOF
name: nordic-themes
version: '1.0'
summary: Nordic GTK theme, exported for snaps
description: |
  Exports the Nordic GTK theme over the gtk-3-themes content interface so that
  confined snaps can use it. Connect it alongside gtk-common-themes:
    sudo snap connect <snap>:gtk-3-themes nordic-themes:gtk-3-themes
architectures:
- all
base: bare
confinement: strict
grade: stable
slots:
  gtk-3-themes:
    interface: content
    source:
      read:
      - \$SNAP/share/themes/$THEME_NAME
EOF

mksquashfs "$STAGE" "$OUT" -noappend -comp xz -no-fragments -all-root -no-xattrs >/dev/null

echo "built $OUT ($(du -h "$OUT" | cut -f1))"
cat <<EOF

Install and wire it up (needs root):

  sudo snap install --dangerous "$OUT"
  sudo snap connect mailspring:gtk-3-themes nordic-themes:gtk-3-themes

--dangerous is required because the snap is not signed by the store. It runs
nothing — it is a read-only pile of CSS and PNGs — so the flag is only saying
"this did not come from the store".

Then fully quit Mailspring (check the tray) and reopen it.
EOF

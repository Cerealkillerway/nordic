# Nordic fork — libadwaita support

Fork of [EliverLara/Nordic](https://github.com/EliverLara/Nordic) that makes the
theme apply to **libadwaita** apps (Files, Settings, Text Editor, Software,
Calendar…), which upstream Nordic does not touch.

Install: `./install-nordic.sh` — undo with `./install-nordic.sh --uninstall`.

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

## Known limits (not fixable in this repo)

- **Snap apps** are unaffected — they need the theme packaged as a theme snap.
- **GTK4 flatpaks** are unaffected — Flathub has 337 `org.gtk.Gtk3theme.*`
  extensions and **zero** `Gtk4theme` ones; no such extension point exists.
- This override is unsupported by GNOME upstream and may need revisiting when
  libadwaita changes its token set (i.e. around Ubuntu 28.04).

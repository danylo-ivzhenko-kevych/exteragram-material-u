# Material U — Pixel clean UI (exteraGram plugin)

A thin "switcher" plugin. It does **not** hand-draw a new UI (that would be brittle
and break on every app update). Instead it flips exteraGram's **own** appearance
flags toward a flat, Material-You look (like Google Pixel) — no liquid glass / blur,
Material-style switches, system font — and ships a **diagnostic** that lists the exact
settings keys present on *your* installed version.

## Why this approach

- Telegram's Android UI is drawn manually on a Canvas, so a full plugin reskin is
  fragile and breaks easily. We drive what exteraGram already supports instead.
- "Liquid glass", "settings islands" and "Monet / dynamic colours" are exteraGram
  options. In the open source (`exteraSquad/exteraGram`) some keys are older than the
  shipped app, so the exact modern keys are read **straight from your phone** via
  `preferences.getAll()` — no ADB required.

## "Errors" in the editor are not real

The imports (`base_plugin`, `hook_utils`, `ui.settings`, …) are provided by the
exteraGram runtime (Chaquopy) **on the device**. They don't exist on a desktop, so a
local editor underlines them as unresolved. That is expected; the code compiles and
runs inside the app. Imports carry `# type: ignore` to silence the warning.

## Install (manual — always works)

1. exteraGram → Settings → **exteraGram → Plugins** (enable the plugin system).
2. Send `material_u.py` to any chat (e.g. Saved Messages) and open the file.
3. Tap **Install**, then **Enable after installation**.
4. Open the plugin settings (Plugins → Material U).

## Install via repository (auto-update)

exteraGram reads **public** repositories only, over raw HTTPS. This repo already ships
a manifest `extera-plugins.json`.

1. exteraGram → Plugins → **add repository**, paste the raw URL:
   `https://raw.githubusercontent.com/<owner>/<repo>/main/extera-plugins.json`
2. Find "Material U" in the list → Install.

> `sha256` / `size` in the manifest must match `material_u.py`. After any change,
> refresh them:
> ```sh
> shasum -a 256 material_u.py   # -> sha256
> wc -c < material_u.py         # -> size
> ```
> If the client requires a `.plugin` extension instead of `.py`, just change the
> `file` field in the manifest; manual install of the `.py` always works.

## How to use

- **✨ Apply Material You preset** — turns off glass/blur/islands and enables Monet
  where your version supports it; shows exactly what changed.
- **Quick toggles** — per-option switches (blur, switch style, font, FAB). Their state
  is read from the live exteraGram config and written straight back.
- Some changes apply instantly; others need reopening the screen or restarting
  exteraGram.

## Find the exact keys (to target liquid glass / islands / Monet)

v1 deliberately does **not** guess modern field names. Instead:

1. Open **Diagnostics → 🔍 Show all exteraGram keys**.
2. Tap **📋 Copy keys to clipboard** and share the list.
3. From that list the exact keys (e.g. `liquidGlass…`, `…Island…`, `monet…`) get
   wired into `KNOWN_BOOL_FLAGS` / `PRESET_HEURISTICS`, so the preset targets your
   version precisely.

> Keys are also written to the plugin log on load (tag `plugin.material_u`).

## Status / caveats

- v1 is verified against the SDK docs and the `ExteraConfig` source, but not yet run
  on a device (no ADB). If a row isn't tappable or an option doesn't apply, it's almost
  always a field-name difference between versions — the diagnostic exists for that.
- Nothing is hardcoded or deleted; only known/discovered flags are toggled.

## Files

- `material_u.py` — the plugin.
- `extera-plugins.json` — exteraGram repository manifest.
- `README.md` — this file.

# 2026-08-23 — the installed Linux packages have no app icon

Status: implemented on `fix/openai-streaming-tts-hardening` (ships in fork v0.20.7) · Reported on
Ubuntu 26.04 and Fedora Workstation 44.

## Why

The deb and rpm installed from the release artifacts show no application icon anywhere in the
shell — app grid, dash, dock. The running window is fine on X11 (the main process sets a
`BrowserWindow` icon from `public/apple-touch-icon.png`, `electron/main.ts:824-831`), which is why
this only shows up once the package is installed, and why it is total on Wayland, where the shell
takes the icon from the `.desktop` entry alone.

Root cause is in how electron-builder resolves `linux.icon`, confirmed by running its own resolver
(`app-builder-lib/out/util/iconConverter.js`) against our config:

```
sources: ["assets/icon"] isFallback: false
  size=1024  ->  /usr/share/icons/hicolor/1024x1024/apps/Hermes.png   (from assets/icon.png)
```

`convertIcon(..., format: "set")` returns a *set* of icons when it resolves a directory, but when
it resolves a single PNG it takes the early return

```js
// set: source is already a .png — return as-is with its dimensions
const { width, height } = await getPngSize(resolved)
return [{ file: resolved, size: Math.max(width, height) }]
```

and yields exactly one entry. `FpmTarget` then installs each entry at
`/usr/share/icons/hicolor/${size}x${size}/apps/${executableName}.png` (`FpmTarget.js:216-219`), so
our 1024x1024 master became a lone `hicolor/1024x1024/apps/Hermes.png`. `1024x1024` is not one of
the directories listed in hicolor-icon-theme's `index.theme` (it stops at `512x512` plus
`scalable`), and the freedesktop Icon Theme Specification only searches indexed directories — so
`Icon=Hermes` in the generated `Hermes.desktop` resolved to nothing. The config was never wrong in
an obvious way: `"icon": "assets/icon"` is correct for mac and Windows, and Linux silently
inherited it.

## Change

- [x] `apps/desktop/assets/icons/{16x16,24x24,32x32,48x48,64x64,128x128,256x256,512x512}.png`,
      generated from the 1024 master: cropped to the artwork bounding box and re-centred on a
      square canvas (full-bleed, like `assets/icon.ico`) then Lanczos-resized. The master carries
      the ~10% macOS grid margin, which renders visibly small next to native icons — the same
      reason Windows ships a full-bleed `.ico` (commits `80c86c494`, `e52431011`). The generated
      256 differs from the `.ico`'s 256 frame by 3.85/255 mean absolute error, i.e. the same
      treatment.
- [x] `build.linux.icon: "assets/icons"` in `apps/desktop/package.json`. mac and Windows keep
      inheriting the top-level `assets/icon` — untouched.
- [x] `apps/desktop/assets/icons/README.md` — why it is a directory, the artwork treatment, and
      the regeneration snippet.
- [x] `apps/desktop/scripts/linux-icons.test.mjs` — asserts `build.linux.icon` is a directory,
      every `NxN.png` is a size hicolor actually indexes (this is what fails on the old config),
      each file's IHDR matches its name, and 48/256 are present. Verified it fails when
      `build.linux.icon` is removed.

## Verification

```
$ node -e '<electron-builder convertIcon with linux.icon>'
  size=16   -> /usr/share/icons/hicolor/16x16/apps/Hermes.png
  size=24   -> ... 24x24 ...      size=32  -> ... 32x32 ...
  size=48   -> ... 48x48 ...      size=64  -> ... 64x64 ...
  size=128  -> ... 128x128 ...    size=256 -> ... 256x256 ...
  size=512  -> /usr/share/icons/hicolor/512x512/apps/Hermes.png
$ npx vitest run --project electron scripts/linux-icons.test.mjs   # 2 passed
```

Operator check after the next release build: install the deb/rpm, then
`ls /usr/share/icons/hicolor/*/apps/Hermes.png` should list eight files, and the icon should
appear in the app grid without a `gtk-update-icon-cache` run (the packages trigger it).

## Out of scope / follow-ups

- **`apps/desktop/assets/icon.icns` is not an ICNS** — it is a PNG with an `.icns` extension
  (`89 50 4e 47` where `icns` belongs), and `MacPackager` copies it into
  `Contents/Resources/icon.icns` verbatim (`macPackager.js:374-380`), so Finder and Launchpad get
  an invalid icon file. The Dock looks right because `main.ts:12040` calls `app.dock.setIcon()`
  with the PNG at runtime, which probably masked it. Not touched here: it is a separate defect on
  a different platform, and regenerating a real `.icns` should be its own change.
- `StartupWMClass` is not set in the desktop entry. Not added speculatively — if the app-grid icon
  is now right but the *running* window still shows a generic icon on Wayland, that is the next
  thing to add.

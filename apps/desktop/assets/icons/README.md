# Linux app icons (`build.linux.icon`)

electron-builder installs each PNG here at
`/usr/share/icons/hicolor/<size>x<size>/apps/Hermes.png` in the deb, rpm and
AppImage, which is what `Icon=Hermes` in the generated `Hermes.desktop`
resolves against.

**Why a directory and not `assets/icon.png`.** electron-builder's icon
resolver returns a set of icons when it is given a directory, but when it is
given a single PNG it returns exactly one entry sized to that file. The master
art is 1024x1024, so the packages used to ship a lone
`hicolor/1024x1024/apps/Hermes.png` — and `1024x1024` is not one of the
directories listed in hicolor-icon-theme's `index.theme`, so the icon lookup
never found it and the installed app had no icon at all (seen on Ubuntu 26.04
and Fedora 44). Every size here must therefore be a directory the hicolor
theme actually indexes; `scripts/linux-icons.test.mjs` enforces that.

**Artwork.** Cropped from `../icon.png` to the artwork's bounding box and
re-centred on a square canvas, i.e. full-bleed like `../icon.ico`. The 1024
master carries the ~10% macOS grid margin, which is right for the Dock but
renders visibly smaller than neighbouring icons on Linux, the same reason
Windows uses the full-bleed `.ico`.

To regenerate after the brand art changes (needs Pillow):

```python
from PIL import Image
master = Image.open("assets/icon.png").convert("RGBA")
art = master.crop(master.getbbox())
side = max(art.size)
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(art, ((side - art.width) // 2, (side - art.height) // 2))
for s in (16, 24, 32, 48, 64, 128, 256, 512):
    canvas.resize((s, s), Image.LANCZOS).save(f"assets/icons/{s}x{s}.png", optimize=True)
```

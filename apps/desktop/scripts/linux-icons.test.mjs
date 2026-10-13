import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { test } from 'vitest'

// Guards the Linux app icon, which was missing from the installed deb/rpm
// (Ubuntu 26.04, Fedora 44) until 2026-08-23.
//
// Why this file exists: electron-builder resolves `linux.icon` through an
// "icon set" resolver. Handed a single PNG it returns exactly ONE entry sized
// to that PNG, and the fpm/AppImage targets install each entry at
// /usr/share/icons/hicolor/<size>x<size>/apps/<executableName>.png. Our master
// art is 1024x1024, so the packages shipped a lone
// hicolor/1024x1024/apps/Hermes.png — and 1024x1024 is not one of the
// directories listed in the freedesktop hicolor theme's index.theme, so the
// icon lookup behind `Icon=Hermes` never saw it and every desktop showed no
// icon at all. Pointing linux.icon at a DIRECTORY of NxN.png files is what
// makes the resolver emit a real set.
const DESKTOP_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')

// Directories shipped by hicolor-icon-theme's index.theme. An icon installed
// outside this list is invisible to the icon-theme lookup, however valid the
// PNG is.
const HICOLOR_SIZES = new Set([8, 16, 22, 24, 32, 36, 48, 64, 72, 96, 128, 192, 256, 512])

// Sizes desktop shells actually request: 48 for the app grid / file manager,
// 256 for dock and alt-tab on HiDPI. Keep both present so nothing has to be
// upscaled from a smaller entry.
const REQUIRED_SIZES = [48, 256]

function readPngSize(file) {
  // PNG signature is 8 bytes, then the IHDR chunk header is 8 more: width and
  // height are big-endian uint32 at offsets 16 and 20.
  const buf = readFileSync(file)
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) }
}

function iconDir() {
  const pkg = JSON.parse(readFileSync(join(DESKTOP_ROOT, 'package.json'), 'utf8'))
  const configured = pkg.build?.linux?.icon
  assert.ok(
    configured,
    'build.linux.icon must be set: without it electron-builder falls back to the top-level ' +
      'single-PNG icon and installs one unusable hicolor/1024x1024 entry'
  )
  return join(DESKTOP_ROOT, configured)
}

test('build.linux.icon points at a directory of icons, not a single PNG', () => {
  const dir = iconDir()
  assert.ok(statSync(dir).isDirectory(), `${dir} must be a directory (a lone PNG yields a one-size icon set)`)
})

test('every Linux icon lands in a directory the hicolor theme actually indexes', () => {
  const dir = iconDir()
  const sizes = readdirSync(dir)
    .map(name => /^(\d+)x(\d+)\.png$/.exec(name))
    .filter(Boolean)
    .map(match => ({ name: `${match[1]}x${match[2]}.png`, width: Number(match[1]), height: Number(match[2]) }))

  assert.ok(sizes.length > 0, `${dir} contains no NxN.png files, so electron-builder would find no icon set`)

  for (const { name, width, height } of sizes) {
    assert.equal(width, height, `${name}: icons must be square`)
    assert.ok(
      HICOLOR_SIZES.has(width),
      `${name}: ${width}x${width} is not a hicolor theme directory, so the desktop will never find this icon`
    )
    const actual = readPngSize(join(dir, name))
    assert.deepEqual(
      actual,
      { width, height },
      `${name}: the file is ${actual.width}x${actual.height}; the name decides its install path, so they must agree`
    )
  }

  const present = new Set(sizes.map(s => s.width))
  for (const required of REQUIRED_SIZES) {
    assert.ok(present.has(required), `missing ${required}x${required}.png, a size desktop shells request directly`)
  }
})

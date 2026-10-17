// ForgeGuard fork: the fork's electron-builder settings, as one overlay.
//
// Upstream owns the base packaging config. Before upstream 0.22 that is the
// "build" block in package.json; from 0.22 on it is electron-builder.config.cjs
// (and package.json has no "build" block at all). The fork keeps none of its
// packaging choices inside either file: they all live here, and
// scripts/forgeguard-dist.mjs builds with `--config electron-builder.forgeguard.cjs`,
// so a sync only has to keep this file, never re-apply hunks to upstream's.
//
// What the fork changes, and why:
//   - Installer set: Linux AppImage + deb + rpm, Windows NSIS + portable
//     (unsigned), macOS dmg + zip. Upstream 0.22 ships AppImage, MSIX and
//     dmg/zip only.
//   - Artifact names: hermes-desktop-client-<version>-<os>-<arch>.<ext>, plus
//     -win-<arch>-setup / -portable for the two Windows .exe files so they
//     cannot overwrite each other. Release notes and docs name these files.
//   - Linux icon set: assets/icons/ (NxN.png). A single PNG gives
//     electron-builder a one-entry icon set and the deb/rpm install an icon
//     the hicolor theme never indexes (scripts/linux-icons.test.mjs).
//   - homepage: the deb/rpm (fpm) targets refuse to build without one.
//   - publish: null. Fork builds are uploaded by the release workflow, never
//     by electron-builder, and must not embed an update feed.
//   - afterPack: scripts/forgeguard-after-pack.mjs runs upstream's hook, then
//     ad-hoc signs the macOS bundle (no Developer ID on the fork).
//   - electronVersion follows the exact electron devDependency pin.
//
// Default export: an electron-builder config function (electron-builder calls
// it when this file is passed as --config) returning the resolved config.
// Named exports are for scripts and tests.
// @ts-check
'use strict'

const fs = require('node:fs')
const path = require('node:path')

const ARTIFACT_PREFIX = 'hermes-desktop-client'
const HOMEPAGE = 'https://github.com/forgeguard-ai/hermes-agent#readme'
const UPSTREAM_CONFIG_FILE = 'electron-builder.config.cjs'

/** The fork's settings. Each object key here replaces the base's key of the same name. */
const FORGEGUARD = Object.freeze({
  artifactName: `${ARTIFACT_PREFIX}-\${version}-\${os}-\${arch}.\${ext}`,
  homepage: HOMEPAGE,
  afterPack: 'scripts/forgeguard-after-pack.mjs',
  mac: Object.freeze({
    target: Object.freeze(['dmg', 'zip'])
  }),
  win: Object.freeze({
    target: Object.freeze(['nsis', 'portable']),
    // Keeps electron-builder's signtool/winCodeSign step out of the build; the
    // exe identity is stamped by scripts/set-exe-identity.mjs instead.
    signAndEditExecutable: false
  }),
  nsis: Object.freeze({
    artifactName: `${ARTIFACT_PREFIX}-\${version}-win-\${arch}-setup.\${ext}`,
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    perMachine: false,
    shortcutName: 'Hermes',
    uninstallDisplayName: 'Hermes',
    warningsAsErrors: false
  }),
  portable: Object.freeze({
    artifactName: `${ARTIFACT_PREFIX}-\${version}-win-\${arch}-portable.\${ext}`
  }),
  linux: Object.freeze({
    icon: 'assets/icons',
    target: Object.freeze(['AppImage', 'deb', 'rpm'])
  })
})

/** Platform sections that may carry their own `publish` key. */
const PUBLISH_SECTIONS = [
  'mac',
  'mas',
  'win',
  'linux',
  'appImage',
  'deb',
  'rpm',
  'nsis',
  'portable',
  'msix',
  'appx',
  'snap'
]

/**
 * @param {string} [desktopDir]
 * @returns {Record<string, any>}
 */
function readPackageJson(desktopDir = __dirname) {
  return JSON.parse(fs.readFileSync(path.join(desktopDir, 'package.json'), 'utf8'))
}

/**
 * The upstream base config: electron-builder.config.cjs when it exists
 * (upstream 0.22 and later), else package.json's "build" block.
 * @param {string} [desktopDir]
 * @returns {{ source: string, config: Record<string, any> }}
 */
function loadBaseConfig(desktopDir = __dirname) {
  const upstreamFile = path.join(desktopDir, UPSTREAM_CONFIG_FILE)
  if (fs.existsSync(upstreamFile)) {
    return { source: UPSTREAM_CONFIG_FILE, config: require(upstreamFile) }
  }
  const build = readPackageJson(desktopDir).build
  if (!build || typeof build !== 'object') {
    throw new Error(`no ${UPSTREAM_CONFIG_FILE} and no "build" block in ${path.join(desktopDir, 'package.json')}`)
  }
  return { source: 'package.json#build', config: build }
}

/**
 * Return a copy of `base` with the fork's settings applied. `base` is not
 * modified. Values may be functions (upstream's config has some), so this
 * copies section by section rather than cloning.
 * @param {Record<string, any>} base
 * @param {{ electronVersion?: string }} [options]
 * @returns {Record<string, any>}
 */
function applyForgeguardOverlay(base, { electronVersion } = {}) {
  /** @type {Record<string, any>} */
  const config = { ...base }

  if (electronVersion) {
    config.electronVersion = electronVersion
  }
  config.artifactName = FORGEGUARD.artifactName
  config.afterPack = FORGEGUARD.afterPack
  config.extraMetadata = { ...base.extraMetadata, homepage: FORGEGUARD.homepage }

  for (const section of /** @type {const} */ (['mac', 'win', 'nsis', 'portable', 'linux'])) {
    config[section] = { ...base[section], ...copyArrays(FORGEGUARD[section]) }
  }

  config.publish = null
  for (const section of PUBLISH_SECTIONS) {
    if (config[section] && typeof config[section] === 'object' && 'publish' in config[section]) {
      config[section] = { ...config[section], publish: null }
    }
  }

  return config
}

/**
 * Frozen arrays would leak into electron-builder's config; hand it copies.
 * @param {Record<string, any>} section
 */
function copyArrays(section) {
  return Object.fromEntries(
    Object.entries(section).map(([key, value]) => [key, Array.isArray(value) ? [...value] : value])
  )
}

/**
 * The exact electron pin from package.json devDependencies.
 * @param {string} [desktopDir]
 * @returns {string}
 */
function pinnedElectronVersion(desktopDir = __dirname) {
  const spec = readPackageJson(desktopDir).devDependencies?.electron
  if (typeof spec !== 'string' || !/^\d+\.\d+\.\d+$/.test(spec)) {
    throw new Error(`electron devDependency must be an exact version, got ${JSON.stringify(spec)}`)
  }
  return spec
}

/**
 * Base config + the fork overlay: the config forgeguard-dist.mjs builds with.
 * @param {string} [desktopDir]
 * @returns {Record<string, any>}
 */
function resolveForgeguardConfig(desktopDir = __dirname) {
  const { config } = loadBaseConfig(desktopDir)
  return applyForgeguardOverlay(config, { electronVersion: pinnedElectronVersion(desktopDir) })
}

function forgeguardElectronBuilderConfig() {
  return resolveForgeguardConfig(__dirname)
}

module.exports = forgeguardElectronBuilderConfig
module.exports.FORGEGUARD = FORGEGUARD
module.exports.UPSTREAM_CONFIG_FILE = UPSTREAM_CONFIG_FILE
module.exports.applyForgeguardOverlay = applyForgeguardOverlay
module.exports.loadBaseConfig = loadBaseConfig
module.exports.pinnedElectronVersion = pinnedElectronVersion
module.exports.resolveForgeguardConfig = resolveForgeguardConfig

/**
 * forgeguard-after-pack.mjs — the fork's electron-builder afterPack hook.
 *
 * electron-builder.forgeguard.cjs points `afterPack` here. It runs upstream's
 * hook (scripts/after-pack.mjs, kept byte-identical to upstream) first, then
 * the fork's own step, so a sync never has to re-apply fork code inside
 * upstream's after-pack.mjs.
 *
 * The fork's step: on macOS, guarantee the packed bundle carries at least an
 * AD-HOC code signature. electron-builder skips its signing pass entirely when
 * it detects a pull-request build (release-on-merge.yml is
 * pull_request-triggered) or when no identity is discoverable — and on Apple
 * Silicon a fully unsigned, quarantined app fails Gatekeeper's assessment with
 * "«app» is damaged and can't be opened" before a single line of the main
 * process runs (this shipped in v2026.7.1-forgeguard.1). afterPack runs before
 * electron-builder's own sign step, so when that step does run (a real
 * Developer ID someday) it simply re-signs over this; when it skips, this
 * signature is what lands in the dmg/zip. Deliberately plain ad-hoc — no
 * --options runtime, no entitlements: hardened runtime only matters for
 * notarization, and without the entitlement file an ad-hoc hardened binary
 * would break Electron's JIT. This THROWS on failure: an unsigned arm64 bundle
 * is a broken deliverable, not a cosmetic defect.
 *
 * The signature goes on last, after upstream's hook, because anything that
 * changes the bundle after signing invalidates the signature.
 */

import { execFileSync } from 'node:child_process'
import path from 'node:path'

import upstreamAfterPack from './after-pack.mjs'

/**
 * @param {{ appOutDir: string, packager?: { appInfo?: { productFilename?: string } } }} context
 * @param {typeof execFileSync} [run]
 * @returns {string} the signed .app path
 */
export function adhocSignMacBundle(context, run = execFileSync) {
  const productName = context.packager?.appInfo?.productFilename || 'Hermes'
  const appPath = path.join(context.appOutDir, `${productName}.app`)

  console.log(`[forgeguard-after-pack] ad-hoc signing ${appPath}`)
  run('codesign', ['--force', '--deep', '--sign', '-', appPath], { stdio: 'inherit' })
  run('codesign', ['--verify', '--deep', '--strict', appPath], { stdio: 'inherit' })

  return appPath
}

/**
 * @param {{ electronPlatformName: string, appOutDir: string }} context
 * @param {{ upstream?: (context: any) => unknown, sign?: (context: any) => unknown }} [steps]
 */
export async function forgeguardAfterPack(context, { upstream = upstreamAfterPack, sign = adhocSignMacBundle } = {}) {
  await upstream(context)

  if (context.electronPlatformName === 'darwin') {
    sign(context)
  }
}

export default async function afterPack(context) {
  await forgeguardAfterPack(context)
}

/**
 * ForgeGuard fork build-time switches.
 *
 * The fork ships a static, self-hosted client: the desktop app is installed from
 * the fork's own release artifacts and the runtime image is what the lab
 * deploys, so nothing in the client should be measuring itself against
 * upstream's `main` or nudging the operator to update. Upstream's desktop update
 * machinery does exactly that — `git ls-remote` / a GitHub compare every 30
 * minutes from the Electron process, an "N commits behind" readout on the
 * version pills, and a bottom-right "Update ready" toast — with no config flag
 * anywhere to turn it off. This constant is that flag.
 *
 * With it off: the update poller never starts (no network calls, no toast, no
 * `(+N)` on the pills), the two version pills become plain readouts the user
 * may hide, and the manual "Check for updates" paths short-circuit. Flip it
 * back on to restore upstream behaviour wholesale.
 */
export const FORK_UPDATE_CHECKS_ENABLED = false

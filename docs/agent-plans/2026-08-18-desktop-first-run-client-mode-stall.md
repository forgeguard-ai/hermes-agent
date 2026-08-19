# 2026-08-18 — Desktop: first-run Client Mode connect stalls at "Starting Hermes… 2%"

Status: **open — root cause found, no fix applied** (research only; nothing in
`apps/desktop` was modified for this record) · Affects: every fork desktop
release since `v0.19.0` (upstream base `v2026.7.20`), including `v0.20.4` ·
Related: `2026-08-17-upstream-sync-v2026.8.16.2-plan.md` item 2 (post-recreate
re-auth stall — a *different* stall with the same "must restart the app" workaround).

## Symptom

On a fresh profile (first launch, or after wiping `Application Support/Hermes`),
the first-run chooser opens, the user picks **Client Mode**, enters the gateway
URL, signs in, and presses **Connect**. The chooser closes and the app sits on
the onboarding card:

> **Let's get you setup with Hermes Agent** · Connect a model provider to start
> chatting. Most options take one click.
> Starting Hermes… ▮░░░░░░░ Starting Hermes Desktop… **2%**

It never advances. Quitting and relaunching the client connects immediately,
**without** asking for sign-in again — the URL and credential were saved fine.
Only the *first* launch is affected; returning users never see it.

## What the screen is, exactly

The card is `DesktopOnboardingOverlay` (`apps/desktop/src/components/onboarding/index.tsx`)
in its `Preparing` branch (`:378-401`): it renders while
`onboarding.configured !== true` and the gateway is not open, and shows the
**boot store's** progress. The two visible values are diagnostic:

- **"Starting Hermes Desktop…"** is `INITIAL_BOOT_STATE.message`
  (`src/store/boot.ts:13`), i.e. the renderer's boot store still holds its
  construction-time message — no boot progress event ever replaced it.
- **2%** is `Math.max(2, boot.progress)` (`onboarding/index.tsx:379`) over a
  parked progress of **0**: `suspendDesktopBootForChoice()` (`store/boot.ts:71-84`)
  sets `progress: 0, running: false, phase: 'renderer.first-run'` and keeps
  `...current` (hence the initial message).

So the renderer is showing the **parked** boot state left behind by the
first-run gate. Once the real boot wiring starts it immediately posts
`renderer.boot` at **6%** (`use-gateway-boot.ts:477-481`); a display frozen at
2% means that wiring never ran.

## Root cause

The fork's renderer-side first-run gate in `useGatewayBoot`
(`apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts:933-966`) runs once
(`useEffect(…, [])`):

```ts
const fr = await desktop.firstRunChoice.get()
if (fr?.required) { enterFirstRunChoice(); return }   // parks boot, opens chooser, NO wiring
teardown = initGatewayBoot()                            // gateway + boot-progress wiring
```

`enterFirstRunChoice()` (`:165-169`) deliberately does **not** call
`initGatewayBoot()` — so nothing subscribes to boot progress, nothing listens
for `hermes:connection:applied`, and no `getConnection()` is issued. Everything
that follows depends on *something* re-driving that effect after the choice.

The two branches of the chooser (`src/components/connection-mode-dialog.tsx`)
handle that differently:

| Choice | Code path | Re-drives boot? |
|---|---|---|
| **Local** — `applyLocalMode()` `:159-166` | `firstRunChoice.complete('local')` → `window.location.reload()` | **Yes** — reload re-runs the effect; the gate now says `required=false`, `initGatewayBoot()` runs |
| **Client Mode → Connect** — `connect()` `:174-186` | `save(true)` → `applyConnectionConfig` (main) → `firstRunChoice.complete('remote')` → `closeConnectionModeDialog()` | **No** — nothing reloads, nothing re-runs the effect |

Main's side does its part correctly and is *not* the problem:
`hermes:connection-config:apply` (`electron/main.ts:13279-13309`) writes the
config and calls `rehomePrimaryConnection` (`electron/primary-connection-rehome.ts`)
→ `sendConnectionApplied()` (`main.ts:9816`) → `hermes:connection:applied`. But
the only renderer listener for that event is registered *inside*
`initGatewayBoot()` (`use-gateway-boot.ts:568`), which never ran — the event is
sent to nobody. `hermes:first-run:complete` (`main.ts:12717`) records the choice
and resets the cached gate (`writeFirstRunChoice`, `main.ts:8362-8373`, whose
own comment says "The window reloads in the SAME process after a choice") — but
nothing reloads.

Result: chooser closes → `isFirstRunChoiceActive()` is false → the onboarding
overlay stops standing down (`onboarding/index.tsx:271-273`) and renders
`Preparing` over the parked boot store, forever. On relaunch `first-run.json`
exists and `connection.json` is remote, so the gate returns `required=false`
(`main.ts:8422-8441`, `hasExplicitRemoteTarget()` `:8379`), `initGatewayBoot()`
runs, and the saved OAuth/native token or session token connects — which is
exactly the "restart fixes it, no re-auth" behaviour observed.

### Why it used to work, and when it broke

- Fork commit `672f00971` (2026-07-01, "implement first-run choice") relied on
  the *apply* handler reloading the window — its `connect()` comment read
  "remember the remote pick BEFORE apply (apply reloads the window)", and at that
  time `hermes:connection-config:apply` did `mainWindow?.reload()`.
- Fork commit `ae6670551` (2026-07-01, TLS bypass) reordered `connect()` to
  record the choice *after* a successful apply (so a failed remote never
  suppresses the chooser) — still no renderer reload, still relying on main.
- Upstream `f003d888e` (2026-07-15, "integrate SSH with soft gateway switching")
  changed apply from a window reload to a **soft re-home** that only *notifies*
  the renderer (`sendConnectionApplied`). The fork picked that up in the
  `v2026.7.20` sync (fork `v0.19.0`) — and the fork's Client-Mode first-run
  path silently lost its only re-drive. Every fork release since has this.
- No test covers "after the first-run **remote** apply, the gateway boots":
  `connection-mode-dialog.test.tsx:381-405` asserts only that the choice is
  recorded and apply is called; `use-gateway-boot.test.tsx:455-480` asserts only
  that the gate defers. The local path *is* asserted to reload (`:363-376`).

## Reproduction (operator)

1. Quit Hermes Desktop; move `~/Library/Application Support/Hermes` aside
   (or delete only `first-run.json` + `connection.json` — that is enough to
   re-arm the gate; appearance prefs live in renderer localStorage and are
   untouched).
2. Launch → first-run chooser → **Client Mode** → gateway URL → sign in (or paste
   a session token) → **Connect**.
3. Observe the onboarding card stuck at "Starting Hermes Desktop… 2%".
4. Confirm the diagnosis from the main-process log (Help → logs / `rememberLog`
   ring): `[boot] first-run choice decision: required=true (choiceRecorded=false, …)`
   at launch, later `hermes:connection:applied` sent, and **no**
   `renderer.boot` / gateway-connect lines afterwards.
5. Quit and relaunch → connects with no sign-in prompt.

Workaround until fixed: quit and relaunch after the first Connect (or a plain
window reload — the error-boundary "Reload window" button, or `Cmd/Ctrl+R` if
enabled in that build — would do the same without quitting).

## Fix options (not implemented — for the next desktop change set)

**A. Restore the reload in the Client-Mode branch (minimal, symmetric with Local).**
In `connection-mode-dialog.tsx` `connect()`, after
`firstRunChoice.complete('remote')` resolves on the first-run path, call
`window.location.reload()` (skip the `closeConnectionModeDialog()` — the reload
resets the store). Reuse the existing `reloadSpy` in the dialog test to assert
one reload after `firstRunComplete('remote')`. Cost: one visible reload flash on
first run only — the same the Local path already has. This is what the original
fork design assumed.

**B. Make the boot hook re-drive itself (no flash, more code).** In
`useGatewayBoot`, after `enterFirstRunChoice()`, subscribe to
`$connectionModeDialog` and, when the first-run chooser closes *and*
`desktop.firstRunChoice.get()` now reports `required=false`, run
`initGatewayBoot()` (a cold boot: `getConnection()` etc.). Note the ordering
trap: `hermes:connection:applied` is emitted by `save(true)` **before**
`complete('remote')` runs, so B must not depend on catching that event — the
cold-boot path already doesn't. Needs a hook test: gate → chooser closes with a
recorded remote choice → wiring starts (asserts the `renderer.boot`/6% step).

**C. Reload from main on `first-run:complete` when the choice is `remote`**
(`main.ts:12717`), mirroring what the pre-July apply handler did. Centralised,
but splits responsibility for the two branches across processes (renderer
reloads for local, main for remote); if chosen, move the local reload there
too and drop it from the dialog.

Recommendation: **A** now (one line + one assertion, restores the documented
contract in `store/boot.ts:66-70` and `main.ts:8366-8369`), B if the flash is
judged unacceptable later. Whichever lands, add the missing end-to-end
assertion so the next upstream sync cannot silently drop it again, and add the
`connect()`/`initGatewayBoot` pairing to
`docs/maintainers/upstream-sync/patch-inventory.md` (desktop first-run section).

## Not the cause (checked)

- Not authentication: the token/OAuth session is saved and works on relaunch;
  the `remoteFailure`/re-auth overlay never appears (no boot ever ran to fail).
- Not upstream's main-side `firstRunSetupGate` (`main.ts:1762-1826`,
  `abandonForRemoteApply`): that gate only has a waiter while a *local*
  backend start is parked; on the fork's deferred first run `startHermes()` is
  never entered (`main.ts:10545-10556` sentinel), so `hasWaiter()` is false and
  the apply falls through to the soft re-home as designed.
- Not the connecting splash / z-order fix (`onboarding/index.tsx:265-273`) —
  that correctly stands down while the chooser is open and correctly resumes
  after; it is showing the truth (boot never started).

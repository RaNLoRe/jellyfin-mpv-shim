# Final personal-fork audit — 2026-09-09

Scope: the complete personal diff against upstream `fa990688`, including
the two original fixes, the queue bridge, playlist card behavior and portable
mpv integration. No deployment or remote push is part of this audit.

Portable config is committed on `RaNLoRe/mpv-conf` branch `main` at
`50b84aff80899693d355290b511d21096b370dfb`. It changes exactly two files:
`scripts/playlistmanager.lua` and `script-modules/jellyfin_queue_adapter.lua`.
The original `scripts/jellyfin.lua` is byte-for-byte equal to its previous
commit. No history, credentials, input bindings or other configuration was
added to the commit. The bundled adapter matches exactly, and applying the
bundled patch to the original script reproduces the installed portable script.

The audit found one shared-test-model gap: FakeMPV lacked `seeking`, which
the stable intro snapshot reads. Both fake backends now model its idle value;
the intro regression tests exercise the transitions explicitly. No additional
production behavior changes were needed.

Verification uses uv and the preserved Python 3.13 build environment:

- Focused regression suite: 468 tests run, 465 passed and 3 skipped. It covers
  compatibility, binding ownership, trickplay, queue edits/reporting, playlist
  cards, hardware decoding and static audits.
- Fake integration matrix: all four legs passed, 353 tests run with 4 skipped.
  It covers both libmpv and JSON IPC, including lifecycle, keyboard controls
  and playback start. Real-media legs are excluded here.
- Lua queue adapter assertions and all 48 thumbfast assertions passed.
- Isolated real mpv loaded the complete portable playlistmanager; selection,
  sorting, reversal and shuffle checks passed without native queue mutation
  or Lua errors. This test uses synthetic entries, with no server login.
- Translation template parses successfully. GNU xgettext is unavailable on
  this device, so full template regeneration was not performed; the three new
  translated labels were added explicitly. No locale files changed.
- Source whitespace checks pass excluding the bundled unified diff, whose
  blank context lines necessarily contain a space; its application is verified.

Earlier upstream font checks retain one failure and two errors involving
Arial spacing and Mongolian font rendering. They are recorded in
[upgrade verification](fork-v3-upgrade.md); this is not a fully green upstream
suite. The final Windows executable/installer has **not** been rebuilt yet:
the existing installer predates the queue and card features and must not be
used as their release artifact.

The user confirmed intro prompt/Right-arrow behavior, fullscreen mouse
responsiveness, next/previous after queue reordering, accepted queue bulk
operations and the playlist card/overlay gestures. Keep Add to play queue and
Play next unchanged. Remaining operator checks are queue insertion during
playback, removing a non-playing entry, optional SyncPlay, and normal production
tray exit/relaunch after installation. Final context-menu labels load on the
next diagnostic/app restart.

Known limits: title lookup failures retain generic queue labels for that
authenticated client; sorting uses displayed titles rather than Jellyfin's
server SortName. The history-writing launch remains unidentified. Jellyfin
12 session queue reporting remains a server issue with evidence and a proposed
fix in [the investigation](fork-jellyfin12-queue.md); no fake stops are sent.

## Publication and deployment plan

Remote references were fetched during the audit. `origin/feat-fix-bindings`
is an ancestor of the reviewed personal branch. Portable `origin/main` is
an ancestor of its new commit. Fork `origin/master` can fast-forward to local
`master`, which is the upstream reference. No force push or branch deletion is
needed. Recheck these relationships immediately before publishing.

After the user approves the push plan, publish the personal branch, clean
upstream master and the two existing rollback tags to the fork; publish the
portable main commit to mpv-conf. Then build the exact committed fork revision
using the safe separate PyInstaller work directory, validate the wheel, x64
bundle and installer, and record hashes. Do not run the destructive
`build-win.bat` over the diagnostic profile.

Before installation, coordinate stopping playback, privately back up the
production shim profile and application, and retain the prior portable commit
`0be80e0`. Install the validated build using the production identity, never
the diagnostic identity. Smoke-test startup, playback, Ctrl+L, intro skip and
exit/relaunch. Rollback restores the previous app/profile and reverts the
portable adapter commit together; preserve unrelated later edits. Detailed
instructions are in [the upgrade notes](fork-v3-upgrade.md).

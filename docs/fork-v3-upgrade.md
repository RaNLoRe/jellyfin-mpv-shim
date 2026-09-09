# RaNLoRe fork: v3 upgrade

Prepared 2026-09-09 in an isolated worktree, initially based on upstream
`v3.0.0` (`9970b2dc4a91f0c96a9fa5a1fcecf6a69331e315`), then updated at the
user's request to `upstream/master` at
`fa9906882aab4dc76464933926fbba4c15d02271` (53 post-release commits).
The final daily-use branch is `feat-fix-bindings`. The former tip
`bbd4df7062771f224a79ec37a1079bd358820edb` is preserved as
`rollback/pre-v3-bbd4df70`. An ancestry-only merge retains the old fork history
with the verified v3 tree unchanged, allowing a later non-forced push. The
temporary upgrade branch is removed. At the user's request, local `master`
tracks `upstream/master` and was fast-forwarded to `fa990688` on 2026-09-09.
It is the clean upstream reference, not another personal variant. The personal
branch includes that same upstream tip plus the compatibility changes below.
Upstream was merged rather than rebased to preserve the old fork ancestry and
avoid a force push. `rollback/v3-tested-2026-09-09` preserves the earlier
verified release-based build. Playback compatibility files are byte-for-byte
unchanged by the post-release merge.
No installed app was replaced and nothing was pushed. This is a selective
port, not a replay of the old patches.

## Custom commit comparison

| Original change | v3 disposition |
| --- | --- |
| `124ee049`: Windows IPC readiness using WaitNamedPipe | Covered by v3's required python-mpv-jsonipc >=1.4.0 (tested with 1.4.0). `_ipc_endpoint_ready` uses WaitNamedPipeW, with startup polling, pipe attach retries and failed-process cleanup. The old MPVProcess class replacement is omitted. |
| External `force_window(False)` must not call `play("")` | Retained in `player_window.py`; external mpv must not interpret the working directory as media. The embedded backend keeps its existing behavior. |
| Custom thumbfast/OSC overlay coordination | Retained only the `osc-thumb-is-shown` and `osc-thumb-overlay-id` notifications required by the user's portable OSC. v3's windowed frame loading, bounds checks, deduplication and preview API remain. |
| Old up/down volume bindings and seek command overrides | v3 discovers and claims keys around the user's input.conf. The diagnostic process confirmed the user's volume and seek bindings were loaded. No wholesale replay of the old controls/OSC. |
| Old dependency/lock and Python 3.14 changes | Use v3's Python 3.13 baseline and current dependency declarations. Build/test commands use uv in an isolated environment. The old lock is not transplanted. |
| `bbd4df70`: configurable seek-to-skip | v3 already has `skip_intro_on_seek`. Migrate the old `seek_to_skip_intro` value; an explicit v3 value wins, and saving removes the old alias. |
| Stable pre-seek position and original prompted segment | Retained. IPC can expose the destination before the seeking-start event. Snapshot the segment during normal playback, retain it through seeking, and reject a snapshot belonging to another video. |
| Prompt remains visible with seek-to-skip disabled | Restored after live testing exposed this missed port: custom/classic OSC shows the neutral “Skip Intro” notification when the gesture is disabled, and “Seek to Skip Intro” when enabled. SyncPlay uses the neutral label because the gesture is exempt. This is a text notification, not a new custom-OSC button. |
| Dedicated Right-arrow intro skip | Restored separately from the general seek gesture. The old fork's menu-right binding skipped the active intro even with seek-to-skip OFF. For classic/custom playback the fork claims that key only when it resolves to a forward seek, leaves modified seeks and non-seek custom bindings alone, and retains menu navigation. |
| OSD appearance restored after menu use | Retained: sample the current OSD appearance each time the menu opens, rather than restoring a constructor-time snapshot. |

Intentional behavior: a forward seek over 0.5 seconds from inside an enabled
segment skips to its end only if the destination is still inside that same
segment. A jump past it is respected; it neither jumps backwards nor skips a
different segment. Backwards seeks and entering a segment from outside do not
trigger a skip. SyncPlay and seeks through the shim UI remain exempt. v3's
segment policies and explicit skip control remain available. The user's old
preference was **false**. It was temporarily enabled for a diagnostic retest;
the user clarified the intended behavior: **Right skips the active intro;
Shift+Right (+3 seconds), Ctrl+Shift+Right (+1 second), and backwards seeks
remain ordinary seeks**, with the neutral “Skip Intro” notification. Right
outside a segment uses the configured forward distance (+10 seconds here).
The final setting is `skip_intro_on_seek=false`: it disables the general
any-forward-seek gesture, not the dedicated Right shortcut. The latter respects
disabled segment policies and defers to normal SyncPlay seeking in a group;
the mpvtk HUD retains upstream behavior. The production profile is untouched.
Custom mpv input.conf controls its own seek OSD; no global `osd-auto` override
is added to v3's internal seek path.

## Verification

Offline results, with uv and Python 3.13.12 on Windows x64:

- Both fake-backend integration matrices passed (`jsonipc` and `libmpv`):
  concurrency, restart, playback start/state, keyboard and lifecycle legs.
- Earlier focused suites: 458 tests with 5 skips, and 214 with 2 skips.
  These overlap; their counts must not be added as unique coverage.
- Final focused suite after the prompt/hwdec/arrow corrections: 327 tests with 3 skips, including all 17 new fork
  regressions, playstate payloads, custom key claims, classic OSC mouse handoff,
  trickplay, remote playback, Play All, playlist editing, session reporting,
  and test import-path checks.
- An additional 77 shader/profile checks passed for the hwdec ownership change.
- Lua thumbfast suite: 48 assertions passed, including repeated notification,
  clear and re-render cycles. The early-destination regression fails against
  the unmodified v3 seeking handler, confirming that test detects the old bug.
- Real external mpv, without a server/window: three startup/load/seek/pause/
  resume/stop/shutdown cycles passed and each child exited. Used the user's
  Scoop mpv executable, `v0.41.0-1042-g7e4cb538a`.
- Wheel/sdist, x64 PyInstaller bundle and Inno Setup installer built. Bundled
  translations, shaders and Lua resources checked; architecture, DLL imports
  and bundled FriBiDi/Raqm checks passed. Frozen `run.exe --version` returned
  `3.0.0`. These artifacts are test builds, not an installed upgrade.

The complete repository test suite, real embedded-libmpv playback, ARM64 and
legacy-x64 packaging have not been run. Fake integration tests do not establish
real Web casting or display performance. Local verification logs and artifacts
are under `build/verification/`; they are intentionally not committed.

### Post-release upstream verification

The merge was conflict-free. Both fake-backend integration matrices, the
focused playback/compatibility suite, translations and Windows packaging were
rerun on the combined branch. The native-arrow integration assertion now
explicitly exercises the upstream HUD policy; classic/custom Right-arrow
behavior is covered by the fork regressions. The new font suite is **not fully passing** on
this host: 170 tests ran, with 9 skips, 1 failure and 2 errors (158 passed).
The failure compares an emoji-adjacent Latin gap with an isolated space;
Arial/Raqm measures the contextual gap as 4.453125px and the isolated space
as 5.5625px, and the actual mixed-text gap correctly matches the contextual
measurement. Both errors arise when Pillow tries to rasterize this host's
`monbaiti.ttf` and raises `OSError: invalid reference`. Mongolian rendering
compatibility remains unresolved; these upstream tests were not changed or
silently skipped to obtain a green result.

The upstream text sample sheet rendered successfully and was visually checked
for Latin, Thai, CJK and emoji. Missing glyphs remain in several other script
rows; broad language/font coverage is not claimed. The previous tested installer
was retained as `build/verification/jellyfin-mpv-shim-v3-tested-before-upstream.exe`
in the build worktree, with its original SHA256 verified before copying.

## Diagnostic setup and remaining operator tests

The separate `Shim v3 diagnostic` profile uses a distinct device UUID and IPC
pipe. Login was performed locally. It retains v3's library browser with
`enable_gui=true`, `headless=false`, `osc_style="custom"`, `mpv_ext=true`,
`mpv_ext_no_ovr=true` and the user's Scoop mpv path. This loads the user's
existing portable mpv.conf, input.conf and scripts. The diagnostic IPC name
starts with `mpv-jellyfin`, as required by the user's detection script.
No portable configuration files were changed.

The initial playback was **Resume from a playlist inside the shim library**
and supplied one queue entry. A later, user-confirmed Play from **Jellyfin Web**
supplied all 11 playlist entries, but in the server's SortName order rather
than saved playlist order, beginning at saved position 7. A coordinated
repeat confirmed the incoming PlayNow command already has that order and the shim preserves it exactly. See the server investigation;
saved playlist ordering through Web has not passed, and the defect is upstream
of the shim's command handling.

The user's usual workflow was then verified separately: **right-click an
episode inside the Web playlist → Play all from here**. Its incoming command
contained all 11 entries in saved order and StartIndex=1 (the second entry).
The shim started that exact entry and retained the complete ordered queue.
This workflow passes; it differs from the playlist header's Play action above.

Coordinate these tests before replacing the installed app:

1. Web playlist Play captured: all 11 IDs arrive in SortName order, and the shim
   preserves that order. To isolate Web versus server expansion fully, capture
   the Web outbound request. Verify saved playlist order after an upstream fix;
   receiving all 11 entries alone is insufficient. The user's context-menu
   Play all from here workflow passes with the correct order and start index.
2. Next/Previous and pause/resume completed from Web: reports show received
   queue positions 1 → 2 → 1 and pause/resume/pause, retaining all 11 entries.
   Both HTTP and WebSocket then exposed the full queue after the genuine stop
   reports at episode transitions. Adding items with Play Next/Play Last is
   still pending; confirm placement and queue persistence across a transition.
3. Test custom arrow/volume/mouse bindings during playback and menu navigation;
   confirm the library releases its mouse/key bindings when video starts.
4. The user confirmed trickplay previews and seeking work with the custom OSC.
   Exhaustive distant-window, hide/show and episode-transition preview checks
   remain operator coverage beyond that confirmation.
5. Temporarily enable `skip_intro_on_seek` in the diagnostic profile. Test a
   small forward seek inside an intro, a backwards seek, a jump beyond it,
   entry from outside, the explicit skip control, and disabled segment policy.
   The tested episode has an intro from 36.7804082 to 124.9999754 seconds.
   Final user preference is **false**: retain the neutral notification and
   small modified seeks (+1/+3 seconds) and backward seeks. The dedicated
   Right shortcut still skips the active segment. Enabling the general gesture
   was only a test and intentionally changes the label and modified-seek behavior.
   After restoring the separate Right-arrow handler, the user confirmed that
   intro skipping works as expected with the general gesture disabled.
6. Fullscreen mouse responsiveness passed after restoring the external mpv
   config's hwdec setting, as detailed below. Normal window/tray exit and
   relaunch remain operator checks; automated external-process lifecycle
   checks passed.

Hardware-decoding follow-up: the user reported standalone mpv behaved properly
with hwdec enabled. The diagnostic IPC read showed `hwdec=no` and
`hwdec-current=no` despite the portable config's bare `hwdec` option. v3 read
only the shim's mpv.conf for an explicit pin, then imposed its software default
at startup/per-file even with `mpv_ext_no_ovr=true`. The fork now leaves hwdec
to external mpv's config in that mode, including shader-profile handling;
the explicit `--disable-hwdec` recovery option still wins. Other backend/config
modes retain upstream policy. The next playback confirmed
`hwdec-current=d3d11va` and `hwdec-interop=d3d11va`; the user confirmed the
fullscreen mouse issue fixed.

Ctrl+L now has a fork queue bridge plus an adapter for the user's portable
playlistmanager. See [adapter setup and verification](../contrib/mpv/README.md).
The portable changes are applied locally; queue navigation after reordering
and the bulk operations have user confirmation. See the final audit for
remaining operator checks.
The previously built installer predates this feature and must be rebuilt
before installing the queue-enabled version.

## Jellyfin 12 session queue evidence

See [the server investigation](fork-jellyfin12-queue.md). v3 still sends
`NowPlayingQueue` and `PlaylistItemId` in start/progress payloads. The measured
one-entry diagnostic session reproduced stale server session queues despite
those reports. No fabricated stop, queue-owning manager or client refresh
workaround is included.

## Upgrade and rollback

Before installation, finish the live checks above and explicitly authorize
deployment. Keep the existing installer/application directory. With both apps
closed, back up `%APPDATA%\jellyfin-mpv-shim` and the Scoop mpv
`portable_config` directory privately: the profile contains credentials.
Record the old mpv executable/version too; Scoop's `current` target can change.

The generated x64 installer remains in the preserved build worktree at
`.worktrees/v3-selective-fixes/build/verification/jellyfin-mpv-shim-v3-selective-test-installer.exe`;
the uninstalled bundle is `.worktrees/v3-selective-fixes/dist/run/`.
Keep its paired `_internal` directory. The build worktree is detached at the
verified revision; it is not a second ongoing branch.
Do not run `build-win.bat` over the live diagnostic profile: it deletes `build`.
The verification build used its PyInstaller arguments with a separate work path.

When an install is authorized, stop the old shim, install the reviewed build,
and use the existing production profile/device identity. Do not copy the
diagnostic identity or credentials over it. Apply the custom-OSC/external-mpv
settings above to preserve the desired library-plus-custom-player experience.
v3 can migrate configuration, so retain the pre-upgrade backup unchanged.

For rollback: stop v3, restore the saved old application and pre-v3 shim
profile, and restore the mpv configuration/version if it was subsequently
changed. Start only one production shim. Source rollback is simply the
rollback tag `rollback/pre-v3-bbd4df70`. Use a separate detached checkout of
that tag for an old-source build; do not reset or force-push the daily-use
branch. Pushing `feat-fix-bindings` requires authorization.

## Playlist card behavior

The playlist card now opens details, while its overlay play button starts
the full playlist at that entry with resume preserved. See the
[playback action audit](fork-playback-actions.md) for other surfaces and tests.

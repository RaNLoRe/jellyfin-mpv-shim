# v3.1 upgrade assessment — 2026-10-06

## Implementation follow-up

The assessment below was followed by an authorized **rebase onto latest
upstream master**, not a merge or a rebase onto the release tag alone.
Local `master` now equals upstream `46af845a91154e197ba3bd3d3eb182c06da2d0c5`.
That is 15 commits beyond v3.1.0, including IME input, fractional artwork crop
fixes and translations. The six personal commits were replayed onto that base.
Rollback tag `rollback/pre-v3.1-rebase-2026-10-06` preserves `f4cf0084`.

All custom behavior listed below is retained. Seeking combines the upstream
landed-position recording with the fork's original-segment snapshot, using the
same guarded read. Thumbnails combine upstream scale handling with the OSC
notifications. Payload fixtures combine the loading and lifecycle fields.
Fork fake-player tests now register upstream's refused-property-write cleanup.
New regressions cover landed-position recording with intro gestures disabled,
seek completion on a dead handle, and scaled preview visibility notifications.

Verification on Python 3.13.12, python-mpv 1.0.8, python-mpv-jsonipc 1.4.0,
jellyfin-apiclient-python 1.20.0 and Pillow 12.3.0:

- Focused sweep: 1,190 JSON IPC tests and 1,249 libmpv-model tests, no failures,
  seven skips per backend. These overlap and must not be summed as unique tests.
- All four `run_integration.py --no-real` legs passed. The summary reports
  82 / 14 / 235 / 235 executed outcomes, with 4 / 1 / 1 / 1 skips respectively.
- Six DLL-dependent checks initially skipped because the test process lacked
  the DLL search path. A focused rerun with the repository DLL available passed
  all 67 key-sweep, third-party-OSC and property-guard tests with no skips.
  A real no-window libmpv startup reported `v0.39.0-1025-g6c4218252`.
- Lua 5.1 via Lupa: 85 thumbnail assertions passed in each of modern-overlay
  and old-mpv fallback modes; queue adapter assertions passed.
- Real external mpv: eight unsigned-in browser close/reopen cycles, including
  four idle terminations, had exactly one live player at every check. A parent
  process check confirmed zero surviving test players after a successful Quit.
- Real external-mpv stats: three cycles passed for timed expiry, mixed keys,
  persistent toggling and cleanup on returning to the library.

Logs and the isolated verification environment are in `build/v3.1-verify/`.
The first lifecycle probe could not write the sandbox-external font cache; it
was rerun with a workspace-local cache and no such errors. No production
profile, portable configuration or installed app was changed. No push occurred.
The full unit suite, real-media integration matrix, live-server casting,
offline migration with the user's data and a new installer build were not run.

## Original source assessment (before the rebase)

Recommendation: upgrade the personal fork to v3.1.0 after integrating and
testing the changes below. A stock upstream installer would lose the fork's
custom behavior. This is a source assessment, not a tested upgrade or deployment.

## Evidence and scope

- Current branch: `feat-fix-bindings`, `f4cf008449570a5921d8fa7baf08bc86c189950d`.
- Release: `v3.1.0`, `7e9fd292459358dde12f054c24f79642ab5ec98f`, published October 5.
- Common ancestor: `9db70b24315badfc1cc8d8b9c1e506a95d339c05`.
- Six fork commits; 36 changed files against that ancestor, including documentation/tests.
- Upstream has 230 commits after that ancestor; 281 changed files, including
  translations, tests and documentation. This is substantially more than a version bump.
- Inspected every fork production-code change and its upstream counterpart,
  the portable adapter, release notes, configuration/dependency changes, and
  the relevant queue, reporting, lifecycle and browser interfaces.
- `git merge-tree --write-tree HEAD v3.1.0` simulated the merge without changing
  the index, working tree or branch. It reported three conflicting files.
  Its nonzero exit status means conflicts, not a successful merge.
- No application tests, live-server checks, installation or configuration
  migration were run in this assessment. Earlier test counts in the fork docs
  apply to the old tree, not a prospective v3.1 build.

[Release notes](https://github.com/jellyfin/jellyfin-mpv-shim/releases/tag/v3.1.0).
The tag was fetched locally for the code comparison; `upstream/master` was not
advanced, and no merge, commit or push was performed.

## Why upgrade

The most relevant additions beyond this fork's existing upstream baseline are:

- Resume uses an explicit mpv command, avoiding a refused property write
  becoming a stale Python attribute. A new `mpv_guard` also guards property
  writes across both backends.
- HDR colorspace parking/restoration is serialized to prevent a second park
  saving the already-disabled value.
- Video stays paused while its loading work and resume positioning finish.
- External IPC closure is handled even when mpv's shutdown event is lost.
  A second app launch during a film raises the player instead of briefly
  switching into the library.
- Interrupted streams can return to the library with an error and preserved
  resume position instead of being treated as successful completion.
- Offline progress, watched marks, multiple accounts/servers, playlist
  identity and download relocation receive extensive changes. SyncPlay can
  replace a stale downloaded copy with the server's current source.
- Server recovery/discovery, library sort persistence, metadata refresh,
  missing-episode handling, season actions, artwork and HiDPI previews improve.

Some advertised v3-to-v3.1 features are already in this fork: the interface
language picker/system-language work and SteamOS gamepad migration, for
example. They are not additional reasons to upgrade from this exact checkout.

## Complete custom-feature disposition

“Clean” below means Git merged the text automatically, not that runtime
compatibility has been proven.

| Custom behavior | v3.1 comparison | Disposition |
| --- | --- | --- |
| Migrate `seek_to_skip_intro` to `skip_intro_on_seek`, with the explicit new value winning | Upstream still lacks this fork alias migration; `conf.py` merges cleanly | Keep for old fork profiles. Already-migrated profiles no longer need it, but v3.1 has not replaced it. |
| Stable pre-seek intro snapshot; skip only within the original segment; respect backward seeks and jumps past it | Upstream still uses the old intro-seek logic, but adds immediate landed-position recording in the same method | Manual merge: preserve the snapshot behavior AND the new playback-position update/alive guard. |
| Dedicated Right-arrow intro skip with general seek-to-skip off; modified seeks stay ordinary | Upstream does not add this behavior | Keep. Preserve custom binding ownership, segment policy and SyncPlay exemptions. |
| Neutral “Skip Intro” prompt when the general gesture is off, including SyncPlay | Upstream still gates the classic/custom prompt on `skip_intro_on_seek` | Keep. Do not reinstate upstream's prompt suppression. |
| Preserve portable external-mpv hardware decoding at startup, per file and during shader changes | Upstream adds unrelated Flatpak plugin and server-scoped shader lookup changes; it does not add the portable hwdec exception | Keep both `mpv_options.py` and `video_profile.py` changes. Retain `--disable-hwdec` precedence. Both merge cleanly. |
| Avoid `play("")` when hiding idle external mpv | Upstream's `force_window` behavior is unchanged here | Keep; its IPC-close fix does not replace this. Clean merge. |
| Restore the OSD appearance sampled each time the menu opens | Upstream leaves `menu.py` unchanged | Keep. The new property guard handles refused writes, not when the OSD appearance is sampled. |
| Notify the portable OSC of thumbnail visibility and overlay ID | Upstream introduces DPI scaling and an OSC-owned rendering response path, but not these notifications | Manual merge in `thumbfast.lua`; retain notifications with upstream scaling, frame-window bounds and deduplication. |
| Ctrl+L playlistmanager bridge: entry-aware select/remove/move/sort/reverse/shuffle | No upstream `queue_bridge.py` or equivalent portable protocol. Existing queue-operation interfaces remain available | Keep bridge, dispatch hook, Lua adapter and playlistmanager patch. Group edits must remain disabled during SyncPlay. |
| Playlist cards open details; overlay Play starts the current occurrence in the full playlist with resume | Upstream still uses the older card-click behavior. Its changes add server scope and missing-episode/metadata actions | Keep all three browser-file changes; they merge cleanly. Retest online/offline playlists and missing entries. |
| Duplicate playlist occurrences survive filtering; use current route data at activation | Upstream still relocates selection by media ID in `play_list`, which selects the first duplicate | Keep positional filtering and entry identity handling. |
| Explicit “episode (series order)” context-menu labels | Upstream does not supply these labels | Keep labels and the three POT entries alongside new upstream translations. |
| Lowercase `i` shows temporary stats; Shift+i toggles persistent stats; clear correctly on return to library | Upstream `_stats_key` still routes video stats to `toggle_stats` | Keep `show_stats`, timer-aware persistent-state handling and tests. |
| Serialize mpv recreation, reuse an existing live handle, suppress startup reporting/reopening during shutdown, reset idle suppression after teardown | Upstream `_init_mpv` still lacks the fork's lock/alive/shutdown guard | Keep the complete lifecycle fix. Upstream's IPC-close notification and second-launch behavior are complementary, not replacements. |

No current custom behavior is fully superseded by v3.1. The documentation-only
fork commit contains no feature to port, but its history and limitations remain useful.

Older patches that were already retired during the v3 upgrade should stay
retired: the Windows named-pipe monkeypatch is covered by the required
`python-mpv-jsonipc>=1.4.0`; wholesale legacy seek/volume binding overrides are
replaced by upstream key discovery/claims; the old Python/dependency lock
should not be transplanted. These are not newly superseded by v3.1.

## Exact conflicts and integration risks

1. **`jellyfin_mpv_shim/player.py`: `_on_seeking`.** Keep upstream's immediate
   `_last_playback_position` update on seek completion and combine it with the
   fork's captured `(video, intro, start)` logic. Selecting either entire side
   loses a real fix. Use the guarded playback-time read for the combined path;
   upstream explicitly warns that reading a terminated libmpv handle can crash.
2. **`jellyfin_mpv_shim/thumbfast.lua`: two conflict regions.** The announcement
   needs both `drawn_size()` and `osc-thumb-overlay-id`. The draw condition needs
   upstream's scale-change detection and the fork's `set_img_shown(true)`.
   Preserve new `render_to` handling and clear/miss notifications. OSC-owned
   overlays should not be confused with the shim-owned overlay's visibility.
3. **`tests/test_playstate_payload.py`: ten fixture conflicts.** Combine the
   fork's `_ready_player()` initialization (`_mpv_alive`, `_shutting_down`) with
   upstream's `_start_in_progress=False`. Check new upstream fixtures too:
   `player_reporting.py` merges cleanly but its fork guard reads those lifecycle
   fields directly. Choosing a whole test-file side would discard coverage.

Clean merges still need behavioral checks:

- `mpv_guard` changes backend construction. Exercise OSD restoration, shader
  options, external-mpv properties, shutdown callbacks and the lifecycle fake
  models with the guarded handles.
- New loading/reporting logic must retain both the startup/shutdown suppression
  and upstream's “no playstate until start finishes” rule.
- The queue bridge's core operations are unchanged upstream, but test them
  through transitions, interrupted playback and SyncPlay source replacement.
- Playlist overrides must retain upstream's server-scoped offline identifiers,
  no-play affordances for missing episodes and metadata refresh.
- The test runners now support per-platform outcome manifests. A release check
  must account for fork tests and justified skips instead of reusing old totals.

## Settings, dependencies and rollback

- Required `jellyfin-apiclient-python` increases from `>=1.18.0` to `>=1.19.0`
  for server discovery. Python remains `>=3.9`; the two mpv-binding minimums
  remain unchanged. Rebuild the application with the updated dependency.
- `thumbnail_scale=None` follows display scaling. This changes preview size on
  HiDPI displays; `1.0` is the available fixed-size preference if wanted.
- `kb_nav_back` is a new, initially unbound navigation action that avoids the
  Escape fullscreen fallback. It does not replace the fork's playback Right key.
- Browser fullscreen now implies fullscreen video playback; the two preferences
  and Escape behavior need checking against the existing personal workflow.
- Auto-download eligibility moves from `conf.json`'s legacy
  `auto_download_servers` list into account-scoped profile data in `users.json`.
  A new watched-download retention setting defaults to 24 hours, subject to
  storage-budget eviction.
- The offline catalog has schema/data migrations for account/server scope.
  Before deployment, retain a consistent closed-app backup of profile data and
  the offline catalog alongside the old app and portable mpv configuration.
  Do not assume restoring only the old executable rolls back migrated data.

The old Jellyfin 12 session-queue and Web playlist ordering findings are NOT
proven fixed by this client release. Its remote Play changes validate empty or
invalid queues and enable slideshows; they do not reorder a Web-supplied queue
or repair server-side session state. Recheck the current server separately;
do not reintroduce fabricated stop reports. See `fork-jellyfin12-queue.md`.

## Verification required on the combined build

1. Run the fork compatibility, stats, playlist-card, queue bridge, lifecycle,
   playback/reporting, hwdec, key ownership and thumbnail tests, plus the new
   upstream property-guard, resume, interrupted-stream and IPC-close tests.
   Run both fake backend integration matrices; adapt fixtures rather than
   deleting new upstream assertions.
2. Run both Lua suites with the combined thumbnail implementation, including
   DPI changes, hide/show, window misses and the portable queue adapter.
3. In an isolated profile with the user's portable mpv configuration, check
   Right vs modified seeks, neutral intro prompt, temporary/persistent stats,
   hwdec during shader/episode transitions, OSD restoration and previews.
4. Repeat library/tray reopen and quit cycles: one live player, no orphan,
   correct lost-IPC handling. Check second launch while a film is playing.
5. Verify duplicate playlist entries, Play Next/Last, reorder then Next/Previous,
   resume, Web “Play all from here”, stream failure, HDR stop/start and SyncPlay.
6. If offline features are used, verify migration on a disposable profile/catalog
   copy, account isolation, offline watch/resume updates and reconnect sync.
7. Build a fresh Windows artifact only after these checks. Old v3 installers
   documented elsewhere do not contain the proposed v3.1 integration.

Upstream's checked-in October 4 hand-test record includes a Windows installer
smoke test and real-device checks, but also leaves some checks/open findings
unresolved (including Windows 11 slow-pointer HUD behavior and a subtitle
reproduction). It is useful evidence for upgrading, not proof that this fork's
portable setup has passed. No claim of a regression-free v3.1 is made here.

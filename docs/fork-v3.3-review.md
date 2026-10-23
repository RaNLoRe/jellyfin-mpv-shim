# v3.3 upgrade — 2026-10-23

Base: upstream `535a9688`, containing v3.3.0 (`daca187a`) and two translation
commits. The previous fork tip is retained locally as
`rollback/pre-v3.3-ad79d4f3`. No rollback ref is published.

## Integration

Upstream replaces the former fork reopen implementation; only the final-shutdown
protection remains. See [current fork behavior](fork-features.md) for the retained
features and lifecycle ownership. The queue adapter matched the personal mpv repo
at verification. OSD fixtures now model `is_menu_shown`; MPRIS coverage permits
upstream initial publication and still checks suppression during final shutdown.

## Verification

Logs and diagnostics: ignored `build/v3.3-verify/`.

- JSON IPC focused sweep: 1,323 tests, seven skips, no failures.
- libmpv-model focused sweep: 1,382 tests, seven skips, no failures.
- Four integration matrix legs (`--no-real`) pass; platform/backend and
  second-volume exclusions are listed in `matrix.log`.
- Additional v3.3 features/invariants: 139 tests, two skips, no failures.
- Lua 5.1: 85 thumbnail assertions in each of modern and old-overlay modes;
  queue adapter assertions pass, including older-shim compatibility.
- Real external mpv with an unsigned-in temporary profile: eight close/reopen
  cycles, four idle terminations, one living player after every reopen. All five
  diagnostic player PIDs absent after Quit.
- Real external-mpv stats: three timed-expiry, mixed-key, persistent-toggle and
  library-cleanup cycles pass.

## Installer verification

The `e14c9e81` Windows installer was built and verified, without installation.
Its local manifest is `dist/releases/e14c9e81/manifest.json`:

- All 172 packaged Python modules matched source; Lua resources and 86 compiled
  catalogs matched. Three unsafe translation entries were filtered during packaging.
- Executable version is 3.3.0; x64 architecture and DLL dependency checks passed.
- Packaged certifi 2026.10.23 matched the build environment's CA bundle, satisfying
  the upstream minimum of 2026.10.19. The removed emSign G3 roots were absent.
- libmpv remains upstream's pinned 20261017 archive.

Subsequent history squashing preserved the exact tree; documentation cleanup
changes no runtime source or packaged resources, so this installer remains usable.

These are overlapping focused suites, not unique cumulative coverage. Full
live-server playback/casting/SyncPlay, offline migration on user data, and an
independent eMudhra MITM test are not performed. These checks do not establish a fully passing upstream suite or live-server coverage.
Earlier v3 font checks also had host-specific Arial/Mongolian failures; resolution
was not established by this focused v3.3 run.

Release: https://github.com/jellyfin/jellyfin-mpv-shim/releases/tag/v3.3.0

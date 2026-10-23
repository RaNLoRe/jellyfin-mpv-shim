# Personal fork features

Current baseline: upstream v3.3.0 plus translation commits at `535a9688`.
This describes the maintained differences; earlier upgrade reports are in Git history.

## Playback and portable mpv

- In classic/custom OSC playback, the configured menu-right key (normally Right)
  skips the active intro even with `skip_intro_on_seek=false`. It is claimed only
  when its existing binding is a forward seek. Modified keys keep their normal
  seeks with that setting off; non-seek custom bindings retain ownership. Segment
  policies and SyncPlay exemptions apply. The mpvtk HUD retains upstream behavior.
- Optional seek-to-skip captures the original video, segment and pre-seek position.
  A forward seek over 0.5 seconds skips only when both positions are inside that
  segment. Backward seeks, entry from outside, and jumps beyond it are respected.
  Shim UI seeks and SyncPlay are exempt. The old `seek_to_skip_intro` setting
  migrates to `skip_intro_on_seek`; an explicit new value wins.
- Classic/custom OSC shows a neutral Skip Intro notification when the general
  gesture is disabled or SyncPlay is active.
- With `mpv_ext=true` and `mpv_ext_no_ovr=true`, portable mpv owns hardware decoding,
  including shader-profile changes. Explicit `--disable-hwdec` still wins.
- Hiding idle external mpv avoids `play("")`. The OSD menu restores appearance
  sampled when it opens. Thumbnail visibility and overlay-ID notifications let
  the personal OSC coordinate its overlays with upstream trickplay rendering.
- Lowercase `i` uses mpv's temporary stats display; Shift+i toggles persistent
  stats. Mixed-key use does not leave false persistent state, and returning to
  the library clears tracked persistent stats.

## Queue and library controls

[Ctrl+L setup and behavior](../contrib/mpv/README.md) and
[personal OSC integration](fork-osc-queue.md) use the shim's session queue,
including duplicate entry identities and revision-checked operations.
[Playlist card behavior](fork-playback-actions.md) preserves the selected
occurrence and resume position in the full playlist.

## Lifecycle ownership

v3.3 owns player construction, concurrent reopening, publication and per-handle
teardown. The former fork initialization lock, idle-reset handling and initial
playstate suppression are superseded and must not be restored.

The remaining fork guard sets `_shutting_down` under the player lock during
`terminate()`. Reopen/playback requests refuse late work, browser window requests
return without reopening, and incidental playstate publication stops during exit.
This protects final application shutdown, separately from upstream's failed-reopen
state. A boundary probe demonstrated late construction without the guard; normal
upstream tray Quit did not reproduce an orphan.

## Maintenance

See [refresh guidance](fork-upstream-refresh.md), [v3.3 validation](fork-v3.3-review.md)
and [the dated Jellyfin 12 server findings](fork-jellyfin12-queue.md).
The old Windows IPC monkeypatch, wholesale seek/volume binding overrides and
legacy dependency lock are superseded by upstream and remain removed.

# Ctrl+L Jellyfin queue adapter

Copy `jellyfin_queue_adapter.lua` into your portable config's `script-modules/` and
apply `playlistmanager-jellyfin.patch` to `scripts/playlistmanager.lua`.
For Ctrl+L, no mpv.conf, input.conf, script options or thumbfast changes
are required. The separate [OSC integration](../../docs/fork-osc-queue.md) also
requires the modified `scripts/osc.lua` maintained in the personal mpv config repo. Restart mpv to load the scripts.

The adapter observes the same `mpv-jellyfin` IPC prefix as `jellyfin.lua`.
Direct observation also handles script startup ordering. It wraps only
playlistmanager's local mp API; standalone mpv retains the native playlist.
`mp.find_config_file` locates the module. Without a config/module the script
falls back to its original behavior, including explicit `--no-config` launches
([mpv path documentation](https://mpv.io/manual/master/#paths)).

During Jellyfin playback:

- Ctrl+L retains the user's existing display, key bindings and script options.
- Up/Down navigates; Enter uses the shim's `skip_to` path, including SyncPlay.
  The original playlistmanager behavior of Enter on the current row advancing
  to the next row is retained.
- Select a row with Left/Right, then move it with the existing navigation keys.
  Backspace/Delete bindings remove a non-playing row. The currently playing
  row cannot be removed, matching the shim's existing queue editor.
- Local editing is disabled during SyncPlay. Saved-playlist load/save
  operations remain delegated to Jellyfin. Shuffle randomizes only the
  current session queue, preserving the current episode and duplicate entries;
  it never updates the saved playlist or restarts playback. Sort cycles between displayed-title
  natural ascending and descending order, retaining duplicate-title order.
  Reverse flips the entire queue. Each uses one complete, revision-checked
  reorder and preserves the playing entry; remote rows do not support local
  filesystem date/size sorting.
- Only entry IDs and display titles cross the bridge. Native mpv still holds
  one playable item; no stream URLs or credentials are copied into the adapter.
- Revisions reject actions for a replaced/edited queue; duplicate media items
  are addressed by distinct PlaylistItemId. Refreshes cannot swallow Enter.
- Titles load in a background worker and are cached per authenticated client.
  Missing metadata uses numbered generic rows. A one-second poll observes
  Web queue edits and episode changes without querying HTTP on each poll.

This does not fix Jellyfin 12's stale /Sessions queue reporting. It reads the
shim's authoritative playback queue directly and never fabricates stop reports.
It edits the playback queue, not the saved Jellyfin playlist.

The adapter and modified scripts are maintained in the personal mpv config Git
repository. Keep its runtime adapter synchronized with this bundled copy.
The playlistmanager patch is for the original personal script; inspect changes
before applying it to another script revision. Restart mpv after updating scripts.

Python coverage is in `tests/test_queue_bridge.py`; Lua coverage is in
`tests/lua/test_queue_adapter.lua`. See [current validation](../../docs/fork-v3.3-review.md)
for tested scope and live-server limitations.

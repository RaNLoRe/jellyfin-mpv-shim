# Ctrl+L Jellyfin queue adapter

The portable repository was clean at `0be80e0e42e5f0dc0926267e31cb3a1b95dc3710`
(`main`) before this change. Its resolved path is
`C:/Users/User/scoop/persist/mpv-git/portable_config`.

Copy `jellyfin_queue_adapter.lua` into that config's `script-modules/` and
apply `playlistmanager-jellyfin.patch` to `scripts/playlistmanager.lua`.
Both changes have been applied locally and audited together with the fork.
No mpv.conf, input.conf, script options, OSC or thumbfast changes
are required. Restart mpv to load the scripts.

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

Verification: Python bridge/routing regressions, Lua adapter tests, and a real
windowless mpv test loading the complete modified portable playlistmanager.
The latter drives Ctrl+L, Down and Enter and checks the selected entry, no Lua
errors, and an unchanged native playlist. The user confirmed next/previous
after reordering and accepted the bulk queue operations. Removal and SyncPlay
still have automated coverage only; they remain optional operator checks.

Rollback both portable changes together: restore playlistmanager from its
pre-adapter Git version and remove only the added adapter module. Preserve
any later unrelated edits. For an older installed shim without this protocol,
roll back these portable changes as well. No remote push was made.

Operator follow-up: the user confirmed next/previous follows the queue after
manual reordering. Automated real-mpv coverage now also exercises natural
ascending/descending sorting and reverse, including duplicate titles.

The speculative portable history-disabling code was removed at the user's
request. A subsequent instrumented diagnostic launch detected the Jellyfin
IPC prefix immediately, never loaded manual-mpv.conf, and retained
save-watch-history=false through multiple episode changes. The real history
file stayed byte-for-byte unchanged at 592 lines. The original writing launch
remains unidentified (the user removed those entries before inspection).
The original detector is restored byte-for-byte on disk. The diagnostic
process that held temporary read-only tracing has since exited.

Real-mpv synthetic tests also verified Shuffle emits one complete reorder
without a select action or native playlist mutation.

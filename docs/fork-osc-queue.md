# Personal classic OSC queue controls

The personal `portable_config/scripts/osc.lua` previously read mpv's native
one-file playlist. Its small previous/next arrows were disabled even when the
Jellyfin session had more entries. Chapter controls are separate and unchanged.

The OSC and its runtime adapter are maintained directly in the mpv config Git
repository. The integration adds a queue position/count to the title, refreshes
state once per second and on file load, redraws the controls only when the queue
revision changes, and routes arrow clicks and the arrows' playlist picker through the existing
Jellyfin queue/playlistmanager paths. Native playlist looping does not enable
arrows at Jellyfin queue boundaries. Standalone mpv retains its native behavior.

The OSC activates queue integration only after a version-1 capability reply.
Probes omit the serial, so an older shim's reply to playlistmanager is ignored
without changing that script's state or request sequence. Until negotiation
succeeds, the OSC retains its native behavior. Probes retry at most every five
seconds. The shim must include `queue_bridge.py`'s capability and `reply_to`
support. Each script gets
its own replies and request serials, so the OSC cannot consume Ctrl+L's replies.
Old playlistmanager requests without `reply_to` retain their original behavior.
Selection still uses entry identity and revision checking, including SyncPlay.
No media URLs are copied into mpv's native playlist.

Validation: Python queue bridge tests and Lua 5.1 adapter tests cover reply
routing, duplicate entries, stale actions, SyncPlay, first/last boundaries,
reordering, repaint notifications, stopped queues, picker routing, and standalone
fallback. Live server playback remains a manual check after installing the build.

The OSC shades enabled Jellyfin media segments inside the seekbar in amber at 50% opacity. These
are visual ranges; chapter navigation and seek behavior are unchanged. Ranges
arrive through OSC queue refresh replies and require the matching shim and
runtime adapter. Older shims omit the ranges, leaving the normal seekbar.

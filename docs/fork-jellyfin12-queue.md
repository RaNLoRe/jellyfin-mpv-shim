# Jellyfin 12 server queue limitations

These findings were observed on 2026-09-09 against a server reporting 12.0.0,
with public source tag `v12.0`. They are not a claim about later server releases;
the deployed binary was not matched to an exact source commit.

## Stale session queue

In [SessionManager at v12.0](https://github.com/jellyfin/jellyfin/blob/v12.0/Emby.Server.Implementations/Session/SessionManager.cs),
start/progress update the current entry but do not assign `NowPlayingQueue`.
A real playback stop updates the queue. Both HTTP `/Sessions` and WebSocket
session DTOs can therefore expose an older queue while current-item/pause state
continues to update.

An isolated diagnostic reproduced this with one-entry and 11-entry queues:
outgoing start/progress reports contained the queue, while both server transports
exposed an empty or stale queue. Genuine episode transitions updated it.
The corrected WebSocket observer sent application-level KeepAlive; results from
an earlier observer after it stopped receiving updates were excluded.

The fork's adapter reads the shim's authoritative queue directly. It does not
fabricate stops. A server correction should accept non-null queues on genuine
start/progress, preserve omitted fields, allow explicit empty queues, retain
duplicate entry identities, and avoid stale synthetic progress overwriting edits.
No server fix or upstream PR was made as part of this work.

## Remote playlist order

Web's playlist Play supplied 11 IDs already sorted by SortName rather than saved
playlist order. The shim preserved the incoming order. Server playlist-as-folder
expansion is the leading explanation, but Web's outbound request was not captured,
so Web versus server attribution is not fully isolated.

The user's Web workflow, right-click episode → Play all from here, supplied the
saved order and correct StartIndex and worked in that diagnostic. This is a dated
observation, not a guarantee for every server/Web version.

Do not reorder incoming flat ID lists to compensate: they may represent intentional
shuffle or different playlists. Queue length alone cannot detect stale order or
entry identities. Recheck both on the actual server before calling either issue fixed.

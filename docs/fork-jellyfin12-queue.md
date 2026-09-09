# Jellyfin 12: session queue reporting

Investigated 2026-09-09 against a server identifying as **12.0.0**. The public
source tag used is `v12.0` (not `v12.0.0`). The user's earlier running shim
identified as 2.10.0. Media Manager is intended to manage existing playback
sessions; Web or another client initiates and owns the queue.

## Source findings

In [SessionManager at v12.0](https://github.com/jellyfin/jellyfin/blob/v12.0/Emby.Server.Implementations/Session/SessionManager.cs),
`OnPlaybackStart` and `OnPlaybackProgress` call `UpdateNowPlayingItem`. That
method assigns `PlaylistItemId`, but not `NowPlayingQueue`. The queue assignment
appears in `OnPlaybackStopped`, guarded against null. `ToSessionInfoDto` reads
both fields from the session. Local source line references: 389/459,
765/777, 897/913, 1119–1124, and 1263–1265 respectively.

The [HTTP controller](https://github.com/jellyfin/jellyfin/blob/v12.0/Jellyfin.Api/Controllers/SessionController.cs)
and [WebSocket listener](https://github.com/jellyfin/jellyfin/blob/v12.0/Jellyfin.Api/WebSocketListeners/SessionInfoWebSocketListener.cs)
expose the same session DTO data. Thus both transports can agree on a stale
queue while the current item and pause state update correctly. This is a
server-state hypothesis supported by the inspected source, not evidence that
the playback client failed to advance its actual queue.

## Observed diagnostic behavior

The isolated v3 shim reported a one-entry queue on start and progress; wrapped
report calls returned successfully. HTTP `/Sessions` and a separate WebSocket
observer initially exposed an empty queue while reflecting the current entry
and pause state. After a **real** playback stop, both exposed the one-entry
queue. This supports the source finding for this server installation.

The initial WebSocket observer lacked application-level KeepAlive and stopped
receiving updates. Its silence is excluded from the evidence. A corrected
observer sent KeepAlive and reproduced the stale-queue/real-stop transition.
Both observers used distinct diagnostic device IDs, retained tokens only in
memory, and recorded only whitelisted item/entry IDs, queue entries, timestamps
and pause state. Raw private captures are kept locally, not committed.

The initial test resumed an item **inside the shim's library UI**. A subsequent
test was confirmed by the user to be Play on a playlist in **Jellyfin Web**:
all 11 entries appeared in outgoing progress reports, while HTTP `/Sessions`
still exposed an empty queue and the correct paused/current-item state. The
corrected WebSocket observer was no longer running for that first 11-entry
test. A subsequent coordinated restart/replay captured both HTTP and WebSocket
exposing empty queues while the shim successfully reported all 11 entries and
both transports reflected its paused/current-item state.
The coordinated Next/Previous test then reproduced the user's original
observation: the shim transitioned through received queue positions 1 → 2 → 1,
retaining all 11 entries. After those real episode transitions (and their real
stop reports), both HTTP and WebSocket exposed all 11 entries and the correct
current item. Subsequent pause/resume/pause transitions were also reported.
The deployed server binary has not been matched to an
exact public source commit beyond its reported version.

Both the old fork and v3 include queue/current-entry data in normal playback
reports. v3's `player_reporting.py:get_timeline_options` still builds these
fields from the actual media queue. Upgrading the client alone therefore does
not remove the inspected server assignment gap.

## Proposed upstream correction

Update session queue state from non-null `NowPlayingQueue` on genuine client
start and progress reports, before publishing playback events/session DTOs.
Preserve existing state when the field is omitted/null; allow an explicit empty
list to clear it. Copy the ordered entries and retain their PlaylistItemIds,
including distinct entries that share an ItemId.

Do not blindly apply this in a shared helper: automated synthetic progress
must not overwrite a newer client queue with an older snapshot. Cover this
distinction explicitly in server tests.

Suggested regression tests: first cast with a full queue; add/remove/reorder
while playing; duplicate ItemIds with distinct PlaylistItemIds; current-entry
changes; omitted versus empty queues; automated progress after a client edit;
and genuine stop. Assert HTTP and WebSocket DTOs expose the same updated order.

No server change, upstream issue/PR submission or misleading client workaround
was performed. In particular, no playback-stop report was fabricated to force
a queue refresh. Media Manager should not recreate or initiate the queue to
compensate for stale server reporting.

## Separate finding: remote playlist order

In the 11-entry Web test, the actual playback queue was ordered as saved
playlist positions **7, 8, 11, 2, 3, 1, 9, 4, 10, 6, 5**, beginning at position
7. A read-only comparison against `GET /Playlists/{id}/Items` confirmed the
saved playlist order differs. A second comparison against `GET /Items` with
that playlist as ParentId, Recursive=true and SortBy=SortName matched the
playback order exactly. This was alphabetical sorting, not a random shuffle.

`SessionManager.SendPlayCommand` expands items through
`TranslateItemForPlayback`, whose Folder branch requests SortName ascending.
[Playlist derives from Folder](https://github.com/jellyfin/jellyfin/blob/v12.0/MediaBrowser.Controller/Playlists/Playlist.cs).
The shim's remote Play handler passes received ItemIds and StartIndex to
Media, which preserves their order. On the coordinated repeat, the captured
incoming `PlayNow` message contained exactly the SortName-ordered 11 IDs,
with null StartIndex and StartPositionTicks. The reported queue retained that
order exactly and playback began at its first entry (saved position 7).
This confirms the ordering defect occurs before the shim handles the command.
The server expansion remains the leading explanation; without capturing Web's
outbound request, attribution between Web and the server is not fully isolated.

Proposed server investigation: distinguish playlists before generic folders,
expand their playable entries in saved order, preserve duplicate entries and
visibility filtering, and apply shuffle only when explicitly requested. Test
normal Play, PlayNext/PlayLast, and explicit Shuffle against an intentionally
non-alphabetical playlist. The shim cannot safely reconstruct the intended
playlist from a flat list of IDs: doing so could undo intentional shuffle or
confuse different playlists containing the same items.

The user's normal **right-click episode → Play all from here** workflow was
subsequently tested. Its incoming PlayNow supplied all 11 IDs in saved playlist
order and StartIndex=1. The shim's first playback report identified the second
saved entry and preserved the full ordered queue. Thus this workflow is a
verified way to start the queue correctly, without any shim reordering patch.
HTTP and WebSocket still exposed the previous SortName-ordered queue and old
entry identities while updating the current PlaylistItemId. Comparing only
queue length (11 in both cases) would miss this stale-state reproduction.

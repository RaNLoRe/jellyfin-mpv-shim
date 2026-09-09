# Library playback actions

Audited against the fork based on upstream `fa990688` (v3.0.0 plus 53 commits).

| Surface | Card/body click | Play button |
| --- | --- | --- |
| Episode/movie cards in ordinary grids | Open details | Play/resume the item; an episode with SeriesId uses the normal series continuation queue |
| Series card | Open series | Start Next Up, with series continuation |
| Season card | Open season | Queue the season starting at its first unplayed episode |
| Playlist container card | Open playlist | Queue its supported entries from the beginning |
| Episode/movie entry inside a playlist | **Open details** | **Queue the full playlist in its displayed/saved order, starting at this occurrence and resuming it** |
| Music playlist track rows | Start the playlist at that row | Existing track-list behavior remains |
| Episode/movie detail page | Browse metadata | Existing Play/Resume actions, including normal episode continuation; this page is not the playlist route |

The playlist page's header Play All and Shuffle retain their existing whole-list
behavior. Right-click playback retains its generic item behavior. For episodes
with a SeriesId inside playlists, the labels now say “Play episode (series
order)”, “Resume episode (series order)” and “Restart episode (series order)”
to distinguish it from the overlay button; this change targets the separate card and overlay play button, without
adding the abandoned context-menu entry. The saved Jellyfin playlist is not
modified by starting playback.

The common play-list launcher now preserves the selected occurrence when it
filters empty IDs. Previously, searching the filtered list by media ID jumped
to the first duplicate. The playlist chip locates by PlaylistItemId (or object
identity when absent) and reads the current route data when activated. If the
entry has been removed, it does not fall back to playing the item alone.

Verification: 135 tests passed across playlist card actions, tile play chips,
playlist shell actions and Play All. New tests drive the actual card and chip
handlers and cover detail navigation without playback, full queue plus resume,
duplicate occurrences, changed snapshots and removed entries. Live operator
confirmation of the revised card and overlay gestures passed. The three
series-order labels are included in the translation template; the running
diagnostic needs its next restart to display those final labels.

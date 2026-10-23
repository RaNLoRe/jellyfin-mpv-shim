# Playlist playback actions

The fork changes episode/movie cards inside a playlist:

| Action | Result |
| --- | --- |
| Card/body click | Open details |
| Overlay Play | Play the full supported playlist in displayed order, starting at this occurrence and retaining its resume position |
| Episode context-menu Play/Resume/Restart | Normal series continuation, explicitly labelled with “episode (series order)” |

Header Play All/Shuffle, music track rows, ordinary library cards and detail-page
playback keep upstream behavior. Starting playback does not modify the saved playlist.

The play-list launcher preserves the selected occurrence when filtering empty
IDs. The overlay handler reads current route data on activation and identifies
entries by `PlaylistItemId`, or object identity when absent. If the entry was
removed, it does not fall back to playing the item alone.

Regression coverage lives in `tests/test_playlist_card_actions.py` and the
upstream tile/playlist action suites. Latest validation scope is recorded in
[the v3.3 review](fork-v3.3-review.md).

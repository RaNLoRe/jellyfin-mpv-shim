"""Opt-in playlist-script access to the shim's existing queue.

Messages contain entry identities and display titles, never playable URLs or
credentials. Commands run on the player action thread under its lock. The
revision prevents a delayed keypress from editing a replacement queue.
"""
import json
import uuid
from threading import Thread

from .items_api import get_items


class QueueBridge:
    def __init__(self):
        self.signature = None
        self.revision = None
        self.client = None
        self.titles = {}
        self.worker = None

    def state(self, player):
        video = player._video
        if video is None:
            signature = None
            entries = []
            current = None
        else:
            entries = list(video.parent.queue)
            current = video.get_playlist_id()
            signature = (video.parent, current,
                         tuple((q.get("Id"), q.get("PlaylistItemId"))
                               for q in entries))
        if signature != self.signature or self.revision is None:
            self.signature = signature
            self.revision = uuid.uuid4().hex
        return video, entries, current

    def handle(self, player, raw):
        if not isinstance(raw, str) or len(raw) > 65536:
            return
        try:
            request = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(request, dict):
            return
        video, entries, current = self.state(player)
        action = request.get("action")
        ids = [q.get("PlaylistItemId") for q in entries]
        target = request.get("entry")
        if (video is not None and action != "refresh"
                and request.get("revision") == self.revision
                and isinstance(target, str) and target in ids):
            if action == "select":
                if target != current:
                    player.skip_to(target)
            elif not player.syncplay.is_enabled():
                # Group edits belong to SyncPlay, not the local queue editor.
                if action == "remove":
                    player.queue_remove_many([target])
                elif action == "reorder":
                    order = request.get("order")
                    # A bulk operation must be a complete permutation of
                    # this revision, including distinct duplicate entries.
                    if (isinstance(order, list) and len(order) == len(ids)
                            and all(isinstance(key, str) for key in order)
                            and len(set(order)) == len(order)
                            and set(order) == set(ids)):
                        player.queue_reorder(order)
                elif action == "move":
                    before = request.get("before")
                    if before is None or (isinstance(before, str) and before in ids):
                        if before != target:
                            order = [p for p in ids if p != target]
                            order.insert(len(order) if before is None else order.index(before), target)
                            player.queue_reorder(order)
            video, entries, current = self.state(player)
        if video is not None:
            if self.client is not video.client:
                self.client = video.client
                self.titles = {}
            missing = list(dict.fromkeys(q["Id"] for q in entries
                                        if q.get("Id") not in self.titles))
            # Metadata must not block the player action thread or mpv events.
            # The worker owns a captured cache, so an old server's response
            # cannot populate the replacement client's titles.
            if missing and (self.worker is None or not self.worker.is_alive()):
                cache = self.titles
                cache.update((key, None) for key in missing)
                self.worker = Thread(target=self._load_titles,
                                     args=(video.client, missing, cache), daemon=True)
                self.worker.start()
        payload = {
            "serial": request.get("serial"),
            "active": video is not None,
            "revision": self.revision,
            "editable": video is not None and not player.syncplay.is_enabled(),
            "current": current,
            "items": [{"entry": q.get("PlaylistItemId"),
                       "title": self.titles.get(q.get("Id")) or "Queue item %d" % (i + 1)}
                      for i, q in enumerate(entries)],
        }
        player._player.command("script-message-to", "playlistmanager",
                               "jms-queue-state", json.dumps(payload))

    @staticmethod
    def _load_titles(client, missing, cache):
        for start in range(0, len(missing), 200):
            batch = missing[start:start + 200]
            try:
                result = get_items(client.jellyfin, ids=batch,
                                   enable_images=False, enable_user_data=False)
                for item in result.get("Items", []):
                    name = item.get("Name")
                    if name and item.get("SeriesName"):
                        episode = ""
                        if item.get("ParentIndexNumber") is not None and item.get("IndexNumber") is not None:
                            episode = "S%02dE%02d — " % (item["ParentIndexNumber"], item["IndexNumber"])
                        name = item["SeriesName"] + " — " + episode + name
                    if item.get("Id") in batch:
                        cache[item["Id"]] = name
            except Exception:
                # API errors can contain URLs/tokens. Keep generic row titles.
                pass

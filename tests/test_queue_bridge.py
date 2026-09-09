"""Queue adapter actions keep entry identity and use the real queue mutators."""
import json
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

sys.argv = [sys.argv[0]]
from tests.integration import _harness as h
player = h.import_player_with_fake_mpv()
from jellyfin_mpv_shim.queue_bridge import QueueBridge


class QueueBridgeTest(unittest.TestCase):
    def setUp(self):
        self.pm = h.build_player(player, test=self)
        self.media = SimpleNamespace(queue=[{'Id': 'same', 'PlaylistItemId': 'a'},
            {'Id': 'other', 'PlaylistItemId': 'b'}, {'Id': 'same', 'PlaylistItemId': 'c'}], seq=0)
        self.pm._video = SimpleNamespace(parent=self.media, client=object(),
            get_playlist_id=lambda: self.media.queue[self.media.seq]['PlaylistItemId'])
        self.pm.syncplay = mock.Mock(is_enabled=mock.Mock(return_value=False))
        self.pm.skip_to = mock.Mock()
        self.bridge = QueueBridge()
        self.bridge.client = self.pm._video.client
        self.bridge.titles = {'same': 'Repeated episode', 'other': 'Other episode'}
        self.state = self.send('refresh')

    def send(self, action, **args):
        self.bridge.handle(self.pm, json.dumps(dict(action=action, serial=1, **args)))
        return json.loads(self.pm._player.commands[-1][-1])

    def test_duplicates_select_the_entry_not_the_item(self):
        self.send('select', entry='c', revision=self.state['revision'])
        self.pm.skip_to.assert_called_once_with('c')

    def test_replacement_and_queue_edits_reject_stale_actions(self):
        self.media.queue = self.media.queue + [{'Id': 'extra', 'PlaylistItemId': 'd'}]
        self.bridge.titles['extra'] = 'Extra'
        self.send('select', entry='c', revision=self.state['revision'])
        self.pm.skip_to.assert_not_called()

    def test_reorder_preserves_current_and_duplicate_entries(self):
        state = self.send('move', entry='c', before='a', revision=self.state['revision'])
        self.assertEqual([x['entry'] for x in state['items']], ['c', 'a', 'b'])
        self.assertEqual(state['current'], 'a')
        self.assertEqual(self.media.seq, 1)
        self.assertNotEqual(state['revision'], self.state['revision'])

    def test_remove_never_removes_current(self):
        state = self.send('remove', entry='a', revision=self.state['revision'])
        self.assertEqual(len(state['items']), 3)
        state = self.send('remove', entry='c', revision=state['revision'])
        self.assertEqual([x['entry'] for x in state['items']], ['a', 'b'])

    def test_syncplay_select_uses_player_but_refuses_local_edits(self):
        self.pm.syncplay.is_enabled.return_value = True
        state = self.send('remove', entry='c', revision=self.state['revision'])
        self.assertEqual(len(state['items']), 3)
        self.assertFalse(state['editable'])
        self.send('select', entry='c', revision=state['revision'])
        self.pm.skip_to.assert_called_once_with('c')

    def test_stopped_state_clears_list_and_rejects_old_selection(self):
        self.pm._video = None
        state = self.send('select', entry='c', revision=self.state['revision'])
        self.assertFalse(state['active'])
        self.assertEqual(state['items'], [])
        self.pm.skip_to.assert_not_called()

    def test_invalid_messages_do_not_issue_commands(self):
        before = len(self.pm._player.commands)
        for raw in (None, 'bad json', '[]', 'x' * 65537):
            self.bridge.handle(self.pm, raw)
        self.assertEqual(before, len(self.pm._player.commands))

    def test_metadata_fetch_does_not_block_player_or_expose_urls(self):
        gate = threading.Event()
        self.pm._video.client = SimpleNamespace(jellyfin=object())
        def lookup(*args, **kwargs):
            gate.wait(2)
            return {'Items': [{'Id': 'same', 'Name': 'Title', 'Path': 'secret-url',
                               'SeriesName': 'Series', 'ParentIndexNumber': 1, 'IndexNumber': 2}]}
        with mock.patch('jellyfin_mpv_shim.queue_bridge.get_items', side_effect=lookup):
            state = self.send('refresh')
            self.assertEqual(state['items'][0]['title'], 'Queue item 1')
            gate.set()
            self.bridge.worker.join(3)
            state = self.send('refresh')
        self.assertEqual(state['items'][0]['title'], 'Series — S01E02 — Title')
        self.assertNotIn('secret-url', json.dumps(state))

    def test_event_dispatch_queues_work_instead_of_running_on_mpv_thread(self):
        self.pm._handle_queue_bridge = mock.Mock()
        self.pm.put_task = mock.Mock()
        self.pm._on_client_message({'args': ['jms-queue', '{"action":"refresh"}']})
        self.pm._handle_queue_bridge.assert_not_called()
        self.pm.put_task.assert_called_once_with(self.pm._handle_queue_bridge, '{"action":"refresh"}')

    def test_bulk_reorder_preserves_playing_entry_and_next_previous(self):
        state = self.send('reorder', entry='a', order=['c', 'b', 'a'], revision=self.state['revision'])
        self.assertEqual([x['entry'] for x in state['items']], ['c', 'b', 'a'])
        self.assertEqual(state['current'], 'a')
        self.assertEqual(self.media.seq, 2)
        self.assertTrue(self.media.has_prev)
        self.assertFalse(self.media.has_next)
        state = self.send('reorder', entry='a', order=['a', 'b', 'c'], revision=state['revision'])
        self.assertEqual(self.media.seq, 0)
        self.assertTrue(self.media.has_next)
        self.pm.skip_to.assert_not_called()

    def test_bulk_reorder_refuses_incomplete_duplicate_and_foreign_ids(self):
        for order in (None, {}, ['a', 'b'], ['a', 'b', 'b'], ['a', 'b', 'unknown'], ['a', 'b', []]):
            with self.subTest(order=order):
                state = self.send('reorder', entry='a', order=order, revision=self.state['revision'])
                self.assertEqual([x['entry'] for x in state['items']], ['a', 'b', 'c'])

    def test_bulk_reorder_refuses_stale_revision_and_syncplay(self):
        self.send('reorder', entry='a', order=['c', 'b', 'a'], revision='stale')
        self.assertEqual(self.media.queue[0]['PlaylistItemId'], 'a')
        self.pm.syncplay.is_enabled.return_value = True
        self.send('reorder', entry='a', order=['c', 'b', 'a'], revision=self.state['revision'])
        self.assertEqual(self.media.queue[0]['PlaylistItemId'], 'a')

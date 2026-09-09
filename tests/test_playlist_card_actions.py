"""Drive the playlist card and its separate play chip through UI handlers."""
import sys
import unittest
sys.argv = ['test']
from jellyfin_mpv_shim.mpvtk_browser.app import MpvtkBrowser
from tests._shell_harness import FakeController, FakeSource, _SyncPool, build_scene


class PlaylistCardActionsTest(unittest.TestCase):
    def setUp(self):
        self.items = [
            {'Id':'same','PlaylistItemId':'a','Name':'First','Type':'Episode'},
            {'Id':'other','PlaylistItemId':'b','Name':'Second','Type':'Episode'},
            {'Id':'same','PlaylistItemId':'c','Name':'Repeated','Type':'Episode',
             'UserData':{'PlaybackPositionTicks':123000000}},
        ]
        self.ctl = FakeController()
        source = FakeSource()
        source.get_playlist_items = lambda *args: self.items
        self.b = MpvtkBrowser(app=None, source=source, controller=self.ctl)
        self.b._pool = _SyncPool()
        self.b.server = 'srv1'
        self.b.navigate({'kind':'playlist','server':'srv1','item_id':'PL','title':'Mix'})

    def cards(self):
        nodes, handlers = build_scene(self.b)
        cards = [n['id'] for n in nodes if n.get('id','').startswith('pl-') and n.get('hev')]
        self.assertEqual(len(cards),3)
        return cards, handlers

    def test_card_opens_details_without_starting_playback(self):
        cards, handlers = self.cards()
        handlers[cards[-1]]['click']()
        self.assertEqual(self.b.route['kind'], 'detail')
        self.assertEqual(self.b.route['item_id'], 'same')
        self.assertEqual(self.ctl.played, [])

    def test_chip_starts_full_playlist_at_clicked_duplicate_and_resumes(self):
        cards, handlers = self.cards()
        handlers[cards[-1]]['hover']('')
        _, handlers = build_scene(self.b)
        handlers[cards[-1]+'-play']['click']()
        self.assertEqual(self.ctl.played, [(['same','other','same'],'srv1',2)])
        self.assertEqual(self.ctl.play_offsets, [123000000])

    def test_chip_reads_latest_order_when_snapshot_moves_entry(self):
        cards, handlers = self.cards()
        handlers[cards[-1]]['hover']('')
        _, handlers = build_scene(self.b)
        self.b.route['_data'] = [self.items[2],self.items[0],self.items[1]]
        handlers[cards[-1]+'-play']['click']()
        self.assertEqual(self.ctl.played, [(['same','same','other'],'srv1',0)])

    def test_removed_entry_does_not_fall_back_to_single_episode(self):
        item = self.items[2]
        self.b.route['_data'] = self.items[:2]
        self.b._play_tile(item)
        self.assertEqual(self.ctl.played, [])

    def test_play_list_retains_duplicate_after_filtering_empty_ids(self):
        self.b._actions.play_list(['same',None,'same'],'srv1',2)
        self.assertEqual(self.ctl.played, [(['same','same'],'srv1',1)])

"""Stats key intent survives the browser's playback routing."""
import sys
import unittest

sys.argv = [sys.argv[0]]
from tests.integration import _harness as h
player = h.import_player_with_fake_mpv()


class StatsShortcutsTest(unittest.TestCase):
    def setUp(self):
        self.pm = h.build_player(player, test=self)
        self.pm.mpvtk_active = True
        self.pm._video = object()
        self.pm._current_is_audio = lambda: False
        self.pm._player.commands.clear()

    def press(self, oneshot):
        self.pm._stats_key(oneshot)
        while not self.pm.evt_queue.empty():
            func, args = self.pm.evt_queue.get_nowait()
            func(*args)

    def test_lowercase_repeatedly_requests_native_temporary_display(self):
        for _ in range(3):
            self.press(True)
            self.assertFalse(self.pm._stats_shown)
            self.assertEqual(self.pm._player.commands[-1],
                             ('script-binding', 'stats/display-stats'))

    def test_uppercase_stays_persistent_and_library_cleanup_clears_it(self):
        for _ in range(3):
            self.press(False)
            self.assertTrue(self.pm._stats_shown)
            self.pm.clear_stats()
            self.assertFalse(self.pm._stats_shown)

    def test_toggle_during_oneshot_does_not_arm_a_false_cleanup_toggle(self):
        self.press(True)
        self.pm._player.input_bindings = [dict(owner='stats', priority=1,
            cmd='nonscalable script-binding stats/__forced_1')]
        self.press(False)
        self.pm._player.input_bindings[0]['priority'] = -1  # timer expired
        self.pm.clear_stats()
        self.assertFalse(self.pm._stats_shown)
        self.assertEqual(self.pm._player.commands,
                         [('script-binding', 'stats/display-stats')])
        self.press(False)
        self.assertTrue(self.pm._stats_shown)

    def test_a_queued_key_does_not_show_stats_after_returning_to_library(self):
        self.pm._stats_key(True)
        self.pm._video = None
        func, args = self.pm.evt_queue.get_nowait()
        func(*args)
        self.assertEqual(self.pm._player.commands, [])

    def test_library_and_audio_swallow_both_keys(self):
        for audio in (False, True):
            self.pm._video = object() if audio else None
            self.pm._current_is_audio = lambda: audio
            for oneshot in (True, False):
                self.press(oneshot)
        self.assertEqual(self.pm._player.commands, [])

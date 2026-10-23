"""Regressions retained from the fork, using the isolated fake-mpv harness."""
if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.argv = [sys.argv[0]]
from tests.integration import _harness as h

player = h.import_player_with_fake_mpv()
from jellyfin_mpv_shim import conf
from jellyfin_mpv_shim.menu import OSDMenu


class ForkSeekTest(unittest.TestCase):
    def setUp(self):
        self.pm = h.build_player(player, test=self)
        self.intro = SimpleNamespace(start=10.0, end=60.0, type="Intro",
                                     has_triggered=False)
        self.pm._video = SimpleNamespace(get_current_intro=lambda pos:
            (False, self.intro if 10 <= pos < 60 else None))
        self.pm._player.playback_time = 20.0
        self.pm._player.seeking = False
        self.pm._player.playback_abort = False
        self.pm._last_ui_seek_time = 0.0
        self.pm._pump_trickplay = lambda: None
        self.pm.push_playstate = lambda: None
        self.pm._hud_skip = None
        self.pm._osc_style_resolved = "mpvtk"
        self.pm.update()  # Real producer: snapshot the prompted segment/position.
        self.pm._player.commands.clear()
        patch = mock.patch.object(conf.settings, "skip_intro_on_seek", True)
        patch.start()
        self.addCleanup(patch.stop)

    def seek(self, destination, during=None):
        # Reproduce the IPC ordering: position has moved BEFORE seeking=True.
        self.pm._player.playback_time = destination
        self.pm._player.seeking = True
        self.pm._on_seeking("seeking", True)
        self.pm.update()  # An action-thread poll must not replace the snapshot.
        if during:
            during()
        self.pm._player.seeking = False
        self.pm._on_seeking("seeking", False)
        return [c for c in self.pm._player.commands if c[0] == "seek"]

    def test_forward_seek_with_early_destination_skips_original_segment(self):
        self.assertEqual(self.seek(30), [("seek", 60.0, "absolute")])
        self.assertTrue(self.intro.has_triggered)
        self.assertEqual(self.pm._last_playback_position, 30)

    def test_landed_position_is_recorded_with_intro_gesture_disabled(self):
        with mock.patch.object(conf.settings, "skip_intro_on_seek", False):
            for destination in (30, 80, 15):
                self.assertEqual(self.seek(destination), [])
                self.assertEqual(self.pm._last_playback_position, destination)

    def test_seek_completion_after_shutdown_does_not_read_the_dead_handle(self):
        self.pm._pending_intro_seek = (self.pm._video, self.intro, 20.0)
        self.pm._mpv_alive = False
        self.pm._last_playback_position = 20.0
        with mock.patch.object(type(self.pm._player), "playback_time",
                               new_callable=mock.PropertyMock, create=True) as clock:
            clock.side_effect = AssertionError("read a terminated mpv")
            self.pm._on_seeking("seeking", False)
            clock.assert_not_called()
        self.assertIsNone(self.pm._pending_intro_seek)
        self.assertIsNone(self.pm._intro_seek_context)
        self.assertEqual(self.pm._last_playback_position, 20.0)

    def test_backwards_and_small_movements_do_not_skip(self):
        for destination in (15, 20, 20.5):
            self.pm._intro_seek_context = (self.pm._video, self.intro, 20.0)
            self.assertEqual(self.seek(destination), [])

    def test_seek_beyond_intro_does_not_jump_back_or_skip_another_segment(self):
        other = SimpleNamespace(start=70, end=100, type="Intro", has_triggered=False)
        self.pm._video.get_current_intro = lambda pos: (False, other)
        self.assertEqual(self.seek(80), [])
        self.assertTrue(self.intro.has_triggered)
        self.assertFalse(other.has_triggered)

    def test_syncplay_ui_and_disabled_segments_are_exempt(self):
        for mode in ("syncplay", "ui", "disabled", "setting"):
            with self.subTest(mode=mode):
                self.pm._intro_seek_context = (self.pm._video, self.intro, 20.0)
                with mock.patch.object(self.pm.syncplay, "is_enabled",
                                       return_value=mode == "syncplay"), \
                     mock.patch.object(conf.settings, "segment_intro",
                                       "off" if mode == "disabled" else "ask"), \
                     mock.patch.object(conf.settings, "skip_intro_on_seek",
                                       mode != "setting"):
                    self.pm._last_ui_seek_time = time.time() if mode == "ui" else 0
                    self.assertEqual(self.seek(30), [])

    def test_video_change_during_seek_cannot_skip_new_video(self):
        self.assertEqual(self.seek(30, lambda: setattr(self.pm, "_video", object())), [])

    def test_entering_intro_from_outside_does_not_skip(self):
        self.pm._intro_seek_context = None
        self.assertEqual(self.seek(30), [])

    def test_credits_use_the_same_original_segment_rule(self):
        self.intro.type = "Outro"
        self.assertEqual(self.seek(30), [("seek", 60.0, "absolute")])


class ForkIntroArrowTest(unittest.TestCase):
    def setUp(self):
        self.pm = h.build_player(player, test=self)
        self.intro = SimpleNamespace(start=10, end=60, type="Intro", has_triggered=False)
        self.pm._video = SimpleNamespace(get_current_intro=lambda pos:
            (False, self.intro if 10 <= pos < 60 else None))
        self.pm._player.playback_time = 20
        self.pm._osc_style_resolved = "custom"
        self.pm.menu = mock.Mock(is_menu_shown=False)
        self.pm.seek = mock.Mock()
        self.pm.skip_intro = mock.Mock()
        self.pm._key_claims = {}
        self.pm._swept = [("RIGHT", "seek", (10, False)),
                          ("LEFT", "seek", (-10, False)),
                          ("Shift+RIGHT", "seek", (3, False)),
                          ("Ctrl+Shift+RIGHT", "seek", (1, False))]
        self.pm._swept_ptr = []
        for name, value in (("skip_intro_on_seek", False), ("segment_intro", "ask"),
                            ("kb_menu_right", "right"), ("use_web_seek", False)):
            patch = mock.patch.object(conf.settings, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.pm._refresh_key_section()

    def test_only_the_dedicated_arrow_is_claimed(self):
        self.assertEqual(set(self.pm._key_actions), {"RIGHT"})

    def test_disabled_menu_right_preserves_independent_seek_claims(self):
        with mock.patch.object(conf.settings, "kb_menu_right", None):
            self.pm._refresh_key_section()
            self.assertEqual(self.pm._key_actions, {})
            self.pm._key_claims = {"test": {"seek"}}
            self.pm._refresh_key_section()
            self.pm._on_claimed_key("seek", "RIGHT")
        self.pm.seek.assert_called_once_with(10, exact=False)
        self.pm.skip_intro.assert_not_called()

    def test_right_skips_with_the_general_seek_gesture_disabled(self):
        self.pm._on_claimed_key("seek", "RIGHT")
        self.pm.skip_intro.assert_called_once_with(self.intro)
        self.pm.seek.assert_not_called()

    def test_modified_arrows_remain_normal_even_if_another_feature_claims_seeks(self):
        self.pm._key_claims = {"test": {"seek"}}
        self.pm._refresh_key_section()
        for key, amount in (("Shift+RIGHT", 3), ("Ctrl+Shift+RIGHT", 1), ("LEFT", -10)):
            self.pm._on_claimed_key("seek", key)
            self.pm.seek.assert_called_with(amount, exact=False)
        self.pm.skip_intro.assert_not_called()

    def test_right_outside_intro_keeps_the_users_ten_second_seek(self):
        self.pm._player.playback_time = 70
        self.pm._on_claimed_key("seek", "RIGHT")
        self.pm.seek.assert_called_once_with(10, exact=False)
        self.pm.skip_intro.assert_not_called()

    def test_disabled_segment_does_not_turn_right_into_skip(self):
        with mock.patch.object(conf.settings, "segment_intro", "off"):
            self.pm._on_claimed_key("seek", "RIGHT")
        self.pm.seek.assert_called_once_with(10, exact=False)
        self.pm.skip_intro.assert_not_called()

    def test_menu_navigation_wins_over_skip(self):
        self.pm.menu.is_menu_shown = True
        self.pm._on_claimed_key("seek", "RIGHT")
        self.pm.menu.menu_action.assert_called_once_with("right")
        self.pm.skip_intro.assert_not_called()

    def test_hud_and_nonseek_right_bindings_are_not_claimed(self):
        self.pm._osc_style_resolved = "mpvtk"
        self.pm._refresh_key_section()
        self.assertEqual(self.pm._key_actions, {})
        self.pm._osc_style_resolved = "custom"
        self.pm._swept = [("RIGHT", "pause", None)]
        self.pm._refresh_key_section()
        self.assertEqual(self.pm._key_actions, {})


class ForkCompatibilityTest(unittest.TestCase):
    def test_old_preference_migrates_and_explicit_v3_preference_wins(self):
        for old, new, expected in ((True, None, True), (False, None, False),
                                   (True, False, False), ("false", None, False)):
            with self.subTest(old=old, new=new), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "conf.json"
                data = {"config_version": conf.CONFIG_VERSION, "seek_to_skip_intro": old}
                if new is not None:
                    data["skip_intro_on_seek"] = new
                path.write_text(json.dumps(data), encoding="utf-8")
                with mock.patch.object(conf, "config_path", None):
                    cfg = conf.Settings()
                    self.assertTrue(cfg.load(str(path)))
                    self.assertIs(cfg.skip_intro_on_seek, expected)
                    self.assertNotIn("seek_to_skip_intro", json.loads(path.read_text()))
                    again = conf.Settings()
                    self.assertTrue(again.load(str(path)))
                    self.assertIs(again.skip_intro_on_seek, expected)

    def test_external_aborted_video_never_loads_empty_path(self):
        pm = h.build_player(player, video=object(), test=self)
        pm._player.playback_abort = True
        with mock.patch.object(player, "is_using_ext_mpv", True), \
             mock.patch.object(pm._player, "play") as play:
            pm.force_window(False)
            play.assert_not_called()

    def test_menu_restores_style_from_each_open_not_construction(self):
        pm = mock.MagicMock()
        pm.get_osd_settings.return_value = ("initial", 20, "outline")
        pm.is_playing.return_value = False
        pm.playback_is_aborted.return_value = False
        menu = OSDMenu(pm, pm._player)
        for size in (24, 28, 32):
            style = ("#112233", size, "outline")
            pm.get_osd_settings.return_value = style
            with mock.patch("jellyfin_mpv_shim.menu.time.sleep"):
                menu.show_menu()
                pm.get_osd_settings.return_value = ("menu", 40, "background-box")
                menu.show_menu()
                menu.hide_menu()
            self.assertEqual(pm.set_osd_settings.call_args.args, style)


if __name__ == "__main__":
    unittest.main()

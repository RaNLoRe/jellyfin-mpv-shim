# Duplicate mpv after reopening the library — 2026-09-23

Reproduced on Windows against local `245a3c36`, using an unsigned-in profile,
a unique device ID and IPC pipe, and the installed external mpv executable.
No production profile or portable configuration was changed.

The trigger is library close → mpv idle termination → tray Show Library.
The diagnostic called the real `idle_quit()` directly to avoid waiting for
the configured idle timeout; other close/reopen cycles kept mpv alive.

During `_init_mpv`, registering volume/mute observers produces initial values.
The event thread calls `_on_volume_change` → `push_playstate` → browser
`on_playstate({stopped: True})` → `enter_browse` → `set_browse_window(True)`.
The original initialization has not yet set `_mpv_alive`, so this second
caller starts another mpv on the same IPC pipe and overwrites `_player`.

Observed process evidence:

- First reproduction: tray thread created PID 33584, then the event thread
  created PID 19684 about 0.1 seconds later. Both remained alive.
- Tray Quit stopped the tracked player; PID 33584 survived app shutdown.
  It was subsequently removed as part of diagnostic cleanup.
- A second reproduction captured the full volume-observer call chain and
  accumulated multiple surviving processes over repeated reopen cycles.
- A browser recreation request also occurred during application shutdown.

This reproduces the duplicate-player/orphan symptom reported by the user.
It explains how two IPC controllers can be attached to the same player and
double-handle the shim's Space binding, while native mpv mouse pause works.
The earlier production occurrence had two children on `mpv-jellyfin`, but
did not capture their creation stacks; its historical trigger cannot be
proven retrospectively.

The fix suppresses incidental browser snapshots until mpv is initialized,
serializes initialization and re-checks whether a player already exists,
and prevents browser/player recreation once application shutdown starts.
The idle-quit flag is reset for browser reopen as well as playback reopen,
after the outgoing event thread is joined. No key binding workaround or
process-name-wide kill is added.

Verification via uv / Python 3.13:

- Real external mpv: eight close/reopen cycles, including four idle exits,
  kept exactly one player alive; tray Quit left no diagnostic mpv process.
- JSON IPC focused suite: 408 passed.
- libmpv focused suite: 467 passed (using the installed bundled DLL path).
- Regression coverage: initial volume notification during recreation,
  competing creation requests, shutdown callbacks, and existing lifecycle,
  window, playstate, gateway and keyboard behavior. Payload fixtures now
  explicitly model a ready player. Audio tests run with their libmpv model;
  forcing that unit model through JSON IPC gives unrelated property-read
  failures, so it is not counted as an external-backend check.

The installed application is unchanged. A replacement build and a user check
of library close/reopen, Space during playback, and tray Quit are still needed
before calling the installed version fixed.

## Follow-up sweep

The broader source/test audit found no further runtime defect in this change.
It corrected older test fixtures that did not model shutdown state, preserved
the actual creation caller in lifecycle logs after adding the locking wrapper,
and added a regression asserting that idle-shutdown suppression stays enabled
until the outgoing termination thread has joined.

The expanded uv runs completed with 959 JSON IPC tests and 1,018 libmpv tests,
with six skips per backend and no failures. They cover the fake player state
machine, playback start, keyboard controls, application lifecycle, picture
settings, and the unit suites that exercise creation/window/reporting paths.
The test cache was isolated after the initial runs stalled scanning the shared
Windows temporary directory. Source whitespace checks also pass. The existing
real-process eight-cycle result above remains applicable: the only production
change made during this sweep was caller logging.
The two binding/OSC suites were then rerun with the installed DLL directory
on PATH: all 44 tests passed, including the five real-libmpv cases skipped
by the broader run because its DLL was not on PATH.

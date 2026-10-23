# Maintaining the personal fork

Keep `master` as the clean upstream reference and rebase `feat-fix-bindings`
onto it. Review each custom change for upstream replacements before resolving
conflicts; a clean textual replay does not establish behavioral compatibility.
The current base is `535a9688` (v3.3.0 plus two translation commits).

Use [the feature inventory](fork-features.md) as the retention checklist and
[the v3.3 verification record](fork-v3.3-review.md) for the latest tested scope.
Keep documentation about current behavior and unresolved limitations; Git history
holds previous upgrade plans and results.

For each refresh:

1. Compare upstream changes with the retained features and their regression tests.
   Keep upstream lifecycle handling and only the fork's final-shutdown guard.
2. Run relevant tests on both backend models, the integration matrix and Lua
   adapters. Check real external-mpv close/reopen/Quit and stats behavior.
   Record skips and untested live-server paths explicitly.
3. Review the combined diff and the personal mpv scripts together. The runtime
   queue adapter must match `contrib/mpv/jellyfin_queue_adapter.lua`.
4. Build into separate work/output directories and retain earlier installers.
   `build-win.bat` deletes `build` and `dist`; do not run it over retained artifacts.
   Verify packaged source, Lua/resources, DLL architecture/dependencies and certifi.
5. Publish rewritten history with an explicit force-with-lease against the
   verified remote tip. Do not publish rollback tags or implicitly follow tags.

Building does not install the application. Use the production identity when
installing, not a diagnostic profile. An old executable alone cannot undo any
upstream profile or offline-catalog migration.

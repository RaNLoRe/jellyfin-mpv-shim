# Upstream refresh — 2026-10-06

Standing preference: keep `master` as the clean upstream reference and
**rebase** `feat-fix-bindings` onto it for each upstream refresh. Preserve the
old personal tip under a dated `rollback/` tag before rewriting history.
Do not introduce upstream merge commits into the personal commit stack.

Local `master` was fast-forwarded from `9db70b24` to upstream `46af845a`
(245 commits). The six personal commits were rebased onto it, retaining every
custom feature. The original tip is tagged
`rollback/pre-v3.1-rebase-2026-10-06` at `f4cf0084`.

Conflicts were resolved in the intro-seek handler, the thumbnail compatibility
script and playback-state fixtures. Regression checks passed on both fake
backends, with real external-mpv lifecycle/stats probes and targeted real-libmpv
checks. See [the v3.1 assessment and verification](fork-v3.1-review.md) for exact
counts, exclusions and migration considerations. Remote branches and the
installed app remain unchanged.

## Previous refresh — 2026-09-23

The personal branch is now a linear stack of six custom commits based on
upstream `9db70b24315badfc1cc8d8b9c1e506a95d339c05`, 116 upstream commits
after the previous `fa990688` base. Local and origin `master` mirror that tip.
The original upgrade merge was replayed relative to its upstream parent,
preserving its final compatibility changes rather than replaying the two
obsolete v2 patches. The remaining five custom commits applied cleanly.
Before the translator-note update, the resulting tree exactly matched a
three-way merge of the previous personal tip with the new upstream.

Upstream now requires translator context for every template entry; notes
were added for the fork's three episode context-menu labels. No per-locale
translations or portable configuration were changed.

Verification via uv: 1,026 JSON IPC tests and 1,085 libmpv tests completed
with no failures and six skips per backend. This includes custom features,
the new upstream static checks, and upstream's state-restoration scenarios.
An unsigned-in real external-mpv diagnostic also completed eight close/reopen
cycles, with four idle terminations, one player at each check and clean Quit.
This does not replace testing Space and playback in the next installed build.

Rollback: local tag `rollback/pre-rebase-2026-09-23` preserves the complete
previous personal history at `08ac535e`. The remote feature branch is not
changed as part of this preparation; publishing rewritten history needs the
user's approval for a force-with-lease push. The installed app is unchanged.

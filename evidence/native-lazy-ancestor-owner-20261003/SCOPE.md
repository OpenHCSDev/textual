# Consume native ancestry lazily through the existing DOM owner

Stacked after frozen45 f7683fa772 in the same native checkout. No new environment,
recording, provider, type, cache, traversal state or parent registry. Heisenberg
owns Toad405 Body/ViewportPresentation/WindowMembership consumers. This branch
owns DOMNode and all native short-circuit consumers; frozen45 source is unchanged.

Existing DOMNode.walk_ancestors(*, with_self=False) will traverse the original
weak parent relation on demand, nearest first. Public ancestors and
ancestors_with_self keep their list contracts and derive the traversal.
query_ancestor consumes the iterator while retaining original DOM base, TCSS
parser/matcher, expected type, nearest-match order and detached NoMatches.
Migrate every native nearest/membership/early-stop consumer; retain deliberate
reverse/root-index/snapshot collection behavior. No source identity/cycle cache
or synthetic parent. Existing reparent admission continues owning cycle rejection.

Source-first whole native/dependency AST, then semantic read of the original
parent lifetime and all consumers. Native custom paint ancestry remains its
existing override contract. Original402 observed stack edges motivate removal
of eager ancestor materialization; they do not establish CPU dominance or speed.
One coherent final batch and changed installed journey joins405 using existing
native App/recording tools. Do not rerun frozen44/45 checks or402 film, create new
fixtures/environments, or reason from test failures. Ship a working source
checkpoint promptly; actual installed qualification remains a distinct boundary.

"""Detect chain reorganisations from a sequence of block observations.

Feed it (height, hash) pairs in the order you observed them. A reorg shows up as
one of two shapes: the same height with a different hash, or a height that goes
backwards. Both are reported, because they mean different things to an indexer.

The interesting output is not "a reorg happened" but "these block hashes are now
orphaned", which is what you need in order to roll back derived state.
"""


class Reorg(Exception):
    """A height was seen twice with different hashes, or height went backwards."""

    def __init__(self, kind, from_height, to_height, orphaned):
        super().__init__("%s: %d -> %d, %d orphaned block(s)"
                         % (kind, from_height, to_height, len(orphaned)))
        self.kind = kind
        self.from_height = from_height
        self.to_height = to_height
        self.orphaned = orphaned


class Watcher:
    """Track the canonical chain, one observed block at a time."""

    def __init__(self):
        self.chain = {}        # height -> hash
        self.orphaned = []     # (height, hash) no longer canonical
        self.reorgs = 0
        self.height = -1

    def observe(self, height, block_hash):
        """Record a block. Returns 'extend', 'duplicate' or raises Reorg.

        A height strictly below the current head is a regression: every block
        above it leaves the canonical chain. Checking that BEFORE the
        already-seen check matters, because a regression usually lands on a
        height we have already observed, and the regression label carries the
        information the caller needs.
        """
        block_hash = block_hash.lower()

        if height < self.height:
            return self._reorg(height, block_hash, "height-regression")

        if height in self.chain:
            if self.chain[height] == block_hash:
                return "duplicate"
            return self._reorg(height, block_hash, "same-height")

        self.chain[height] = block_hash
        self.height = height
        return "extend"

    def _reorg(self, height, block_hash, kind):
        dropped = []
        for h in sorted([h for h in self.chain if h >= height], reverse=True):
            dropped.append((h, self.chain.pop(h)))
        self.orphaned.extend(dropped)
        self.reorgs += 1
        self.chain[height] = block_hash
        self.height = height
        raise Reorg(kind, height, height, dropped)

    def head(self):
        return (self.height, self.chain.get(self.height))


def replay(observations):
    """Run a whole observation list through a Watcher.

    Returns (final_height, final_hash, reorg_count, orphaned_hashes). A reorg is
    recorded and the replay continues, which is what an indexer does.
    """
    w = Watcher()
    for height, block_hash in observations:
        try:
            w.observe(height, block_hash)
        except Reorg:
            pass
    return w.height, w.chain.get(w.height), w.reorgs, [h for _, h in w.orphaned]


def main(argv):
    import sys

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    lines = open(argv[0]).read().split()
    obs = []
    for ln in lines:
        height, _, block_hash = ln.partition(",")
        obs.append((int(height), block_hash.strip()))
    height, head, reorgs, orphaned = replay(obs)
    print("head:    %d %s" % (height, head))
    print("reorgs:  %d" % reorgs)
    print("orphaned: %d block(s)" % len(orphaned))
    for h in orphaned:
        print("  %s" % h)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))

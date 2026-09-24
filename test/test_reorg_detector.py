import unittest

from reorg_detector import Reorg, Watcher, replay

A = "0xaa" + "00" * 31
B = "0xbb" + "00" * 31
C = "0xcc" + "00" * 31
D = "0xdd" + "00" * 31


class Observe(unittest.TestCase):
    def test_linear_extension(self):
        w = Watcher()
        self.assertEqual(w.observe(1, A), "extend")
        self.assertEqual(w.observe(2, B), "extend")
        self.assertEqual(w.head(), (2, B))
        self.assertEqual(w.reorgs, 0)

    def test_duplicate_is_not_a_reorg(self):
        w = Watcher()
        w.observe(1, A)
        self.assertEqual(w.observe(1, A), "duplicate")
        self.assertEqual(w.reorgs, 0)

    def test_same_height_different_hash_is_a_reorg(self):
        w = Watcher()
        w.observe(1, A)
        w.observe(2, B)
        with self.assertRaises(Reorg) as cm:
            w.observe(2, C)
        self.assertEqual(cm.exception.kind, "same-height")
        self.assertEqual(w.head(), (2, C))
        self.assertEqual(w.reorgs, 1)

    def test_height_regression_orphans_everything_above(self):
        w = Watcher()
        w.observe(1, A)
        w.observe(2, B)
        w.observe(3, C)
        with self.assertRaises(Reorg) as cm:
            w.observe(1, D)
        self.assertEqual(cm.exception.kind, "height-regression")
        # heights 1, 2 and 3 all left the canonical chain
        self.assertEqual(len(cm.exception.orphaned), 3)
        self.assertEqual(w.height, 1)

    def test_hashes_are_compared_case_insensitively(self):
        w = Watcher()
        w.observe(1, A)
        self.assertEqual(w.observe(1, A.upper().replace("0X", "0x")), "duplicate")

    def test_state_is_consistent_after_a_reorg(self):
        w = Watcher()
        w.observe(1, A)
        w.observe(2, B)
        try:
            w.observe(2, C)
        except Reorg:
            pass
        self.assertEqual(w.chain, {1: A, 2: C})
        self.assertEqual(w.orphaned, [(2, B)])


class Replay(unittest.TestCase):
    def test_clean_chain_reports_no_reorgs(self):
        height, head, reorgs, orphaned = replay([(1, A), (2, B), (3, C)])
        self.assertEqual((height, head, reorgs, orphaned), (3, C, 0, []))

    def test_replay_continues_past_a_reorg(self):
        height, head, reorgs, orphaned = replay([(1, A), (2, B), (2, C), (3, D)])
        self.assertEqual(reorgs, 1)
        self.assertEqual(height, 3)
        self.assertEqual(head, D)
        self.assertEqual(orphaned, [B])

    def test_multiple_reorgs_accumulate(self):
        _, _, reorgs, orphaned = replay([(1, A), (1, B), (1, C)])
        self.assertEqual(reorgs, 2)
        self.assertEqual(len(orphaned), 2)


if __name__ == "__main__":
    unittest.main()

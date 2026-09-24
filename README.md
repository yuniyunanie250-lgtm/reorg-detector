# reorg-detector

Detect chain reorganisations from a sequence of observed blocks, and know exactly
which hashes were orphaned.

An indexer that ignores reorgs drifts out of sync silently. The useful output is
not "a reorg happened" but "these specific blocks are no longer canonical",
because that is the list you have to undo.

## Usage

```bash
python3 -m reorg_detector observations.txt
```

```
head:    19000412 0xdd...
reorgs:  1
orphaned: 1 block(s)
  0xbb...
```

`observations.txt` is one `height,hash` per line, in the order you saw them.

```python
from reorg_detector import Watcher, Reorg

w = Watcher()
w.observe(100, hash_a)      # 'extend'
try:
    w.observe(100, hash_b)  # raises
except Reorg as e:
    roll_back(e.orphaned)   # your compensating action
```

## Two shapes, two meanings

- **`same-height`** — the same height arrived with a different hash. A sibling
  block won; only the block at that height is orphaned.
- **`height-regression`** — a height at or below the current head arrived. Every
  block above it is orphaned, and the watcher drops them.

Reporting both under one label would hide the difference, and the amount of state
to roll back differs by a lot between them.

## What it does not do

- **No finality tracking.** It has no notion of "deep enough to stop worrying";
  add a confirmation depth above it.
- **No RPC.** It watches observations you supply.
- **No persistence.** State is in memory; back it with a store if you need it
  across restarts.
- **No fork-choice.** If two chains are extended alternately it will report a
  reorg every time, because it trusts the most recent observation.

## Development

```bash
python3 -m unittest discover -s test -t .
```

## License

MIT

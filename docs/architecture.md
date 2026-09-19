# Architecture

A description of how the systems are put together, without the operational
specifics that would be harmful to expose.

---

## Shape of the whole thing

```
   public venue APIs / archives
              |
        [ collectors ]                 continuous, watchdog-supervised
              |
        [ raw archive ]                immutable, manifest-verified
              |
        [ integrity gates ]            blocking: a failure stops the pipeline
              |
        [ processed layer ]            only admitted rows, split-partitioned
              |
    +---------+---------+
    |                   |
[ research ]        [ live panel ]     read-only inspection
```

Two rules hold across every component:

1. **The raw layer is immutable.** Nothing downstream writes back to it.
2. **Research code never reads the raw layer directly.** It reads only the
   processed layer, which contains exclusively rows admitted by the frozen
   rules. This prevents an analysis from silently including data the
   protocol excluded.

## Collectors

Per-venue clients for public market data. Each handles its own rate limits
through a single gatekeeper rather than per-call-site checks — an earlier
design distributed the limit logic and the individual checks turned out to
be inert.

Collectors are supervised. The supervisor measures the collector's own
heartbeat rather than inferring health from a port or a sibling process, and
it acts before it logs, because a supervisor that cannot write its log must
still be able to act.

## Archive and storage

- **Raw layer** — source objects stored exactly as retrieved, with a
  manifest recording size, checksum, retrieval time and byte counts. For one
  study this is roughly 85 GB across 16,861 objects.
- **Processed layer** — columnar Parquet, partitioned by split, containing
  only admitted rows. One file per source object per split, which makes
  provenance traceable back to a single physical source.
- **Time-series archive** — SQLite with WAL for the live monitoring path,
  plus a never-prune history layer for research.

Acquisition is **resumable and idempotent**: every object has a settled
state, a re-run skips what is already complete, and a source object proven
absent is recorded as absent rather than substituted or interpolated.

## Integrity gates

A fixed set of checks between raw and processed:

| gate | what it establishes |
|---|---|
| schema era | the source layout is one of the known, handled shapes |
| source-partition containment | records sit in the physical partition the storage rule implies |
| source-integrity envelope | event times fall inside the permitted window for their partition |
| identifier canonicalization | parent identifiers convert losslessly and unambiguously |
| actor invariants | records claiming to be actor fills satisfy the properties that definition requires |
| null-identifier check | identity fields that define a record are present |
| duplicate identity | no registered identity appears more than once |
| parent/child reconciliation | child quantities sum to the parent's declared executed quantity |

Gates **block**. A failure ends the run and is published as a failure.

Reconciliation arithmetic is **decimal-exact** — fixed-precision decimals
throughout, never binary floating point — because the comparison tolerance is
tighter than float error would be at these magnitudes.

## Memory discipline

These datasets do not fit in memory, and naive approaches fail hard. Patterns
that proved necessary:

- **Find duplicates in the columnar engine, materialise only the repeats.**
  Building Python objects for every row to find the fraction that repeat
  exhausted memory outright.
- **Stream with a sliding window.** Where duplicates can only occur within a
  partition or between adjacent ones, holding two partitions at a time is
  sufficient and bounded.
- **Aggregate in the worker, not the reducer.** Returning rows to a parent
  process makes memory scale with the data; returning per-entity aggregates
  makes it flat.
- **Return memory explicitly.** Columnar allocators retain freed buffers
  across tasks, so long-running workers are recycled periodically and pools
  released.

## Provenance

Results that support a decision carry the generator, the result artifact,
SHA-256 hashes of both, and an asserted input corpus identity that aborts the
run if the expected object and row counts are not observed.

Where exact bytes matter, files are pinned against line-ending normalization,
because a hash covers a byte sequence and silent EOL conversion changes it.

## What is not described here

Deployment topology, hostnames, addresses, credential handling, alerting
destinations, and the thresholds and scoring constants inside the detection
layer.

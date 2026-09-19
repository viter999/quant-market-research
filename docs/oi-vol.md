# OI-VOL

Multi-exchange open-interest, volume and order-flow monitoring, with a
research layer built on top of it.

---

## Multi-exchange data acquisition

Designed for continuous collection of public market data on a personal
research host, with documented gaps caused by host sleep and network
interruptions. Uptime is not claimed.

Venue connectors have been developed for **Binance, Bitget, Bybit, Coinbase,
Gate.io, Kraken and MEXC**, each handling that exchange's own rate limits,
symbol conventions and quirks. The standalone deep-collection package is
**Binance USDT-M only**; the broader venue set is used by the monitoring
layer. That distinction is deliberate — depth of collection and breadth of
coverage are different claims and are not merged here.

Collected series (Binance USDT-M) include:

- **open interest** — periodic snapshots per instrument
- **book ticker** — top-of-book quotes
- **funding settlements** — scheduled funding events
- **liquidation tape** — forced-liquidation events as they print

Storage is a local time-series archive in SQLite with write-ahead logging,
plus a separate **never-prune history layer**. That second layer exists
because the live scanner prunes aggressively for performance, and research
later needs the history the scanner has already discarded. Losing data to a
retention policy designed for a different purpose is an easy and permanent
mistake.

A FastAPI service exposes a panel for live inspection, with end-to-end tests
covering the API surface.

## Research layer

The research question is whether joint anomalies in open interest, volume,
price and order flow carry information about what happens next.

Candidate rules are registered before evaluation, with the hurdle and kill
conditions written in advance. Several have been evaluated and formally
rejected. In one audit **the composite score was found not to rank** — and
the consequence was visible in the product, not just the write-up: the panel
label was changed from "score" to "activity", because the number described
how much was happening, not how likely anything was to work.

**No candidate rule from this project has been validated as predictive.**
The infrastructure is real; the signals are not established.

## Reliability engineering

An always-on collector that silently stops is worse than no collector,
because the gap is discovered late and the archive is unrecoverable. Several
classes of failure have been found and written up:

- **Liveness probes that lie.** A port check can pass while the service
  behind it is dead, because a proxy answers on the port. The ordering that
  actually works is: the process's own heartbeat file, then a lock probe,
  then a process scan — and a port check last, if at all.
- **A process cannot vouch for another process.** Liveness is measured
  directly, never asserted by a neighbour.
- **Checks that cannot fire.** One health check searched log output for a
  string the logger never emitted; it returned zero hits across more than
  19,000 log lines and had been inert since it was written.
- **A widened threshold is a timer on a kill loop.** Relaxing a watchdog
  limit to accommodate a blockage converts a detector into a delay.
- **Machine sleep looks exactly like an outage.** Archive gaps were traced to
  the host sleeping, which required judging staleness against the watchdog's
  own observation gap rather than against wall-clock time.

Each of these is documented as an incident or defect report with a root
cause, not merely patched.

## Forward-testing philosophy

Backtests on a system whose own collection history is entangled with its
development are weak evidence. The approach here is:

- fix the rule and its reading before the evaluation window opens;
- pin the interim-look dates in a calendar committed in advance, so a
  mid-flight peek cannot quietly become a decision point;
- treat the deploy — not the commit — as the boundary separating in-sample
  from out-of-sample, because a rule only affects the world once it is
  actually running;
- report the evaluable sample size per rule, because a rule that rarely
  fires produces a verdict on far fewer observations than the calendar
  suggests.

## What is not in this document

- live alert thresholds, scoring constants or eviction rules
- execution logic or position management
- server hostnames, addresses or production topology
- credentials of any kind
- account identifiers or position sizes

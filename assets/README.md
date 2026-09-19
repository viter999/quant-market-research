# Assets

Four diagrams are **done**. Two screenshots still need capturing — and they
need a person at the keyboard, for reasons stated below.

Every file here is either a newly drawn diagram reflecting the actual
system, or a capture specification. **Nothing is a mock-up, and no terminal
output has been manufactured.**

---

## Done — diagrams

These are drawn, not captured. Each is labelled *"Diagram (not a
screenshot)"* inside the image itself so it can never be mistaken for one.
Both light and dark themes are handled.

### `diagram-data-architecture.svg`

**Caption.** "Data architecture: public venue APIs through supervised
collectors and blocking integrity gates to a processed research layer."

**Proves.** That there is a real pipeline with a gate stage between raw and
processed data, and two structural invariants — the raw layer is never
written back to, and research code never reads it directly.

**Does NOT prove.** That the pipeline produces a useful signal, that all
venues are collected at the same depth, or that it runs uninterrupted.

### `diagram-research-workflow.svg`

**Caption.** "Research workflow: hypothesis through preregistration, freeze
and prospective test to a verdict read under pre-committed rules."

**Proves.** The method has explicit freeze points, and a fired stopping rule
terminates a hypothesis family rather than recycling it.

**Does NOT prove.** That any hypothesis survived, or that the process has
produced a positive result. It has not.

### `diagram-whale-lab-integrity.svg`

**Caption.** "Whale Lab: an integrity failure recorded as failed, then
decomposed forensically without being repaired."

**Proves.** The gates blocked a real study; the failure was preserved; the
forensic work is separated from the official result; and one question was
left explicitly unresolved rather than guessed.

**Does NOT prove.** Anything predictive. The 98.80% figure is an attribution
of a *data defect*, not a model result — and the diagram states the gate
still fails.

### `diagram-prereg-provenance.svg`

**Caption.** "Preregistration to result: what a public reader can verify, and
what they cannot."

**Proves.** The documents are internally consistent and the ordering claim is
stated with its limitation on the face of the image.

**Does NOT prove.** The commit ordering. The diagram says so directly: the
private hash is provenance, not proof.

---

## Still to capture — needs a person at the keyboard

I have deliberately **not** captured these. Both would require driving a live
application whose screen may contain positions, balances or account state,
and confirming what is on screen at capture time is a judgement a person
present at the machine has to make. Capturing them unattended risks exactly
the exposure this whole exercise is meant to prevent.

### 1. OI-VOL panel — the highest-value missing image

| | |
|---|---|
| **Source** | The monitoring panel, main view |
| **Proposed caption** | "Research interface for monitoring multi-venue market-state inputs." |
| **Proves** | Working infrastructure against live public data |
| **Does NOT prove** | That anything on screen predicts anything |
| **Must not be visible** | any alert score or threshold column, any position or balance, account identifiers, the URL bar if it shows host or port, browser chrome |
| **Crop** | The instrument table and venue indicators only |

**Caption rule:** name only the venues actually visible in the capture. The
seven-connector claim belongs in the prose, not in an image that does not
show seven venues.

### 2. Test suite — green run

| | |
|---|---|
| **Source** | `pytest` summary line |
| **Proposed caption** | "Test suite for the research and integrity tooling." |
| **Proves** | The test discipline is real and currently passing |
| **Does NOT prove** | That the tested logic is scientifically correct |
| **Must not be visible** | **the shell prompt — this is the highest-risk capture for username leakage** — and pytest's `rootdir` line, which prints the absolute path |
| **Crop** | The final summary lines only |

**Before capturing:** set a neutral prompt (`PS1='$ '`), and run from a
directory whose path is uninformative so `rootdir` reveals nothing.

---

## Rejected as a screenshot

**"A failed hypothesis, as published."** Originally planned as an image of a
findings document's verdict block. Dropped — the actual documents are now
published in `research/basis-dislocation/`, and a real document a reader can
open beats a picture of one. A screenshot of text is strictly worse than the
text.

---

## Rules for anything added here later

- No manufactured terminal output, ever. If it looks like a program printed
  it, a program printed it.
- Diagrams are labelled as diagrams, inside the image.
- No capture showing a position, order, balance, account identifier, host,
  address or credential.
- Captions describe what the image *is*, never what it predicts.

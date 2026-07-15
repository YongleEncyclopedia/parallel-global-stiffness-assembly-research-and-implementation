# Reproducible Source Delivery

This directory defines the source-package contract for the CSC3 symmetric
assembly demo. A delivery archive is evidence-bound, source-only, and marked
**INTERNAL EVALUATION ONLY**. It must not be described as a public release.

## Formal acceptance entry points

Research-institute delivery uses seven durable acceptance documents:

- [controlled Linux Intel runbook](LINUX_FORMAL_RUNBOOK.zh-CN.md);
- [two-stage acceptance workflow design](TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md);
- [immutable machine-facts schema](ACCEPTANCE_MACHINE_FACTS.schema.json);
- [human and organizational decision schema](ACCEPTANCE_DECISION.schema.json);
- [formal acceptance checklist](ACCEPTANCE_CHECKLIST.zh-CN.md);
- [rendered acceptance-record schema](ACCEPTANCE_RECORD.schema.json);
- [internal delivery-note template](DELIVERY_NOTE_TEMPLATE.zh-CN.md).

The runbook is the normative operator procedure. Its automated terminal state
is `PACKAGE_CANDIDATE`, not final acceptance. The three approval objects are
the candidate package, its immutable machine facts, and the human and
organizational decision. The mandatory handoff order is `draft`, human decision,
`render`, `validate`, then `finalize`.

1. `scripts/prepare_acceptance_materials.py draft` revalidates the candidate
   and publishes `acceptance-machine-facts.json` with a pending
   `acceptance-decision.json` template.
2. Humans edit only `acceptance-decision.json`; all four approval roles bind
   their decisions to the same candidate and machine-facts digest.
   `acceptance-machine-facts.json` is immutable and must not be edited.
3. `scripts/prepare_acceptance_materials.py render` revalidates both inputs and
   creates `acceptance-record.json`,
   `completed-acceptance-checklist.zh-CN.md`, and
   `completed-delivery-note.zh-CN.md` as deterministic renderer outputs.
4. `scripts/validate_acceptance_record.py` validates the rendered record and
   its candidate/evidence bindings.
5. `scripts/finalize_delivery.py` independently revalidates and rerenders the
   sidecars before publishing the hash-bound final directory.

The three rendered sidecars must not be created by copying templates or be
manually edited. Only the resulting directory with a verified
`FINAL_SHA256SUMS` is a final `PASS` delivery bundle. Issue #44 remains open
until that sequence passes. The checked macOS bundle is local-smoke evidence
only and cannot satisfy the condition.

The final directory contains the candidate source ZIP, the approved JSON
record, the completed checklist and delivery note, `FINALIZATION.json`, and an
`ACCEPTANCE_EVIDENCE/` snapshot of every non-ZIP artifact referenced by the
record. `FINAL_SHA256SUMS` covers every delivered file. Finalization preserves
the committed document structure and rejects keyword-only substitutes,
unresolved placeholders, unchecked items, path aliases, or changed evidence.

The source ZIP intentionally contains the reusable blank
`DELIVERY_NOTE_TEMPLATE.zh-CN.md` as renderer input. Only the deterministic
renderer output is a completed, approval-bound delivery note; the blank
template is never itself a delivery claim and must not be filled manually.

## Preconditions

Both packaging modes require a clean Git worktree at one captured source
commit. The packager rejects staged changes, tracked working-tree changes,
untracked files, symbolic links, and any source identity change during
packaging.

The committed-evidence mode is retained for checked local-smoke or historical
bundles. In that mode, the intended report and raw evidence must already be
committed under this demo, and paths outside the demo are rejected.

The external-formal mode is the only mode suitable for a new formal acceptance
package. Its evidence and canonical Markdown report must be generated outside
the repository from the exact clean package source commit. The packager opens
an immutable evidence snapshot, independently revalidates formal semantics,
recomputes the canonical report, and requires the evidence-producing source
commit to equal the captured package source commit.

Both modes require the same four required evidence files:

- `benchmark_samples.csv`;
- `benchmark_summary.json`;
- `ctest.xml`;
- `run_manifest.json`.

In committed-evidence mode those four files and the selected report must be
committed below this demo. An optional `summary.md` may also be committed and
included, but it is not required for a historical or local-smoke package. The
report must be a committed Markdown file under `reports/`. A local-smoke report
remains local-smoke evidence after packaging; packaging never promotes it to
formal controlled-host evidence.

External-formal mode instead has five required evidence files: the same four
files above plus `summary.md`. All five and the canonical Markdown report must
come from the repository-external controlled-host run directory and must pass
the external evidence snapshot and recomputation checks.

Formal evidence has one canonical sampling contract: two warmups, seven
measured repeats, and an amortization count of one ($W=2$, $R=7$, $m=1$).
Every producer, verifier, report generator, and finalizer rejects any other
formal count. If a matrix comparison cannot be evaluated because the CSC3
structures differ or a non-finite value is encountered, raw CSV/JSON uses a
paired maximum-finite-double transport sentinel for $e_F$ and $e_{\max}$ so
the failed evidence remains valid JSON. The report renders those sentinel
values as `不可评估` (`NOT_EVALUATED`); they are never presented as measured
errors.

## Create a committed-evidence archive

Run from the demo root, replacing the evidence and report names with the
checked artifacts for the delivery commit:

```bash
python3 scripts/create_delivery_package.py \
  --evidence-dir results/2026-07-13-macos-arm64-local-smoke \
  --report reports/2026-07-13-csc3-demo-macos-local-smoke-test-report.zh-CN.md
```

The default output is the ignored `dist/` directory. The filename is
`csc3-symmetric-assembly-demo-v0.2.0+<12-character-commit>.zip`. Delivery ZIP
files are generated artifacts and must not be committed.

## Create an external formal archive

Follow the controlled-host runbook rather than invoking this mode ad hoc. Its
core packaging command is:

```bash
python3 scripts/create_delivery_package.py \
  --external-evidence-dir /absolute/repository-external/evidence \
  --external-report /absolute/repository-external/report.zh-CN.md \
  --bundle-id controlled-linux-intel-run-id \
  --out-dir /absolute/repository-external/dist
```

All three external-formal selectors are mandatory and mutually exclusive with
`--evidence-dir` and `--report`. The bundle ID becomes the archive-relative
evidence/report identity; external absolute paths are never stored in the ZIP.
The runbook requires two independent package creations and a byte-for-byte
`cmp` before acceptance.

The packager captures one full commit SHA and reads the explicit source
whitelist from that commit's Git blobs, not from mutable worktree files. It
rechecks both `HEAD` and worktree cleanliness immediately before publication.
It writes members in lexicographic order, stores them without compression,
fixes every timestamp to the ZIP epoch, fixes permissions to `0644`, and
normalizes all packaged text to LF. `BUILD_INFO.json` binds the source commit,
evidence manifest, report, distribution state, and archive policy. Before
writing, the packager recomputes every selected artifact's size and SHA-256
after LF normalization and requires an exact match with `run_manifest.json`;
stale or incomplete raw-evidence bindings are rejected.
The caller-supplied existing parent path is the publication trust boundary: the
packager resolves it to its canonical directory, so system- or
operator-managed parent symlinks are followed deliberately. The output leaf is
then inspected without following it; an output-directory symlink is rejected.
Archive bytes are staged in a private directory on the same filesystem and
published with an atomic hard link that never replaces a destination.
An existing archive, destination symbolic link, or competing destination that
appears during publication is preserved and causes packaging to fail.
`MANIFEST.sha256` covers every other packaged file and intentionally does not
hash itself.

Generated figures, TIFF files, build directories, Python caches, editor files,
and unrelated result directories are outside the whitelist.

## Verify the archive

Integrity-only verification needs only Python's standard library:

```bash
python3 scripts/verify_delivery_package.py \
  dist/csc3-symmetric-assembly-demo-v0.2.0+<short-sha>.zip \
  --manifest-only
```

Full clean-room verification additionally requires Git, CMake, Ninja, a C++17
compiler, OpenMP, and the declared Python test dependency. Install the latter
with the same Python interpreter that will run the verifier:

```bash
python3 -m pip install -r requirements-test.txt
```

The full verifier and CMake configurations with
`CSC3_DEMO_BUILD_ACCEPTANCE_TESTS=ON` fail with an installation command when
`jsonschema>=4.23,<5` is missing or outside the supported range. A C++-only
`BUILD_TESTING=ON` configuration uses `CSC3_DEMO_BUILD_CPP_TESTS=ON` and does
not inspect Python dependencies. Its authoritative nine-test names and order
are recorded in `tests/ctest/expected-cpp-tests.txt`.
Manifest-only verification intentionally remains standard-library-only.

Then run:

```bash
python3 scripts/verify_delivery_package.py \
  dist/csc3-symmetric-assembly-demo-v0.2.0+<short-sha>.zip
```

The verifier rejects unsafe paths, duplicate or unlisted members, symbolic
links, noncanonical ZIP metadata, forbidden artifacts, invalid build
information, stale `run_manifest.json` artifact bindings, and every SHA-256
mismatch before extraction. Full mode extracts to a temporary directory,
configures and builds the `delivery` preset, checks the exact ten-test `ci`
inventory, validates JUnit contains no failed, skipped, disabled, or not-run
test, then independently configures, builds, and validates the single named
consumer test under `tests/external_consumer/`.

On macOS, set `OpenMP_ROOT="$(brew --prefix libomp)"` before full verification.
On Windows, run from an x64 Native Tools command prompt with Ninja on `PATH`.

## Provenance-path caveat

Raw `run_manifest.json` and CTest evidence are preserved byte-for-byte apart
from LF normalization. They may therefore contain absolute paths recorded on
the machine that produced the evidence. Those absolute paths are provenance,
not portable build instructions, and the verifier never follows them. All
package build and verification commands operate only on archive-relative paths
inside a newly created temporary directory.

`BUILD_INFO.json` records both the package source commit and, when present in
the evidence manifest, the evidence-producing source commit. These commits may
differ because a checked `LOCAL_SMOKE` bundle can predate packaging hardening.
Such evidence remains useful for traceability, but it must not be presented as
formal performance evidence for the package commit. Only a controlled-host
formal run generated from the final clean package source can support a formal
delivery performance conclusion. External-formal mode therefore requires the
two commits to be identical and rejects every non-`PASS`, non-`formal`, or
non-`delivery` evidence bundle.

The canonical evidence report is Markdown. A PDF may be supplied separately as
a presentation derivative, but it is not part of the source ZIP contract and
cannot replace or alter the hash-bound Markdown report.

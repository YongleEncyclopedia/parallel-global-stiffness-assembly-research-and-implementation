# Reproducible Source Delivery

This directory defines the source-package contract for the CSC3 symmetric
assembly demo. A delivery archive is evidence-bound, source-only, and marked
**INTERNAL EVALUATION ONLY**. It must not be described as a public release.

## Formal acceptance entry points

Research-institute delivery uses four durable Chinese acceptance documents:

- [controlled Linux Intel runbook](LINUX_FORMAL_RUNBOOK.zh-CN.md);
- [formal acceptance checklist](ACCEPTANCE_CHECKLIST.zh-CN.md);
- [JSON Schema Draft 2020-12 acceptance record](ACCEPTANCE_RECORD.schema.json);
- [internal delivery-note template](DELIVERY_NOTE.zh-CN.md).

The runbook is the normative operator procedure. Issue #44 remains open until
a controlled physical Linux Intel WindHub run passes. The checked macOS bundle
is local-smoke evidence only and cannot satisfy that condition.

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

The selected evidence directory must contain committed copies of:

- `benchmark_samples.csv`;
- `benchmark_summary.json`;
- `ctest.xml`;
- `run_manifest.json`.

In committed-evidence mode, the report must be a committed Markdown file under
`reports/`. A local-smoke report remains local-smoke evidence after packaging;
packaging never promotes it to formal controlled-host evidence.

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
Archive publication uses an exclusively created temporary file, so a
pre-existing path or symbolic link cannot redirect the write.
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
compiler, and OpenMP:

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

# Reproducible Source Delivery

This directory defines the source-package contract for the CSC3 symmetric
assembly demo. A delivery archive is evidence-bound, source-only, and marked
**INTERNAL EVALUATION ONLY**. It must not be described as a public release.

## Preconditions

Create a package only from a clean Git worktree after the intended source,
test report, and raw evidence have been committed. The packager rejects staged
changes, tracked working-tree changes, untracked files, symbolic links, and
evidence or report paths outside the demo.

The selected evidence directory must contain committed copies of:

- `benchmark_samples.csv`;
- `benchmark_summary.json`;
- `ctest.xml`;
- `run_manifest.json`.

The report must be a committed Markdown file under `reports/`. A local-smoke
report remains local-smoke evidence after packaging; packaging never promotes
it to formal controlled-host evidence.

## Create the archive

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

The packager reads the explicit whitelist from committed Git blobs at `HEAD`,
not from worktree files. It writes members in lexicographic order, stores them
without compression, fixes every timestamp to the ZIP epoch, fixes permissions
to `0644`, and normalizes all packaged text to LF. `BUILD_INFO.json` binds the
source commit, evidence manifest, report, distribution state, and archive
policy. Before writing, the packager recomputes every selected artifact's size
and SHA-256 after LF normalization and requires an exact match with
`run_manifest.json`; stale or incomplete raw-evidence bindings are rejected.
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
delivery performance conclusion.

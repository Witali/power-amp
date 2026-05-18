# Native Go layout scanner

This is an experimental lower-level rewrite of the image-analysis parts of the
Python OpenCV page-layout pipeline. It lives beside the current Python and
Node.js scripts and does not replace them.

The first implementation intentionally uses only the Go standard library:

- JPEG/PNG image loading.
- Grayscale conversion and Otsu thresholding.
- Connected-component candidate extraction.
- Coarse block merging.
- Feature extraction for ink density, edge density, run-line density,
  luma histograms, and schematic component signatures.
- Rule-based labels: `text`, `image`, `schematic`, `diagram`, `table`,
  and `other`.
- JSON output plus optional PNG crops.

It is not a full OpenCV replacement yet. The goal is to make the core ideas
portable and fast enough to compare against the Python detector.

## Build

The project-level build script uses portable Go from `local_tools/go`, writes
Go caches under `.tmp`, and builds command-line tools into `local_tools/bin`:

```text
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_go_tools.ps1
```

To build and run the smoke page check:

```text
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_go_tools.ps1 -Smoke -Crops
```

## Example

```text
go run ./cmd/layoutscan --image ../../.tmp/layout_candidate_pages/b.2000-02.037.jpg --out ../../.tmp/native-layout/page037 --crops
```

The command writes `layout.json` and, with `--crops`, block crop PNG files.

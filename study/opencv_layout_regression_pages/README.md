# OpenCV Layout Regression Pages

This folder preserves a fixed local set of processed Radio magazine pages for
layout-detector regression work.

Contents:

- `sources/` - copied source page scans. These are kept outside `.tmp` so the
  regression set survives cache cleanup.
- `baselines/` - current detector output for each page: `layout.json` and
  `preview.png`.
- `manifest.json` - selected page ids, source paths, baseline paths, and the
  reason each page is interesting.

Regenerate with:

```text
python scripts/build_layout_regression_set.py
```

The baseline intentionally stores no block crops to keep the set compact; crops
can be regenerated from the source scans when needed.

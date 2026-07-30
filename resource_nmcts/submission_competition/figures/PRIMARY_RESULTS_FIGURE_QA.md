# F4 primary-results figure QA

## Status

PASS

## Automated export checks

- PASS — source grid: 20/20 comparison cells.
- PASS — SVG: 129 editable text nodes and 0 embedded raster images.
- PASS — PDF: 1 page, 183.000 × 130.000 mm, extractable text present.
- PASS — PNG: 4322 × 3070 px at 599.999 dpi metadata.
- PASS — every displayed relative-effect confidence interval lies inside the common x-axis limits [-70.0, 80.0]%.
- PASS — strict/neutral classification was recomputed with all three conditions (family-Holm rejection, raw median-delta CI upper < 0, relative-improvement CI lower > 0); zero-touching remains neutral.
- PASS — the recomputed 10 strict and 10 neutral cells match final analysis `xa202609-primary20-836553591061`.

## Manual visual inspection

- PASS — all four metric columns and all five baseline rows are legible at the declared 183 mm width.
- PASS — no point estimate, confidence interval, W/T/L field, p-value or footer overlaps another element.
- PASS — filled strict and hollow neutral markers remain distinguishable without relying on colour.
- PASS — the documented timeout boundary (SSHR-Beam comparison covers all 20 functions (AES cells completed via n=8 vectorisation; no timeout boundary)) and three-part strict-gate definition are visible in the figure.

## Integrity boundary

The SVG/PDF are authoritative programmatic vector outputs. The PNG and QA preview are rasterizations of the same matplotlib figure. No source statistic, database record or manuscript file is modified by the generator.

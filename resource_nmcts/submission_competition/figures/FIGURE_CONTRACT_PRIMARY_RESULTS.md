# Figure contract — F4 frozen primary results

## Core conclusion

Across the frozen primary20 benchmark, Resource-NMCTS delivers broad, strictly
supported reductions relative to Direct ANF and selected reductions relative to
stronger baselines, while several CNOT/native-2Q/depth comparisons only touch or
cross the null and must remain visually neutral rather than being overclaimed.

## Figure archetype

`quantitative grid` with one dominant four-metric forest-plot panel and one
subordinate statistical-evidence matrix.

## Target journal/output

- Competition manuscript with Nature/Nature Machine Intelligence-style visual
  discipline.
- Python-only rendering with matplotlib.
- Double-column width: 183 mm; intended height: approximately 126–132 mm.
- Editable SVG and PDF, plus 600 dpi PNG and a lower-resolution QA preview.

## Panel map and evidence chain

- **a — effect-size grid (hero evidence):** four aligned forest plots show the
  function-level median relative improvement of Resource-NMCTS over each of five
  baselines for T count, CNOT count, native two-qubit count, and mapped depth.
  Horizontal bars are deterministic 95% percentile-bootstrap confidence
  intervals. Positive values favour Resource-NMCTS; a shared zero line makes
  null-crossing visible.
- **b — inferential audit matrix (validation evidence):** the same 5 × 4 cells
  report `W/T/L` and family-wise Holm-adjusted p-values. Filled signal cells mark
  the frozen strict gate only: `Holm reject = true`, the upper bound of the 95%
  bootstrap CI for the raw function-level median difference
  `(candidate − baseline)` is strictly below zero, **and** the lower bound of the
  95% bootstrap CI for median relative improvement is strictly above zero.
  Hollow/neutral cells cover intervals that touch zero, cross zero, or fail Holm
  rejection; zero-touching never qualifies as strict.

Every panel carries unique evidence: panel a communicates effect magnitude and
uncertainty; panel b makes sample size, direction counts, multiplicity correction,
and the strict claim boundary auditable.

## Evidence hierarchy

- **Hero evidence:** median relative improvement with 95% bootstrap CI for all
  20 baseline–metric comparisons.
- **Validation evidence:** exact independent-function `n`, W/T/L, family-Holm
  p-value, and strict-gate state for every plotted comparison.
- **Coverage boundary:** `n=20` for Direct ANF, Greedy factor, MCTS factor and
  SSHR-H. For SSHR-Beam, all three required seeds for each of two AES functions
  reached the 300 s synthesis timeout; therefore its complete-case comparison is
  `n=18`.
- **Controls/robustness:** the zero reference line, common x scale, neutral
  encoding for non-strict cells, and explicit lower-is-better direction prevent
  selective visual interpretation.

## Statistical contract

- Inference unit: independent Boolean function.
- Required seeds: 7, 17 and 29.
- Within-function aggregation: median over strictly paired seed results.
- Effect displayed: median of
  `100 × (baseline − Resource-NMCTS) / abs(baseline)`; positive values favour
  Resource-NMCTS.
- Interval displayed: deterministic percentile bootstrap over Boolean-function
  aggregates, 20,000 resamples, seed 202609, 95% confidence level; seeds are not
  resampled as independent observations.
- Direction counts: win/tie/loss for Resource-NMCTS under the lower-is-better
  metric convention.
- Test: paired two-sided Wilcoxon signed-rank test from the frozen statistics.
- Multiple comparisons: family-wise Holm correction from the frozen statistics.
- Strict display gate: `holm_reject` is true,
  `median_delta_ci_high < 0`, and
  `median_relative_improvement_pct_ci_low > 0`, where delta is
  `(Resource-NMCTS − baseline)` after within-function seed aggregation. Any
  confidence interval that touches zero is non-strict.
- Important interpretation boundary: the strict marker requires agreement of
  the raw-difference CI, relative-improvement CI, and family-Holm result; none of
  the three conditions is sufficient alone.

## Source-data contract

- Read-only quantitative inputs: the five frozen
  `results/final_stats/resource_vs_*.json` files. The final headline JSON and
  final-analysis manifest are read only to authenticate the three-part claim gate,
  its 10/20 classification, and the SSHR-Beam timeout boundary.
- The plotting program must select rows by exact metric key and scope; it must not
  hard-code favourable values.
- Deliver normalized source data as CSV and JSON, including input SHA-256 hashes,
  analysis-contract hashes, effect estimates, intervals, raw-difference intervals,
  n, W/T/L, Holm p-values and strict-gate state.
- Deliver an output manifest with script, input and artifact hashes.

## Visual contract

- White background; restrained blue/teal signal and neutral grey family.
- Filled teal points/cells denote strict support; hollow grey points/cells denote
  all other outcomes. Shape/fill, text and colour jointly encode state so the
  figure remains interpretable in greyscale.
- Shared x limits across all four metric plots; no truncated confidence bars.
- 5–7 pt body text and approximately 8 pt panel labels at final size.
- Panel titles and baseline labels are direct; no repeated legends.

## Image-integrity notes

This is fully programmatic vector line art. There are no photographs, crops,
contrast adjustments, pseudo-colour transformations or stitched raster panels.
The PNG is a deterministic raster export of the same matplotlib figure; SVG/PDF
are the authoritative editable outputs.

## Reviewer risks and mitigations

1. **Relative-improvement CI and raw-difference CI can yield different boundary
   cases.** State both definitions in panel annotations, source data and legend;
   classify strict support only when both confidence-interval conditions and the
   family-Holm condition pass.
2. **SSHR-Beam has smaller n.** Put `n=18` directly in its row label and state
   below the grid that all three seeds for two AES functions reached the 300 s
   synthesis timeout.
3. **Touching zero can be misread as significant.** Use the neutral hollow style
   whenever either gate interval touches zero, even if Holm rejects.
4. **Large negative and positive intervals share a scale.** Use one common scale
   covering every confidence bound and label exact medians in the source bundle;
   do not clip extreme intervals.
5. **Multiple tests invite cherry-picking.** Show every one of the 20 frozen
   primary metric comparisons in a fixed 5 × 4 grid.

## Legend draft

**Fig. F4 | Frozen function-level resource comparison.** **a,** Median relative
improvement of Resource-NMCTS over five baselines for logical T and CNOT counts
and mapped native two-qubit count and depth; points show medians and bars show
deterministic 95% percentile-bootstrap confidence intervals. Positive values
favour Resource-NMCTS. Filled teal points satisfy family-Holm rejection, a
strictly negative upper confidence bound for the raw median difference, and a
strictly positive lower confidence bound for median relative improvement;
hollow grey points do not, and zero-touching is non-strict. **b,** Audit matrix reports Resource-NMCTS
win/tie/loss counts and family-Holm-adjusted p-values for the same comparisons.
Independent Boolean functions are the inference units after median aggregation
over three strictly paired seeds (7, 17 and 29); n=20 except SSHR-Beam (n=18,
because all three seeds for two AES functions reached the 300 s synthesis
timeout). Confidence
intervals use 20,000 deterministic bootstrap resamples (seed 202609). Source data
are provided as CSV and JSON files.

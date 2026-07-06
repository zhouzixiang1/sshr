# Paper LaTeX Draft

Working title:

> Resource-NMCTS: Neural Monte Carlo Tree Search with Affine Boolean Preconditioning for Resource-Constrained Quantum Oracle Synthesis

This folder is the manuscript workspace for the resource-constrained quantum
Boolean oracle synthesis project.  The draft is intentionally evidence-first:
claims in `main.tex` are limited to the current `evidence_affine`,
`ablation_affine`, `traditional_resource`, `resource_sweep`,
`large_resource_core`, `highdim_resource`, `highdim_scale_resource`,
`ultra_highdim_resource`, and exported SSHR/ABC/BDD/LUT/ESOP baseline results.

Build:

```bash
latexmk -pdf main.tex
```

Current source evidence:

- experiment CSV: `../results/raw_evidence_affine.csv`
- compact analysis: `../results/analysis_evidence_affine.md`
- ablation CSV: `../results/raw_ablation_affine.csv`
- compact ablation analysis: `../results/analysis_ablation_affine.md`
- runtime/resource analysis: `../results/runtime_ablation_affine.md`
- neural-prior ablation CSV: `../results/raw_neural_prior_ablation.csv`
- neural-prior ablation analysis:
  `../results/analysis_neural_prior_ablation.md`
- traditional baseline CSV: `../results/raw_traditional_resource.csv`
- traditional baseline analysis: `../results/analysis_traditional_resource.md`
- traditional runtime/resource analysis:
  `../results/runtime_traditional_resource.md`
- external exact SSHR-I pilot CSV:
  `../results/raw_external_traditional_resource_n4.csv`
- external exact SSHR-I pilot analysis:
  `../results/analysis_external_traditional_resource_n4.md`
- external time-limited SSHR-I plus ABC-AIG/ABC-XAG/ABC-LUT/BDD/ABC-ESOP extension CSV:
  `../results/raw_external_traditional_resource_n6.csv`
- external time-limited SSHR-I plus ABC-AIG/ABC-XAG/ABC-LUT/BDD/ABC-ESOP extension analysis:
  `../results/analysis_external_traditional_resource_n6.md`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD CSV:
  `../results/raw_external_highdim_resource.csv`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD analysis:
  `../results/analysis_external_highdim_resource.md`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD scale CSV:
  `../results/raw_external_highdim_scale_resource.csv`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD scale analysis:
  `../results/analysis_external_highdim_scale_resource.md`
- resource-sweep CSV: `../results/raw_resource_sweep.csv`
- resource-sweep analysis: `../results/analysis_resource_sweep.md`
- large-scale core CSV: `../results/raw_large_resource_core.csv`
- large-scale core analysis: `../results/analysis_large_resource_core.md`
- large-scale core runtime/resource analysis:
  `../results/runtime_large_resource_core.md`
- high-dimensional stress CSV: `../results/raw_highdim_resource.csv`
- high-dimensional stress analysis: `../results/analysis_highdim_resource.md`
- high-dimensional stress runtime/resource analysis:
  `../results/runtime_highdim_resource.md`
- high-dimensional scaling CSV: `../results/raw_highdim_scale_resource.csv`
- high-dimensional scaling analysis:
  `../results/analysis_highdim_scale_resource.md`
- high-dimensional scaling runtime/resource analysis:
  `../results/runtime_highdim_scale_resource.md`
- ultra-high-dimensional scaling CSV:
  `../results/raw_ultra_highdim_resource.csv`
- ultra-high-dimensional scaling analysis:
  `../results/analysis_ultra_highdim_resource.md`
- ultra-high-dimensional scaling runtime/resource analysis:
  `../results/runtime_ultra_highdim_resource.md`
- external-tool benchmark exporter: `../export_benchmarks.py`
- LaTeX tables: `tables/runtime_ablation_affine.tex`,
  `tables/resource_ablation_affine.tex`,
  `tables/neural_prior_ablation.tex`,
  `tables/resource_traditional_resource.tex`,
  `tables/runtime_traditional_resource.tex`,
  `tables/resource_sweep_affine.tex`,
  `tables/resource_sweep_resource.tex`,
  `tables/resource_sweep_winners.tex`,
  `tables/resource_large_resource_core.tex`,
  `tables/runtime_large_resource_core.tex`,
  `tables/resource_highdim_resource.tex`,
  `tables/runtime_highdim_resource.tex`,
  `tables/resource_highdim_scale_resource.tex`,
  `tables/runtime_highdim_scale_resource.tex`,
  `tables/resource_ultra_highdim_resource.tex`,
  `tables/runtime_ultra_highdim_resource.tex`,
  `tables/external_traditional_resource_n6.tex`,
  `tables/external_highdim_abc_aig.tex`
- manifests: `../results/manifest_evidence_affine.json`,
  `../results/manifest_traditional_resource_no_prior.json`,
  `../results/manifest_highdim_resource.json`,
  `../results/manifest_highdim_scale_resource.json`,
  `../results/manifest_ultra_highdim_resource.json`,
  `../results/manifest_external_traditional_resource_n4.json`,
  `../results/manifest_external_traditional_resource_n6.json`,
  `../results/manifest_external_highdim_resource.json`,
  `../results/manifest_external_highdim_scale_resource.json`

Known manuscript gaps:

- add reproduced non-ABC/non-LUT/non-BDD high-dimensional external baselines where
  runtime allows; ABC-ESOP is stable on `n <= 6` but times out on complex
  high-dimensional examples;
- extend the external high-dimensional comparison to the `n=16`
  `ultra_highdim_resource` suite if ABC/BDD runtimes remain practical;
- add reproduced ROS or mockturtle-style reversible-toolchain results;
- decide the target venue and required reference/section style.

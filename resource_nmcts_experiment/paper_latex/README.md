# Paper LaTeX Draft

Working title:

> Resource-NMCTS: Neural Monte Carlo Tree Search with Affine Boolean Preconditioning for Resource-Constrained Quantum Oracle Synthesis

This folder is the manuscript workspace for the resource-constrained quantum
Boolean oracle synthesis project.  The draft is intentionally evidence-first:
claims in `main.tex` are limited to the current `evidence_affine`,
`ablation_affine`, `traditional_resource`, `resource_sweep`, and
`large_resource_core` results.

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
- traditional baseline CSV: `../results/raw_traditional_resource.csv`
- traditional baseline analysis: `../results/analysis_traditional_resource.md`
- traditional runtime/resource analysis:
  `../results/runtime_traditional_resource.md`
- resource-sweep CSV: `../results/raw_resource_sweep.csv`
- resource-sweep analysis: `../results/analysis_resource_sweep.md`
- large-scale core CSV: `../results/raw_large_resource_core.csv`
- large-scale core analysis: `../results/analysis_large_resource_core.md`
- large-scale core runtime/resource analysis:
  `../results/runtime_large_resource_core.md`
- LaTeX tables: `tables/runtime_ablation_affine.tex`,
  `tables/resource_ablation_affine.tex`,
  `tables/resource_traditional_resource.tex`,
  `tables/runtime_traditional_resource.tex`,
  `tables/resource_sweep_affine.tex`,
  `tables/resource_sweep_resource.tex`,
  `tables/resource_sweep_winners.tex`,
  `tables/resource_large_resource_core.tex`,
  `tables/runtime_large_resource_core.tex`
- manifest: `../results/manifest_evidence_affine.json`

Known manuscript gaps:

- verify all BibTeX metadata against publisher/arXiv records before submission;
- decide the target venue and required reference/section style.

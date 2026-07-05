# Paper LaTeX Draft

Working title:

> Neural Monte Carlo Tree Search with Affine Boolean Preconditioning for Resource-Constrained Quantum Oracle Synthesis

This folder is the manuscript workspace for the resource-constrained quantum
Boolean oracle synthesis project.  The draft is intentionally evidence-first:
claims in `main.tex` are limited to the current `evidence_affine` results.

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
- LaTeX tables: `tables/runtime_ablation_affine.tex`,
  `tables/resource_ablation_affine.tex`
- manifest: `../results/manifest_evidence_affine.json`

Known manuscript gaps:

- verify all BibTeX metadata against publisher/arXiv records before submission;
- decide the target venue and required reference/section style.

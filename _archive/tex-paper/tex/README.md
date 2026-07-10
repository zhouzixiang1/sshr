# tex/ — LaTeX Paper Source

This directory contains the LaTeX source files, figures, and bibliography for the paper.

## Files

- `main_template.tex` — Main paper source file
- `ref.bib` — Bibliography
- `gbt7714-numerical.bst` — Chinese citation style (GB/T 7714)
- `CjC.cls` — Journal document class
- `captionhack.sty` — Caption formatting patch
- `picins.sty` — Picture insertion macros

## Figures

- `figure/` — Paper figures referenced by `main_template.tex`
  - `CCCG_D/` — CCCG/CCCX gate diagrams
  - `S=N/` — S=N curve plots (active figures: `S=NCNOT.png`, `S=NCNOTns.png`)
  - `cnot_*.png` — CNOT cost comparison plots
  - `heavyhex.png`, `square.png` — Architecture diagrams
  - `step1.png`, `step2.png` — Synthesis pipeline illustrations
  - `circuit_n4_s5.png` — Example circuit diagram
- Archive directories (local only, not tracked by git):
  - `固定N/`, `固定S/` — Historical figure variants

## Building

```bash
cd tex
xelatex -output-directory=build main_template.tex
bibtex main_template
xelatex -output-directory=build main_template.tex
xelatex -output-directory=build main_template.tex
```

> **Note**: The `build/` directory is excluded from git via `.gitignore`. Do not commit auxiliary files (`.aux`, `.bbl`, `.blg`, `.log`, `.synctex*`) or the generated PDF.

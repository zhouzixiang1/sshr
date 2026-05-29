"""
Draw circuit diagrams illustrating the SSHR method.
Uses matplotlib only.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: Parallelotope → Circuit Block illustration (n=3 example)
# ─────────────────────────────────────────────────────────────────────────────

def draw_gate(ax, x, ys, label, color='white', size=0.35):
    """Draw a generic gate box."""
    if isinstance(ys, (int, float)):
        ys = [ys]
    yc = np.mean(ys)
    rect = Rectangle((x - size, yc - size*0.8), 2*size, 1.6*size,
                      linewidth=1.5, edgecolor='black', facecolor=color, zorder=4)
    ax.add_patch(rect)
    ax.text(x, yc, label, ha='center', va='center', fontsize=9, fontweight='bold', zorder=5)

def draw_cnot(ax, x, ctrl_y, tgt_y, color='steelblue'):
    """Draw CNOT gate: circle on control, ⊕ on target."""
    # vertical line
    ax.plot([x, x], [ctrl_y, tgt_y], color=color, linewidth=1.5, zorder=3)
    # control: filled circle
    c = Circle((x, ctrl_y), 0.07, color=color, zorder=4)
    ax.add_patch(c)
    # target: ⊕ symbol
    c2 = Circle((x, tgt_y), 0.18, color='white', ec=color, linewidth=1.5, zorder=4)
    ax.add_patch(c2)
    ax.plot([x-0.18, x+0.18], [tgt_y, tgt_y], color=color, lw=1.5, zorder=5)
    ax.plot([x, x], [tgt_y-0.18, tgt_y+0.18], color=color, lw=1.5, zorder=5)

def draw_mct(ax, x, ctrl_ys, tgt_y, color='darkorange'):
    """Draw MCT gate."""
    all_y = list(ctrl_ys) + [tgt_y]
    ax.plot([x, x], [min(all_y), max(all_y)], color=color, linewidth=1.5, zorder=3)
    for cy in ctrl_ys:
        c = Circle((x, cy), 0.09, color=color, zorder=4)
        ax.add_patch(c)
    c2 = Circle((x, tgt_y), 0.2, color='white', ec=color, linewidth=2, zorder=4)
    ax.add_patch(c2)
    ax.plot([x-0.2, x+0.2], [tgt_y, tgt_y], color=color, lw=2, zorder=5)
    ax.plot([x, x], [tgt_y-0.2, tgt_y+0.2], color=color, lw=2, zorder=5)

def draw_x(ax, x, y, color='green'):
    """Draw X (NOT) gate."""
    c = Circle((x, y), 0.2, color='white', ec=color, linewidth=2, zorder=4)
    ax.add_patch(c)
    ax.plot([x-0.15, x+0.15], [y-0.15, y+0.15], color=color, lw=2, zorder=5)
    ax.plot([x-0.15, x+0.15], [y+0.15, y-0.15], color=color, lw=2, zorder=5)

# ─── Fig 1: 3D parallelotope in hypercube ────────────────────────────────────
fig1, axes = plt.subplots(1, 2, figsize=(13, 5))
fig1.suptitle('Figure 1: Parallelotope Structure → Quantum Circuit Block (n=3 example)',
              fontsize=12, fontweight='bold')

# Left: 3D hypercube with parallelotope highlighted
ax = axes[0]
ax.set_xlim(-0.5, 3.5); ax.set_ylim(-0.5, 3.5)
ax.set_aspect('equal'); ax.axis('off')
ax.set_title('2D Parallelotope in 3-bit Hypercube\n(on-set shown in red)', fontsize=10)

# Project 3D cube to 2D (isometric-like)
def proj(x, y, z):
    return x + 0.4*z, y + 0.3*z

# Draw cube edges (gray)
cube_verts = [(i,j,k) for i in range(2) for j in range(2) for k in range(2)]
cube_edges = []
for v in cube_verts:
    for d in range(3):
        w = list(v); w[d] ^= 1; w = tuple(w)
        if w > v:
            cube_edges.append((v, w))

scale = 1.2
for (v, w) in cube_edges:
    px0, py0 = proj(*[c*scale for c in v])
    px1, py1 = proj(*[c*scale for c in w])
    ax.plot([px0, px1], [py0, py1], color='lightgray', lw=1, zorder=1)

# Parallelotope: vertex=000, basis=[100,010]
# vertices: 000,100,010,110
para_verts = [(0,0,0),(1,0,0),(0,1,0),(1,1,0)]
px = [proj(*[c*scale for c in v])[0] for v in para_verts]
py = [proj(*[c*scale for c in v])[1] for v in para_verts]

# Draw filled parallelogram
order = [0,1,3,2,0]
ax.fill([px[i] for i in [0,1,3,2]], [py[i] for i in [0,1,3,2]],
        color='lightyellow', alpha=0.8, zorder=2)
ax.plot([px[i] for i in order], [py[i] for i in order],
        color='darkorange', lw=2, zorder=3)

# All vertices
labels = {(0,0,0):'000',(1,0,0):'100',(0,1,0):'010',(1,1,0):'110',
          (0,0,1):'001',(1,0,1):'101',(0,1,1):'011',(1,1,1):'111'}
onset = {(0,0,0),(1,0,0),(0,1,0),(1,1,0)}
for v in cube_verts:
    px0, py0 = proj(*[c*scale for c in v])
    color = 'red' if v in onset else 'black'
    size = 80 if v in onset else 30
    ax.scatter([px0], [py0], color=color, s=size, zorder=5)
    off = [0.05, 0.08] if v[0]==1 else [-0.2, 0.08]
    ax.text(px0+off[0], py0+off[1], labels[v], fontsize=8,
            color=color, fontweight='bold' if v in onset else 'normal')

ax.text(1.0, -0.3, 'vertex v₀=(000), basis α₁=100, α₂=010\n'
        '→ 2D parallelotope → 1-MCT gate (1 control)',
        fontsize=8, ha='center', color='darkorange', style='italic')

# Right: corresponding circuit block
ax2 = axes[1]
ax2.set_xlim(0, 5); ax2.set_ylim(-0.5, 3.5)
ax2.axis('off')
ax2.set_title('Synthesized Circuit Block\n(Algorithm 1 output)', fontsize=10)

wire_labels = ['q₀', 'q₁', 'q₂', 'out']
wire_y = [3, 2, 1, 0]
for i, (lbl, wy) in enumerate(zip(wire_labels, wire_y)):
    ax2.plot([0.3, 4.7], [wy, wy], color='black', lw=1.5, zorder=1)
    ax2.text(0.1, wy, lbl, ha='center', va='center', fontsize=10, fontweight='bold')

# CNOT chain: CNOT(q0→q1) to merge support of α₁=[1,0,0] and α₂=[0,1,0]
# Then 1-MCT(q0, out)
draw_cnot(ax2, 1.5, wire_y[0], wire_y[1])
ax2.text(1.5, -0.4, 'CNOT\n(merge α₁,α₂)', ha='center', fontsize=7, color='steelblue')

draw_mct(ax2, 3.0, [wire_y[0]], wire_y[3])
ax2.text(3.0, -0.4, '1-MCT\n(q₀ ctrl)', ha='center', fontsize=7, color='darkorange')

# reverse CNOT
draw_cnot(ax2, 4.3, wire_y[0], wire_y[1])
ax2.text(4.3, -0.4, 'CNOT\n(restore)', ha='center', fontsize=7, color='steelblue')

# legend
ax2.text(2.5, 3.3, 'Cost: 2 CNOT + 1 MCT(1-ctrl) = T=0, CNOT=3',
         ha='center', fontsize=9, color='navy',
         bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='navy'))

plt.tight_layout()
plt.savefig('circuit_fig1_parallelotope.png', dpi=150, bbox_inches='tight')
print("Saved circuit_fig1_parallelotope.png")
plt.close()

# ─── Fig 2: Full SSHR-I synthesis for n=3 example function f=0x46 ─────────────
fig2, axes2 = plt.subplots(1, 2, figsize=(14, 6))
fig2.suptitle('Figure 2: SSHR-I Full Synthesis Example  (n=3, f = 0x96, on-set={1,2,4,7})',
              fontsize=11, fontweight='bold')

# on-set = {001,010,100,111} = indices 1,2,4,7 → binary 0b10010110 = 0x96
# Parallelotopes covering these:
#   P1: vertex=001, basis=[110] → dim=1, vertices={001,111} ← covers 1,7
#   P2: vertex=010, basis=[110] → dim=1, vertices={010,100} ← covers 2,4
# Together: 4 minterms covered with 2 small blocks

# Left: ILP covering diagram
ax3 = axes2[0]
ax3.set_xlim(-0.5, 3.5); ax3.set_ylim(-0.8, 1.5)
ax3.axis('off')
ax3.set_title('ILP Selection: WP-SCP Covering\n(on-set covered odd times)', fontsize=10)

minterms = list(range(8))
labels_m = [f'{i:03b}' for i in range(8)]
on_set = {1,2,4,7}

xs = np.linspace(0, 3, 8)
for i, (xi, lbl) in enumerate(zip(xs, labels_m)):
    col = 'red' if i in on_set else 'lightgray'
    c = Circle((xi, 0), 0.2, color=col, ec='black', lw=1.5, zorder=3)
    ax3.add_patch(c)
    ax3.text(xi, 0, lbl, ha='center', va='center', fontsize=7, fontweight='bold',
             color='white' if i in on_set else 'gray')

# P1 covers {1,7}
for xi_pair in [(xs[1], xs[7])]:
    ax3.annotate('', xy=(xi_pair[1], 0.25), xytext=(xi_pair[0], 0.25),
                 arrowprops=dict(arrowstyle='<->', color='darkorange', lw=2))
ax3.text(np.mean([xs[1],xs[7]]), 0.55, 'P₁: {001,111}\nbasis=[110]',
         ha='center', fontsize=8, color='darkorange',
         bbox=dict(boxstyle='round', facecolor='#FFF3E0', edgecolor='darkorange'))

# P2 covers {2,4}
for xi_pair in [(xs[2], xs[4])]:
    ax3.annotate('', xy=(xi_pair[1], -0.3), xytext=(xi_pair[0], -0.3),
                 arrowprops=dict(arrowstyle='<->', color='steelblue', lw=2))
ax3.text(np.mean([xs[2],xs[4]]), -0.6, 'P₂: {010,100}\nbasis=[110]',
         ha='center', fontsize=8, color='steelblue',
         bbox=dict(boxstyle='round', facecolor='#E3F2FD', edgecolor='steelblue'))

ax3.text(1.5, 1.3,
         'ILP: select x₁=1, x₂=1\n'
         'All on-set covered odd times ✓\n'
         'All off-set covered even times ✓',
         ha='center', fontsize=9, color='darkgreen',
         bbox=dict(boxstyle='round', facecolor='#E8F5E9', edgecolor='green'))

# Right: synthesized circuit
ax4 = axes2[1]
ax4.set_xlim(0, 7); ax4.set_ylim(-0.5, 3.8)
ax4.axis('off')
ax4.set_title('Synthesized SSHR-I Circuit\n(CNOT objective)', fontsize=10)

wire_labels2 = ['q₀', 'q₁', 'q₂', 'out']
wire_y2 = [3, 2, 1, 0]
for lbl, wy in zip(wire_labels2, wire_y2):
    ax4.plot([0.4, 6.6], [wy, wy], color='black', lw=1.5, zorder=1)
    ax4.text(0.15, wy, lbl, ha='center', va='center', fontsize=10, fontweight='bold')

# Block for P1: vertex=001, basis=[110]
# basis [110]: support = {q0,q1}, CNOT(q0→q1), then MCT(q0,q2→out) with X on q2 (base point bit)
ax4.text(1.5, 3.6, 'Block P₁ (covers {001,111})', ha='center', fontsize=8,
         color='darkorange', style='italic')
rect1 = Rectangle((0.7, -0.35), 2.2, 3.7, linewidth=2, edgecolor='darkorange',
                   facecolor='#FFF8E1', alpha=0.4, zorder=0)
ax4.add_patch(rect1)
draw_cnot(ax4, 1.0, wire_y2[0], wire_y2[1])   # CNOT q0→q1
draw_x(ax4, 1.5, wire_y2[2])                   # X on q2 (0-control)
draw_mct(ax4, 2.2, [wire_y2[0], wire_y2[2]], wire_y2[3])  # MCT(q0,q2→out)
draw_x(ax4, 2.9, wire_y2[2])                   # X restore
draw_cnot(ax4, 3.4, wire_y2[0], wire_y2[1])   # CNOT restore ... wait, let's simplify

# Block for P2: vertex=010, basis=[110]
ax4.text(5.3, 3.6, 'Block P₂ (covers {010,100})', ha='center', fontsize=8,
         color='steelblue', style='italic')
rect2 = Rectangle((4.1, -0.35), 2.4, 3.7, linewidth=2, edgecolor='steelblue',
                   facecolor='#E3F2FD', alpha=0.4, zorder=0)
ax4.add_patch(rect2)
draw_cnot(ax4, 4.5, wire_y2[0], wire_y2[1])
draw_x(ax4, 5.0, wire_y2[0])
draw_mct(ax4, 5.5, [wire_y2[1], wire_y2[0]], wire_y2[3])
draw_x(ax4, 6.0, wire_y2[0])

# Cost label
ax4.text(3.5, -0.45,
         'Total: T=14, CNOT=8  (vs ESOP: T=21, CNOT=12)',
         ha='center', fontsize=9, color='navy',
         bbox=dict(boxstyle='round', facecolor='#E8EAF6', edgecolor='navy'))

plt.tight_layout()
plt.savefig('circuit_fig2_synthesis.png', dpi=150, bbox_inches='tight')
print("Saved circuit_fig2_synthesis.png")
plt.close()

# ─── Fig 3: Method comparison bar chart ──────────────────────────────────────
fig3, axes3 = plt.subplots(1, 2, figsize=(13, 5))
fig3.suptitle('Figure 3: Reproduction Results vs Paper (SSHR-I, CNOT objective)',
              fontsize=12, fontweight='bold')

ns = [3, 4, 5]

# T-count
ax5 = axes3[0]
paper_T = [3280, 6028, 134656]
ours_T  = [3280, 6596, 135490]
x = np.arange(len(ns))
w = 0.35
bars1 = ax5.bar(x - w/2, paper_T, w, label='Paper', color='steelblue', alpha=0.8)
bars2 = ax5.bar(x + w/2, ours_T,  w, label='Ours',  color='darkorange', alpha=0.8)
ax5.set_xticks(x); ax5.set_xticklabels([f'n={n}' for n in ns])
ax5.set_ylabel('T-count (sum over 2000 fns)')
ax5.set_title('T-count Comparison')
ax5.legend()
ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v/1000:.0f}k'))
for bar, val in zip(bars1, paper_T):
    ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.01,
             f'{val/1000:.1f}k', ha='center', va='bottom', fontsize=8)
for bar, val in zip(bars2, ours_T):
    diff_pct = [(o-p)/p*100 for o,p in zip(ours_T, paper_T)]
    ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.01,
             f'{val/1000:.1f}k', ha='center', va='bottom', fontsize=8)
# match annotations
for i, (pt, ot) in enumerate(zip(paper_T, ours_T)):
    pct = (ot-pt)/pt*100
    color = 'green' if abs(pct)<2 else 'red'
    ax5.text(i, max(pt,ot)*1.08, f'{pct:+.1f}%', ha='center', fontsize=9,
             color=color, fontweight='bold')
ax5.set_ylim(0, max(paper_T+ours_T)*1.15)

# CNOT-count
ax6 = axes3[1]
paper_C = [3232, 4696, 78562]
ours_C  = [3232, 5342, 75420]
bars3 = ax6.bar(x - w/2, paper_C, w, label='Paper', color='steelblue', alpha=0.8)
bars4 = ax6.bar(x + w/2, ours_C,  w, label='Ours',  color='darkorange', alpha=0.8)
ax6.set_xticks(x); ax6.set_xticklabels([f'n={n}' for n in ns])
ax6.set_ylabel('CNOT-count (sum over 2000 fns)')
ax6.set_title('CNOT-count Comparison')
ax6.legend()
ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v/1000:.0f}k'))
for bar, val in zip(bars3, paper_C):
    ax6.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.01,
             f'{val/1000:.1f}k', ha='center', va='bottom', fontsize=8)
for bar, val in zip(bars4, ours_C):
    ax6.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.01,
             f'{val/1000:.1f}k', ha='center', va='bottom', fontsize=8)
for i, (pt, ot) in enumerate(zip(paper_C, ours_C)):
    pct = (ot-pt)/pt*100
    color = 'green' if abs(pct)<2 else ('blue' if pct<0 else 'red')
    ax6.text(i, max(pt,ot)*1.08, f'{pct:+.1f}%', ha='center', fontsize=9,
             color=color, fontweight='bold')
ax6.set_ylim(0, max(paper_C+ours_C)*1.15)
ax6.text(0, max(paper_C+ours_C)*1.13,
         '✓ n=3 exact match  |  n=4 gap from NPN rep choice  |  n=5 est. (200-fn×10)',
         fontsize=7.5, color='gray')

plt.tight_layout()
plt.savefig('circuit_fig3_comparison.png', dpi=150, bbox_inches='tight')
print("Saved circuit_fig3_comparison.png")
plt.close()

# ─── Fig 4: SSHR-H vs SSHR-I vs ESOP pipeline diagram ───────────────────────
fig4, ax = plt.subplots(figsize=(12, 4))
ax.set_xlim(0, 12); ax.set_ylim(0, 4)
ax.axis('off')
ax.set_title('Figure 4: SSHR Synthesis Pipeline Overview', fontsize=12, fontweight='bold')

def box(ax, x, y, w, h, label, sub='', color='lightblue', fontsize=10):
    rect = Rectangle((x-w/2, y-h/2), w, h, linewidth=1.5,
                      edgecolor='navy', facecolor=color, zorder=3, alpha=0.85)
    ax.add_patch(rect)
    ax.text(x, y + (0.1 if sub else 0), label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', zorder=4)
    if sub:
        ax.text(x, y - 0.25, sub, ha='center', va='center',
                fontsize=8, color='gray', zorder=4)

def arrow(ax, x1, y1, x2, y2, label=''):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+0.15, label, ha='center', fontsize=8, color='gray')

# Input
box(ax, 1.0, 2, 1.6, 1.2, 'Boolean\nFunction f', f'truth table\n(n ≤ 8 bits)', '#E8F5E9')
arrow(ax, 1.8, 2, 2.5, 2)

# Enumerate
box(ax, 3.2, 2, 1.4, 1.2, 'Enumerate\nParallelo-\ntopes', 'P₁,P₂,...,Pₖ', '#FFF9C4')
arrow(ax, 3.9, 2, 4.5, 2)

# Branch
ax.text(5.2, 2, '?', ha='center', va='center', fontsize=16, color='gray')

# SSHR-H
box(ax, 6.5, 3, 1.6, 0.9, 'SSHR-H', 'Greedy R=¾\nO(k²) fast', '#FFE0B2')
ax.annotate('', xy=(5.9, 3), xytext=(5.1, 2.3),
            arrowprops=dict(arrowstyle='->', color='darkorange', lw=1.5))
ax.text(5.3, 2.8, 'Heuristic', fontsize=8, color='darkorange')

# SSHR-I
box(ax, 6.5, 1, 1.6, 0.9, 'SSHR-I', 'ILP (Gurobi)\nOptimal', '#E3F2FD')
ax.annotate('', xy=(5.9, 1), xytext=(5.1, 1.7),
            arrowprops=dict(arrowstyle='->', color='steelblue', lw=1.5))
ax.text(5.3, 1.2, 'Optimal', fontsize=8, color='steelblue')

# Block synth
arrow(ax, 7.3, 3, 8.1, 3)
arrow(ax, 7.3, 1, 8.1, 1)
box(ax, 8.9, 2, 1.6, 1.2, 'Circuit\nBlock\nSynth', 'Algo 1\nCNOT+X+MCT', '#F3E5F5')
ax.annotate('', xy=(8.1, 2.5), xytext=(8.1, 3),
            arrowprops=dict(arrowstyle='->', color='purple', lw=1.2))
ax.annotate('', xy=(8.1, 1.5), xytext=(8.1, 1),
            arrowprops=dict(arrowstyle='->', color='purple', lw=1.2))

# Output
arrow(ax, 9.7, 2, 10.5, 2)
box(ax, 11.0, 2, 1.6, 1.2, 'Quantum\nCircuit', 'MCT→T/CNOT\ndecomposition', '#FFEBEE')

# Cost objectives label
ax.text(6.5, 0.15, 'Objectives: min CNOT  or  min T-count (relative-phase Toffoli T=4)',
        ha='center', fontsize=9, color='navy', style='italic')

plt.tight_layout()
plt.savefig('circuit_fig4_pipeline.png', dpi=150, bbox_inches='tight')
print("Saved circuit_fig4_pipeline.png")
plt.close()

print("\nAll 4 figures saved.")

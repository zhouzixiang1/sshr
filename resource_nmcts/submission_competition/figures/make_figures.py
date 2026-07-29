# -*- coding: utf-8 -*-
"""
竞赛级图表生成脚本（挑战杯 XA-202609 量子+AI 双向赋能）
==========================================================
从 resource_nmcts/results/ 下的真实实验 summary/raw CSV 生成 8 张图（F1–F8），
每张同时输出 .pdf 与 .png（dpi=200）。所有数字均来自 CSV 实读，
运行时将每张图对应的聚合表打印到 stdout 供审计。

运行方式（Git Bash）：
    cd /d/University/code/sshr/resource_nmcts && \
    KMP_DUPLICATE_LIB_OK=TRUE C:\\Users\\32143\\.conda\\envs\\mcts-qoracle\\python.exe \
        submission_competition/figures/make_figures.py
"""
import torch  # noqa: F401  必须先于任何 qiskit 系导入（本机 DLL 加载顺序约束）

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------- 全局样式
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", font="Microsoft YaHei")
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]  # set_theme 后再保险一次

ROOT = Path(__file__).resolve().parents[2]          # resource_nmcts/
RESULTS = ROOT / "results"
OUTDIR = ROOT / "submission_competition" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)
DPI = 200

# 方法中文名映射（仅用于图例展示）
METHOD_ZH = {
    "direct_anf": "Direct ANF（朴素展开）",
    "and_direct_anf": "AND-Direct ANF",
    "sshr_h": "SSHR-H（基线）",
    "and_mcts_factor": "Fixed MCTS",
    "and_affine_nmcts": "Affine-NMCTS",
    "and_affine_greedy": "Affine-Greedy（消融）",
    "and_affine_no_guard": "Affine-NMCTS 无守卫（消融）",
    "and_resource_nmcts": "Resource-NMCTS（本文）",
    "and_pareto_resource_nmcts": "Pareto-Resource-NMCTS（本文）",
    "and_profile_resource_nmcts": "Profile-Resource-NMCTS（本文）",
    "and_resource_nmcts_screen_gate": "Resource-NMCTS+屏幕门控（本文）",
    "and_resource_no_mcts": "Resource 无 MCTS（消融）",
    "and_resource_beam_only": "Resource 仅束搜索（消融）",
    "and_resource_heuristic": "Resource 纯启发式（消融）",
    "and_cube_beam": "ESOP Cube Beam（基线）",
    "and_esop_milp": "ESOP-MILP（基线）",
    "and_fprm_polarity_archive": "FPRM 极性归档",
    "and_fprm_greedy": "FPRM-Greedy",
    "and_fprm_linear_pair": "FPRM 线性对",
    "and_fprm_linear_pair_deep": "FPRM 线性对-深",
    "and_fprm_linear_pair_deep_ai_guard": "FPRM 线性对-深+AI守卫",
    "and_fprm_linear_pair_deep_root_neural": "FPRM 线性对-深+根神经",
    "and_fprm_root_beam": "FPRM 根束搜索",
    "and_boolean_linear_pair_screen": "布尔线性对+屏幕",
    "and_boolean_linear_pair_screen_adaptive": "布尔线性对+自适应屏幕",
}
OURS = {"and_resource_nmcts", "and_pareto_resource_nmcts", "and_profile_resource_nmcts",
        "and_resource_nmcts_screen_gate", "and_affine_nmcts"}


def zh(method: str) -> str:
    return METHOD_ZH.get(method, method)


def save(fig: plt.Figure, name: str):
    pdf = OUTDIR / f"{name}.pdf"
    png = OUTDIR / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=DPI)
    plt.close(fig)
    print(f"  [已保存] {pdf}\n           {png}")


def audit(title: str, df: pd.DataFrame):
    print(f"\n{'=' * 78}\n[审计表] {title}\n{'=' * 78}")
    print(df.to_string(index=False))


def load_summary(name: str) -> pd.DataFrame:
    df = pd.read_csv(RESULTS / name)
    df["source_csv"] = name
    return df


# ---------------------------------------------------------------- 基准族聚合
# 四个基准族：传统小规模(n=3–6)、高维(n=14)、超高维(n=16)、门保持(n=19–20)
FAMILY_FILES = {
    "传统小规模\n(n=3–6, 177函数)": "summary_traditional_resource.csv",
    "高维\n(n=14, 64函数)": "summary_highdim_resource.csv",
    "超高维\n(n=16, 24函数)": "summary_ultra_highdim_resource.csv",
    "门保持\n(n=19–20, 16函数)": "summary_gate_holdout_resource.csv",
}


def aggregate_family(csv_name: str) -> pd.DataFrame:
    """按 method 聚合一个族内所有 n 行：T/CNOT 用函数数加权平均，depth/score 同理。"""
    df = load_summary(csv_name)
    rows = []
    for m, g in df.groupby("method"):
        f = g["functions"].sum()
        rows.append({
            "method": m,
            "functions": int(f),
            "mean_T": (g["total_T"] ).sum() / f,
            "mean_CNOT": (g["total_CNOT"]).sum() / f,
            "mean_depth": (g["mean_depth"] * g["functions"]).sum() / f,
            "mean_score": (g["mean_score"] * g["functions"]).sum() / f,
            "mean_ancilla": (g["mean_peak_ancilla"] * g["functions"]).sum() / f,
        })
    return pd.DataFrame(rows).sort_values("mean_T").reset_index(drop=True)


family_tables = {fam: aggregate_family(csv) for fam, csv in FAMILY_FILES.items()}
for fam, t in family_tables.items():
    audit(f"基准族聚合 — {fam.replace(chr(10), ' ')}（来源: {FAMILY_FILES[fam]}）",
          t.round(2))


# ---------------------------------------------------------------- F1: 平均 T 数
def family_bar_figure(metric: str, ylabel: str, title: str, fname: str):
    fig, axes = plt.subplots(1, 4, figsize=(17, 5.2), sharey=False)
    palette = sns.color_palette("viridis", 12)
    for ax, (fam, tbl) in zip(axes, family_tables.items()):
        tbl = tbl.copy()
        colors = ["#d62728" if m in OURS else "#4c72b0" for m in tbl["method"]]
        ax.bar(range(len(tbl)), tbl[metric], color=colors)
        ax.set_yscale("log")
        ax.set_title(fam, fontsize=11)
        ax.set_xticks(range(len(tbl)))
        ax.set_xticklabels([zh(m) for m in tbl["method"]], rotation=38,
                           ha="right", fontsize=8)
        ax.set_ylabel(ylabel if ax is axes[0] else "")
        for i, v in enumerate(tbl[metric]):
            ax.text(i, v * 1.12, f"{v:,.0f}", ha="center", va="bottom",
                    fontsize=7, rotation=90)
    import matplotlib.patches as mpatches
    fig.legend(handles=[mpatches.Patch(color="#d62728", label="本文方法"),
                        mpatches.Patch(color="#4c72b0", label="基线/消融方法")],
               loc="upper right", fontsize=10)
    fig.suptitle(title, fontsize=14, y=1.02)
    fig.tight_layout()
    save(fig, fname)


family_bar_figure("mean_T", "平均每函数 T 门数（对数轴）",
                  "F1  各基准族平均每函数 T 门数对比（越低越好）", "F1_tcount_by_family")
family_bar_figure("mean_CNOT", "平均每函数 CNOT 门数（对数轴）",
                  "F2  各基准族平均每函数 CNOT 门数对比（越低越好）", "F2_cnot_by_family")
family_bar_figure("mean_depth", "平均每函数线路深度（对数轴）",
                  "F3  各基准族平均每函数线路深度对比（越低越好）", "F3_depth_by_family")

# F2 附：传统族平均总门数（raw_traditional_resource.csv 含 gates 列，summary 无）
raw_trad = pd.read_csv(RESULTS / "raw_traditional_resource.csv")
raw_trad_ok = raw_trad[raw_trad["correct"] == True]  # noqa: E712
gates_tbl = (raw_trad_ok.groupby("method")["gates"].mean()
             .reset_index().rename(columns={"gates": "mean_gates"})
             .sort_values("mean_gates").reset_index(drop=True))
audit("传统小规模族平均每函数总门数（来源: raw_traditional_resource.csv）",
      gates_tbl.round(2))
fig, ax = plt.subplots(figsize=(9.5, 4.6))
colors = ["#d62728" if m in OURS else "#4c72b0" for m in gates_tbl["method"]]
ax.bar(range(len(gates_tbl)), gates_tbl["mean_gates"], color=colors)
ax.set_xticks(range(len(gates_tbl)))
ax.set_xticklabels([zh(m) for m in gates_tbl["method"]], rotation=30, ha="right", fontsize=9)
ax.set_ylabel("平均每函数总门数（X+CNOT+MCT 展开）")
ax.set_title("F2b  传统小规模基准族（n=3–6）平均每函数总门数对比")
for i, v in enumerate(gates_tbl["mean_gates"]):
    ax.text(i, v * 1.01, f"{v:,.1f}", ha="center", va="bottom", fontsize=8)
fig.tight_layout()
save(fig, "F2b_gates_traditional")

# ---------------------------------------------------------------- F4: 相对最强基线的改进率
imp_rows = []
for fam, tbl in family_tables.items():
    ours_tbl = tbl[tbl["method"].isin(OURS)]
    base_tbl = tbl[~tbl["method"].isin(OURS)]
    if ours_tbl.empty or base_tbl.empty:
        continue
    our_best = ours_tbl.loc[ours_tbl["mean_T"].idxmin()]
    base_best = base_tbl.loc[base_tbl["mean_T"].idxmin()]
    imp = (base_best["mean_T"] - our_best["mean_T"]) / base_best["mean_T"] * 100
    imp_rows.append({
        "family": fam.replace("\n", " "), "our_method": our_best["method"],
        "our_T": our_best["mean_T"], "baseline": base_best["method"],
        "baseline_T": base_best["mean_T"], "improvement_pct": imp,
    })
imp_df = pd.DataFrame(imp_rows)
audit("F4 本文最优方法 vs 各基准族最强基线的 T 门改进率", imp_df.round(2))

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(imp_df["family"], imp_df["improvement_pct"],
              color=sns.color_palette("rocket", len(imp_df)))
for b, (_, r) in zip(bars, imp_df.iterrows()):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.6,
            f"{r['improvement_pct']:.1f}%", ha="center", fontsize=12,
            fontweight="bold")
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() / 2,
            f"对比基线:\n{zh(r['baseline'])}", ha="center", va="center",
            fontsize=8, color="white")
ax.set_ylabel("T 门数降低比例（%）")
ax.set_title("F4  本文最优方法相对各基准族最强基线的 T 门改进率")
ax.set_ylim(0, max(imp_df["improvement_pct"]) * 1.25)
fig.tight_layout()
save(fig, "F4_improvement_vs_best_baseline")

# ---------------------------------------------------------------- F5: 可扩展性
abl = load_summary("summary_ablation_affine.csv")
abl["mean_T"] = abl["total_T"] / abl["functions"]
scale_methods = ["direct_anf", "sshr_h", "and_direct_anf", "and_mcts_factor",
                 "and_affine_greedy", "and_affine_nmcts"]
scale_tbl = abl[abl["method"].isin(scale_methods)][["method", "n", "mean_T", "functions"]]
audit("F5 可扩展性：各方法平均每函数 T 门数随 n 变化（来源: summary_ablation_affine.csv）",
      scale_tbl.round(2))

fig, ax = plt.subplots(figsize=(9, 5.6))
for m in scale_methods:
    g = scale_tbl[scale_tbl["method"] == m].sort_values("n")
    style = "-" if m in OURS else "--"
    ax.plot(g["n"], g["mean_T"], style, marker="o", ms=5, lw=2 if m in OURS else 1.4,
            label=zh(m))
ax.set_yscale("log")
ax.set_xlabel("输入比特数 n")
ax.set_ylabel("平均每函数 T 门数（对数轴）")
ax.set_title("F5  可扩展性：T 门数随输入规模 n 的增长曲线（n=3–12）")
ax.legend(fontsize=9)
fig.tight_layout()
save(fig, "F5_scalability_T_vs_n")

# ---------------------------------------------------------------- F6: Pareto 权衡散点
trad_tbl = family_tables["传统小规模\n(n=3–6, 177函数)"].copy()
audit("F6 Pareto 散点数据（传统族 method 级平均，来源: summary_traditional_resource.csv）",
      trad_tbl.round(2))

fig, ax = plt.subplots(figsize=(8.6, 6))
xs, ys = trad_tbl["mean_CNOT"].values, trad_tbl["mean_T"].values
colors = ["#d62728" if m in OURS else "#4c72b0" for m in trad_tbl["method"]]
ax.scatter(xs, ys, s=90, c=colors, zorder=3, edgecolors="black", linewidths=0.6)
for _, r in trad_tbl.iterrows():
    ax.annotate(zh(r["method"]), (r["mean_CNOT"], r["mean_T"]),
                textcoords="offset points", xytext=(7, 5), fontsize=8.5)
# Pareto 前沿（双目标最小化：CNOT 与 T）
pts = sorted(zip(xs, ys))
frontier, best_y = [], np.inf
for x, y in pts:
    if y < best_y:
        frontier.append((x, y))
        best_y = y
fx, fy = zip(*frontier)
ax.step(list(fx) + [max(xs) * 1.05], list(fy) + [fy[-1]], where="post",
        color="#d62728", lw=1.6, ls=":", label="Pareto 前沿（双目标最小化）")
ax.set_xlabel("平均每函数 CNOT 门数")
ax.set_ylabel("平均每函数 T 门数")
ax.set_title("F6  传统小规模基准族（n=3–6）T 门–CNOT 双目标权衡")
ax.legend(fontsize=9)
fig.tight_layout()
save(fig, "F6_pareto_T_vs_CNOT")

# ---------------------------------------------------------------- F7: 消融实验
search_abl = load_summary("summary_search_ablation_traditional.csv")
search_abl["mean_T"] = search_abl["total_T"] / search_abl["functions"]
ab_methods = ["and_resource_nmcts", "and_resource_no_mcts",
              "and_resource_beam_only", "and_resource_heuristic"]
ab_tbl = search_abl[search_abl["method"].isin(ab_methods)][["method", "n", "mean_T"]]
audit("F7a 搜索组件消融（来源: summary_search_ablation_traditional.csv）", ab_tbl.round(2))

affine_tbl = abl[abl["method"].isin(
    ["and_affine_nmcts", "and_affine_no_guard", "and_affine_greedy"])]
affine_tbl = affine_tbl[affine_tbl["n"].isin([6, 8, 10, 12])][["method", "n", "mean_T"]]
audit("F7b 仿射搜索消融（来源: summary_ablation_affine.csv）", affine_tbl.round(2))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))
piv = ab_tbl.pivot(index="n", columns="method", values="mean_T")[ab_methods]
piv.plot(kind="bar", ax=ax1, color=sns.color_palette("Set2", len(ab_methods)))
ax1.set_yscale("log")
ax1.set_xlabel("输入比特数 n")
ax1.set_ylabel("平均每函数 T 门数（对数轴）")
ax1.set_title("F7a  搜索组件消融：MCTS / 束搜索 / 启发式")
ax1.set_xticklabels([str(n) for n in piv.index], rotation=0)
ax1.legend([zh(m) for m in piv.columns], fontsize=8)
piv2 = affine_tbl.pivot(index="n", columns="method", values="mean_T")[
    ["and_affine_nmcts", "and_affine_no_guard", "and_affine_greedy"]]
piv2.plot(kind="bar", ax=ax2, color=sns.color_palette("Set1", 3))
ax2.set_yscale("log")
ax2.set_xlabel("输入比特数 n")
ax2.set_ylabel("平均每函数 T 门数（对数轴）")
ax2.set_title("F7b  仿射搜索消融：神经引导 / 无守卫 / 纯贪心")
ax2.set_xticklabels([str(n) for n in piv2.index], rotation=0)
ax2.legend([zh(m) for m in piv2.columns], fontsize=8)
fig.suptitle("F7  关键组件消融实验", fontsize=14)
fig.tight_layout()
save(fig, "F7_ablation")

# ---------------------------------------------------------------- F8: AES S-box 案例
aes = pd.read_csv(RESULTS / "summary_aes_sbox.csv")
audit("F8 AES S-box 逐输出位对比（来源: summary_aes_sbox.csv）", aes)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
x = np.arange(len(aes))
w = 0.38
ax1.bar(x - w / 2, aes["direct_T"], w, label="AND-Direct ANF（基线）", color="#4c72b0")
ax1.bar(x + w / 2, aes["resource_T"], w, label="Resource-NMCTS（本文）", color="#d62728")
for i, (d, r) in enumerate(zip(aes["direct_T"], aes["resource_T"])):
    ax1.text(i - w / 2, d + 12, str(d), ha="center", fontsize=8)
    ax1.text(i + w / 2, r + 12, str(r), ha="center", fontsize=8)
ax1.set_xticks(x)
ax1.set_xticklabels([f"bit {b}" for b in aes["bit"]])
ax1.set_xlabel("AES S-box 输出位")
ax1.set_ylabel("T 门数")
ax1.set_title("F8a  AES S-box 各输出位 Oracle 的 T 门数")
ax1.legend(fontsize=9)
bars = ax2.bar(x, aes["improvement_pct"], color=sns.color_palette("rocket", len(aes)))
mean_imp = aes["improvement_pct"].mean()
ax2.axhline(mean_imp, color="black", ls="--", lw=1.2,
            label=f"平均 {mean_imp:.1f}%")
for b, v in zip(bars, aes["improvement_pct"]):
    ax2.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}%",
             ha="center", fontsize=9, fontweight="bold")
ax2.set_xticks(x)
ax2.set_xticklabels([f"bit {b}" for b in aes["bit"]])
ax2.set_xlabel("AES S-box 输出位")
ax2.set_ylabel("T 门数降低比例（%）")
ax2.set_title("F8b  相对基线的 T 门改进率（全部 8 位验证正确）")
ax2.set_ylim(0, max(aes["improvement_pct"]) * 1.25)
ax2.legend(fontsize=9)
fig.suptitle("F8  AES S-box（8 比特密码学基准）案例研究", fontsize=14)
fig.tight_layout()
save(fig, "F8_aes_sbox_case_study")

print(f"\n全部完成。输出目录: {OUTDIR}")

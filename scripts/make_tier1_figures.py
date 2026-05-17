"""Generate matplotlib PNG figures for the tinyvm_dataset.md doc.

Reads docs/stats/tier1_stats.json, writes PNGs to docs/figures/.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np

STATS = Path("docs/stats/tier1_stats.json")
FIG_DIR = Path("docs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Color palette — colorblind-safe.
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
          "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22"]


def fig1_op_frequency(stats: dict) -> None:
    """Horizontal bar chart of op usage across the entire dataset."""
    agg = stats["aggregate_op_freq"]
    ops = list(agg.keys())
    counts = list(agg.values())
    # Sort by count desc
    order = np.argsort(counts)[::-1]
    ops = [ops[i] for i in order]
    counts = [counts[i] for i in order]
    total = sum(counts)
    pcts = [100 * c / total for c in counts]

    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.35 * len(ops))))
    y = np.arange(len(ops))
    ax.barh(y, counts, color=COLORS[0], edgecolor="black", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(ops)
    ax.invert_yaxis()
    ax.set_xlabel("count (across all train + eval programs)")
    ax.set_title(f"Tier 1 — Op frequency across {total:,} instructions")
    # Annotate counts + percentages.
    for i, (c, p) in enumerate(zip(counts, pcts)):
        ax.text(c + max(counts) * 0.01, i, f"{c:,} ({p:.1f}%)", va="center", fontsize=9)
    ax.set_xlim(0, max(counts) * 1.22)
    ax.spines[["right", "top"]].set_visible(False)
    fig.tight_layout()
    out = FIG_DIR / "tier1_op_frequency.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"wrote {out}")


def fig2_program_length_dist(stats: dict) -> None:
    """Histogram of program lengths in the train sample."""
    raw = stats["splits"]["train"]["program_length_raw"]
    arr = np.array(raw)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.arange(arr.min(), arr.max() + 2) - 0.5
    ax.hist(arr, bins=bins, color=COLORS[0], edgecolor="black", linewidth=0.5)
    ax.set_xlabel("program length (instructions, including PRINT + HALT)")
    ax.set_ylabel("count (train sample)")
    train_summary = stats["splits"]["train"]["program_length"]
    ax.set_title(
        f"Tier 1 train — program length distribution\n"
        f"sampled axes: n ~ Uniform{{8..32}} → actual: min={train_summary['min']}, "
        f"max={train_summary['max']}, mean={train_summary['mean']:.1f}"
    )
    ax.axvline(train_summary["p50"], color="black", linestyle="--",
               label=f"median = {train_summary['p50']}")
    ax.legend()
    ax.spines[["right", "top"]].set_visible(False)
    fig.tight_layout()
    out = FIG_DIR / "tier1_program_length.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"wrote {out}")


def fig3_token_length_per_bucket(stats: dict) -> None:
    """Box plot of input + target token IDs lengths per eval bucket."""
    bucket_order = ["eval_len_8", "eval_len_16", "eval_len_32", "eval_len_48",
                    "eval_len_64", "eval_len_96", "eval_len_128"]
    # Use raw arrays for box plots
    input_data = []
    target_data = []
    labels = []
    for name in bucket_order:
        if name not in stats["splits"]:
            continue
        s = stats["splits"][name]
        input_data.append(s["input_id_len_raw"])
        target_data.append(s["target_id_len_raw"])
        labels.append(name.replace("eval_", ""))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    bp1 = ax1.boxplot(input_data, tick_labels=labels, patch_artist=True,
                      boxprops=dict(facecolor=COLORS[0], alpha=0.6),
                      medianprops=dict(color="black"))
    ax1.set_title("Input token IDs length (program tokens)")
    ax1.set_ylabel("tokens")
    ax1.set_xlabel("eval bucket")
    ax1.grid(axis="y", alpha=0.3)
    ax1.spines[["right", "top"]].set_visible(False)

    bp2 = ax2.boxplot(target_data, tick_labels=labels, patch_artist=True,
                      boxprops=dict(facecolor=COLORS[1], alpha=0.6),
                      medianprops=dict(color="black"))
    ax2.set_title("Target token IDs length (output stream)")
    ax2.set_ylabel("tokens")
    ax2.set_xlabel("eval bucket")
    ax2.grid(axis="y", alpha=0.3)
    ax2.spines[["right", "top"]].set_visible(False)

    fig.suptitle("Tier 1 — Token sequence length per eval bucket (direct render mode)",
                 y=1.02, fontsize=12)
    fig.tight_layout()
    out = FIG_DIR / "tier1_token_lengths_per_bucket.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def fig4_register_usage(stats: dict) -> None:
    """Bar chart of register-write frequency for R0..R7, aggregated across splits."""
    agg: dict[int, int] = {i: 0 for i in range(8)}
    for split_name, s in stats["splits"].items():
        for r_str, count in s["register_writes"].items():
            agg[int(r_str)] += count
    regs = list(range(8))
    counts = [agg[r] for r in regs]
    total = sum(counts)

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar([f"R{r}" for r in regs], counts, color=COLORS[2],
                   edgecolor="black", linewidth=0.6)
    ax.set_ylabel("writes (count across all analysed rows)")
    ax.set_title(
        f"Tier 1 — Register write distribution\n"
        f"Expected uniform-ish: gen_register_trace samples k regs / program from R0..R7"
    )
    for bar, c in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, c + total * 0.005,
                f"{100 * c / total:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, max(counts) * 1.12)
    ax.spines[["right", "top"]].set_visible(False)
    fig.tight_layout()
    out = FIG_DIR / "tier1_register_writes.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"wrote {out}")


def fig5_per_bucket_program_length_violin(stats: dict) -> None:
    """Mini panel: per-bucket program length distribution (should be tight at n+2)."""
    bucket_order = ["eval_len_8", "eval_len_16", "eval_len_32", "eval_len_48",
                    "eval_len_64", "eval_len_96", "eval_len_128"]
    labels = []
    means = []
    mins = []
    maxs = []
    for name in bucket_order:
        if name not in stats["splits"]:
            continue
        pl = stats["splits"][name]["program_length"]
        labels.append(name.replace("eval_", ""))
        means.append(pl["mean"])
        mins.append(pl["min"])
        maxs.append(pl["max"])

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(labels))
    width = 0.4
    ax.bar(x, means, width, color=COLORS[3], edgecolor="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("eval bucket (axis n)")
    ax.set_ylabel("instructions per program (PRINT + HALT included)")
    ax.set_title("Tier 1 eval buckets — actual program length\n(n is the count of body instructions; +2 for PRINT + HALT)")
    for i, (mn, mx, mean) in enumerate(zip(mins, maxs, means)):
        ax.text(i, mean + max(maxs) * 0.01,
                f"{int(mean)}",
                ha="center", fontsize=9)
    ax.spines[["right", "top"]].set_visible(False)
    fig.tight_layout()
    out = FIG_DIR / "tier1_program_length_per_bucket.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"wrote {out}")


def main():
    stats = json.loads(STATS.read_text())
    fig1_op_frequency(stats)
    fig2_program_length_dist(stats)
    fig3_token_length_per_bucket(stats)
    fig4_register_usage(stats)
    fig5_per_bucket_program_length_violin(stats)
    print(f"\n✓ All figures written to {FIG_DIR}/")


if __name__ == "__main__":
    main()

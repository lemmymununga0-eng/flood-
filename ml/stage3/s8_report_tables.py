"""Stage 3, step 8 — the results tables (§28, §29), generated from the result files.

Every number in the paper's tables should come from here, not from a human retyping them.
Missing results are shown as NOT EVALUATED, never filled in (§29).

    python ml/stage3/s8_report_tables.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402


def f(x, nd=4):
    return "n/a" if x is None or pd.isna(x) else f"{x:.{nd}f}"


def main() -> None:
    p = C.S3_OUT_REPORTS / "rolling_origin_results.csv"
    if not p.exists():
        raise SystemExit("no results yet")
    res = pd.read_csv(p)
    ok = res[res.status == "ok"].dropna(subset=["pr_auc"])
    done = sorted(int(h) for h in ok.horizon.unique())
    md = ["# Stage 3 results (generated)\n",
          f"Horizons with results: {', '.join('H+%d' % h for h in done) or 'none'}. "
          "Metrics are means over leave-one-year-out folds; PR-AUC is the primary metric.\n"]

    # ---- §28 model comparison, per horizon ----
    for h in done:
        hh = ok[ok.horizon == h]
        base = hh[hh.kind == "baseline"].groupby("fold_year").pr_auc.max()
        rows = []
        for (nm, fs), g in hh[hh.kind == "model"].groupby(["name", "features"]):
            g = g.set_index("fold_year")
            c = g.index.intersection(base.index)
            if not len(c):
                continue
            rows.append({"Model": nm, "Features": fs, "Folds": len(c),
                         "PR-AUC": g.pr_auc[c].mean(), "ROC-AUC": g.roc_auc[c].mean(),
                         "Precision": g.precision[c].mean(), "Recall": g.recall[c].mean(),
                         "F1": g.f1[c].mean(), "Specificity": g.specificity[c].mean(),
                         "NPV": g.npv[c].mean(), "Brier": g.brier[c].mean(),
                         "Wins vs baseline": f"{int((g.pr_auc[c] > base[c]).sum())}/{len(c)}"})
        bl = (hh[hh.kind == "baseline"].groupby("name")
              [["pr_auc", "roc_auc", "recall", "specificity"]].mean()
              .sort_values("pr_auc", ascending=False))
        md.append(f"\n## H+{h}\n")
        md.append("### Baselines (no machine learning)\n")
        md.append(bl.round(5).to_markdown())
        md.append("\n### Models\n")
        if rows:
            md.append(pd.DataFrame(rows).sort_values("PR-AUC", ascending=False)
                      .round(5).to_markdown(index=False))

    # ---- §29 horizon summary ----
    md.append("\n## Horizon summary (§29)\n")
    sel_path = C.S3_OUT_REPORTS / "selection_decision.json"
    sel = json.loads(sel_path.read_text()) if sel_path.exists() else {}
    hdr = ("| Horizon | Best model | PR-AUC | ROC-AUC | Recall | Specificity | "
           "Best baseline PR-AUC | Beats baseline? | Gate decision |\n"
           "|---|---|---:|---:|---:|---:|---:|---|---|")
    lines = [hdr]
    for h in C.S3_HORIZONS:
        if h not in done:
            lines.append(f"| H+{h} | NOT EVALUATED | | | | | | | |")
            continue
        hh = ok[ok.horizon == h]
        base = hh[hh.kind == "baseline"].groupby("name").pr_auc.mean().sort_values(ascending=False)
        m = hh[hh.kind == "model"].groupby(["name", "features"])[
            ["pr_auc", "roc_auc", "recall", "specificity"]].mean().sort_values(
            "pr_auc", ascending=False)
        if m.empty:
            lines.append(f"| H+{h} | no model folds | | | | | | | |")
            continue
        (nm, fs), r = m.index[0], m.iloc[0]
        dec = sel.get("horizons", {}).get(f"h{h}", {}).get("decision", "not yet assessed")
        beats = "yes" if r.pr_auc > base.iloc[0] else "NO"
        lines.append(f"| H+{h} | {nm} / {fs} | {f(r.pr_auc)} | {f(r.roc_auc)} | "
                     f"{f(r.recall)} | {f(r.specificity)} | {f(base.iloc[0])} | "
                     f"{beats} | {dec} |")
    md.append("\n".join(lines))

    out = C.S3_OUT_REPORTS / "results_tables.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

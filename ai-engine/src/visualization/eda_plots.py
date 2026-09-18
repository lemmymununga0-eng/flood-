"""
visualization/eda_plots.py
===========================
Exploratory Data Analysis (EDA) visualisations for FloodShield-Zambia.

Why EDA?
---------
Before training any model, you must understand your data.  EDA helps you:
  1. Identify data quality issues (outliers, gaps, impossible values)
  2. Understand the distribution of each variable
  3. Discover correlations between features
  4. Understand seasonality patterns relevant to Zambia's rainy season
  5. Identify class imbalance in the labels
  6. Communicate data insights to supervisors and examiners

Plots generated
---------------
- Histograms for all features
- Correlation heatmap
- Monthly rainfall trends
- Time-series plots for key variables
- Seasonality analysis (rainy vs dry season)
- Missing data heatmap
- Class balance bar chart
- Feature importance from Random Forest (tree-based, pre-SHAP)
- Outlier detection (boxplots)

Usage
-----
    from src.visualization.eda_plots import EDAPlotter
    plotter = EDAPlotter(df)
    plotter.run_full_eda()
"""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.dpi": 120,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
})


class EDAPlotter:
    """
    Generates a complete suite of EDA visualisations.

    Parameters
    ----------
    df : pd.DataFrame
        The feature-engineered DataFrame (with DatetimeIndex).
    figures_dir : Path
        Directory to save all plot files.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        figures_dir: Path = settings.figures_dir,
    ) -> None:
        self.df = df
        self._figures_dir = figures_dir
        self._numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_full_eda(self) -> None:
        """Run all EDA plots and save them to the figures directory."""
        logger.info(f"Running full EDA | {len(self.df)} rows, {len(self._numeric_cols)} features")

        self.plot_missing_data()
        self.plot_class_balance()
        self.plot_histograms()
        self.plot_correlation_heatmap()
        self.plot_rainfall_timeseries()
        self.plot_monthly_analysis()
        self.plot_seasonality()
        self.plot_boxplots()

        logger.info(f"EDA complete. All plots saved to {self._figures_dir}")

    def plot_missing_data(self, save: bool = True) -> plt.Figure:
        """
        Heatmap showing the location and density of missing values.

        Helps identify: temporal gaps, sensor failures, API outages.
        White = data present, coloured = missing.
        """
        missing = self.df[self._numeric_cols].isna()
        missing_pct = missing.mean().sort_values(ascending=False)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))

        # Bar chart of missing %
        ax1.barh(missing_pct.index, missing_pct.values * 100, color="#DC2626")
        ax1.set_xlabel("Missing Values (%)")
        ax1.set_title("Missing Data by Feature", fontsize=13)
        ax1.axvline(5, color="k", linestyle="--", alpha=0.5, label="5% threshold")
        ax1.legend()

        # Heatmap (sample every 30 days for readability)
        sampled = missing.iloc[::30]
        im = ax2.imshow(sampled.T, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1)
        ax2.set_yticks(range(len(sampled.columns)))
        ax2.set_yticklabels(sampled.columns, fontsize=7)
        ax2.set_xlabel("Time (every 30 days)")
        ax2.set_title("Missing Data Heatmap (sampled)", fontsize=13)

        fig.suptitle("Missing Data Analysis", fontsize=15, y=1.01)
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_missing_data.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Missing data plot saved to {path}")

        return fig

    def plot_class_balance(self, save: bool = True) -> Optional[plt.Figure]:
        """
        Bar chart showing Flood vs No-Flood class distribution.

        Class imbalance is the rule, not the exception, in disaster data.
        This plot motivates our use of class_weight='balanced'.
        """
        if "flood_label" not in self.df.columns:
            logger.warning("No 'flood_label' column for class balance plot.")
            return None

        counts = self.df["flood_label"].value_counts().sort_index()
        labels = ["No Flood (0)", "Flood (1)"]
        colours = ["#059669", "#DC2626"]

        fig, ax = plt.subplots(figsize=(6, 5))
        bars = ax.bar(labels, counts.values, color=colours, width=0.5, edgecolor="none")

        for bar, count in zip(bars, counts.values):
            pct = count / counts.sum() * 100
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 50,
                f"{count:,}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=11,
            )

        ax.set_ylabel("Number of days")
        ax.set_title("Class Balance: Flood vs No-Flood Days", fontsize=13)
        ax.set_ylim(0, counts.max() * 1.2)
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_class_balance.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Class balance plot saved to {path}")

        return fig

    def plot_histograms(self, save: bool = True) -> plt.Figure:
        """
        Histograms for all numerical features.

        Shows the distribution of each variable.  Rainfall is typically
        right-skewed (most days have little rain, few days have heavy rain).
        This justifies using RobustScaler over StandardScaler.
        """
        raw_cols = [c for c in ["prectotcorr", "t2m", "rh2m", "ws2m",
                                 "gwetroot", "gwetprof", "allsky_sfc_sw_dwn"]
                    if c in self.df.columns]

        n_cols = 3
        n_rows = (len(raw_cols) + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, n_rows * 4))
        axes = axes.flatten()

        for i, col in enumerate(raw_cols):
            axes[i].hist(
                self.df[col].dropna(), bins=50,
                color="#2563EB", edgecolor="white", alpha=0.8,
            )
            axes[i].set_title(col, fontsize=11)
            axes[i].set_xlabel("Value")
            axes[i].set_ylabel("Frequency")

        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        fig.suptitle("Feature Distributions — FloodShield Zambia", fontsize=15, y=1.01)
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_histograms.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Histograms saved to {path}")

        return fig

    def plot_correlation_heatmap(self, save: bool = True) -> plt.Figure:
        """
        Pearson correlation heatmap for all numerical features.

        Reveals multicollinearity (e.g. T2M and T2M_MAX are likely correlated).
        High correlation between a feature and flood_label signals predictive power.
        """
        try:
            import seaborn as sns
        except ImportError:
            logger.warning("Seaborn not installed. Using matplotlib for heatmap.")
            sns = None

        corr_cols = [c for c in self._numeric_cols if c in self.df.columns][:25]
        corr = self.df[corr_cols].corr()

        fig, ax = plt.subplots(figsize=(14, 12))

        if sns:
            sns.heatmap(
                corr,
                ax=ax,
                cmap="RdBu_r",
                center=0,
                vmin=-1, vmax=1,
                annot=False,
                fmt=".2f",
                linewidths=0.5,
                square=True,
            )
        else:
            im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=90, fontsize=8)
            ax.set_yticklabels(corr.columns, fontsize=8)
            fig.colorbar(im, ax=ax, shrink=0.8)

        ax.set_title(
            "Pearson Correlation Matrix — Top 25 Features", fontsize=13, pad=12
        )
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_correlation_heatmap.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Correlation heatmap saved to {path}")

        return fig

    def plot_rainfall_timeseries(self, save: bool = True) -> plt.Figure:
        """
        Time-series plot of daily rainfall with flood events highlighted.

        Zambia has a distinct rainy season (November to April).  This plot
        makes that seasonality immediately visible.
        """
        if "prectotcorr" not in self.df.columns:
            logger.warning("prectotcorr column missing. Skipping rainfall plot.")
            return plt.figure()

        fig, ax = plt.subplots(figsize=(16, 5))
        ax.fill_between(
            self.df.index,
            self.df["prectotcorr"],
            color="#2563EB",
            alpha=0.6,
            label="Daily Rainfall (mm)",
        )

        if "flood_label" in self.df.columns:
            flood_days = self.df[self.df["flood_label"] == 1]
            ax.scatter(
                flood_days.index,
                flood_days["prectotcorr"],
                color="#DC2626",
                s=10,
                zorder=5,
                alpha=0.6,
                label="Flood Event",
            )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_xlabel("Date")
        ax.set_ylabel("Rainfall (mm/day)")
        ax.set_title(
            "Daily Rainfall Time-Series with Flood Events — Zambia",
            fontsize=13,
        )
        ax.legend(loc="upper right")
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_rainfall_timeseries.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Rainfall time-series saved to {path}")

        return fig

    def plot_monthly_analysis(self, save: bool = True) -> plt.Figure:
        """
        Monthly average rainfall bar chart.

        Shows the sharp contrast between Zambia's wet season (Nov–Apr)
        and dry season (May–Oct).  This contextualises our seasonal feature.
        """
        if "prectotcorr" not in self.df.columns:
            return plt.figure()

        monthly = self.df["prectotcorr"].groupby(self.df.index.month).mean()
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        colours = [
            "#DC2626" if m in [11, 12, 1, 2, 3, 4] else "#059669"
            for m in range(1, 13)
        ]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(months, monthly.values, color=colours, edgecolor="none", width=0.7)
        ax.set_xlabel("Month")
        ax.set_ylabel("Average Daily Rainfall (mm)")
        ax.set_title(
            "Monthly Average Rainfall — Zambia\n"
            "(Red = Rainy Season, Green = Dry Season)",
            fontsize=13,
        )

        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#DC2626", label="Rainy Season (Nov–Apr)"),
            Patch(facecolor="#059669", label="Dry Season (May–Oct)"),
        ]
        ax.legend(handles=legend_elements)
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_monthly_rainfall.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Monthly rainfall saved to {path}")

        return fig

    def plot_seasonality(self, save: bool = True) -> plt.Figure:
        """
        Boxplot of rainfall by month showing seasonality spread.

        Shows not just the mean but the variability of rainfall per month.
        High variance in the rainy season months reflects inter-annual
        variability (e.g. El Niño years have drier than average conditions
        in southern Africa).
        """
        if "prectotcorr" not in self.df.columns:
            return plt.figure()

        monthly_data = [
            self.df["prectotcorr"][self.df.index.month == m].dropna().values
            for m in range(1, 13)
        ]
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        fig, ax = plt.subplots(figsize=(12, 5))
        bp = ax.boxplot(monthly_data, labels=months, patch_artist=True, notch=False)

        rainy_months = {1, 2, 3, 4, 11, 12}
        for i, (patch, label) in enumerate(zip(bp["boxes"], months), start=1):
            colour = "#DC2626" if i in rainy_months else "#059669"
            patch.set_facecolor(colour)
            patch.set_alpha(0.6)

        ax.set_ylabel("Daily Rainfall (mm)")
        ax.set_title(
            "Rainfall Seasonality — Zambia (Monthly Boxplots)", fontsize=13
        )
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_seasonality_boxplot.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Seasonality boxplot saved to {path}")

        return fig

    def plot_boxplots(self, save: bool = True) -> plt.Figure:
        """
        Boxplots for outlier detection across raw meteorological variables.

        Outliers (points beyond the whiskers) represent extreme weather events.
        This informs our clipping thresholds in the cleaning step.
        """
        raw_cols = [c for c in ["prectotcorr", "t2m", "rh2m", "ws2m", "gwetroot"]
                    if c in self.df.columns]

        fig, axes = plt.subplots(1, len(raw_cols), figsize=(14, 5))
        if len(raw_cols) == 1:
            axes = [axes]

        for ax, col in zip(axes, raw_cols):
            ax.boxplot(
                self.df[col].dropna(),
                patch_artist=True,
                boxprops={"facecolor": "#BFDBFE"},
                medianprops={"color": "#DC2626", "linewidth": 2},
                whiskerprops={"color": "#374151"},
                flierprops={"marker": "o", "markerfacecolor": "#DC2626",
                             "markersize": 3, "alpha": 0.3},
            )
            ax.set_title(col, fontsize=11)
            ax.set_ylabel("Value")

        fig.suptitle("Outlier Detection — Key Meteorological Variables", fontsize=14)
        fig.tight_layout()

        if save:
            path = self._figures_dir / "eda_outlier_boxplots.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Outlier boxplots saved to {path}")

        return fig

"""
explainability/explain_models.py
=================================
Explainable AI (XAI) engine for FloodShield-Zambia using SHAP.

What is SHAP?
--------------
SHAP (SHapley Additive exPlanations) is a mathematically grounded method
for explaining machine learning model predictions.

It answers the question: **"Why did the model predict a flood today?"**

SHAP assigns each feature a contribution score (Shapley value) representing
how much it pushed the prediction above or below the average prediction.

Why is explainability critical for this project?
-------------------------------------------------
1. **Trust**: Zambia's disaster management officials will not act on a
   "black box" prediction.  They need to know WHY.

2. **Debugging**: If the model makes wrong predictions, SHAP helps identify
   which features are causing the error.

3. **Science**: The SHAP values show which meteorological variables matter
   most — this is a genuine scientific finding.

4. **Dissertation quality**: A model with explainability demonstrates
   understanding beyond just training a classifier.

Outputs generated
-----------------
1. **Global Feature Importance** — which features matter most across the
   entire dataset (bar chart of mean |SHAP| values)

2. **Summary Plot** — combined view of feature importance AND direction of
   effect (do high values push towards or away from flood prediction?)

3. **Waterfall Plot** — single prediction explanation showing step-by-step
   how each feature contributed to a specific flood prediction

4. **Dependence Plot** — how one feature's effect changes with its value
   (e.g. does rainfall effect increase linearly or has a threshold?)

5. **Force Plot** — interactive HTML explanation of a single prediction

Usage
-----
    from src.explainability.explain_models import SHAPExplainer
    explainer = SHAPExplainer(model, feature_names, X_train)
    explainer.compute_shap_values(X_test)
    explainer.plot_global_importance()
    explainer.plot_summary()
    explainer.plot_waterfall(sample_index=0)
"""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SHAPExplainer:
    """
    SHAP-based explainability engine for any scikit-learn or Keras classifier.

    Parameters
    ----------
    model : object
        A trained sklearn classifier (with predict_proba) or Keras model.
    feature_names : list[str]
        Names of the input features (used as axis labels in plots).
    X_background : np.ndarray
        A representative sample of training data used to initialise the
        SHAP explainer.  Typically 100–500 randomly sampled rows.
    figures_dir : Path
        Directory where plots are saved.
    model_type : str
        One of "tree" (for Random Forest / XGBoost) or "kernel" (for others).
        Tree explainers are faster and exact; Kernel explainers are model-agnostic.
    """

    def __init__(
        self,
        model,
        feature_names: list[str],
        X_background: np.ndarray,
        figures_dir: Path = settings.figures_dir,
        model_type: str = "tree",
    ) -> None:
        self.model = model
        self.feature_names = feature_names
        self.X_background = X_background
        self._figures_dir = figures_dir
        self.model_type = model_type
        self._shap_values: Optional[np.ndarray] = None
        self._explainer = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build_explainer(self) -> "SHAPExplainer":
        """
        Initialise the SHAP explainer based on model type.

        TreeExplainer works for tree-based models (Random Forest, XGBoost,
        Gradient Boosting) and is exact and fast.

        KernelExplainer works for any model but uses Monte Carlo sampling,
        so it is slower.  It is used for Logistic Regression and LSTM.

        Returns
        -------
        self
        """
        try:
            import shap
        except ImportError as exc:
            raise ImportError(
                "SHAP not installed. Install with: pip install shap"
            ) from exc

        logger.info(f"Building SHAP {self.model_type} explainer ...")

        if self.model_type == "tree":
            self._explainer = shap.TreeExplainer(
                self.model,
                feature_names=self.feature_names,
            )
        else:
            # KernelExplainer — use a smaller background sample for speed
            bg_sample = shap.sample(self.X_background, min(100, len(self.X_background)))
            self._explainer = shap.KernelExplainer(
                lambda x: self.model.predict_proba(x)[:, 1]
                if hasattr(self.model, "predict_proba")
                else self.model.predict(x).flatten(),
                bg_sample,
                feature_names=self.feature_names,
            )

        logger.info("SHAP explainer built ✓")
        return self

    def compute_shap_values(
        self,
        X: np.ndarray,
        max_samples: int = 500,
    ) -> np.ndarray:
        """
        Compute SHAP values for a set of input samples.

        SHAP values tell us how much each feature pushed each prediction
        above or below the baseline (average prediction).

        Parameters
        ----------
        X : np.ndarray
            Input feature matrix.  For KernelExplainer, limit to ~500
            samples for speed.
        max_samples : int
            Maximum samples to explain (KernelExplainer is slow for large N).

        Returns
        -------
        np.ndarray
            SHAP values array of shape (n_samples, n_features).
        """
        if self._explainer is None:
            self.build_explainer()

        X_explain = X[:max_samples] if len(X) > max_samples else X
        logger.info(f"Computing SHAP values for {len(X_explain)} samples ...")

        if self.model_type == "tree":
            self._shap_values = self._explainer.shap_values(X_explain)
            # For binary classifiers, TreeExplainer returns a list [class0, class1]
            if isinstance(self._shap_values, list):
                self._shap_values = self._shap_values[1]
        else:
            self._shap_values = self._explainer.shap_values(X_explain)

        self._X_explained = X_explain
        logger.info(
            f"SHAP values computed | shape: {self._shap_values.shape}"
        )
        return self._shap_values

    def plot_global_importance(
        self,
        top_n: int = 20,
        model_name: str = "Model",
        save: bool = True,
    ) -> plt.Figure:
        """
        Plot Global Feature Importance as a bar chart of mean |SHAP| values.

        This shows which features matter most ACROSS all predictions.
        The length of each bar is the average magnitude of that feature's
        SHAP value.

        Parameters
        ----------
        top_n : int
            Number of top features to display.
        model_name : str
        save : bool

        Returns
        -------
        matplotlib.figure.Figure
        """
        self._require_shap_values()

        mean_abs_shap = np.abs(self._shap_values).mean(axis=0)
        indices = np.argsort(mean_abs_shap)[-top_n:]
        selected_names = [self.feature_names[i] for i in indices]
        selected_values = mean_abs_shap[indices]

        fig, ax = plt.subplots(figsize=(9, 6))
        colours = ["#DC2626" if v > selected_values.mean() else "#2563EB"
                   for v in selected_values]
        ax.barh(selected_names, selected_values, color=colours, edgecolor="none")
        ax.set_xlabel("Mean |SHAP value| (impact on flood prediction)", fontsize=11)
        ax.set_title(
            f"Global Feature Importance — {model_name}\n"
            "(Larger bar = greater influence on flood prediction)",
            fontsize=13,
        )
        fig.tight_layout()

        if save:
            path = self._figures_dir / f"shap_global_importance_{model_name.lower()}.png"
            fig.savefig(path, bbox_inches="tight", dpi=150)
            logger.info(f"Global importance plot saved to {path}")

        return fig

    def plot_summary(
        self,
        top_n: int = 20,
        model_name: str = "Model",
        save: bool = True,
    ) -> None:
        """
        Generate a SHAP summary (beeswarm) plot.

        The summary plot shows both feature importance AND direction:
        - Features are ordered by importance (top = most important)
        - Each dot represents one prediction
        - Red dot = high feature value; Blue = low feature value
        - Dot position on x-axis = SHAP contribution to flood prediction

        This is one of the most informative plots in explainable AI.

        Parameters
        ----------
        top_n : int
        model_name : str
        save : bool
        """
        self._require_shap_values()

        try:
            import shap
        except ImportError:
            logger.warning("SHAP not installed. Cannot generate summary plot.")
            return

        fig, ax = plt.subplots(figsize=(10, 7))
        shap.summary_plot(
            self._shap_values,
            self._X_explained,
            feature_names=self.feature_names,
            max_display=top_n,
            show=False,
            plot_type="dot",
        )
        plt.title(f"SHAP Summary Plot — {model_name}", fontsize=13, pad=10)

        if save:
            path = self._figures_dir / f"shap_summary_{model_name.lower()}.png"
            plt.savefig(path, bbox_inches="tight", dpi=150)
            logger.info(f"SHAP summary plot saved to {path}")

        plt.close()

    def plot_waterfall(
        self,
        sample_index: int = 0,
        model_name: str = "Model",
        save: bool = True,
    ) -> None:
        """
        Generate a SHAP waterfall plot for a single prediction.

        The waterfall plot shows step-by-step how each feature pushed the
        prediction away from the baseline average.  It answers:
        "Why did the model predict a flood on THIS specific day?"

        Parameters
        ----------
        sample_index : int
            Which sample in X_explained to explain.
        model_name : str
        save : bool
        """
        self._require_shap_values()

        try:
            import shap
        except ImportError:
            logger.warning("SHAP not installed.")
            return

        if self._explainer is None:
            logger.warning("Explainer not built. Cannot create waterfall plot.")
            return

        expected_value = (
            self._explainer.expected_value[1]
            if isinstance(self._explainer.expected_value, (list, np.ndarray))
            else self._explainer.expected_value
        )

        explanation = shap.Explanation(
            values=self._shap_values[sample_index],
            base_values=expected_value,
            data=self._X_explained[sample_index],
            feature_names=self.feature_names,
        )

        plt.figure(figsize=(10, 7))
        shap.plots.waterfall(explanation, show=False)
        plt.title(
            f"SHAP Waterfall — {model_name} | Sample #{sample_index}",
            fontsize=12,
        )

        if save:
            path = self._figures_dir / f"shap_waterfall_{model_name.lower()}_s{sample_index}.png"
            plt.savefig(path, bbox_inches="tight", dpi=150)
            logger.info(f"Waterfall plot saved to {path}")

        plt.close()

    def plot_dependence(
        self,
        feature: str,
        model_name: str = "Model",
        save: bool = True,
    ) -> None:
        """
        Generate a SHAP dependence plot for one feature.

        This shows how that feature's contribution changes with its value.
        For example: "At what rainfall amount does flood risk start to
        increase dramatically?"

        Parameters
        ----------
        feature : str
            Feature name (must be in self.feature_names).
        model_name : str
        save : bool
        """
        self._require_shap_values()

        try:
            import shap
        except ImportError:
            logger.warning("SHAP not installed.")
            return

        if feature not in self.feature_names:
            logger.error(f"Feature '{feature}' not found in feature names.")
            return

        feat_idx = self.feature_names.index(feature)

        fig, ax = plt.subplots(figsize=(8, 5))
        shap.dependence_plot(
            feat_idx,
            self._shap_values,
            self._X_explained,
            feature_names=self.feature_names,
            ax=ax,
            show=False,
        )
        ax.set_title(
            f"SHAP Dependence: {feature} — {model_name}", fontsize=12
        )

        if save:
            safe_feat = feature.replace("/", "_").replace(" ", "_")
            path = self._figures_dir / f"shap_dependence_{model_name.lower()}_{safe_feat}.png"
            fig.savefig(path, bbox_inches="tight", dpi=150)
            logger.info(f"Dependence plot saved to {path}")

        plt.close(fig)

    def run_full_explanation(
        self,
        X_test: np.ndarray,
        model_name: str = "Model",
        top_features: int = 5,
    ) -> None:
        """
        Run the complete explainability pipeline.

        Generates global importance, summary, waterfall (for the first
        flood prediction), and dependence plots for the top 5 features.

        Parameters
        ----------
        X_test : np.ndarray
        model_name : str
        top_features : int
            Number of top features to generate dependence plots for.
        """
        logger.info(f"Running full SHAP explanation for {model_name} ...")

        self.compute_shap_values(X_test)
        self.plot_global_importance(model_name=model_name)
        self.plot_summary(model_name=model_name)

        # Waterfall for the highest-probability flood sample
        self.plot_waterfall(sample_index=0, model_name=model_name)

        # Dependence plots for top features by mean |SHAP|
        mean_abs = np.abs(self._shap_values).mean(axis=0)
        top_indices = np.argsort(mean_abs)[-top_features:][::-1]
        for idx in top_indices:
            feat = self.feature_names[idx]
            self.plot_dependence(feat, model_name=model_name)

        logger.info(f"Full SHAP explanation complete for {model_name} ✓")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_shap_values(self) -> None:
        """Raise an error if SHAP values have not been computed yet."""
        if self._shap_values is None:
            raise RuntimeError(
                "SHAP values not computed yet. "
                "Call compute_shap_values(X) first."
            )

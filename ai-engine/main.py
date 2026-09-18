"""
main.py
========
FloodShield-Zambia AI Engine — Master Orchestration Pipeline.

This is the single entry point for the entire AI training workflow.
Running this script executes all 9 phases in sequence:

  Phase 1: Architecture setup (already defined in src/)
  Phase 2: Data ingestion (NASA POWER API or synthetic fallback)
  Phase 3: Validation and cleaning
  Phase 4: Feature engineering and EDA
  Phase 5: Baseline model training and comparison
  Phase 6: LSTM training (requires Python 3.11 + TensorFlow)
  Phase 7: Full model evaluation and comparison
  Phase 8: SHAP explainability
  Phase 9: Production model export

Usage
-----
    # From the ai-engine directory:
    python main.py

    # Run only specific phases:
    python main.py --phases 1,2,3,4
    python main.py --use-synthetic    # Use synthetic data (no internet required)
    python main.py --skip-lstm        # Skip LSTM if TF not installed

Environment
-----------
    Python 3.11 required for LSTM (TensorFlow)
    Python 3.14 supported for all non-TF phases
    See README.md for full setup instructions.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config.settings import settings
from src.datasets.split_data import DataSplitter
from src.evaluation.metrics import ModelEvaluator
from src.features.build_features import FeatureEngineer
from src.ingestion.flood_events_ingestor import FloodEventsIngestor
from src.ingestion.nasa_power_ingestor import NASAPowerIngestor
from src.ingestion.synthetic_data_generator import SyntheticDataGenerator
from src.models.baselines import BaselineModelFactory
from src.preprocessing.clean_data import DataCleaner
from src.preprocessing.validation import DataValidator
from src.training.train_baselines import BaselineTrainer
from src.utils.experiment_tracker import ExperimentTracker
from src.utils.logger import get_logger
from src.utils.reproducibility import set_global_seed
from src.visualization.eda_plots import EDAPlotter

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="FloodShield-Zambia AI Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Full pipeline with API data
  python main.py --use-synthetic        # Full pipeline with synthetic data
  python main.py --phases 1,2,3,4      # Run only phases 1-4
  python main.py --skip-lstm            # Skip LSTM (no TensorFlow required)
        """,
    )
    parser.add_argument(
        "--use-synthetic",
        action="store_true",
        help="Use synthetic data (no internet required)",
    )
    parser.add_argument(
        "--skip-lstm",
        action="store_true",
        help="Skip LSTM training (run only baseline models)",
    )
    parser.add_argument(
        "--phases",
        type=str,
        default=None,
        help="Comma-separated list of phases to run (e.g. '1,2,3,4')",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=settings.training.random_seed,
        help=f"Random seed (default: {settings.training.random_seed})",
    )
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the full AI training pipeline."""

    start_time = time.time()
    set_global_seed(args.seed)

    active_phases = (
        [int(p) for p in args.phases.split(",")]
        if args.phases
        else list(range(1, 10))
    )

    logger.info("=" * 60)
    logger.info("FloodShield-Zambia AI Engine Starting")
    logger.info(f"Active phases: {active_phases}")
    logger.info(f"Use synthetic data: {args.use_synthetic}")
    logger.info(f"Skip LSTM: {args.skip_lstm}")
    logger.info(f"Random seed: {args.seed}")
    logger.info("=" * 60)

    # ================================================================
    # Phase 2: Data Ingestion
    # ================================================================
    if 2 in active_phases:
        logger.info("\n{'='*50}\nPHASE 2: Data Ingestion\n{'='*50}")

        if args.use_synthetic:
            logger.info("Using synthetic data generator (offline mode)")
            gen = SyntheticDataGenerator(seed=args.seed)
            df_raw = gen.generate(start_year=2000, end_year=2023)
        else:
            logger.info("Downloading NASA POWER data ...")
            ingestor = NASAPowerIngestor()
            try:
                df_raw = ingestor.download()
            except RuntimeError as exc:
                logger.warning(
                    f"NASA POWER download failed: {exc}\n"
                    "Falling back to synthetic data generator."
                )
                gen = SyntheticDataGenerator(seed=args.seed)
                df_raw = gen.generate(start_year=2000, end_year=2023)

        logger.info(f"Raw data shape: {df_raw.shape}")

    # ================================================================
    # Phase 3: Validation, Cleaning, and Label Creation
    # ================================================================
    if 3 in active_phases:
        logger.info("\nPHASE 3: Validation & Cleaning")

        # Validate
        validator = DataValidator()
        report = validator.validate(df_raw)
        logger.info(report.summary())
        if not report.is_valid:
            logger.warning(
                "Data validation failed, but continuing with available data. "
                "Check the validation report and fix issues for production use."
            )

        # Clean
        cleaner = DataCleaner()
        df_clean = cleaner.clean(df_raw)

        # Attempt to load real flood event labels
        events_ingestor = FloodEventsIngestor()
        label_series = events_ingestor.events_to_daily_labels(df_clean.index)
        has_real_labels = label_series.sum() > 0

        if has_real_labels:
            df_clean["flood_label"] = label_series
            logger.info("Real historical flood labels applied ✓")
        else:
            logger.warning("Using proxy labels (no real events file found).")
            # Proxy labels are added by FeatureEngineer in Phase 4

    # ================================================================
    # Phase 4: Feature Engineering & EDA
    # ================================================================
    if 4 in active_phases:
        logger.info("\nPHASE 4: Feature Engineering & EDA")

        fe = FeatureEngineer()
        df_features = fe.build(
            df_clean,
            has_labels=has_real_labels or "flood_label" in df_clean.columns,
        )
        df_scaled = fe.scale_features(df_features, fit=True)

        # Save feature list for model metadata
        feature_list_path = settings.saved_models_dir / "feature_columns.json"
        feature_list_path.write_text(
            json.dumps(fe.feature_columns, indent=2), encoding="utf-8"
        )
        logger.info(f"Feature list saved: {len(fe.feature_columns)} features")

        # Run EDA plots
        logger.info("Generating EDA plots ...")
        plotter = EDAPlotter(df_features)
        plotter.run_full_eda()
        logger.info(f"EDA plots saved to {settings.figures_dir}")

    # ================================================================
    # Phase 4b: Data Splitting
    # ================================================================
    splitter = DataSplitter()
    splits = splitter.split(df_scaled)

    # LSTM sequences
    X_seq, y_seq = fe.create_sequences(df_scaled)
    dates_seq = df_scaled.index[settings.features.window_size:]
    splits = splitter.split_sequences(X_seq, y_seq, dates_seq)
    splits.feature_columns = fe.feature_columns

    # ================================================================
    # Phase 5: Baseline Model Training
    # ================================================================
    if 5 in active_phases:
        logger.info("\nPHASE 5: Baseline Model Training")

        baseline_trainer = BaselineTrainer()
        comparison_df = baseline_trainer.train_all(splits)

        logger.info(f"\nBaseline Model Comparison:\n{comparison_df.to_string()}")

    # ================================================================
    # Phase 6: LSTM Training
    # ================================================================
    if 6 in active_phases and not args.skip_lstm:
        logger.info("\nPHASE 6: LSTM Training")

        try:
            from src.training.train_lstm import LSTMTrainer

            lstm_trainer = LSTMTrainer(n_features=len(fe.feature_columns))
            lstm_metrics = lstm_trainer.train(splits)
            logger.info(f"LSTM Metrics: {lstm_metrics}")

        except ImportError:
            logger.warning(
                "TensorFlow not available on this Python version. "
                "LSTM training skipped.\n"
                "To train the LSTM, use Python 3.11:\n"
                "  1. Install Python 3.11 from python.org\n"
                "  2. Create virtualenv: py -3.11 -m venv venv311\n"
                "  3. Activate: venv311\\Scripts\\activate\n"
                "  4. Install: pip install -r requirements.txt\n"
                "  5. Run: python main.py"
            )

    # ================================================================
    # Phase 7 & 8: Full Evaluation and SHAP Explainability
    # ================================================================
    if 7 in active_phases:
        logger.info("\nPHASE 7 & 8: Evaluation & Explainability")

        evaluator = ModelEvaluator()
        factory = BaselineModelFactory()

        # Load best saved model for explainability
        rf_path = settings.saved_models_dir / "randomforest_model.joblib"
        if rf_path.exists():
            rf_model = joblib.load(rf_path)
            logger.info("Loaded saved RandomForest model for SHAP analysis ...")

            try:
                from src.explainability.explain_models import SHAPExplainer

                # Use a background sample of training data
                bg_indices = np.random.choice(
                    len(splits.X_train),
                    min(500, len(splits.X_train)),
                    replace=False,
                )
                explainer = SHAPExplainer(
                    model=rf_model,
                    feature_names=splits.feature_columns,
                    X_background=splits.X_train[bg_indices],
                    model_type="tree",
                )
                explainer.run_full_explanation(
                    X_test=splits.X_test,
                    model_name="RandomForest",
                )
                logger.info("SHAP explainability complete ✓")

            except ImportError:
                logger.warning("SHAP not installed. Skipping explainability plots.")
        else:
            logger.warning(
                "No saved RandomForest model found for SHAP. "
                "Run Phase 5 first."
            )

    # ================================================================
    # Phase 9: Production Model Export
    # ================================================================
    if 9 in active_phases:
        logger.info("\nPHASE 9: Production Model Export")

        # Save model metadata
        metadata = {
            "project": "FloodShield-Zambia",
            "version": "1.0.0",
            "training_seed": args.seed,
            "n_features": len(fe.feature_columns) if "fe" in locals() else 0,
            "window_size": settings.features.window_size,
            "data_source": "synthetic" if args.use_synthetic else "nasa_power",
            "feature_columns": fe.feature_columns if "fe" in locals() else [],
        }

        metadata_path = settings.saved_models_dir / "model_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        logger.info(f"Model metadata saved to {metadata_path}")

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Pipeline complete in {elapsed:.1f}s ✓")
    logger.info(f"Figures   : {settings.figures_dir}")
    logger.info(f"Models    : {settings.saved_models_dir}")
    logger.info(f"Reports   : {settings.reports_dir}")
    logger.info(f"Experiments: {settings.experiments_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args)

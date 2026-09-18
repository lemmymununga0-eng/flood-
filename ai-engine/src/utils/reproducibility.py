"""
utils/reproducibility.py
=========================
Global random seed control for the FloodShield-Zambia AI Engine.

Why is reproducibility important?
----------------------------------
Machine learning models involve randomness at many levels:
  - Data shuffling (train/val/test splits)
  - Model weight initialisation
  - Dropout during training
  - Stochastic gradient descent

Without fixing seeds, the same code produces different results on every run,
making experiments impossible to compare fairly.  This module provides a
single ``set_global_seed`` function that locks all sources of randomness.

Usage
-----
    from src.utils.reproducibility import set_global_seed
    set_global_seed(42)   # Call once at the top of every training script
"""

import os
import random

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


def set_global_seed(seed: int = 42) -> None:
    """
    Fix all random seeds to ensure fully reproducible experiments.

    This function seeds Python's built-in ``random``, ``numpy``, and
    TensorFlow/Keras (if available).  It also sets the ``PYTHONHASHSEED``
    environment variable which affects dictionary ordering in older Python.

    Parameters
    ----------
    seed : int
        The random seed to use.  Default is 42.

    Notes
    -----
    Even with seeds fixed, GPU operations may introduce small non-determinism
    due to parallel floating-point reductions.  For fully deterministic GPU
    training set ``TF_DETERMINISTIC_OPS=1`` in your environment.
    """
    logger.info(f"Setting global random seed to {seed}")

    # Python built-in
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    # NumPy
    np.random.seed(seed)

    # TensorFlow / Keras (optional dependency)
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
        logger.debug("TensorFlow seed set successfully.")
    except ImportError:
        logger.warning(
            "TensorFlow not installed — skipping TF seed. "
            "Install tensorflow==2.15.0 with Python 3.11 for full functionality."
        )

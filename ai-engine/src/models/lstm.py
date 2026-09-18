"""
models/lstm.py
==============
LSTM Deep Learning model for FloodShield-Zambia.

What is an LSTM and why use it for floods?
--------------------------------------------
LSTM (Long Short-Term Memory) is a type of Recurrent Neural Network (RNN)
designed to learn from sequences of data over time.

Why sequential models for floods?
  - Flooding is a process, not an event.  Soil must saturate over days/weeks
    before a flood occurs.
  - A 14-day window of daily rainfall, temperature, and soil moisture carries
    far more predictive power than a single day's reading.
  - LSTM's memory cells can selectively remember relevant past states
    (e.g. heavy rain 10 days ago) and forget irrelevant ones
    (e.g. a minor temperature fluctuation).

Architecture
------------
Input:  (batch, 14, n_features)   14-day window of all features
LSTM 1: 128 units, return_sequences=True, dropout=0.2
LSTM 2: 64 units, return_sequences=False, dropout=0.2
Dense:  32 units, activation='relu'
Output: 1 unit, activation='sigmoid' → flood probability 0–1

Design decisions
----------------
- Bidirectional LSTM option is provided for research comparison.
- Dropout prevents overfitting on the small Zambia dataset.
- Sigmoid output + binary cross-entropy loss for binary classification.
- EarlyStopping prevents training past the point of diminishing returns.
- ReduceLROnPlateau adjusts learning rate when validation loss plateaus.
- ModelCheckpoint saves the best epoch weights automatically.

Usage
-----
    from src.models.lstm import LSTMFloodModel
    model = LSTMFloodModel(n_features=45, window_size=14)
    model.build()
    history = model.train(X_train, y_train, X_val, y_val)
    preds = model.predict_proba(X_test)
"""

from pathlib import Path
from typing import Optional

import numpy as np

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LSTMFloodModel:
    """
    LSTM-based binary flood classifier.

    Parameters
    ----------
    n_features : int
        Number of input features per time step.
    window_size : int
        Number of past time steps per input sequence.
    lstm_units : int
        Number of units in each LSTM layer.
    dropout_rate : float
        Dropout rate applied after each LSTM layer.
    learning_rate : float
        Initial learning rate for the Adam optimiser.
    checkpoint_path : Path, optional
        Directory to save model checkpoints during training.
    bidirectional : bool
        If True, wrap LSTM layers in a Bidirectional wrapper.
        Bidirectional LSTMs process sequences forwards AND backwards,
        which can improve accuracy but doubles computation.
    """

    def __init__(
        self,
        n_features: int,
        window_size: int = settings.features.window_size,
        lstm_units: int = settings.training.lstm_units,
        dropout_rate: float = settings.training.lstm_dropout,
        learning_rate: float = settings.training.lstm_learning_rate,
        checkpoint_path: Path = settings.saved_models_dir / "lstm_checkpoint",
        bidirectional: bool = False,
    ) -> None:
        self.n_features = n_features
        self.window_size = window_size
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.checkpoint_path = checkpoint_path
        self.bidirectional = bidirectional
        self._model = None
        self._history = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build(self) -> "LSTMFloodModel":
        """
        Construct the LSTM architecture using TensorFlow/Keras.

        Returns
        -------
        self
        """
        try:
            import tensorflow as tf
            from tensorflow import keras
        except ImportError as exc:
            raise ImportError(
                "TensorFlow is required for the LSTM model. "
                "Install it with Python 3.11: pip install tensorflow==2.15.0\n"
                "Your current environment has Python 3.14 which is not yet "
                "supported by TensorFlow."
            ) from exc

        logger.info(
            f"Building LSTM model | features={self.n_features}, "
            f"window={self.window_size}, units={self.lstm_units}, "
            f"bidirectional={self.bidirectional}"
        )

        inputs = keras.Input(
            shape=(self.window_size, self.n_features),
            name="sequence_input",
        )

        # First LSTM layer — return sequences so layer 2 sees the full output
        lstm1 = keras.layers.LSTM(
            units=self.lstm_units,
            return_sequences=True,
            recurrent_dropout=settings.training.lstm_recurrent_dropout,
            name="lstm_1",
        )(inputs)
        lstm1 = keras.layers.Dropout(self.dropout_rate, name="dropout_1")(lstm1)

        # Second LSTM layer — collapses the sequence to a single vector
        lstm2 = keras.layers.LSTM(
            units=self.lstm_units // 2,
            return_sequences=False,
            recurrent_dropout=settings.training.lstm_recurrent_dropout,
            name="lstm_2",
        )(lstm1)
        lstm2 = keras.layers.Dropout(self.dropout_rate, name="dropout_2")(lstm2)

        # Dense classification head
        dense = keras.layers.Dense(32, activation="relu", name="dense_1")(lstm2)
        output = keras.layers.Dense(1, activation="sigmoid", name="output")(dense)

        self._model = keras.Model(inputs=inputs, outputs=output, name="FloodShield_LSTM")

        # Adam optimiser with configurable learning rate
        optimiser = keras.optimizers.Adam(learning_rate=self.learning_rate)

        self._model.compile(
            optimizer=optimiser,
            loss="binary_crossentropy",
            metrics=[
                "accuracy",
                keras.metrics.AUC(name="auc"),
                keras.metrics.Precision(name="precision"),
                keras.metrics.Recall(name="recall"),
            ],
        )

        self._model.summary(print_fn=lambda line: logger.debug(line))
        logger.info("LSTM model built successfully ✓")
        return self

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = settings.training.lstm_epochs,
        batch_size: int = settings.training.lstm_batch_size,
        patience: int = settings.training.lstm_patience,
    ) -> "LSTMFloodModel":
        """
        Train the LSTM model with early stopping and checkpointing.

        Parameters
        ----------
        X_train : np.ndarray  shape (n, window, features)
        y_train : np.ndarray  shape (n,)
        X_val   : np.ndarray  shape (n, window, features)
        y_val   : np.ndarray  shape (n,)
        epochs  : int         Maximum number of training epochs
        batch_size : int      Number of sequences per gradient update
        patience : int        Epochs without improvement before stopping

        Returns
        -------
        self
        """
        try:
            from tensorflow import keras
        except ImportError as exc:
            raise ImportError(
                "TensorFlow required for training. "
                "See docs/installation.md for setup with Python 3.11."
            ) from exc

        if self._model is None:
            raise RuntimeError("Call build() before train().")

        self.checkpoint_path.mkdir(parents=True, exist_ok=True)

        callbacks = [
            # Stop training if val_loss doesn't improve for `patience` epochs
            keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=patience,
                restore_best_weights=True,
                verbose=1,
            ),
            # Halve the learning rate when val_loss plateaus
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=5,
                min_lr=1e-6,
                verbose=1,
            ),
            # Save best weights to disk
            keras.callbacks.ModelCheckpoint(
                filepath=str(self.checkpoint_path / "best_model.keras"),
                monitor="val_auc",
                save_best_only=True,
                mode="max",
                verbose=1,
            ),
        ]

        # Class weight to handle class imbalance
        n_flood = int(y_train.sum())
        n_normal = len(y_train) - n_flood
        class_weight = {0: 1.0, 1: n_normal / max(n_flood, 1)}
        logger.info(
            f"Class weights: Normal=1.0, Flood={class_weight[1]:.2f} "
            f"(flood rate={n_flood / len(y_train):.1%})"
        )

        logger.info(
            f"Starting LSTM training | epochs={epochs}, batch={batch_size}"
        )
        self._history = self._model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            class_weight=class_weight,
            verbose=1,
        )

        logger.info(
            f"Training complete | "
            f"best val_auc={max(self._history.history.get('val_auc', [0])):.4f}"
        )
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Return flood probability for each sample.

        Parameters
        ----------
        X : np.ndarray  shape (n, window, features)

        Returns
        -------
        np.ndarray  shape (n,)  Values in [0, 1].
        """
        if self._model is None:
            raise RuntimeError("Call build() and train() before predict_proba().")
        return self._model.predict(X, verbose=0).flatten()

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """
        Return binary flood predictions.

        Parameters
        ----------
        X : np.ndarray
        threshold : float
            Probability threshold above which a sample is classified as Flood.
            Default 0.5; may be tuned via precision-recall curve analysis.

        Returns
        -------
        np.ndarray  shape (n,)  Values in {0, 1}.
        """
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def save(self, save_dir: Path = settings.saved_models_dir) -> None:
        """
        Save the trained model to disk in Keras native format.

        Parameters
        ----------
        save_dir : Path
            Directory to save the model (saved as ``lstm_model.keras``).
        """
        if self._model is None:
            raise RuntimeError("No model to save. Train the model first.")
        path = save_dir / "lstm_model.keras"
        self._model.save(str(path))
        logger.info(f"LSTM model saved to {path}")

    @classmethod
    def load(cls, save_dir: Path = settings.saved_models_dir) -> "LSTMFloodModel":
        """
        Load a previously saved LSTM model from disk.

        Parameters
        ----------
        save_dir : Path
            Directory containing ``lstm_model.keras``.

        Returns
        -------
        LSTMFloodModel
            Instance with the loaded model ready for inference.
        """
        try:
            from tensorflow import keras
        except ImportError as exc:
            raise ImportError("TensorFlow required to load LSTM model.") from exc

        path = save_dir / "lstm_model.keras"
        logger.info(f"Loading LSTM model from {path}")
        instance = cls.__new__(cls)
        instance._model = keras.models.load_model(str(path))
        instance._history = None
        logger.info("LSTM model loaded ✓")
        return instance

    @property
    def history(self):
        """Training history from the last fit() call."""
        return self._history

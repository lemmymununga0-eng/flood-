"""
config/settings.py
==================
Central configuration for the FloodShield-Zambia AI Engine.

All hyperparameters, paths, API keys, and global constants are defined
here so that every other module imports from a single source of truth.
This design follows the "Single Responsibility" principle — one place to
change configuration, one place to read it.

Usage
-----
    from src.config.settings import settings

Design decisions
----------------
- Uses python-dotenv to load secrets (API keys) from a .env file so they
  are never hard-coded.
- All paths are expressed as pathlib.Path objects for OS independence.
- Dataclass-style with a frozen Pydantic-like approach using plain Python
  dataclasses so there is no external dependency beyond the stdlib.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if it exists (development only).
load_dotenv()


# ---------------------------------------------------------------------------
# Root paths
# ---------------------------------------------------------------------------
AI_ENGINE_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = AI_ENGINE_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
EXTERNAL_DIR: Path = DATA_DIR / "external"
SAVED_MODELS_DIR: Path = AI_ENGINE_ROOT / "saved_models"
REPORTS_DIR: Path = AI_ENGINE_ROOT / "reports"
FIGURES_DIR: Path = REPORTS_DIR / "figures"
EXPERIMENTS_DIR: Path = AI_ENGINE_ROOT / "experiments"
LOGS_DIR: Path = AI_ENGINE_ROOT / "logs"

# Ensure directories exist on import.
for _dir in [RAW_DIR, PROCESSED_DIR, EXTERNAL_DIR,
             SAVED_MODELS_DIR, REPORTS_DIR, FIGURES_DIR,
             EXPERIMENTS_DIR, LOGS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data ingestion settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NASAPOWERConfig:
    """Settings for the NASA POWER API data downloader."""
    base_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    # Zambia's bounding box: lat [-18, -8], lon [22, 34]
    default_latitude: float = -15.4167   # Lusaka, Zambia
    default_longitude: float = 28.2833
    community: str = "AG"                # Agro-climatology community
    start_year: int = 2000
    end_year: int = 2023
    # NASA POWER parameters we need for flood modelling
    parameters: tuple = (
        "PRECTOTCORR",   # Precipitation (mm/day)
        "T2M",           # Temperature at 2m (°C)
        "T2M_MAX",       # Daily max temperature
        "T2M_MIN",       # Daily min temperature
        "RH2M",          # Relative humidity at 2m (%)
        "WS2M",          # Wind speed at 2m (m/s)
        "ALLSKY_SFC_SW_DWN",  # Solar radiation (MJ/m²/day)
        "GWETROOT",      # Root zone soil wetness (fraction)
        "GWETPROF",      # Profile soil wetness (fraction)
    )
    timeout_seconds: int = 60
    output_filename: str = "nasa_power_zambia.csv"


@dataclass(frozen=True)
class CHIRPSConfig:
    """Settings for CHIRPS rainfall data (manual download reference)."""
    source_url: str = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p25/"
    resolution: str = "0.25 degree"
    note: str = (
        "CHIRPS data is downloaded manually or via wget/curl. "
        "See docs/dataset_guide.md for instructions."
    )
    output_filename: str = "chirps_zambia.csv"


# ---------------------------------------------------------------------------
# Flood event label settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LabelConfig:
    """
    Configuration for creating flood event labels.

    When real historical flood event records are available, they override
    the proxy label method.  Proxy labels are created using the
    Standardised Precipitation Index (SPI) and multi-day accumulations.
    """
    # Path to historical flood events CSV (from EM-DAT / DMMU Zambia).
    historical_events_path: Path = EXTERNAL_DIR / "zambia_flood_events_log.csv"
    # Proxy label thresholds (used when real labels are unavailable)
    rainfall_3day_threshold_mm: float = 50.0   # >50mm in 3 days = high risk
    rainfall_7day_threshold_mm: float = 80.0   # >80mm in 7 days = high risk
    # Multi-class labels: 0=Low, 1=Medium, 2=High
    use_binary_labels: bool = True             # True = Flood/No-Flood


# ---------------------------------------------------------------------------
# Feature engineering settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FeatureConfig:
    """Time-series windowing and feature extraction parameters."""
    # How many past days the model looks back
    window_size: int = 14
    # How many days ahead we are predicting
    forecast_horizon: int = 1
    # Rolling window sizes for statistics
    rolling_windows: tuple = (3, 7, 14, 30)
    # Lag periods (days)
    lag_periods: tuple = (1, 2, 3, 7, 14)
    # Features used by the model (populated after feature engineering)
    feature_columns: tuple = ()


# ---------------------------------------------------------------------------
# Model training settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TrainingConfig:
    """Shared training settings for all models."""
    random_seed: int = 42
    test_size: float = 0.15
    validation_size: float = 0.15
    # LSTM specific
    lstm_units: int = 64
    lstm_dropout: float = 0.2
    lstm_recurrent_dropout: float = 0.1
    lstm_epochs: int = 100
    lstm_batch_size: int = 32
    lstm_patience: int = 15          # Early stopping patience
    lstm_learning_rate: float = 0.001
    # Baseline models
    n_estimators: int = 200          # Random Forest & Gradient Boosting
    max_depth: int = 6               # Decision Tree & Gradient Boosting


# ---------------------------------------------------------------------------
# MLOps / Experiment tracking settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ExperimentConfig:
    """Settings for experiment versioning and tracking."""
    experiments_dir: Path = EXPERIMENTS_DIR
    saved_models_dir: Path = SAVED_MODELS_DIR
    # Model version prefix
    model_version_prefix: str = "floodshield_v"


# ---------------------------------------------------------------------------
# API Keys (loaded from environment variables via .env)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class APIConfig:
    """External API keys — loaded from .env, never hard-coded."""
    openweathermap_api_key: str = field(
        default_factory=lambda: os.getenv("OWM_API_KEY", "")
    )
    nasa_power_api_key: str = field(
        default_factory=lambda: os.getenv("NASA_POWER_API_KEY", "")
    )


# ---------------------------------------------------------------------------
# Aggregated settings object (import this)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """
    Top-level settings object.

    Import and use like:
        from src.config.settings import settings
        print(settings.training.random_seed)
    """
    nasa_power: NASAPOWERConfig = field(default_factory=NASAPOWERConfig)
    chirps: CHIRPSConfig = field(default_factory=CHIRPSConfig)
    labels: LabelConfig = field(default_factory=LabelConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    experiments: ExperimentConfig = field(default_factory=ExperimentConfig)
    api: APIConfig = field(default_factory=APIConfig)
    # Paths (module-level constants re-exposed for convenience)
    ai_engine_root: Path = AI_ENGINE_ROOT
    raw_dir: Path = RAW_DIR
    processed_dir: Path = PROCESSED_DIR
    external_dir: Path = EXTERNAL_DIR
    saved_models_dir: Path = SAVED_MODELS_DIR
    reports_dir: Path = REPORTS_DIR
    figures_dir: Path = FIGURES_DIR
    experiments_dir: Path = EXPERIMENTS_DIR
    logs_dir: Path = LOGS_DIR


# Singleton instance — import this object everywhere.
settings = Settings()

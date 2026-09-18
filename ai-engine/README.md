# FloodShield-Zambia — AI Engine

> **AI-Powered Real-Time Flood Prediction and Early Warning System for Zambia**  
> Final Year Computer Science Project | Distinction-Level AI Module  
> Python · TensorFlow · Scikit-Learn · SHAP · Loguru

---

## Overview

FloodShield-Zambia is a production-quality AI engine that predicts flood risk across Zambia using multi-source meteorological data and deep learning. The system combines classical machine learning baselines with an LSTM sequence model, full explainability via SHAP, and robust MLOps practices including experiment tracking, model versioning, and reproducible training.

---

## Project Structure

```
FloodShield-Zambia/
└── ai-engine/
    ├── data/
    │   ├── raw/              ← Unprocessed API downloads
    │   ├── processed/        ← Cleaned, feature-engineered datasets
    │   └── external/         ← Historical flood events, shapefiles
    ├── notebooks/            ← EDA and prototyping Jupyter notebooks
    ├── src/
    │   ├── config/           ← Settings, hyperparameters (settings.py)
    │   ├── datasets/         ← Train/val/test splitting (split_data.py)
    │   ├── ingestion/        ← Data downloaders (NASA POWER, synthetic)
    │   ├── preprocessing/    ← Validation and cleaning
    │   ├── features/         ← Feature engineering and LSTM windowing
    │   ├── models/           ← LSTM architecture + baseline classifiers
    │   ├── training/         ← Training runners (baselines + LSTM)
    │   ├── evaluation/       ← Metrics, ROC/PR curves, confusion matrix
    │   ├── explainability/   ← SHAP explainer (global + local)
    │   ├── visualization/    ← EDA plots
    │   └── utils/            ← Logger, seed control, experiment tracker
    ├── saved_models/         ← Production model weights + scaler
    ├── experiments/          ← Versioned experiment runs
    ├── reports/
    │   └── figures/          ← All generated plots
    ├── tests/                ← Pytest unit tests
    ├── main.py               ← Master pipeline orchestrator
    ├── requirements.txt      ← Python dependencies
    └── .env.example          ← Environment variable template
```

---

## ⚠️ Python Version Requirement

| Feature | Python Version |
|---------|---------------|
| All modules except LSTM | Python 3.11+ or 3.14 |
| **LSTM training (TensorFlow)** | **Python 3.11 only** |
| Baseline models | Python 3.11+ |
| SHAP explainability | Python 3.11+ |

**TensorFlow 2.15 does not support Python 3.12, 3.13, or 3.14.**  
All baseline models, feature engineering, EDA, and explainability run on any Python 3.11+.

---

## Installation (Python 3.11)

### Step 1: Install Python 3.11
Download from [python.org/downloads](https://www.python.org/downloads/)

### Step 2: Create a virtual environment
```powershell
# From the FloodShield-Zambia directory:
py -3.11 -m venv venv311
venv311\Scripts\activate
```

### Step 3: Install dependencies
```powershell
pip install -r ai-engine\requirements.txt
```

### Step 4: Set up environment variables
```powershell
copy ai-engine\.env.example ai-engine\.env
# Edit .env and add your API keys
```

---

## Running the Pipeline

All commands are run from the `ai-engine/` directory.

### Full pipeline (with internet connection)
```powershell
python main.py
```

### Full pipeline (offline, synthetic data)
```powershell
python main.py --use-synthetic
```

### Baseline models only (no TensorFlow required)
```powershell
python main.py --use-synthetic --skip-lstm
```

### Run specific phases
```powershell
python main.py --use-synthetic --phases 2,3,4    # Ingestion + EDA only
python main.py --use-synthetic --phases 5         # Baselines only
```

---

## Dataset Sources

| Dataset | Purpose | Access |
|---------|---------|--------|
| **NASA POWER** | Temperature, humidity, rainfall, solar, wind | Free API — automatic |
| **CHIRPS** | High-resolution daily rainfall | Manual download ([UCSB](https://data.chc.ucsb.edu/products/CHIRPS-2.0/)) |
| **ERA5** | Atmospheric reanalysis | [Copernicus CDS](https://cds.climate.copernicus.eu/) |
| **GloFAS** | River discharge forecasts | [ECMWF GloFAS](https://www.globalfloods.eu/) |
| **SRTM** | Digital elevation model | [USGS EarthExplorer](https://earthexplorer.usgs.gov/) |
| **SoilGrids** | Soil texture characteristics | [ISRIC](https://www.isric.org/) |
| **EM-DAT** | Historical flood event records | [Free for academic use](https://www.emdat.be/) |
| **DMMU Zambia** | National disaster records | Government reports |

---

## AI Architecture

```
Data Sources (NASA POWER, CHIRPS, ERA5, GloFAS, EM-DAT)
    ↓
Ingestion (src/ingestion/)
    ↓
Validation (src/preprocessing/validation.py)
    ↓
Cleaning (src/preprocessing/clean_data.py)
    ↓
Feature Engineering (src/features/build_features.py)
    ↓ [2D features]          ↓ [3D sequences (window, features)]
Baseline Models (RF/XGB)     LSTM Model
    ↓                            ↓
Evaluation (src/evaluation/metrics.py)
    ↓
SHAP Explainability (src/explainability/explain_models.py)
    ↓
Production Export (saved_models/)
```

---

## Models

| Model | Type | Class Imbalance | Notes |
|-------|------|----------------|-------|
| Logistic Regression | Linear | class_weight=balanced | Minimum baseline |
| Decision Tree | Non-linear | class_weight=balanced | Interpretable rules |
| Random Forest | Ensemble (Bagging) | class_weight=balanced | Best classic baseline |
| Gradient Boosting | Ensemble (Boosting) | subsample=0.8 | Strong performance |
| XGBoost | Optimised Boosting | scale_pos_weight | Industry standard |
| **LSTM** | **Deep Learning** | class_weight dict | **Best overall** |

---

## Evaluation Metrics

All models are evaluated with the following metrics on the **held-out test set**:

| Metric | Why it matters for flood prediction |
|--------|-------------------------------------|
| **Recall** | We cannot miss real floods (safety-critical) |
| **Precision** | Too many false alarms reduce trust |
| **F1 Score** | Balance between Precision and Recall |
| **ROC-AUC** | Ranking quality across all thresholds |
| **PR-AUC** | Better than ROC for imbalanced data |
| **Brier Score** | Quality of probability calibration |

---

## Explainability Outputs

| Plot | What it shows |
|------|--------------|
| Global Feature Importance | Which features matter most overall |
| SHAP Summary Plot | Feature importance + direction of effect |
| Waterfall Plot | Why THIS specific prediction was made |
| Dependence Plot | How one feature's effect changes with value |

---

## Experiment Tracking

Each training run creates a versioned directory:
```
experiments/
    run_001/
        config.json      ← Hyperparameters, seed, features
        metrics.json     ← F1, AUC, Precision, Recall
        artifacts/       ← Plots, model weights
    run_002/
        ...
```

---

## Reproducibility Checklist

- [x] Random seed: `42` (all modules)
- [x] Python version: 3.11
- [x] Package versions: `requirements.txt`
- [x] Chronological train/val/test split (no data leakage)
- [x] Experiment configs saved as JSON per run
- [x] Model weights checksaved per epoch (ModelCheckpoint)

---

## Running Tests

```powershell
# From ai-engine directory:
python -m pytest tests/ -v --tb=short
```

---

## Future Integration

This AI engine is designed to integrate with:

| Component | Technology | Integration point |
|-----------|-----------|------------------|
| REST API | FastAPI | `main.py` → API endpoint |
| Database | PostgreSQL | `saved_models/` → model registry table |
| Frontend | React | API → dashboard |
| Deployment | Docker | `Dockerfile` (to be added) |
| SMS Alerts | Twilio | Prediction → SMS gateway |

---

## Author

Computer Science Final Year Student  
FloodShield-Zambia — AI Module (Milestone 1)

---

*This project is for academic purposes.  Synthetic data is used when real API data is unavailable.  See dataset guide for real data download instructions.*

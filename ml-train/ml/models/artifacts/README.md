# Model Artifacts Directory

## Version Structure

- **v1/** - Original model with 14 features, 142 sessions
  - Issues: Human-like bot could bypass detection
  - Threshold: 0.50 (hardcoded)

- **v2/** - Baseline model with 44 features, 183 sessions
  - Improvements: Richer features, expanded dataset, tuned threshold
  - Threshold: 0.52 (tuned on validation set)
  - Successfully detects stealth bot (70% probability)

- **root artifacts, 20260622** - Current working model used by backend
  - `random_forest_20260622_133850.pkl`
  - `scaler_20260622_133850.pkl`
  - `random_forest_metadata_20260622_133850.json`
  - `model_comparison_20260622_133856.json`
  - 52 feature columns from metadata; backend loads this through latest comparison.

## Loading Models

### Load Current Working Model
```python
from ml.models.inference import BotDetector
detector = BotDetector()
```

### Load V2 Baseline
```python
from ml.models.inference import BotDetector
detector = BotDetector(model_path='ml/models/artifacts/v2/random_forest_20260619_210124.pkl')
```

### Load V1 (Legacy)
```python
from ml.models.inference import BotDetector
detector = BotDetector(model_path='ml/models/artifacts/v1/random_forest_20260615_193406.pkl')
```

## Version Selection

The backend automatically loads the latest model from the comparison file. To switch versions:

1. Train a new model so it writes a newer `model_comparison_*.json`
2. Or set shadow/canary env vars from `docs/roadmap_s1_s6_runbook.md` to test before full promotion

See `ml/VERSIONS.md` for detailed version history.

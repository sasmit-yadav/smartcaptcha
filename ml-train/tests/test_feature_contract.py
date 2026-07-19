"""Feature-contract consistency tests (strategy step 0.5).

The 52-field V4 feature vector is intentionally present in three places
that cannot physically share one file (sdk-backend deploys standalone to
Render; the SDK publishes standalone to npm):

1. sdk-backend/features/feature_columns.py   (serving)
2. ml-train/ml/features/feature_columns.py   (training)
3. sdk/src/core/features.ts                  (client-side extraction)

These tests fail the moment any copy drifts, which converts "silent
train/serve/client skew" into a loud CI failure.
"""
import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_columns(py_path):
    spec = importlib.util.spec_from_file_location(f"fc_{py_path.parent.name}", py_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_copies_identical():
    ml_train = _load_columns(REPO_ROOT / "ml-train" / "ml" / "features" / "feature_columns.py")
    backend = _load_columns(REPO_ROOT / "sdk-backend" / "features" / "feature_columns.py")
    for name in ("LEGACY_FEATURE_COLUMNS", "V2_FEATURE_COLUMNS",
                 "V3_FEATURE_COLUMNS", "V4_FEATURE_COLUMNS",
                 "V5_FEATURE_COLUMNS", "FEATURE_COLUMNS"):
        assert getattr(ml_train, name) == getattr(backend, name), (
            f"{name} differs between ml-train and sdk-backend copies"
        )


def test_typescript_interface_matches():
    ml_train = _load_columns(REPO_ROOT / "ml-train" / "ml" / "features" / "feature_columns.py")
    ts_source = (REPO_ROOT / "sdk" / "src" / "core" / "features.ts").read_text(encoding="utf-8")

    match = re.search(r"interface FeatureVector \{(.*?)\n\}", ts_source, re.DOTALL)
    assert match, "FeatureVector interface not found in features.ts"
    ts_fields = re.findall(r"^\s*(\w+)\s*:", match.group(1), re.MULTILINE)

    assert ts_fields == ml_train.FEATURE_COLUMNS, (
        "features.ts FeatureVector fields differ from FEATURE_COLUMNS:\n"
        f"only in TS: {set(ts_fields) - set(ml_train.FEATURE_COLUMNS)}\n"
        f"only in py: {set(ml_train.FEATURE_COLUMNS) - set(ts_fields)}\n"
        "(order matters too — the model consumes a positional vector)"
    )


def test_v4_has_52_fields():
    ml_train = _load_columns(REPO_ROOT / "ml-train" / "ml" / "features" / "feature_columns.py")
    assert len(ml_train.V4_FEATURE_COLUMNS) == 52
    assert len(set(ml_train.V4_FEATURE_COLUMNS)) == 52, "duplicate feature names"


def test_v5_adds_seven_neuromotor_fields_no_dupes():
    """Spec §3.5: V5 = V4 + neuromotor (power law + keystroke + tremor),
    all names unique, FEATURE_COLUMNS == V5."""
    ml_train = _load_columns(REPO_ROOT / "ml-train" / "ml" / "features" / "feature_columns.py")
    v5 = ml_train.V5_FEATURE_COLUMNS
    assert len(v5) == 59, f"expected 59 V5 fields, got {len(v5)}"
    assert len(set(v5)) == len(v5), "duplicate feature names in V5"
    assert v5[:52] == ml_train.V4_FEATURE_COLUMNS, "V5 must extend V4 in place"
    assert v5[52:] == [
        "mouse_powerlaw_beta",
        "mouse_powerlaw_r2",
        "key_dwell_cv",
        "key_flight_cv",
        "key_digraph_std",
        "mouse_tremor_band_ratio",
        "mouse_tremor_peak_freq",
    ]
    assert ml_train.FEATURE_COLUMNS == v5, "FEATURE_COLUMNS must point at V5"

# Cell 16: Model Loading & Prediction Logic
import joblib
import pandas as pd
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "student_performance_model.pkl"
_pipeline = None

TOP_FEATURES = [
    "failures", "absences", "schoolsup", "studytime",
    "goout", "Medu", "Fedu", "traveltime", "health", "freetime"
]


def load_model():
    global _pipeline
    if _pipeline is None:
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline


def _engineer_features(data: dict) -> dict:
    """Recreates the same composite features used during training."""
    d = dict(data)
    d["parental_education"] = (d["Medu"] + d["Fedu"]) / 2
    d["alcohol_index"] = (d["Dalc"] + d["Walc"]) / 2
    d["support_index"] = (
        int(d["schoolsup"] == "yes")
        + int(d["famsup"] == "yes")
        + int(d["paid"] == "yes")
    )
    d["studytime_failures"] = d["studytime"] * (d["failures"] + 1)
    return d


def predict_score(student_dict: dict):
    pipeline = load_model()
    engineered = _engineer_features(student_dict)
    input_df = pd.DataFrame([engineered])

    prediction = pipeline.predict(input_df)[0]
    prediction = float(max(0, min(20, prediction)))

    key_values = {f: student_dict.get(f) for f in TOP_FEATURES if f in student_dict}
    return round(prediction, 1), key_values

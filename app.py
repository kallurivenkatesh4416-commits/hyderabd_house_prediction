from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
import json
import math
import mimetypes
import os
import pickle
import traceback

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_PATH = BASE_DIR / "index.html"
MODEL_PATH = BASE_DIR / "model.pkl"
DATA_PATHS = [BASE_DIR / "cleaed_data.csv", BASE_DIR / "cleaned_data.csv"]

CATEGORICAL_COLUMNS = {"location", "building_status", "property_type"}
DEFAULT_FEATURES = [
    "location",
    "area_insqft",
    "building_status",
    "bhk",
    "property_type",
]


def load_model():
    with MODEL_PATH.open("rb") as model_file:
        return pickle.load(model_file)


def load_data():
    for path in DATA_PATHS:
        if path.exists():
            return pd.read_csv(path)
    raise FileNotFoundError("Could not find cleaed_data.csv or cleaned_data.csv")


MODEL = load_model()
DATA = load_data()
FEATURE_COLUMNS = list(getattr(MODEL, "feature_names_in_", DEFAULT_FEATURES))


def as_float(value, fallback=0.0):
    try:
        if value is None or value == "":
            return float(fallback)
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def finite_number(value, fallback=0.0):
    number = as_float(value, fallback)
    if pd.isna(number):
        return float(fallback)
    return float(number)


def round_number(value, digits=2):
    if pd.isna(value):
        return None
    return round(float(value), digits)


def detect_prediction_scale():
    if "price(L)" not in DATA.columns:
        return "lakh"
    try:
        sample = DATA[FEATURE_COLUMNS].head(min(len(DATA), 500))
        predictions = pd.Series(MODEL.predict(sample))
        target_median = DATA["price(L)"].median()
        prediction_median = predictions.median()
        if prediction_median < 20 and target_median > 20:
            return "log_lakh"
    except Exception:
        pass
    return "lakh"


PREDICTION_SCALE = detect_prediction_scale()


def model_display_name():
    estimator = MODEL

    if hasattr(estimator, "regressor_"):
        estimator = estimator.regressor_
    elif hasattr(estimator, "regressor"):
        estimator = estimator.regressor

    if hasattr(estimator, "steps") and estimator.steps:
        estimator = estimator.steps[-1][1]

    class_name = type(estimator).__name__
    labels = {
        "XGBRegressor": "XGBoost model",
        "RandomForestRegressor": "Random Forest model",
        "ExtraTreesRegressor": "Extra Trees model",
        "GradientBoostingRegressor": "Gradient Boosting model",
        "LinearRegression": "Linear Regression model",
        "Ridge": "Ridge model",
        "Lasso": "Lasso model",
        "DecisionTreeRegressor": "Decision Tree model",
        "KNeighborsRegressor": "KNN model",
        "SVR": "SVR model",
    }
    return labels.get(class_name, f"{class_name} model")


MODEL_LABEL = model_display_name()


def inverse_prediction(value):
    if PREDICTION_SCALE == "log_lakh":
        return math.exp(float(value))
    return float(value)


def sorted_values(column):
    values = DATA[column].dropna().astype(str).str.strip()
    unique_values = sorted(values.unique().tolist(), key=str.casefold)
    if "Other" in unique_values:
        unique_values.remove("Other")
        unique_values.append("Other")
    return unique_values


def value_counts(column):
    counts = DATA[column].dropna().astype(str).str.strip().value_counts()
    return [{"name": str(name), "count": int(count)} for name, count in counts.items()]


def first_mode(series, fallback=""):
    clean_series = series.dropna().astype(str).str.strip()
    if clean_series.empty:
        return fallback
    return str(clean_series.mode().iloc[0])


def default_property_type():
    property_values = set(DATA["property_type"].dropna().astype(str).str.strip())
    if "Apartment" in property_values:
        return "Apartment"
    return first_mode(DATA["property_type"])


def default_location(property_type=None):
    source = DATA
    if property_type:
        property_mask = DATA["property_type"].dropna().astype(str).str.strip() == property_type
        source = DATA[property_mask]
        if source.empty:
            source = DATA

    counts = source["location"].dropna().astype(str).str.strip().value_counts()
    without_other = counts[counts.index != "Other"]
    if not without_other.empty:
        return str(without_other.index[0])
    if not counts.empty:
        return str(counts.index[0])
    return ""


def median_from_subset(subset, column, fallback):
    if not subset.empty and column in subset.columns:
        value = subset[column].median()
        if not pd.isna(value):
            return value
    return fallback


def options_payload():
    area_median = DATA["area_insqft"].median()
    price_median = DATA["price(L)"].median() if "price(L)" in DATA.columns else None

    property_type = default_property_type()
    location = default_location(property_type)
    default_subset = DATA[
        (DATA["property_type"].dropna().astype(str).str.strip() == property_type)
        & (DATA["location"].dropna().astype(str).str.strip() == location)
    ]

    default_area = median_from_subset(default_subset, "area_insqft", area_median)
    default_bhk = median_from_subset(default_subset, "bhk", 3)
    default_status = first_mode(default_subset["building_status"], first_mode(DATA["building_status"]))

    return {
        "features": FEATURE_COLUMNS,
        "model": {
            "label": MODEL_LABEL,
            "prediction_scale": PREDICTION_SCALE,
        },
        "prediction_scale": PREDICTION_SCALE,
        "locations": sorted_values("location"),
        "building_statuses": sorted_values("building_status"),
        "property_types": sorted_values("property_type"),
        "bhk_values": sorted(DATA["bhk"].dropna().astype(float).unique().tolist()),
        "popular_locations": value_counts("location")[:12],
        "ranges": {
            "area": {
                "min": round_number(DATA["area_insqft"].min(), 0),
                "max": round_number(DATA["area_insqft"].max(), 0),
                "median": round_number(area_median, 0),
            },
            "price_lakh": {
                "median": round_number(price_median, 2),
            },
        },
        "defaults": {
            "location": location,
            "building_status": default_status,
            "property_type": property_type,
            "bhk": round_number(default_bhk, 0),
            "area_insqft": round_number(default_area, 0),
        },
        "dataset": {
            "rows": int(len(DATA)),
            "locations": int(DATA["location"].nunique()),
            "median_price_lakh": round_number(price_median, 2),
            "median_area": round_number(area_median, 0),
        },
    }


OPTIONS = options_payload()


def normalized_input_row(payload):
    row = {}
    defaults = OPTIONS["defaults"]

    input_columns = list(dict.fromkeys(DEFAULT_FEATURES + FEATURE_COLUMNS))
    for column in input_columns:
        if column in CATEGORICAL_COLUMNS:
            value = payload.get(column, defaults.get(column, ""))
            row[column] = str(value).strip()
        elif column == "bhk":
            row[column] = max(finite_number(payload.get(column), defaults.get(column, 0)), 0)
        elif column == "area_insqft":
            row[column] = max(finite_number(payload.get(column), defaults.get(column, 1)), 1)
        else:
            row[column] = finite_number(payload.get(column), defaults.get(column, 0))

    return row


def build_prediction_frame(payload):
    full_row = normalized_input_row(payload)
    model_row = {column: full_row[column] for column in FEATURE_COLUMNS}
    return pd.DataFrame([model_row], columns=FEATURE_COLUMNS), full_row


def price_label(lakh_value):
    lakh_value = max(float(lakh_value), 0)
    if lakh_value >= 100:
        return f"₹ {lakh_value / 100:.2f} Cr"
    return f"₹ {lakh_value:.2f} L"


def predict_payload(payload):
    frame, row = build_prediction_frame(payload)
    model_output = float(MODEL.predict(frame)[0])
    prediction_lakh = max(inverse_prediction(model_output), 0)

    return {
        "prediction_lakh": round_number(prediction_lakh, 2),
        "model_output": round_number(model_output, 4),
        "prediction_scale": PREDICTION_SCALE,
        "prediction_crore": round_number(prediction_lakh / 100, 3),
        "prediction_label": price_label(prediction_lakh),
        "input": row,
    }


def json_response(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def file_response(handler, path):
    if not path.exists() or not path.is_file():
        handler.send_error(404)
        return

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])

        if path == "/":
            file_response(self, INDEX_PATH)
            return

        if path == "/api/options":
            json_response(self, OPTIONS)
            return

        if path.startswith("/static/"):
            relative = path.removeprefix("/static/").lstrip("/\\")
            static_root = STATIC_DIR.resolve()
            static_path = (STATIC_DIR / relative).resolve()
            if static_path != static_root and static_root not in static_path.parents:
                self.send_error(404)
                return
            file_response(self, static_path)
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/predict":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body or "{}")
            json_response(self, predict_payload(payload))
        except Exception as exc:
            traceback.print_exc()
            json_response(self, {"error": str(exc)}, status=400)


def main():
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    print(f"Hyderabad price app running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

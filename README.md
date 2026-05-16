# Hyderabad House Price Prediction

A local web app for predicting Hyderabad real estate prices from a trained scikit-learn model.

## Run locally

```powershell
.\.env\Scripts\python.exe app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Model inputs

- Location
- Area in sqft
- Building status
- BHK
- Property type

The app loads `model.pkl` and uses `cleaed_data.csv` to populate dropdown values.

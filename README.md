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

## Deploy on Render

1. Push this repository to GitHub.
2. In Render, create a new Web Service from the GitHub repository.
3. Use these settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: python app.py
```

Render provides the `PORT` environment variable automatically. The app binds to `0.0.0.0`, which is required for public web services.

## Model inputs

- Location
- Area in sqft
- Building status
- BHK
- Property type

The app loads `model.pkl` and uses `cleaed_data.csv` to populate dropdown values.

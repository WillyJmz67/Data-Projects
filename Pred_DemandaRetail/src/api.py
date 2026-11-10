"""
API REST para servir predicciones del modelo de demanda.

Endpoints:
    GET  /health              -> estado del servicio y modelo cargado
    POST /predict             -> {"store_id": 1, "date": "2025-08-18"}

La fecha es una fecha FUTURA (posterior al último día con datos). La API construye
las features temporales y de inercia para esa fecha concreta, así que dos fechas
distintas devuelven predicciones distintas.
"""

import os
import sys
from datetime import date

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import (  # noqa: E402
    OUTPUT_DIR, load_latest_model, predict_for_date, select_feature_cols,
)

app = FastAPI(
    title="API de Predicción de Demanda",
    version="1.1",
    description="Predicción de ventas diarias por tienda (modelo Random Forest / XGBoost).",
)

# --- Carga del modelo y del histórico al arrancar ---------------------------
model, MODEL_FILE = load_latest_model()
df_hist = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))
df_hist['Date'] = pd.to_datetime(df_hist['Date'])
FEATURE_COLS = select_feature_cols(df_hist)
LAST_DATE = df_hist['Date'].max().date()


class PredictionRequest(BaseModel):
    store_id: int
    date: str  # Formato: YYYY-MM-DD (debe ser posterior a LAST_DATE)

    @field_validator('date')
    @classmethod
    def _validate_date(cls, value):
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("La fecha debe tener formato YYYY-MM-DD")
        return value


class PredictionResponse(BaseModel):
    store_id: int
    date: str
    predicted_sales: float
    confidence: str
    model_name: str


@app.get("/")
def root():
    return {
        "message": "API de Predicción de Demanda activa",
        "model": MODEL_FILE,
        "features": len(FEATURE_COLS),
        "history_until": LAST_DATE.isoformat(),
    }


@app.get("/stores")
def stores():
    """Tiendas disponibles para predecir."""
    ids = sorted(int(s) for s in df_hist['Store'].unique())
    return {"count": len(ids), "store_ids": ids}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    store_id = request.store_id
    if store_id not in set(df_hist['Store'].unique()):
        raise HTTPException(
            status_code=404,
            detail=f"Tienda {store_id} no encontrada en el histórico procesado.",
        )

    try:
        prediction, confidence = predict_for_date(
            model, df_hist, store_id, request.date, FEATURE_COLS
        )
    except ValueError as exc:
        # Fecha no futura o horizonte demasiado largo: es un error del cliente.
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # pragma: no cover - salvaguarda
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}")

    return PredictionResponse(
        store_id=store_id,
        date=request.date,
        predicted_sales=round(prediction, 2),
        confidence=confidence,
        model_name=MODEL_FILE,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

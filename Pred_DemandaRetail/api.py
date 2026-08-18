"""
API REST para servir predicciones del modelo de demanda
Endpoint: POST /predict
Body: {"store_id": 1, "date": "2025-08-18"}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime

app = FastAPI(title="API de Predicción de Demanda", version="1.0")

# Cargar modelo al iniciar
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')

model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')]
if not model_files:
    raise RuntimeError("No se encontró modelo entrenado")

with open(os.path.join(MODEL_DIR, model_files[0]), 'rb') as f:
    model = pickle.load(f)

df_hist = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))

class PredictionRequest(BaseModel):
    store_id: int
    date: str  # Formato: YYYY-MM-DD

class PredictionResponse(BaseModel):
    store_id: int
    date: str
    predicted_sales: float
    confidence: str

@app.get("/")
def root():
    return {"message": "API de Predicción de Demanda activa", "model": model_files[0]}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        # Validar tienda
        store_data = df_hist[df_hist['Store'] == request.store_id]
        if len(store_data) == 0:
            raise HTTPException(status_code=404, detail=f"Tienda {request.store_id} no encontrada")
        
        # Preparar features (simplificado para el ejemplo)
        exclude_cols = ['Store', 'Date', 'Sales', 'Customers', 'Open', 
                       'Promo2SinceWeek', 'Promo2SinceYear',
                       'CompetitionOpenSinceMonth', 'CompetitionOpenSinceYear',
                       'StateHoliday', 'SchoolHoliday']
        feature_cols = [col for col in df_hist.select_dtypes(include=[np.number]).columns 
                       if col not in exclude_cols]
        
        # Usar la última fila conocida como base
        last_row = store_data.sort_values('Date').iloc[-1].copy()
        X_pred = pd.DataFrame([last_row])[feature_cols]
        
        # Predecir
        pred = model.predict(X_pred)[0]
        pred = max(0, pred)
        
        return PredictionResponse(
            store_id=request.store_id,
            date=request.date,
            predicted_sales=round(pred, 2),
            confidence="Alta" if pred > 0 else "Baja"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
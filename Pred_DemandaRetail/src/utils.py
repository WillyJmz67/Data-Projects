"""Utilidades compartidas por los scripts del pipeline.

Centralizar aquí la selección de features y la construcción de features para una
fecha futura evita el desajuste clásico entre los scripts que *entrenan* el modelo
(model.py) y los que lo *consumen* (predict.py, api.py, app.py, sql.py): si la lista
de features cambia en un sitio y no en el otro, el modelo recibe columnas distintas
a las del entrenamiento y falla o predice mal sin avisar.
"""

import calendar
import os
import pickle

import joblib
import numpy as np
import pandas as pd

# Extensiones de modelo soportadas. Se prefiere .joblib (comprimido) porque un
# Random Forest sin comprimir sobre 983k filas ocupa ~105 MB y GitHub rechaza
# cualquier fichero de más de 100 MB.
MODEL_EXTENSIONS = ('.joblib', '.pkl')

# Columnas que NUNCA deben entrar al modelo:
#   - identificadores y target: Store, Date, Sales, Customers
#   - la columna original 'Open' (se sustituye por 'IsOpen', ya imputada)
#   - columnas con nulos o categóricas sin codificar
EXCLUDE_COLS = [
    'Store', 'Date', 'Sales', 'Customers',
    'Open', 'Promo2SinceWeek', 'Promo2SinceYear',
    'CompetitionOpenSinceMonth', 'CompetitionOpenSinceYear',
    'StateHoliday', 'SchoolHoliday',
]

# Columnas cuyos NaN SÍ son motivo de descarte de la fila: son las features de
# inercia, que necesitan historia previa de la tienda para existir.
LAG_COLUMN_PREFIXES = ('Sales_Lag_', 'Sales_Rolling', 'Customers_Lag_', 'Customers_Rolling')

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')


def select_feature_cols(df):
    """Devuelve las columnas usables como features, en un orden estable.

    OJO: pandas 2+ genera las columnas de ``get_dummies`` con dtype ``bool``, y
    ``select_dtypes(include=[np.number])`` **no** las incluye. Filtrar sólo por
    ``np.number`` hace desaparecer en silencio las one-hot de StoreType y
    Assortment, y el modelo entrena sin la información de tipo de tienda.
    Por eso se incluye explícitamente el dtype ``bool``.
    """
    candidates = df.select_dtypes(include=[np.number, 'bool']).columns
    return [c for c in candidates if c not in EXCLUDE_COLS]


def load_latest_model(model_dir=None):
    """Carga el modelo más reciente. Devuelve ``(modelo, nombre_fichero)``.

    Acepta ``.joblib`` (comprimido, recomendado) y ``.pkl`` (formato antiguo).
    """
    model_dir = model_dir or MODEL_DIR
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"No existe el directorio de modelos: {model_dir}")

    files = [f for f in os.listdir(model_dir) if f.endswith(MODEL_EXTENSIONS)]
    if not files:
        raise FileNotFoundError(
            f"No hay ningún modelo ({'/'.join(MODEL_EXTENSIONS)}) en {model_dir}. "
            "Ejecuta src/model.py primero."
        )

    files.sort(key=lambda f: os.path.getmtime(os.path.join(model_dir, f)), reverse=True)
    path = os.path.join(model_dir, files[0])
    if files[0].endswith('.joblib'):
        return joblib.load(path), files[0]
    with open(path, 'rb') as fh:
        return pickle.load(fh), files[0]


def add_date_features(row, day):
    """Rellena en ``row`` las features temporales derivadas de ``day`` (date)."""
    row['Date'] = pd.Timestamp(day)
    row['Year'] = day.year
    row['Month'] = day.month
    row['Day'] = day.day
    row['DayOfWeek'] = day.weekday()
    row['WeekOfYear'] = day.isocalendar()[1]
    row['DayOfYear'] = day.timetuple().tm_yday
    row['Quarter'] = (day.month - 1) // 3 + 1
    row['IsWeekend'] = int(day.weekday() >= 5)
    row['IsMonthStart'] = int(day.day == 1)
    row['IsMonthEnd'] = int(day.day == calendar.monthrange(day.year, day.month)[1])
    return row


def _shifted_window(values, window, shift=7):
    """Ventana de ``window`` valores que terminan ``shift`` posiciones atrás.

    Reproduce exactamente ``serie.shift(shift).rolling(window).mean()`` de
    features.py: la ventana NO incluye los últimos ``shift`` días. Si se usara la
    ventana "pegada" al presente, las features de entrenamiento y las de
    producción no serían la misma cosa (train/serve skew).
    """
    end = len(values) - shift
    if end <= 0:
        return []
    return values[max(0, end - window):end]


def _mean(values):
    return float(np.mean(values)) if values else 0.0


def _std(values):
    # pandas .std() usa ddof=1; con una sola observación devuelve NaN, que es
    # justo el caso que features.py descartaba. En producción usamos 0.0.
    return float(np.std(values, ddof=1)) if len(values) > 1 else 0.0


def predict_for_date(model, df_hist, store_id, target_date, feature_cols, max_horizon_days=30):
    """Predice las ventas de ``store_id`` para ``target_date``.

    Los lags y las medias móviles se recalculan día a día desde la última fecha
    conocida: si el objetivo está a más de un día vista, la predicción de cada día
    se encadena como si fuese venta real para poder calcular los lags del día
    siguiente (predicción recursiva, igual que en el entrenamiento).

    Supuestos documentados (en producción vendrían de otros sistemas):
      * ``IsOpen``: se estima desde el patrón histórico de la tienda por día de la
        semana (una tienda cerrada los domingos se predice como cerrada).
      * ``Promo``: se arrastra el último valor observado (calendario de promociones).
      * ``Customers``: no se conocen a futuro; se mantiene el último patrón observado.

    Devuelve ``(prediccion, confianza)``.
    """
    store_hist = df_hist[df_hist['Store'] == store_id].sort_values('Date').copy()
    if store_hist.empty:
        raise ValueError(f"La tienda {store_id} no tiene histórico.")

    store_hist['Date'] = pd.to_datetime(store_hist['Date'])
    last_date = store_hist['Date'].max().normalize()
    target = pd.Timestamp(target_date).normalize()
    horizon = (target - last_date).days

    if horizon < 1:
        raise ValueError(
            f"La fecha pedida ({target.date()}) no es futura: "
            f"el histórico llega hasta {last_date.date()}."
        )
    if horizon > max_horizon_days:
        raise ValueError(
            f"Horizonte de {horizon} días demasiado largo (máximo {max_horizon_days})."
        )

    sales = store_hist['Sales'].astype(float).tolist()
    customers = store_hist['Customers'].astype(float).tolist()
    base_row = store_hist.iloc[-1].copy()

    # Patrón de apertura por día de la semana (IsOpen es la feature más importante).
    open_by_dow = store_hist.assign(dow=store_hist['Date'].dt.dayofweek) \
        .groupby('dow')['IsOpen'].mean()

    prediction = None
    for step in range(1, horizon + 1):
        day = (last_date + pd.Timedelta(days=step)).date()
        row = add_date_features(base_row.copy(), day)
        row['IsOpen'] = int(open_by_dow.get(day.weekday(), 1) >= 0.5)

        for lag in (7, 14, 21, 30):
            row[f'Sales_Lag_{lag}'] = sales[-lag] if len(sales) >= lag else sales[0]
        for window in (7, 14, 30):
            win = _shifted_window(sales, window)
            row[f'Sales_RollingMean_{window}'] = _mean(win)
            row[f'Sales_RollingStd_{window}'] = _std(win)

        cust_win = _shifted_window(customers, 7)
        row['Customers_Lag_7'] = customers[-7] if len(customers) >= 7 else customers[0]
        row['Customers_RollingMean_7'] = _mean(cust_win)

        pred = float(model.predict(pd.DataFrame([row])[feature_cols])[0])
        prediction = max(0.0, pred)
        sales.append(prediction)

    return prediction, confidence_label(sales, prediction)


def confidence_label(sales_history, prediction):
    """Confianza cualitativa basada en la volatilidad reciente de la tienda.

    Es una heurística honesta: si la desviación de los últimos 30 días es pequeña
    frente a la predicción, la serie es estable y el pronóstico es más fiable.
    """
    if prediction <= 0:
        return 'Baja'
    recent = sales_history[-30:]
    if len(recent) < 2:
        return 'Media'
    relative_volatility = float(np.std(recent, ddof=1)) / prediction
    if relative_volatility < 0.25:
        return 'Alta'
    if relative_volatility < 0.50:
        return 'Media'
    return 'Baja'

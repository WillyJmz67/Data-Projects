"""Entrena y guarda los modelos de mantenimiento predictivo (NASA Turbofan).

Reproduce exactamente lo que hace `notebooks/02_modelo.ipynb`, pero como script
ejecutable y reproducible desde la terminal:

    python -m src.train_model

- Clasificación de `label` (¿fallará en <= RUL_THRESHOLD ciclos?).
- Regresión de `rul` (ciclos restantes).

Los modelos se guardan comprimidos (`compress=3`).

Sobre el tamaño: el regresor usa `min_samples_leaf=5`. Con 100 árboles sin límite de
profundidad el modelo crece hasta ~15 M de nodos (206 MB comprimido, no cabe en GitHub) y
además generaliza peor. Con `min_samples_leaf=5` baja a ~2.6 M de nodos (54 MB) y **mejora**
el RMSE de test (62.28 vs 62.36 ciclos): menos sobreajuste al ruido de los sensores.

Nota sobre el split: `id` sólo es único DENTRO de cada escenario (FD001 y FD002
comparten los ids 1..100). El split por `id` garantiza que ningún motor quede
partido entre train y val, pero el recuento de "motores" es en realidad el de
identificadores únicos. Para un split estrictamente por motor usar la clave
compuesta (scenario, id).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error

from src.config import BASE_DIR, CURATED_DIR, FEATURES, RAW_DIR, RUL_THRESHOLD

MODELS = BASE_DIR / "models"
SCENARIOS = ["FD001", "FD002", "FD003", "FD004"]


def load_train() -> pd.DataFrame:
    files = sorted(CURATED_DIR.glob("train_FD00*.parquet"))
    if not files:
        raise FileNotFoundError(
            f"No hay train_FD00*.parquet en {CURATED_DIR}. "
            f"Ejecuta antes: python -m src.main"
        )
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def build_test() -> pd.DataFrame:
    """Reconstruye la RUL real del test set con RUL_FD00X.txt.

    En los ficheros `test_*` el motor NO llega a falla, así que el `rul` que
    calcula el ETL (max_cycle - cycle) no es la RUL real. La RUL real es
    `rul_truth + (ultimo_ciclo - ciclo_actual)`.
    """
    frames = []
    for fd in SCENARIOS:
        path = CURATED_DIR / f"test_{fd}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"Falta {path}. Ejecuta antes: python -m src.main"
            )
        t = pd.read_parquet(path)
        rul_truth = np.atleast_1d(np.loadtxt(RAW_DIR / f"RUL_{fd}.txt"))
        parts = []
        for i, mid in enumerate(t["id"].unique()):
            sub = t[t["id"] == mid].copy()
            last = sub["cycle"].max()
            sub["rul"] = int(rul_truth[i]) + (last - sub["cycle"])
            sub["label"] = (sub["rul"] <= RUL_THRESHOLD).astype(int)
            parts.append(sub)
        frames.append(pd.concat(parts, ignore_index=True))
    return pd.concat(frames, ignore_index=True)


def train() -> dict:
    df_train = load_train()
    df_test = build_test()

    # 1. Features: se descartan las columnas sin varianza (sensores constantes).
    constantes = [c for c in FEATURES if df_train[c].nunique() <= 1]
    feature_cols = [c for c in FEATURES if c not in constantes]
    print(f"[train] filas train={len(df_train)} test={len(df_test)}")
    print(f"[train] constantes eliminadas={constantes} | n_features={len(feature_cols)}")

    # 2. Split anti-fuga por motor (no por fila): cada motor es una serie temporal.
    motors = df_train["id"].unique()
    np.random.seed(42)
    np.random.shuffle(motors)
    split = int(0.8 * len(motors))
    train_motors, val_motors = motors[:split], motors[split:]
    train = df_train[df_train["id"].isin(train_motors)]
    val = df_train[df_train["id"].isin(val_motors)]
    print(f"[train] ids train/val: {len(train_motors)}/{len(val_motors)}")

    # 3. Clasificación (fallo inminente).
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(train[feature_cols], train["label"])
    val_pred_c = clf.predict(val[feature_cols])

    # 4. Regresión (RUL). min_samples_leaf=5: reduce el tamaño del modelo ~6x y
    #    mejora la generalización (ver docstring del módulo).
    reg = RandomForestRegressor(
        n_estimators=100, random_state=42, n_jobs=-1, min_samples_leaf=5
    )
    reg.fit(train[feature_cols], train["rul"])
    val_pred_r = reg.predict(val[feature_cols])

    # 5. Evaluación honesta sobre el test set (RUL reconstruida).
    test_pred_c = clf.predict(df_test[feature_cols])
    test_pred_r = reg.predict(df_test[feature_cols])

    metrics = {
        "val_accuracy": accuracy_score(val["label"], val_pred_c),
        "val_f1": f1_score(val["label"], val_pred_c),
        "val_rmse": mean_squared_error(val["rul"], val_pred_r) ** 0.5,
        "test_accuracy": accuracy_score(df_test["label"], test_pred_c),
        "test_f1": f1_score(df_test["label"], test_pred_c),
        "test_rmse": mean_squared_error(df_test["rul"], test_pred_r) ** 0.5,
    }

    # 6. Persistencia comprimida.
    MODELS.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODELS / "modelo_label.joblib", compress=3)
    joblib.dump(reg, MODELS / "modelo_rul.joblib", compress=3)

    print("\n=== MÉTRICAS (RandomForest, 100 árboles) ===")
    print(f"{'Métrica':<24}{'Validación':>12}{'Test (RUL real)':>18}")
    print(f"{'Accuracy (clasificación)':<24}{metrics['val_accuracy']:>12.3f}{metrics['test_accuracy']:>18.3f}")
    print(f"{'F1 clase label=1':<24}{metrics['val_f1']:>12.3f}{metrics['test_f1']:>18.3f}")
    print(f"{'RMSE RUL (ciclos)':<24}{metrics['val_rmse']:>12.2f}{metrics['test_rmse']:>18.2f}")
    print(f"\n[train] modelos guardados en {MODELS} (compress=3)")
    return metrics


if __name__ == "__main__":
    train()

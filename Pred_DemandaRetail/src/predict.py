"""Genera predicciones de demanda de los próximos días para una o varias tiendas.

Uso:
    python src/predict.py                    # tienda por defecto, 7 días
    python src/predict.py --store 1088       # una tienda concreta
    python src/predict.py --stores 1088,955  # varias tiendas
    python src/predict.py --days 14          # otro horizonte
"""

import argparse
import os
import sys
from datetime import timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import (  # noqa: E402
    OUTPUT_DIR, add_date_features, load_latest_model, predict_for_date, select_feature_cols,
)


def forecast_store(model, df_hist, feature_cols, store_id, days):
    """Devuelve un DataFrame con el pronóstico de `days` días para `store_id`."""
    store_hist = df_hist[df_hist['Store'] == store_id].sort_values('Date')
    if store_hist.empty:
        raise ValueError(f"La tienda {store_id} no tiene histórico.")

    last_date = pd.to_datetime(store_hist['Date'].max())
    last_sales = float(store_hist['Sales'].iloc[-1])
    avg_sales = float(store_hist['Sales'].mean())

    rows = []
    for offset in range(1, days + 1):
        future_date = (last_date + timedelta(days=offset)).date()
        pred, confidence = predict_for_date(
            model, df_hist, store_id, future_date, feature_cols
        )
        rows.append({
            'date': future_date,
            'day_name': future_date.strftime('%A'),
            'predicted_sales': round(pred, 2),
            'confidence': confidence,
        })

    forecast = pd.DataFrame(rows)
    forecast.attrs['last_date'] = last_date.date()
    forecast.attrs['last_sales'] = last_sales
    forecast.attrs['avg_sales'] = avg_sales
    return forecast


def main():
    parser = argparse.ArgumentParser(description="Pronóstico de demanda por tienda")
    parser.add_argument('--store', type=int, default=None,
                        help="ID de tienda (por defecto: la de más ventas históricas)")
    parser.add_argument('--stores', type=str, default=None,
                        help="Lista de IDs separada por comas, p. ej. 1088,955")
    parser.add_argument('--days', type=int, default=7, help="Días a predecir (por defecto 7)")
    args = parser.parse_args()

    print("=" * 60)
    print("🔮 PREDICCIÓN DE DEMANDA - MODO PRODUCCIÓN")
    print("=" * 60)

    try:
        model, model_file = load_latest_model()
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return 1
    print(f"✅ Modelo cargado: {model_file}")

    df_hist = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))
    df_hist['Date'] = pd.to_datetime(df_hist['Date'])
    print(f"✅ Datos históricos cargados: {len(df_hist):,} registros")

    feature_cols = select_feature_cols(df_hist)
    print(f"✅ Features del modelo: {len(feature_cols)}")

    if args.stores:
        store_ids = [int(s) for s in args.stores.split(',')]
    elif args.store is not None:
        store_ids = [args.store]
    else:
        # Por defecto, la tienda con más ventas acumuladas: es la más relevante
        # para el negocio y siempre existe en el dataset procesado.
        store_ids = [int(df_hist.groupby('Store')['Sales'].sum().idxmax())]
        print(f"ℹ️  Sin --store/--stores: se usa la tienda de más ventas ({store_ids[0]})")

    exit_code = 0
    for store_id in store_ids:
        try:
            forecast = forecast_store(model, df_hist, feature_cols, store_id, args.days)
        except ValueError as exc:
            print(f"\n❌ Tienda {store_id}: {exc}")
            exit_code = 1
            continue

        print("\n" + "=" * 60)
        print(f"📈 PREDICCIÓN DE DEMANDA - TIENDA {store_id}")
        print("=" * 60)
        print(f"\nBasado en datos hasta: {forecast.attrs['last_date']}")
        print(f"Ventas promedio históricas: €{forecast.attrs['avg_sales']:,.0f}/día\n")
        print(forecast.to_string(index=False))

        total = forecast['predicted_sales'].sum()
        best_day = forecast.loc[forecast['predicted_sales'].idxmax()]
        worst_day = forecast.loc[forecast['predicted_sales'].idxmin()]

        print(f"\n{'='*60}")
        print("💡 RESUMEN PARA EL GERENTE DE TIENDA:")
        print(f"{'='*60}")
        print(f"  📦 Total estimado próximos {args.days} días: €{total:,.0f}")
        print(f"  📊 Promedio diario estimado: €{forecast['predicted_sales'].mean():,.0f}")
        print(f"  ⚠️ Día con mayor demanda: {best_day['day_name']} (€{best_day['predicted_sales']:,.0f})")
        print(f"  ✅ Día con menor demanda: {worst_day['day_name']} (€{worst_day['predicted_sales']:,.0f})")
        print("\n💼 RECOMENDACIÓN DE INVENTARIO:")
        print(f"  - Pedir stock para cubrir €{total * 1.1:,.0f} (+10% margen de seguridad)")
        print(f"  - Reforzar personal el {best_day['day_name']}")

        output_pred = os.path.join(OUTPUT_DIR, f'prediccion_tienda_{store_id}.csv')
        forecast.to_csv(output_pred, index=False)
        print(f"\n✅ Predicciones guardadas en: {output_pred}")

    return exit_code


if __name__ == '__main__':
    sys.exit(main())

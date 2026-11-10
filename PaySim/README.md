# 🏦 Detección de Fraude en Transacciones Móviles (PaySim) con PySpark

Pipeline de análisis y Machine Learning con **PySpark** para detectar transacciones fraudulentas
en un ecosistema de pagos móviles. El análisis se basa en el dataset sintético **PaySim**, que
simula transacciones financieras reales para investigación de fraude.

---

## 🎯 Objetivo

Identificar patrones de comportamiento fraudulentos —transferencias sospechosas y retiros de
efectivo inusuales— mediante ingeniería de características y un clasificador de Random Forest,
y **traducir el resultado a dinero**: cuánto capital se protege y cuánto se fuga.

El problema es de **clasificación binaria muy desbalanceada**: solo ~0,13 % de las transacciones
son fraude. Por eso la métrica relevante no es el *accuracy*, sino el **recall** y el **F1 sobre
la clase fraude**.

---

## 📦 Dataset

| | |
|---|---|
| Fuente | [Kaggle — PaySim1 (ealaxi)](https://www.kaggle.com/datasets/ealaxi/paysim1) |
| Fichero | `PS_20174392719_1491204439457_log.csv` |
| Tamaño | ~470 MB · 6.362.620 filas × 11 columnas |
| Cobertura | 744 pasos temporales (1 paso = 1 hora → ~31 días) |
| Licencia | CC BY-SA 4.0 |

> El CSV **no se versiona** (470 MB y no redistribuible). Descárgalo y colócalo **junto al
> notebook**. El notebook también busca en `data/` y en la ubicación original de desarrollo;
> si no lo encuentra, se detiene con un mensaje que indica dónde ponerlo.

**Esquema** (definido explícitamente con `StructType`, sin inferencia):

`step`, `type`, `amount`, `nameOrig`, `oldbalanceOrg`, `newbalanceOrig`, `nameDest`,
`oldbalanceDest`, `newbalanceDest`, `isFraud`, `isFlaggedFraud`

---

## 🛠️ Stack

- **PySpark 4.2** (Spark SQL + MLlib)
- **Java 17 o 21** — Spark **no** soporta Java 25
- **Python 3.10+**
- **pandas + matplotlib + seaborn** para la visualización final

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

---

## 🚀 Cómo ejecutar

1. Descarga el dataset de Kaggle y colócalo junto al notebook.
2. Comprueba que tienes **Java 21** (el notebook fija `JAVA_HOME` a `jdk-21.0.10` y avisa si no existe).
3. Abre `PaySim_P1PySpark.ipynb` y **ejecuta las celdas en orden**.

La celda de escritura en Parquet está **comentada a propósito**: en Windows requiere `winutils.exe`.
Si trabajas en Linux/macOS, descomenta esas dos líneas.

---

## 🔄 Pipeline

1. **Carga** — lectura del CSV con esquema estricto `StructType` y verificación de nulos por columna.
2. **Ingeniería de características**
   - `errorBalanceOrig` = `(oldbalanceOrg - amount) - newbalanceOrig`
   - `errorBalanceDest` = `(oldbalanceDest + amount) - newbalanceDest`
   - `avg_prev_amount` = media histórica del importe **por usuario**, con una *window function*
     (`partitionBy(nameOrig).orderBy(step).rowsBetween(unboundedPreceding, -1)`). Al usar solo
     filas anteriores, **no hay fuga temporal**; la primera transacción de cada usuario se rellena con 0.
3. **Transformación** — `StringIndexer` sobre `type` y `VectorAssembler` con 10 features.
4. **Modelado** — `RandomForestClassifier` (20 árboles), split 70/30 con semilla fija.

---

## 🤖 Modelo y resultados

Se utilizó un **Random Forest Classifier**. El notebook imprime ahora AUC-ROC, **recall,
precision y F1 sobre la clase fraude**, además de la matriz de confusión.

- **AUC-ROC ≈ 0,998** — excelente capacidad de separación.
- **Recall** — captura la gran mayoría de los fraudes reales (el valor exacto lo imprime el notebook).
- **Variables más predictivas:** la familia de errores de balance domina la importancia del modelo
  (`errorBalanceDest` y `errorBalanceOrig`), seguida de `newbalanceOrig`.

### ⚠️ Nota metodológica importante

`errorBalance*` son **casi separadores perfectos en PaySim**, y no por mérito del modelo: el
generador sintético de datos deja los saldos inconsistentes precisamente en las transacciones
fraudulentas. Es decir, el AUC tan alto es en buena parte un **artefacto del dataset**, no una
capacidad que se traslade sin más a datos reales. Merece la pena decirlo antes de que lo pregunte
un entrevistador.

Sobre el desbalanceo de clases (~0,13 % de fraude): el modelo **no** usa ponderación ni
submuestreo. Funciona porque las features son muy potentes, pero lo correcto en producción sería
usar `weightCol` y elegir el umbral de decisión en función del coste de un falso negativo.

---

## 💰 Impacto económico

El notebook traduce el resultado a términos de negocio, **sobre el conjunto de test**:

- **Dinero salvado:** importe total de los fraudes detectados y bloqueados.
- **Riesgo de fuga:** importe de los fraudes **no** detectados (falsos negativos).
- **Eficiencia por monto:** porcentaje del capital **fraudulento** que el sistema logra proteger.

---

## 🧩 Desafíos técnicos resueltos

Los bugs que aparecieron al ejecutar el pipeline de verdad, no al leerlo:

| Síntoma | Causa raíz | Arreglo |
|---|---|---|
| El pipeline **se caía** en la celda 3 pese a que el comentario decía *"celda a omitir"* | La celda que escribe Parquet estaba **viva**, no comentada. En Windows `df.write.parquet` necesita `winutils.exe` y falla con `java.io.FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset` | Celda comentada de verdad, con explicación y la alternativa para Linux/macOS |
| La tabla de métricas mostraba **99,60 % de recall** siempre, con cualquier dato | El valor estaba **hardcodeado** en el DataFrame de resumen (`"99.60%", # O el valor real que quieras poner`) | El recall se **calcula** desde la matriz de confusión (`tp / (tp + fn)`) |
| El notebook no arrancaba en otro equipo | Ruta **absoluta** al CSV, apuntando a una carpeta que ya no existe | Resolución por lista de candidatos + error explícito con las rutas probadas |
| `SparkContext` fallaba con `WinError 2` | `SPARK_HOME` apuntando a una instalación de Spark **ya borrada** | Se documenta la comprobación; con `pip install pyspark` conviene no tener `SPARK_HOME` obsoleto |
| Spark arrancaba con Java 25 y fallaba | Spark no soporta Java 25 (el `java` del PATH del equipo) | `JAVA_HOME` fijado a Java 21, ahora con aviso si la ruta no existe |

**Aprendizaje clave:** un notebook puede "funcionar" durante meses con una métrica inventada y una
celda que nadie ejecuta. La única forma de saberlo es **ejecutarlo entero** y comparar la salida
con lo que dice el README.

---

## 📁 Estructura

```
PaySim/
├── PaySim_P1PySpark.ipynb      # Notebook: pipeline completo
├── README.md                   # Este fichero
├── requirements.txt            # Dependencias (pyspark, pandas, matplotlib, seaborn)
└── .gitignore                  # Excluye datos, venv y salidas
```

---

## 📝 Notas de entorno (Windows)

- **Java:** instala JDK 17 o 21. Si en el PATH tienes Java 25, Spark fallará; el notebook lo evita
  fijando `JAVA_HOME`.
- **`winutils.exe`:** solo hace falta para escribir Parquet en Windows. Sin él, la celda de Parquet
  está desactivada.
- **pandas 3.x:** PySpark aún avisa de soporte parcial. Por eso `requirements.txt` fija
  `pandas>=2.0,<3.0`.

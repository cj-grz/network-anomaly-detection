# Network Anomaly Detection — SecureOps MX

**Proyecto Integrador de Certificación Senior Data Scientist**  
CERT-TLG-SDS | CRISP-DM | NSL-KDD Dataset

---

## Descripción

Sistema de detección de anomalías en tráfico de red con tres capas:

1. **PySpark MLlib** — Random Forest y GBT para clasificación multiclase de ataques
2. **Autoencoder Keras** — Detección no supervisada de ataques no vistos previamente
3. **Agente Q-Learning** — Decisión inteligente de priorización de alertas (Alert Triage)

El sistema opera sobre el dataset **NSL-KDD** (125,973 registros, 5 categorías de ataque) simulando el entorno de un MSSP SOC (SecureOps MX). La métrica principal es el **Costo Operativo Total (COT)** bajo el constraint duro de **Recall ≥ 0.90**.

---

## Arquitectura

```
NSL-KDD Dataset (125,973 registros)
        │
        ▼
┌─────────────────────────┐
│   PySpark MLlib Pipeline │   StringIndexer → OneHotEncoder
│   (Anti-leakage)         │   → VectorAssembler → StandardScaler
└────────────┬────────────┘
             │
    ┌────────┴─────────┐
    │                  │
    ▼                  ▼
┌─────────┐     ┌──────────────┐
│  RF     │     │ Autoencoder  │   (entrenado SOLO con Normal)
│  GBT    │     │   (Keras)    │
└────┬────┘     └──────┬───────┘
     │                 │
     └────────┬────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Q-Learning Agent   │   60 estados × 3 acciones
   │  (Alert Triage)     │   MongoDB: ventana 100 decisiones
   └──────────┬──────────┘
              │
              ▼
   IGNORAR / MONITOREAR / ESCALAR
```

---

## Estructura del Proyecto

```
network-anomaly-detection/
├── configs/
│   ├── config.yaml              # Hiperparámetros y costos del agente RL
│   └── pipeline_meta.json       # Metadata: label mapping, pesos de clase
├── data/
│   ├── raw/                     # KDDTrain+.txt, KDDTest+.txt
│   └── processed/               # Parquets: train/val/test features
├── models/
│   ├── random_forest/           # Mejor RF (PySpark MLlib)
│   ├── gbt/                     # Mejor GBT One-vs-Rest
│   ├── autoencoder/             # Modelo Keras + threshold
│   └── rl_agent/                # Tabla Q + metadata
├── notebooks/
│   ├── 01_eda.ipynb             #  Análisis exploratorio
│   ├── 02_preprocessing.ipynb  #  Pipeline anti-leakage
│   ├── 03_modeling.ipynb        # Entrenamiento RF, GBT, Autoencoder
│   └── 04_rl_agent.ipynb        # Entrenamiento y evaluación del agente RL
├── reports/                     # Gráficas y CSVs de resultados
├── src/
│   ├── data_pipeline.py         # DataPipeline (PySpark MLlib)
│   ├── train_models.py          # RandomForestModel, GBTModel, AutoencoderModel
│   ├── train_rl_agent.py        # QLearningAgent, AlertEnvironment, baselines
│   └── app.py                   # Dashboard Streamlit (4 vistas)
└── setup.sh                     # Instalación de dependencias
```

---

## Instalación

```bash
# 1. Clonar y navegar al proyecto
cd network-anomaly-detection

# 2. Instalar dependencias
bash setup.sh

# 3. Configurar Java (requerido por PySpark)
export JAVA_HOME="/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home"
```

---

## Ejecución

### Pipeline completo (orden secuencial):

```bash
# Ejecutar notebooks
export JAVA_HOME="/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home"

jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=1800 notebooks/03_modeling.ipynb

jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=900  notebooks/04_rl_agent.ipynb
```

### Dashboard interactivo:

```bash
streamlit run src/app.py
```

---

## Resultados Clave

### Modelos ML (Validation)

| Modelo | F1-macro | Recall DoS | Recall Probe | Recall R2L | Recall U2R |
|--------|----------|-----------|-------------|-----------|-----------|
| Random Forest | — | — | — | — | — |
| GBT One-vs-Rest | — | — | — | — | — |

*Resultados pendientes de ejecutar 03_modeling.ipynb*

### Agente RL (Test FINAL)

| Política | COT | Recall Sistema | Cumple constraint |
|----------|-----|----------------|-------------------|
| Escalar Todo | — | — | — |
| Threshold ≥ 0.85 | — | — | — |
| GBT Argmax | — | — | — |
| Q-Learning | — | — | — |

*Resultados pendientes de ejecutar 04_rl_agent.ipynb*

---

## Integración MLOps (Databricks)

El pipeline también fue ejecutado en **Databricks Community Edition** con:
- **Unity Catalog** para almacenamiento de datos (Delta tables)
- **MLflow Tracking** para experimentos y métricas
- **MLflow Model Registry** — modelo `nslkdd_alert_classifier` v1 (Status: READY)
- F1 baseline en Databricks: **0.7007** (sin pesos de clase ni CrossValidator)

---

## Dataset

**NSL-KDD** — versión mejorada del KDD Cup 1999  
- 125,973 registros de entrenamiento, 22,544 de prueba  
- 41 features + 1 label (5 categorías: Normal, DoS, Probe, R2L, U2R)  
- Desbalance severo: U2R 0.04% en train, R2L sube 10x en test (distribution shift intencional)

---

## Metodología

**CRISP-DM** — 6 fases:

| Fase | Entregable |
|------|-----------|
| Business Understanding | DefinicionPIDA.docx — contexto SecureOps MX |
| Data Understanding | 01_eda.ipynb — análisis de distribuciones y riesgos |
| Data Preparation | 02_preprocessing.ipynb — pipeline anti-leakage |
| Modeling | 03_modeling.ipynb — RF, GBT, Autoencoder |
| Evaluation | 04_rl_agent.ipynb — COT con baselines, constraint Recall ≥ 0.90 |
| Deployment | app.py — dashboard Streamlit + Databricks MLflow |

---

## Autor

**Justin Valdez** | Senior Data Scientist — CERT-TLG-SDS  
Mayo 2026

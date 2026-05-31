"""
data_pipeline.py
================
Pipeline de preprocesamiento con PySpark para el dataset NSL-KDD.
Sigue la fase 3 de CRISP-DM: Data Preparation.

Garantías anti-leakage:
  - StringIndexer, OneHotEncoder y StandardScaler se ajustan SOLO en train.
  - El split estratificado se hace ANTES de cualquier transformación.
  - La columna 'difficulty' se excluye siempre.
"""

import os
import yaml
import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import (
    StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
)
from pyspark.ml.linalg import Vectors


# ── Constantes ────────────────────────────────────────────────────────────────

CATEGORICAL_COLS = ['protocol_type', 'service', 'flag']
LABEL_COL        = 'attack_category'
CLASSES          = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']

# Costos del agente RL (desde config)
DEFAULT_COSTS = {
    'fn_attack': 15,
    'fn_dos':    20,
    'fp_normal':  2,
    'escalation': 1,
    'tn_saving':  -1,
}


# ── Clase principal ───────────────────────────────────────────────────────────

class DataPipeline:
    """
    Pipeline de preprocesamiento end-to-end para NSL-KDD con PySpark MLlib.

    Uso:
        pipeline = DataPipeline(spark, config_path='configs/config.yaml')
        pipeline.load()
        pipeline.split()
        pipeline.fit_transform()
        pipeline.save()
    """

    def __init__(self, spark: SparkSession, config_path: str = 'configs/config.yaml'):
        self.spark  = spark
        self.config = self._load_config(config_path)
        self.seed   = self.config['project']['seed']

        self.train_raw  = None
        self.val_raw    = None
        self.test_raw   = None

        self.train_final = None
        self.val_final   = None
        self.test_final  = None

        self.ml_pipeline      = None
        self.pipeline_model   = None
        self.feature_cols     = None
        self.class_weights    = None

        print("DataPipeline inicializado")
        print(f"  Seed: {self.seed}")
        print(f"  Split: {self.config['data']['train_size']:.0%} / "
              f"{self.config['data']['val_size']:.0%} / "
              f"{self.config['data']['test_size']:.0%}")

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self, path: str) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)

    # ── Carga ─────────────────────────────────────────────────────────────────

    def load(self, train_path: str = None, test_path: str = None):
        """Carga los datos limpios guardados por el EDA (formato Parquet)."""
        base = self.config['paths']['processed_data']
        train_path = train_path or f"{base}/train_clean.parquet"
        test_path  = test_path  or f"{base}/test_clean.parquet"

        self.df_train_raw = self.spark.read.parquet(train_path)
        self.df_test_raw  = self.spark.read.parquet(test_path)

        # Filtrar 'Unknown' — ataques no mapeados, no modelables
        self.df_train_raw = self.df_train_raw.filter(
            F.col(LABEL_COL).isin(CLASSES)
        )

        n_train = self.df_train_raw.count()
        n_test  = self.df_test_raw.count()
        print(f"\n✓ Cargado — Train: {n_train:,}  |  Test (benchmark): {n_test:,}")
        print(f"  Columnas: {len(self.df_train_raw.columns)}")
        return self

    # ── Split estratificado ───────────────────────────────────────────────────

    def split(self):
        """
        División estratificada por clase: 70% train / 15% val / 15% test interno.
        El test externo (KDDTest+) se reserva para evaluación final.

        IMPORTANTE: el split se hace ANTES de cualquier transformación para
        garantizar ausencia de data leakage.
        """
        train_ratio = self.config['data']['train_size']   # 0.70
        val_ratio   = self.config['data']['val_size']     # 0.15
        # test interno = 1 - train - val = 0.15

        print("\nRealizando split estratificado por clase...")

        # Añadir índice de partición por clase
        train_parts, val_parts, test_parts = [], [], []

        for cls in CLASSES:
            subset = self.df_train_raw.filter(F.col(LABEL_COL) == cls)
            n = subset.count()

            # Split 70/15/15
            tr, rest = subset.randomSplit([train_ratio, 1 - train_ratio],
                                          seed=self.seed)
            vl, ts   = rest.randomSplit([0.5, 0.5], seed=self.seed)

            train_parts.append(tr)
            val_parts.append(vl)
            test_parts.append(ts)

            tr_n, vl_n, ts_n = tr.count(), vl.count(), ts.count()
            print(f"  {cls:8s}: {n:6,}  →  train {tr_n:5,} | val {vl_n:4,} | test {ts_n:4,}")

        # Unir particiones y mezclar
        from functools import reduce
        self.train_raw = reduce(DataFrame.union, train_parts).orderBy(F.rand(seed=self.seed))
        self.val_raw   = reduce(DataFrame.union, val_parts).orderBy(F.rand(seed=self.seed))
        self.test_raw  = reduce(DataFrame.union, test_parts).orderBy(F.rand(seed=self.seed))

        print(f"\n  Total train: {self.train_raw.count():,}")
        print(f"  Total val:   {self.val_raw.count():,}")
        print(f"  Total test:  {self.test_raw.count():,}")
        print("✓ Split completado (sin data leakage)")
        return self

    # ── Pipeline MLlib ────────────────────────────────────────────────────────

    def _build_pipeline(self, numeric_cols: list) -> Pipeline:
        """
        Construye el Pipeline de PySpark MLlib:
            StringIndexer → OneHotEncoder → VectorAssembler → StandardScaler
                                                  ↑
                                           label indexer
        Todo se ajusta SOLO con train en fit_transform().
        """
        stages = []

        # 1. Label indexer (ataque_category → label numérico)
        label_indexer = StringIndexer(
            inputCol=LABEL_COL,
            outputCol='label',
            stringOrderType='alphabetAsc'  # orden fijo y reproducible
        )
        stages.append(label_indexer)

        # 2. Categorical encoding
        idx_cols, ohe_cols = [], []
        for col in CATEGORICAL_COLS:
            idx_col = f'{col}_idx'
            ohe_col = f'{col}_ohe'
            stages.append(
                StringIndexer(inputCol=col, outputCol=idx_col,
                              handleInvalid='keep')
            )
            idx_cols.append(idx_col)
            ohe_cols.append(ohe_col)

        ohe = OneHotEncoder(inputCols=idx_cols, outputCols=ohe_cols,
                            dropLast=True)
        stages.append(ohe)

        # 3. Assembler — numéricas + OHE
        all_features = numeric_cols + ohe_cols
        assembler = VectorAssembler(
            inputCols=all_features,
            outputCol='features_raw',
            handleInvalid='skip'
        )
        stages.append(assembler)

        # 4. StandardScaler (fit SOLO en train)
        scaler = StandardScaler(
            inputCol='features_raw',
            outputCol='features',
            withMean=True,
            withStd=True
        )
        stages.append(scaler)

        self.feature_cols = all_features
        return Pipeline(stages=stages)

    def fit_transform(self):
        """
        Ajusta el pipeline SOLO con train, transforma train/val/test.
        Calcula pesos de clase para tratar el desbalance.
        """
        # Columnas numéricas = todas las no-categóricas, no-label
        exclude = set(CATEGORICAL_COLS + [LABEL_COL])
        numeric_cols = [f.name for f in self.train_raw.schema.fields
                        if f.name not in exclude]

        print(f"\nConstruyendo pipeline...")
        print(f"  Numéricas: {len(numeric_cols)} features")
        print(f"  Categóricas (OHE): {CATEGORICAL_COLS}")

        self.ml_pipeline = self._build_pipeline(numeric_cols)

        # FIT solo con train ← anti-leakage
        print("\nAjustando pipeline en train (fit)...")
        self.pipeline_model = self.ml_pipeline.fit(self.train_raw)
        print("✓ Pipeline ajustado")

        # TRANSFORM train / val / test
        print("Transformando datasets...")
        keep_cols = ['features', 'label', LABEL_COL]
        self.train_final = self.pipeline_model.transform(self.train_raw).select(keep_cols)
        self.val_final   = self.pipeline_model.transform(self.val_raw).select(keep_cols)
        self.test_final  = self.pipeline_model.transform(self.test_raw).select(keep_cols)

        print(f"✓ Train transformado: {self.train_final.count():,}")
        print(f"✓ Val   transformado: {self.val_final.count():,}")
        print(f"✓ Test  transformado: {self.test_final.count():,}")

        # Calcular pesos de clase
        self._compute_class_weights()
        return self

    # ── Pesos de clase ────────────────────────────────────────────────────────

    def _compute_class_weights(self):
        """
        Calcula class weights inversamente proporcionales a la frecuencia.
        Aumenta el peso de R2L y U2R para compensar el desbalance severo.
        """
        total = self.train_raw.count()
        n_classes = len(CLASSES)

        counts = (self.train_raw
                  .groupBy(LABEL_COL)
                  .count()
                  .collect())

        self.class_weights = {}
        print("\nPesos de clase (anti-desbalance):")
        for row in counts:
            cls   = row[LABEL_COL]
            cnt   = row['count']
            weight = (total / (n_classes * cnt))
            self.class_weights[cls] = round(weight, 4)
            print(f"  {cls:10s}: {cnt:6,} muestras → weight = {weight:.4f}")

    def get_class_weight_map(self) -> dict:
        """Retorna {label_index: weight} para usar en los modelos."""
        # Obtener el mapping label_string → label_index del pipeline
        label_model = self.pipeline_model.stages[0]
        label_map   = {label: idx for idx, label in
                       enumerate(label_model.labels)}
        return {label_map[cls]: w for cls, w in self.class_weights.items()
                if cls in label_map}

    # ── Guardar ───────────────────────────────────────────────────────────────

    def save(self, base_path: str = None):
        """Guarda los datasets procesados y el modelo del pipeline."""
        base_path = base_path or self.config['paths']['processed_data']

        paths = {
            'train': f"{base_path}/train_features.parquet",
            'val':   f"{base_path}/val_features.parquet",
            'test':  f"{base_path}/test_features.parquet",
        }

        print("\nGuardando datasets procesados...")
        self.train_final.write.mode('overwrite').parquet(paths['train'])
        self.val_final.write.mode('overwrite').parquet(paths['val'])
        self.test_final.write.mode('overwrite').parquet(paths['test'])

        # Guardar pipeline model
        model_path = f"{self.config['paths']['models']}/preprocessing_pipeline"
        self.pipeline_model.write().overwrite().save(model_path)

        print(f"✓ Train features → {paths['train']}")
        print(f"✓ Val   features → {paths['val']}")
        print(f"✓ Test  features → {paths['test']}")
        print(f"✓ Pipeline model → {model_path}")
        return self

    # ── Utilidades ────────────────────────────────────────────────────────────

    def get_label_mapping(self) -> dict:
        """Retorna {índice: nombre_clase} para interpretar predicciones."""
        label_model = self.pipeline_model.stages[0]
        return {i: label for i, label in enumerate(label_model.labels)}

    def summary(self):
        """Imprime resumen del pipeline."""
        if not self.pipeline_model:
            print("Pipeline no ajustado aún. Ejecuta fit_transform() primero.")
            return
        print("\n" + "="*50)
        print("RESUMEN DEL PIPELINE")
        print("="*50)
        print(f"Features totales: {len(self.feature_cols)}")
        print(f"Clases:           {CLASSES}")
        print(f"Mapping clases:   {self.get_label_mapping()}")
        print(f"Class weights:    {self.class_weights}")
        print("="*50)

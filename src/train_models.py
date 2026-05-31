"""
train_models.py
===============
Entrenamiento de los tres modelos del sistema:
  1. Random Forest     — PySpark MLlib (clasificador principal)
  2. Gradient Boosted Trees — PySpark MLlib (clasificador principal)
  3. Autoencoder       — Keras (detector de anomalías, entrenado solo con Normal)

Reglas anti-leakage:
  - RF y GBT: ajustados en train_features.parquet
  - Autoencoder: ajustado SOLO con conexiones Normal del train
  - Threshold del Autoencoder: calibrado en val, NUNCA en test
  - Evaluación final: test evaluado UNA SOLA VEZ al final
"""

import os, json, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')
os.environ['JAVA_HOME'] = '/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home'

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.classification import (
    RandomForestClassifier, GBTClassifier
)
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml import PipelineModel


# ══════════════════════════════════════════════════════════════════════════════
# 1. Clase base de evaluación
# ══════════════════════════════════════════════════════════════════════════════

class ModelEvaluator:
    """Métricas para clasificación multiclase en PySpark."""

    CLASSES = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']

    def __init__(self, label_mapping: dict):
        # label_mapping: {idx_str: class_name}
        self.label_mapping = {int(k): v for k, v in label_mapping.items()}

    def evaluate(self, predictions, dataset_name='Val'):
        """Calcula F1-macro, accuracy y métricas por clase."""
        evaluator = MulticlassClassificationEvaluator(
            labelCol='label', predictionCol='prediction'
        )

        acc     = evaluator.evaluate(predictions, {evaluator.metricName: 'accuracy'})
        f1_mac  = evaluator.evaluate(predictions, {evaluator.metricName: 'f1'})
        wprec   = evaluator.evaluate(predictions, {evaluator.metricName: 'weightedPrecision'})
        wrec    = evaluator.evaluate(predictions, {evaluator.metricName: 'weightedRecall'})

        results = {
            'dataset':           dataset_name,
            'accuracy':          round(acc,    4),
            'f1_macro':          round(f1_mac, 4),
            'weighted_precision':round(wprec,  4),
            'weighted_recall':   round(wrec,   4),
        }

        # Recall por clase (manual con Pandas)
        pred_pd = predictions.select('label', 'prediction').toPandas()
        for idx, cls in self.label_mapping.items():
            tp = ((pred_pd['label'] == idx) & (pred_pd['prediction'] == idx)).sum()
            fn = ((pred_pd['label'] == idx) & (pred_pd['prediction'] != idx)).sum()
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            results[f'recall_{cls}'] = round(recall, 4)

        return results

    def confusion_matrix(self, predictions):
        """Retorna matriz de confusión como DataFrame de pandas."""
        pred_pd = predictions.select('label', 'prediction').toPandas()
        n = len(self.label_mapping)
        matrix = np.zeros((n, n), dtype=int)
        for _, row in pred_pd.iterrows():
            true  = int(row['label'])
            pred  = int(row['prediction'])
            if true < n and pred < n:
                matrix[true][pred] += 1
        labels = [self.label_mapping[i] for i in range(n)]
        return pd.DataFrame(matrix, index=labels, columns=labels)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Random Forest
# ══════════════════════════════════════════════════════════════════════════════

class RandomForestModel:
    """
    Random Forest con PySpark MLlib.
    Soporta pesos de clase para compensar desbalance.
    """

    def __init__(self, config: dict, weight_map: dict, seed: int = 42):
        self.config     = config['model']['random_forest']
        self.seed       = seed
        self.weight_map = weight_map   # {label_idx: weight}
        self.model      = None
        self.best_model = None

    def train(self, train_df, val_df):
        """Entrena con CrossValidator k=5 en train. Selección en val."""
        print("\n" + "="*50)
        print("RANDOM FOREST — Entrenamiento")
        print("="*50)

        # Añadir columna de pesos
        weight_expr = F.create_map(
            [F.lit(x) for kv in self.weight_map.items() for x in kv]
        )
        train_w = train_df.withColumn(
            'classWeight',
            F.coalesce(weight_expr[F.col('label').cast('string')], F.lit(1.0))
        )

        rf = RandomForestClassifier(
            featuresCol='features',
            labelCol='label',
            weightCol='classWeight',
            seed=self.seed,
            numTrees=self.config['num_trees'],
            maxDepth=self.config['max_depth'],
        )

        # Grid de hiperparámetros
        param_grid = (ParamGridBuilder()
                      .addGrid(rf.numTrees,  [50, 100])
                      .addGrid(rf.maxDepth,  [8, 12])
                      .build())

        evaluator = MulticlassClassificationEvaluator(
            labelCol='label',
            predictionCol='prediction',
            metricName='f1'
        )

        cv = CrossValidator(
            estimator=rf,
            estimatorParamMaps=param_grid,
            evaluator=evaluator,
            numFolds=5,
            seed=self.seed,
            parallelism=2
        )

        print("Entrenando con CrossValidator (k=5)... (puede tardar ~5 min)")
        self.model = cv.fit(train_w)
        self.best_model = self.model.bestModel

        best_trees = self.best_model.getNumTrees
        best_depth = self.best_model.getOrDefault('maxDepth')
        print(f"✓ Mejor modelo: numTrees={best_trees}, maxDepth={best_depth}")
        return self

    def predict(self, df):
        return self.best_model.transform(df)

    def feature_importance(self, feature_cols: list) -> pd.DataFrame:
        """Retorna feature importance del Random Forest."""
        importances = self.best_model.featureImportances.toArray()
        n = min(len(importances), len(feature_cols))
        fi = pd.DataFrame({
            'feature':    feature_cols[:n],
            'importance': importances[:n]
        }).sort_values('importance', ascending=False)
        return fi

    def save(self, path: str = 'models/random_forest'):
        self.best_model.write().overwrite().save(path)
        print(f"✓ Random Forest guardado → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Gradient Boosted Trees
# ══════════════════════════════════════════════════════════════════════════════

class GBTModel:
    """
    Gradient Boosted Trees con PySpark MLlib.
    GBT en PySpark solo soporta clasificación binaria nativamente,
    por lo que usamos estrategia One-vs-Rest multiclase.
    """

    def __init__(self, config: dict, seed: int = 42):
        self.config = config['model']['gbt']
        self.seed   = seed
        self.model  = None
        self.best_model = None

    def train(self, train_df, val_df):
        """Entrena GBT con One-vs-Rest y CrossValidator."""
        from pyspark.ml.classification import OneVsRest

        print("\n" + "="*50)
        print("GBT (One-vs-Rest) — Entrenamiento")
        print("="*50)

        gbt = GBTClassifier(
            featuresCol='features',
            labelCol='label',
            seed=self.seed,
            maxIter=self.config['max_iter'],
            maxDepth=self.config['max_depth'],
            stepSize=self.config['step_size'],
        )

        ovr = OneVsRest(
            classifier=gbt,
            featuresCol='features',
            labelCol='label'
        )

        param_grid = (ParamGridBuilder()
                      .addGrid(gbt.maxIter,  [20, 40])
                      .addGrid(gbt.maxDepth, [5, 8])
                      .build())

        evaluator = MulticlassClassificationEvaluator(
            labelCol='label',
            predictionCol='prediction',
            metricName='f1'
        )

        cv = CrossValidator(
            estimator=ovr,
            estimatorParamMaps=param_grid,
            evaluator=evaluator,
            numFolds=3,       # 3 folds para GBT (más lento)
            seed=self.seed,
            parallelism=2
        )

        print("Entrenando GBT One-vs-Rest (k=3)... (puede tardar ~10 min)")
        self.model = cv.fit(train_df)
        self.best_model = self.model.bestModel
        print("✓ GBT entrenado")
        return self

    def predict(self, df):
        return self.best_model.transform(df)

    def save(self, path: str = 'models/gbt'):
        self.best_model.write().overwrite().save(path)
        print(f"✓ GBT guardado → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. Autoencoder (Keras)
# ══════════════════════════════════════════════════════════════════════════════

class AutoencoderModel:
    """
    Autoencoder para detección de anomalías no supervisada.

    REGLA CRÍTICA:
      - Entrenado SOLO con conexiones Normal del conjunto de train.
      - Threshold calibrado en validation, NUNCA en test.
      - Output: anomaly_score = MSE de reconstrucción (normalizado 0-1).
    """

    def __init__(self, config: dict, seed: int = 42):
        self.config    = config['model']['autoencoder']
        self.seed      = seed
        self.model     = None
        self.threshold = None
        self.max_mse   = None

        import tensorflow as tf
        tf.random.set_seed(seed)
        np.random.seed(seed)

    def _build_model(self, input_dim: int):
        """Arquitectura Encoder-Decoder simétrica."""
        import tensorflow as tf
        from tensorflow import keras

        enc_dim = max(input_dim // 4, 8)
        btl_dim = max(input_dim // 8, 4)

        inputs  = keras.Input(shape=(input_dim,))
        encoded = keras.layers.Dense(enc_dim, activation='relu')(inputs)
        encoded = keras.layers.Dense(btl_dim, activation='relu')(encoded)
        decoded = keras.layers.Dense(enc_dim, activation='relu')(encoded)
        outputs = keras.layers.Dense(input_dim, activation='linear')(decoded)

        model = keras.Model(inputs, outputs, name='autoencoder')
        model.compile(
            optimizer=keras.optimizers.Adam(
                learning_rate=self.config['learning_rate']
            ),
            loss='mse'
        )
        return model

    def _spark_to_numpy(self, df, label_filter=None):
        """Convierte features de PySpark a numpy array."""
        if label_filter is not None:
            df = df.filter(F.col('attack_category') == label_filter)
        rows = df.select('features', 'attack_category').collect()
        X = np.array([row['features'].toArray() for row in rows])
        y = np.array([row['attack_category'] for row in rows])
        return X, y

    def train(self, train_df, val_df):
        """
        Entrena el autoencoder SOLO con tráfico Normal del train.
        Calibra el threshold en val (sin ver test).
        """
        print("\n" + "="*50)
        print("AUTOENCODER — Entrenamiento")
        print("="*50)
        print("⚠ Entrenando SOLO con conexiones Normal del train")

        # Extraer solo Normal de train
        X_train_normal, _ = self._spark_to_numpy(train_df, label_filter='Normal')
        print(f"  Muestras Normal para entrenamiento: {len(X_train_normal):,}")

        input_dim   = X_train_normal.shape[1]
        self.model  = self._build_model(input_dim)
        self.model.summary()

        from tensorflow.keras.callbacks import EarlyStopping
        es = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

        history = self.model.fit(
            X_train_normal, X_train_normal,
            epochs=self.config['epochs'],
            batch_size=self.config['batch_size'],
            validation_split=0.1,
            callbacks=[es],
            verbose=1
        )

        print(f"✓ Autoencoder entrenado ({len(history.history['loss'])} epochs)")

        # Calibrar threshold en VALIDATION (nunca en test)
        self._calibrate_threshold(val_df)
        return self

    def _calibrate_threshold(self, val_df):
        """
        Calibra el threshold de anomalía en validation.
        Estrategia: percentil 95 del MSE en conexiones Normales de val.
        """
        print("\nCalibrando threshold en validation...")
        X_val, y_val = self._spark_to_numpy(val_df)

        recon   = self.model.predict(X_val, verbose=0)
        mse_all = np.mean(np.power(X_val - recon, 2), axis=1)

        # Threshold = percentil 95 del MSE en conexiones Normales de val
        normal_mask     = (y_val == 'Normal')
        mse_normal      = mse_all[normal_mask]
        self.max_mse    = float(np.max(mse_all))
        self.threshold  = float(np.percentile(mse_normal, 95))

        print(f"  MSE max en val:              {self.max_mse:.6f}")
        print(f"  Threshold (p95 Normal):      {self.threshold:.6f}")

        # Evaluar detección en val
        anomaly_scores = mse_all / (self.max_mse + 1e-9)
        predicted_anomaly = (mse_all > self.threshold)
        true_anomaly      = (y_val != 'Normal')

        tp = (predicted_anomaly & true_anomaly).sum()
        tn = (~predicted_anomaly & ~true_anomaly).sum()
        fp = (predicted_anomaly & ~true_anomaly).sum()
        fn = (~predicted_anomaly & true_anomaly).sum()

        recall_val = tp / (tp + fn + 1e-9)
        prec_val   = tp / (tp + fp + 1e-9)
        print(f"  Recall (detección ataques):  {recall_val:.4f}")
        print(f"  Precision:                   {prec_val:.4f}")
        print(f"✓ Threshold calibrado en validation (nunca en test)")

    def get_anomaly_scores(self, df) -> pd.DataFrame:
        """
        Retorna DataFrame con anomaly_score (0-1) y predicted_anomaly.
        """
        X, y = self._spark_to_numpy(df)
        recon  = self.model.predict(X, verbose=0)
        mse    = np.mean(np.power(X - recon, 2), axis=1)
        scores = mse / (self.max_mse + 1e-9)
        return pd.DataFrame({
            'attack_category':  y,
            'anomaly_score':    scores,
            'mse':              mse,
            'predicted_anomaly': (mse > self.threshold)
        })

    def save(self, path: str = 'models/autoencoder'):
        import json
        os.makedirs(path, exist_ok=True)
        self.model.save(f'{path}/model.keras')
        meta = {'threshold': self.threshold, 'max_mse': self.max_mse}
        with open(f'{path}/meta.json', 'w') as f:
            json.dump(meta, f, indent=2)
        print(f"✓ Autoencoder guardado → {path}/")

    def load(self, path: str = 'models/autoencoder'):
        import tensorflow as tf, json
        self.model = tf.keras.models.load_model(f'{path}/model.keras')
        with open(f'{path}/meta.json') as f:
            meta = json.load(f)
        self.threshold = meta['threshold']
        self.max_mse   = meta['max_mse']
        print(f"✓ Autoencoder cargado desde {path}/")
        return self

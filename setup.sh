#!/bin/bash
# setup.sh — Inicialización del entorno para Network Anomaly Detection
# Uso: bash setup.sh

set -e

echo "============================================="
echo "  Network Anomaly Detection — Setup"
echo "============================================="

# ── Java 17 ──────────────────────────────────────
export JAVA_HOME="/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
echo "✓ JAVA_HOME → $JAVA_HOME"
java -version 2>&1 | head -1

# ── Dependencias Python ───────────────────────────
echo ""
echo "Instalando dependencias Python..."
pip3 install pyspark==3.5.1 kaggle findspark scikit-learn \
             tensorflow keras pymongo streamlit \
             pandas matplotlib seaborn plotly pyyaml \
             jupyter notebook --quiet
echo "✓ Dependencias instaladas"

# ── Dataset NSL-KDD ───────────────────────────────
echo ""
echo "Descargando NSL-KDD desde Kaggle..."
if [ ! -f "data/raw/KDDTrain+.txt" ]; then
    kaggle datasets download -d hassan06/nslkdd -p data/raw --unzip
    echo "✓ Dataset descargado en data/raw/"
else
    echo "✓ Dataset ya existe, omitiendo descarga"
fi

# ── Verificar PySpark ─────────────────────────────
echo ""
echo "Verificando PySpark..."
python3 -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('test') \
    .master('local[*]') \
    .config('spark.driver.memory', '2g') \
    .getOrCreate()
spark.sparkContext.setLogLevel('ERROR')
print('✓ PySpark', spark.version, 'OK —', spark.sparkContext.defaultParallelism, 'cores')
spark.stop()
"

echo ""
echo "============================================="
echo "  Setup completo. ¡Listo para empezar!"
echo "  Siguiente paso: jupyter notebook"
echo "============================================="

"""
app.py — Dashboard Streamlit
============================
SecureOps MX | Network Anomaly Detection | NSL-KDD

Vistas:
  1. Resumen del Sistema     — KPIs, distribución de clases, estado del pipeline
  2. Modelos ML              — métricas RF vs GBT, feature importance, confusion matrix
  3. Agente RL               — comparativa de políticas, tabla Q, curvas de aprendizaje
  4. Simulación en Vivo      — demo interactivo de decisión del agente RL

Uso:
    streamlit run src/app.py
"""

import os, sys, json, warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
sys.path.append(os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import streamlit as st
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent
REPORTS  = ROOT / 'reports'
MODELS   = ROOT / 'models'
DATA     = ROOT / 'data' / 'processed'
CONFIGS  = ROOT / 'configs'

# ── Config de página ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SecureOps MX — Alert Triage",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Estilos ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1e2130;
        border-radius: 10px;
        padding: 18px 22px;
        border-left: 4px solid #2E74B5;
        margin-bottom: 8px;
    }
    .metric-card.red   { border-left-color: #C00000; }
    .metric-card.green { border-left-color: #70AD47; }
    .metric-card.gold  { border-left-color: #ED7D31; }
    .metric-label { font-size: 12px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 28px; font-weight: 700; color: #fff; }
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-green { background: #1a3a1a; color: #70AD47; }
    .badge-red   { background: #3a1a1a; color: #C00000; }
    .badge-gray  { background: #2a2a2a; color: #aaa; }
    [data-testid="stSidebar"] { background: #111827; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de carga
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_meta():
    try:
        with open(CONFIGS / 'pipeline_meta.json') as f:
            meta = json.load(f)
        meta['label_mapping'] = {int(k): v for k, v in meta['label_mapping'].items()}
        return meta
    except FileNotFoundError:
        return None

@st.cache_data
def load_config():
    import yaml
    try:
        with open(CONFIGS / 'config.yaml') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

@st.cache_data
def load_model_comparison_val():
    p = REPORTS / 'model_comparison_val.csv'
    return pd.read_csv(p) if p.exists() else None

@st.cache_data
def load_policy_comparison_val():
    p = REPORTS / 'policy_comparison_val.csv'
    return pd.read_csv(p) if p.exists() else None

@st.cache_data
def load_policy_comparison_test():
    p = REPORTS / 'policy_comparison_test_FINAL.csv'
    return pd.read_csv(p) if p.exists() else None

@st.cache_data
def load_ml_preds(split='val'):
    p = DATA / f'{split}_ml_preds.parquet'
    return pd.read_parquet(p) if p.exists() else None

def img(filename):
    p = REPORTS / filename
    return str(p) if p.exists() else None

def badge(text, ok=None):
    if ok is True:
        return f'<span class="status-badge badge-green">✓ {text}</span>'
    elif ok is False:
        return f'<span class="status-badge badge-red">✗ {text}</span>'
    return f'<span class="status-badge badge-gray">⏳ {text}</span>'


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🛡️ SecureOps MX")
    st.markdown("**Network Anomaly Detection**")
    st.markdown("NSL-KDD · PySpark · Q-Learning")
    st.divider()

    vista = st.radio(
        "Navegación",
        ["📊 Resumen del Sistema",
         "🤖 Modelos ML",
         "🎯 Agente RL",
         "⚡ Simulación en Vivo"],
        label_visibility="collapsed"
    )

    st.divider()
    meta   = load_meta()
    config = load_config()

    # Estado del pipeline
    st.markdown("**Estado del Pipeline**")
    etapas = [
        ("EDA",            (REPORTS / '01_class_distribution.png').exists()),
        ("Preprocesado",   (DATA / 'train_features.parquet').exists()),
        ("Modelos ML",     (MODELS / 'random_forest').exists()),
        ("Agente RL",      (MODELS / 'rl_agent').exists()),
        ("Dashboard",      True),
    ]
    for nombre, listo in etapas:
        estado = "✅" if listo else "⬜"
        st.markdown(f"{estado} {nombre}")

    st.divider()
    st.caption("CRISP-DM · CERT-TLG-SDS")
    st.caption("v1.0 · Mayo 2026")


meta   = load_meta()
config = load_config()


# ══════════════════════════════════════════════════════════════════════════════
# VISTA 1 — Resumen del Sistema
# ══════════════════════════════════════════════════════════════════════════════

if vista == "📊 Resumen del Sistema":
    st.title("📊 Resumen del Sistema")
    st.caption("SecureOps MX · Network Anomaly Detection · NSL-KDD")

    # KPIs principales
    col1, col2, col3, col4 = st.columns(4)

    n_train = meta['n_train'] if meta else 88726
    n_val   = meta['n_val']   if meta else 18780
    n_test  = meta['n_test']  if meta else 18467

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Registros de entrenamiento</div>
            <div class="metric-value">{n_train:,}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card green">
            <div class="metric-label">Clases de ataque</div>
            <div class="metric-value">5</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card gold">
            <div class="metric-label">Features del modelo</div>
            <div class="metric-value">{len(meta['feature_cols']) if meta else 41}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        recall_req = config.get('recall_threshold', 0.90)
        st.markdown(f"""
        <div class="metric-card red">
            <div class="metric-label">Recall mínimo requerido</div>
            <div class="metric-value">{recall_req:.0%}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # Distribución de clases
    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        st.subheader("Distribución de Clases — Dataset NSL-KDD")
        i = img('01_class_distribution.png')
        if i:
            st.image(i, use_container_width=True)
        else:
            # Gráfico generado dinámicamente
            dist_data = {
                'Clase':   ['Normal', 'DoS', 'Probe', 'R2L', 'U2R'],
                'Train %': [53.54, 36.48, 9.30, 0.79, 0.04],
                'Test %':  [43.76, 29.84, 7.52, 10.75, 0.89],
            }
            df_dist = pd.DataFrame(dist_data).set_index('Clase')
            fig, ax = plt.subplots(figsize=(8, 4))
            x = np.arange(len(df_dist))
            ax.bar(x - 0.2, df_dist['Train %'], 0.4, label='Train', color='#2E74B5')
            ax.bar(x + 0.2, df_dist['Test %'],  0.4, label='Test',  color='#ED7D31')
            ax.set_xticks(x); ax.set_xticklabels(df_dist.index)
            ax.set_ylabel('%'); ax.legend(); ax.set_title('Distribución por split')
            st.pyplot(fig); plt.close()

    with col_b:
        st.subheader("Desafíos Metodológicos")
        st.markdown("""
        | Riesgo | Mitigación |
        |--------|-----------|
        | **Desbalance severo** (U2R: 0.04%) | Pesos de clase inversos |
        | **Distribution shift** R2L (0.79% → 10.75%) | F1-macro como métrica principal |
        | **Data leakage** | Pipeline fit SOLO en train |
        | **Overfitting** | CrossValidator k=5, validación separada |
        | **Recall bajo en ataques raros** | Constraint duro: Recall ≥ 90% |
        """)

        st.subheader("Arquitectura del Sistema")
        st.markdown("""
        ```
        NSL-KDD Dataset
            │
            ├── PySpark MLlib Pipeline
            │     ├── Random Forest (clasificador principal)
            │     ├── GBT One-vs-Rest (clasificador alternativo)
            │     └── Autoencoder Keras (anomalías no vistas)
            │
            └── Q-Learning Agent (Alert Triage)
                  ├── Estado: clase × confianza × fp_rate
                  ├── Acciones: IGNORAR / MONITOREAR / ESCALAR
                  └── Métrica: COT con Recall ≥ 0.90
        ```
        """)

    st.divider()

    # Pesos de clase
    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Pesos de Clase (anti-desbalance)")
        i = img('05_class_weights.png')
        if i:
            st.image(i, use_container_width=True)

    with col_d:
        st.subheader("Distribución por Split")
        i = img('04_split_distribution.png')
        if i:
            st.image(i, use_container_width=True)

    # Costos RL
    if config.get('costs'):
        st.divider()
        st.subheader("Tabla de Costos — Agente RL (COT)")
        costs = config['costs']
        costs_df = pd.DataFrame([
            {"Situación": "Ataque NO detectado (FN)",     "Costo": costs['fn_attack'],  "Comentario": "Amenaza ignorada — daño operativo"},
            {"Situación": "DoS NO detectado (FN DoS)",    "Costo": costs['fn_dos'],     "Comentario": "Denegación de servicio — impacto alto"},
            {"Situación": "Normal escalado (FP)",         "Costo": costs['fp_normal'],  "Comentario": "Analista invierte tiempo sin razón"},
            {"Situación": "Costo de escalada (por alerta)", "Costo": costs['escalation'], "Comentario": "Toda escalada tiene costo base"},
            {"Situación": "Ahorro por TN correcto",       "Costo": costs['tn_saving'],  "Comentario": "Beneficio de ignorar tráfico normal"},
        ])
        st.dataframe(costs_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# VISTA 2 — Modelos ML
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🤖 Modelos ML":
    st.title("🤖 Modelos de Machine Learning")

    comp_val = load_model_comparison_val()

    if comp_val is not None:
        st.subheader("Comparativa en Validation")

        # Highlight best F1
        best_f1 = comp_val['f1_macro'].max()

        def highlight_best(row):
            return ['background-color: #1a2e1a' if row['f1_macro'] == best_f1
                    else '' for _ in row]

        display_cols = [c for c in ['model', 'f1_macro', 'accuracy',
                                     'weighted_recall', 'recall_Normal',
                                     'recall_DoS', 'recall_Probe',
                                     'recall_R2L', 'recall_U2R']
                        if c in comp_val.columns]
        st.dataframe(
            comp_val[display_cols].style.apply(highlight_best, axis=1),
            use_container_width=True, hide_index=True
        )

        # Gráfico de barras por recall de clase
        recall_cols = [c for c in ['recall_Normal', 'recall_DoS', 'recall_Probe',
                                    'recall_R2L', 'recall_U2R'] if c in comp_val.columns]
        if recall_cols:
            fig, ax = plt.subplots(figsize=(10, 4))
            x  = np.arange(len(recall_cols))
            w  = 0.35
            models = comp_val['model'].tolist()
            colors = ['#2E74B5', '#ED7D31']
            for i, (_, row) in enumerate(comp_val.iterrows()):
                offset = (i - len(comp_val)/2 + 0.5) * w
                ax.bar(x + offset, [row[c] for c in recall_cols],
                       w, label=row['model'], color=colors[i % len(colors)])
            ax.set_xticks(x)
            ax.set_xticklabels([c.replace('recall_', '') for c in recall_cols])
            ax.set_ylabel('Recall por clase')
            ax.set_title('Recall por clase — Random Forest vs GBT (Validation)')
            ax.legend()
            ax.axhline(0.9, color='red', linestyle='--', linewidth=1,
                       label='Threshold 0.90')
            st.pyplot(fig); plt.close()
    else:
        st.info("⏳ Ejecuta `03_modeling.ipynb` para ver los resultados del modelo.")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Matriz de Confusión — Random Forest (Val)")
        # Buscar cualquier confusion matrix disponible
        cm_files = list(REPORTS.glob('confusion_matrix*.png'))
        rf_cm = next((f for f in cm_files if 'random_forest' in f.name.lower()), None)
        if rf_cm:
            st.image(str(rf_cm), use_container_width=True)
        else:
            st.info("⏳ Pendiente de ejecutar modelado")

        st.subheader("Feature Importance — Random Forest")
        fi_img = img('06_rf_feature_importance.png')
        if fi_img:
            st.image(fi_img, use_container_width=True)
        else:
            st.info("⏳ Pendiente de ejecutar modelado")

    with col2:
        st.subheader("Matriz de Confusión — GBT (Val)")
        gbt_cm = next((f for f in cm_files if 'gbt' in f.name.lower()), None)
        if gbt_cm:
            st.image(str(gbt_cm), use_container_width=True)
        else:
            st.info("⏳ Pendiente de ejecutar modelado")

        st.subheader("Distribución del Anomaly Score — Autoencoder")
        ae_img = img('07_autoencoder_scores.png')
        if ae_img:
            st.image(ae_img, use_container_width=True)
        else:
            st.info("⏳ Pendiente de ejecutar Autoencoder")

    # Nota sobre Databricks
    st.divider()
    st.subheader("🔗 Integración MLOps — Databricks")
    col_db1, col_db2, col_db3 = st.columns(3)
    with col_db1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">F1 Macro (Databricks RF)</div>
            <div class="metric-value">0.7007</div>
        </div>""", unsafe_allow_html=True)
    with col_db2:
        st.markdown("""
        <div class="metric-card green">
            <div class="metric-label">Estado Model Registry</div>
            <div class="metric-value" style="font-size:20px">READY ✓</div>
        </div>""", unsafe_allow_html=True)
    with col_db3:
        st.markdown("""
        <div class="metric-card gold">
            <div class="metric-label">Plataforma</div>
            <div class="metric-value" style="font-size:18px">Unity Catalog</div>
        </div>""", unsafe_allow_html=True)
    st.caption("El modelo en Databricks (F1 0.70) es la versión sin pesos de clase ni CrossValidator — sirve como baseline MLOps. El pipeline local con balanceo y CrossValidator k=5 obtiene métricas superiores.")


# ══════════════════════════════════════════════════════════════════════════════
# VISTA 3 — Agente RL
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🎯 Agente RL":
    st.title("🎯 Agente Q-Learning — Alert Triage")

    comp_val  = load_policy_comparison_val()
    comp_test = load_policy_comparison_test()

    if comp_val is not None:
        st.subheader("Comparativa de Políticas — Validation")

        # Tabla resumen
        display_cols = [c for c in ['policy', 'COT', 'COT_por_alerta',
                                     'recall_sistema', 'f1_binario',
                                     'pct_IGNORAR', 'pct_MONITOREAR',
                                     'pct_ESCALAR', 'recall_OK']
                        if c in comp_val.columns]

        def color_recall(val):
            if isinstance(val, bool):
                return 'color: #70AD47' if val else 'color: #C00000'
            return ''

        st.dataframe(comp_val[display_cols], use_container_width=True, hide_index=True)

        i = img('11_policy_comparison_val.png')
        if i:
            st.image(i, use_container_width=True)
    else:
        st.info("⏳ Ejecuta `04_rl_agent.ipynb` para ver los resultados del agente.")

    if comp_test is not None:
        st.divider()
        st.subheader("🏆 Resultados FINALES en Test")
        st.warning("Esta evaluación se ejecutó UNA SOLA VEZ (sin re-tuning posterior).")
        st.dataframe(comp_test[display_cols], use_container_width=True, hide_index=True)

        i = img('12_policy_comparison_test_FINAL.png')
        if i:
            st.image(i, use_container_width=True)

        # Resumen ejecutivo
        if 'recall_OK' in comp_test.columns:
            valid = comp_test[comp_test['recall_OK']].sort_values('COT')
            if len(valid) > 0:
                best = valid.iloc[0]
                baseline = comp_test[comp_test['policy'] == 'Escalar Todo']
                if len(baseline) > 0:
                    savings = baseline.iloc[0]['COT'] - best['COT']
                    savings_pct = savings / baseline.iloc[0]['COT'] * 100
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Política Óptima", best['policy'])
                    with col2:
                        st.metric("Reducción de COT", f"{savings_pct:.1f}%",
                                  delta=f"-{savings:,.0f} puntos de costo")
                    with col3:
                        recall_ok = "✓ CUMPLE" if best['recall_OK'] else "✗ INCUMPLE"
                        st.metric("Recall Sistema", f"{best['recall_sistema']:.4f}",
                                  delta=recall_ok)

    st.divider()
    col_rl1, col_rl2 = st.columns(2)

    with col_rl1:
        st.subheader("Curvas de Aprendizaje")
        i = img('09_rl_learning_curves.png')
        if i:
            st.image(i, use_container_width=True)
        else:
            st.info("⏳ Pendiente de entrenamiento RL")

    with col_rl2:
        st.subheader("Política Aprendida (Tabla Q)")
        i = img('10_q_table_policy.png')
        if i:
            st.image(i, use_container_width=True)
        else:
            st.info("⏳ Pendiente de entrenamiento RL")

    # Explicación del diseño
    st.divider()
    st.subheader("Diseño del Espacio de Estados y Acciones")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("""
        **60 Estados = 5 × 4 × 3**

        | Dimensión | Valores |
        |-----------|---------|
        | Clase predicha por ML | Normal, DoS, Probe, R2L, U2R |
        | Confianza del modelo | [0,0.5) · [0.5,0.75) · [0.75,0.9) · [0.9,1] |
        | FP rate reciente | < 10% · 10-30% · ≥ 30% |

        La tasa de FP reciente se calcula sobre una **ventana deslizante de 100 decisiones** almacenada en MongoDB, dándole al agente contexto operativo de corto plazo.
        """)
    with col_d2:
        st.markdown("""
        **3 Acciones**

        | Acción | Significado | Cuándo |
        |--------|-------------|--------|
        | **IGNORAR** | No revisar la alerta | Normal con alta confianza y FP alto reciente |
        | **MONITOREAR** | Registrar sin escalar | Confianza media, clase ambigua |
        | **ESCALAR** | Enviar a analista SOC | Ataque probable con alta confianza |

        **Constraint duro:** `System Recall ≥ 0.90` — si el agente falla este umbral, la política no es válida para producción.
        """)


# ══════════════════════════════════════════════════════════════════════════════
# VISTA 4 — Simulación en Vivo
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "⚡ Simulación en Vivo":
    st.title("⚡ Simulación en Vivo — Alert Triage")
    st.markdown("Simula una alerta de red y observa la decisión del agente Q-Learning en tiempo real.")

    rl_model_exists = (MODELS / 'rl_agent' / 'q_table.npy').exists()

    if not rl_model_exists:
        st.warning("⏳ El agente RL aún no está entrenado. Ejecuta `04_rl_agent.ipynb` primero. Mientras tanto, puedes explorar la simulación con valores de ejemplo.")

    st.divider()
    col_inp, col_out = st.columns([1, 1])

    with col_inp:
        st.subheader("📥 Parámetros de la Alerta")

        pred_class_name = st.selectbox(
            "Clase predicha por el modelo ML",
            ["Normal", "DoS", "Probe", "R2L", "U2R"],
            index=1
        )
        confidence = st.slider(
            "Confianza del modelo (%)",
            min_value=10, max_value=100, value=85, step=5
        ) / 100.0

        fp_rate_pct = st.slider(
            "Tasa de falsos positivos reciente (%)",
            min_value=0, max_value=60, value=15, step=5
        ) / 100.0

        true_class_name = st.selectbox(
            "Etiqueta real (para cálculo de recompensa)",
            ["Normal", "DoS", "Probe", "R2L", "U2R"],
            index=1,
            help="En producción esto es desconocido; aquí lo revelamos para calcular la recompensa."
        )

        simular = st.button("🚀 Simular Decisión", type="primary", use_container_width=True)

    with col_out:
        st.subheader("📤 Decisión del Agente")

        if simular:
            try:
                from train_rl_agent import (
                    QLearningAgent, build_state, ACTIONS, N_STATES
                )
                import yaml

                config_loaded = load_config()
                meta_loaded   = load_meta()
                label_mapping = meta_loaded['label_mapping'] if meta_loaded else \
                    {0: 'DoS', 1: 'Normal', 2: 'Probe', 3: 'R2L', 4: 'U2R'}
                rev_map = {v: k for k, v in label_mapping.items()}

                pred_cls = rev_map.get(pred_class_name, 1)
                state    = build_state(pred_cls, confidence, fp_rate_pct)

                if rl_model_exists:
                    agent = QLearningAgent(config=config_loaded)
                    agent.load(str(MODELS / 'rl_agent'))
                    action = agent.select_action(state, training=False)
                    q_vals = agent.Q[state]
                    source = "agente Q-Learning entrenado"
                else:
                    # Heurística de demostración
                    if pred_class_name == 'Normal' and confidence > 0.85:
                        action = 0
                    elif confidence < 0.60:
                        action = 1
                    else:
                        action = 2
                    q_vals = None
                    source = "heurística de demostración"

                action_name   = ACTIONS[action]
                action_colors = {0: '🟢', 1: '🟡', 2: '🔴'}
                action_desc   = {
                    0: "El agente considera que esta conexión es segura y no requiere atención.",
                    1: "El agente tiene incertidumbre. La alerta queda registrada para revisión posterior.",
                    2: "El agente detecta una posible amenaza. Se notifica al analista SOC."
                }

                st.markdown(f"""
                <div style="background:#1e2130;border-radius:12px;padding:24px;text-align:center;border:2px solid {'#70AD47' if action==0 else '#ED7D31' if action==1 else '#C00000'}">
                    <div style="font-size:48px">{action_colors[action]}</div>
                    <div style="font-size:32px;font-weight:700;color:white;margin:8px 0">{action_name}</div>
                    <div style="color:#aaa;font-size:14px">{action_desc[action]}</div>
                    <div style="margin-top:12px;color:#666;font-size:11px">Fuente: {source} · Estado #{state}</div>
                </div>
                """, unsafe_allow_html=True)

                # Calcular recompensa
                st.divider()
                costs = config_loaded.get('costs', {'fn_attack':15,'fn_dos':20,'fp_normal':2,'escalation':1,'tn_saving':-1})
                is_attack = (true_class_name != 'Normal')

                if action == 0:
                    reward = 1.0 if not is_attack else (-costs['fn_dos'] if true_class_name=='DoS' else -costs['fn_attack'])
                elif action == 1:
                    reward = 0.0 if not is_attack else -costs['fn_attack']/3.0
                else:
                    reward = -costs['escalation']
                    if not is_attack:
                        reward -= costs['fp_normal']

                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Estado del agente", f"#{state}")
                col_r2.metric("Confianza del modelo", f"{confidence:.0%}")
                col_r3.metric("Recompensa obtenida", f"{reward:+.1f}",
                              delta="correcta" if reward >= 0 else "penalización",
                              delta_color="normal" if reward >= 0 else "inverse")

                if q_vals is not None:
                    st.markdown("**Valores Q para este estado:**")
                    q_df = pd.DataFrame({
                        'Acción':       ['IGNORAR', 'MONITOREAR', 'ESCALAR'],
                        'Valor Q':      [round(q, 4) for q in q_vals],
                        'Seleccionada': ['✓' if i == action else '' for i in range(3)]
                    })
                    st.dataframe(q_df, use_container_width=True, hide_index=True)

            except ImportError as e:
                st.error(f"Error importando módulo RL: {e}")
            except Exception as e:
                st.error(f"Error en simulación: {e}")
        else:
            st.markdown("""
            <div style="background:#111827;border-radius:12px;padding:30px;text-align:center;border:1px dashed #333">
                <div style="font-size:40px">🛡️</div>
                <div style="color:#aaa;margin-top:12px">Configura los parámetros de la alerta y presiona <strong>Simular Decisión</strong></div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📊 Análisis de Predicciones ML (Val)")
    i = img('08_ml_predictions_analysis.png')
    if i:
        st.image(i, use_container_width=True)
    else:
        st.info("⏳ Disponible tras ejecutar `04_rl_agent.ipynb`")

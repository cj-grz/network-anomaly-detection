"""
train_rl_agent.py
=================
Agente Q-Learning tabular para priorización de alertas (Alert Triage).

Diseño:
  - Estados: 60 = 5 clases_predichas × 4 niveles_confianza × 3 niveles_fp_rate
  - Acciones: 3 = {IGNORAR, MONITOREAR, ESCALAR}
  - Recompensas: definidas por la tabla de costos en config.yaml (COT)
  - Constraint duro: System Recall ≥ 0.90 (recall_threshold)

Componentes:
  - QLearningAgent     — tabla Q, epsilon-greedy, update, estado discreto
  - AlertEnvironment   — convierte predicciones ML → episodios RL
  - MongoWindow        — ventana deslizante de 100 decisiones (fp_rate_reciente)
  - Baselines          — 3 políticas de comparación
  - RLEvaluator        — métricas COT, recall de sistema, comparativa

Anti-leakage:
  - El agente se entrena en train_features.parquet
  - Threshold del autoencoder ya fue calibrado en val (nunca en test)
  - Test se evalúa UNA SOLA VEZ al final
"""

import os, json, warnings, copy
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')
os.environ['JAVA_HOME'] = '/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


# ══════════════════════════════════════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════════════════════════════════════

ACTIONS = {0: 'IGNORAR', 1: 'MONITOREAR', 2: 'ESCALAR'}
N_ACTIONS = 3
N_CLASSES = 5        # Normal, DoS, Probe, R2L, U2R
N_CONF    = 4        # niveles de confianza: [0,0.5), [0.5,0.75), [0.75,0.90), [0.90,1]
N_FP      = 3        # niveles de fp_rate_reciente: bajo, medio, alto
N_STATES  = N_CLASSES * N_CONF * N_FP   # 60


# ══════════════════════════════════════════════════════════════════════════════
# 1. Ventana MongoDB (simulada con deque cuando no hay conexión)
# ══════════════════════════════════════════════════════════════════════════════

class MongoWindow:
    """
    Ventana deslizante de las últimas `window_size` decisiones del agente.
    Calcula fp_rate_reciente para el estado del agente.

    Intenta conectar a MongoDB; si falla, usa collections.deque en memoria.
    """

    def __init__(self, window_size: int = 100, mongo_uri: str = None,
                 db: str = 'secureops', collection: str = 'decisions'):
        self.window_size = window_size
        self.mongo_uri   = mongo_uri or os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
        self.collection  = None
        self._deque      = None

        try:
            from pymongo import MongoClient
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            client.admin.command('ping')   # comprueba conexión
            db_obj = client[db]
            self.collection = db_obj[collection]
            # Crear índice TTL opcional (no crítico)
            self.collection.create_index('ts')
            print("✓ MongoWindow: conectado a MongoDB")
        except Exception as e:
            from collections import deque
            self._deque = deque(maxlen=window_size)
            print(f"⚠ MongoWindow: MongoDB no disponible ({e}). Usando deque en memoria.")

    def push(self, record: dict):
        """Guarda un registro {true_label, predicted_label, action, is_fp}."""
        import datetime
        record['ts'] = datetime.datetime.utcnow()
        if self.collection is not None:
            self.collection.insert_one(record)
            # Mantener solo los últimos window_size documentos
            count = self.collection.count_documents({})
            if count > self.window_size:
                oldest = list(self.collection.find().sort('ts', 1)
                              .limit(count - self.window_size))
                ids = [d['_id'] for d in oldest]
                self.collection.delete_many({'_id': {'$in': ids}})
        else:
            self._deque.append(record)

    def fp_rate(self) -> float:
        """Tasa de FP en la ventana: (acciones ESCALAR sobre Normal) / total_escaladas."""
        if self.collection is not None:
            docs = list(self.collection.find())
        else:
            docs = list(self._deque)
        if not docs:
            return 0.0
        escalated = [d for d in docs if d.get('action') == 2]  # ESCALAR
        if not escalated:
            return 0.0
        fp = sum(1 for d in escalated if d.get('true_label') == 'Normal')
        return fp / len(escalated)

    def clear(self):
        """Limpia la ventana (usado entre episodios de evaluación)."""
        if self.collection is not None:
            self.collection.delete_many({})
        else:
            self._deque.clear()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Estado discreto
# ══════════════════════════════════════════════════════════════════════════════

def discretize_confidence(prob: float) -> int:
    """Convierte probabilidad max en índice de confianza [0-3]."""
    if prob < 0.50:  return 0
    if prob < 0.75:  return 1
    if prob < 0.90:  return 2
    return 3

def discretize_fp_rate(fp: float) -> int:
    """Convierte fp_rate_reciente en índice [0-2]."""
    if fp < 0.10:  return 0
    if fp < 0.30:  return 1
    return 2

def build_state(predicted_class: int, confidence: float, fp_rate: float) -> int:
    """
    Construye el índice de estado (0-59).
      estado = predicted_class * (N_CONF * N_FP)
             + conf_idx * N_FP
             + fp_idx
    """
    conf_idx = discretize_confidence(confidence)
    fp_idx   = discretize_fp_rate(fp_rate)
    return predicted_class * (N_CONF * N_FP) + conf_idx * N_FP + fp_idx


# ══════════════════════════════════════════════════════════════════════════════
# 3. Agente Q-Learning tabular
# ══════════════════════════════════════════════════════════════════════════════

class QLearningAgent:
    """
    Agente Q-Learning tabular para alert triage.

    Espacio de estados: 60 (5 clases × 4 confianzas × 3 fp_rates)
    Espacio de acciones: 3 (IGNORAR, MONITOREAR, ESCALAR)
    """

    def __init__(self, config: dict, seed: int = 42):
        rl = config['rl_agent']
        self.alpha         = rl['alpha']
        self.gamma         = rl['gamma']
        self.epsilon       = rl['epsilon_start']
        self.epsilon_end   = rl['epsilon_end']
        self.epsilon_decay = rl['epsilon_decay']
        self.seed          = seed
        self.rng           = np.random.default_rng(seed)

        # Tabla Q inicializada en 0
        self.Q = np.zeros((N_STATES, N_ACTIONS))

        # Historial de entrenamiento
        self.history = {
            'episode_reward':  [],
            'epsilon':         [],
            'episode_cot':     [],
        }

    def select_action(self, state: int, training: bool = True) -> int:
        """Epsilon-greedy durante entrenamiento; greedy en evaluación."""
        if training and self.rng.random() < self.epsilon:
            return int(self.rng.integers(N_ACTIONS))
        return int(np.argmax(self.Q[state]))

    def update(self, state: int, action: int, reward: float, next_state: int):
        """Actualización Q-Learning (off-policy)."""
        best_next = np.max(self.Q[next_state])
        td_target = reward + self.gamma * best_next
        td_error  = td_target - self.Q[state, action]
        self.Q[state, action] += self.alpha * td_error

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def save(self, path: str = 'models/rl_agent'):
        os.makedirs(path, exist_ok=True)
        np.save(f'{path}/q_table.npy', self.Q)
        meta = {
            'alpha':         self.alpha,
            'gamma':         self.gamma,
            'epsilon':       self.epsilon,
            'epsilon_end':   self.epsilon_end,
            'epsilon_decay': self.epsilon_decay,
            'n_states':      N_STATES,
            'n_actions':     N_ACTIONS,
        }
        with open(f'{path}/agent_meta.json', 'w') as f:
            json.dump(meta, f, indent=2)
        print(f"✓ Agente RL guardado → {path}/")

    def load(self, path: str = 'models/rl_agent'):
        self.Q = np.load(f'{path}/q_table.npy')
        with open(f'{path}/agent_meta.json') as f:
            meta = json.load(f)
        self.epsilon = meta['epsilon']
        print(f"✓ Agente RL cargado desde {path}/")
        return self


# ══════════════════════════════════════════════════════════════════════════════
# 4. Entorno de alertas
# ══════════════════════════════════════════════════════════════════════════════

class AlertEnvironment:
    """
    Convierte predicciones de modelos ML en episodios RL.

    Cada paso = una alerta (conexión de red) con:
      - Clase predicha por el mejor modelo ML (RF o GBT)
      - Probabilidad máxima de esa clase
      - Etiqueta real (oráculo del dataset NSL-KDD)
    """

    COST = None   # se llena en __init__ desde config

    def __init__(self, config: dict, label_mapping: dict,
                 mongo_window: MongoWindow):
        costs = config['costs']
        self.costs = costs
        self.label_mapping  = label_mapping      # {0: 'DoS', 1: 'Normal', ...}
        self.rev_mapping    = {v: k for k, v in label_mapping.items()}
        self.mongo_window   = mongo_window
        self.recall_threshold = config.get('recall_threshold', 0.90)

        # Contadores de episodio
        self._reset_episode()

    def _reset_episode(self):
        self.tp = 0; self.fn = 0; self.fp = 0; self.tn = 0
        self.total_cost = 0.0

    def reset(self):
        self._reset_episode()
        self.mongo_window.clear()

    def _compute_reward(self, action: int, true_label: str,
                        predicted_label: str) -> float:
        """
        Tabla de recompensas (negativa = costo):

        action=IGNORAR (0):
          true=Normal  → TN saving = -1 (ganancia)
          true=Ataque  → FN penalty (DoS=-20, otros=-15)

        action=MONITOREAR (1):
          true=Normal  → neutral = 0  (no cost, no saving)
          true=Ataque  → FN parcial = -5  (menos grave que ignorar)

        action=ESCALAR (2):
          true=Normal  → FP = -2
          true=Ataque  → TP = 0  (alerta gestionada correctamente)
          + costo de escalada = -1 siempre
        """
        is_attack = (true_label != 'Normal')

        if action == 0:   # IGNORAR
            if not is_attack:
                reward = -self.costs['tn_saving']   # tn_saving=-1 → reward=+1
            else:
                # DoS tiene penalización mayor
                if true_label == 'DoS':
                    reward = -self.costs['fn_dos']
                else:
                    reward = -self.costs['fn_attack']

        elif action == 1:  # MONITOREAR
            if not is_attack:
                reward = 0.0                         # neutral
            else:
                reward = -self.costs['fn_attack'] / 3.0   # penalización reducida

        else:              # ESCALAR
            reward = -self.costs['escalation']       # costo base escalada
            if not is_attack:
                reward -= self.costs['fp_normal']    # FP adicional
            # si es ataque → solo costo de escalada (TP correcto)

        return reward

    def step(self, state: int, action: int,
             true_label: str, predicted_label: str,
             predicted_proba: float) -> tuple:
        """
        Ejecuta un paso del entorno.

        Returns:
            (next_state, reward, info_dict)
        """
        reward = self._compute_reward(action, true_label, predicted_label)
        self.total_cost += (-reward)  # acumular COT (positivo)

        # Registrar en MongoDB (o deque)
        is_fp = (action == 2 and true_label == 'Normal')
        self.mongo_window.push({
            'true_label':      true_label,
            'predicted_label': predicted_label,
            'action':          action,
            'is_fp':           is_fp,
            'reward':          reward,
        })

        # Actualizar contadores de recall
        is_attack = (true_label != 'Normal')
        if action == 2:   # ESCALAR = detección
            if is_attack:  self.tp += 1
            else:          self.fp += 1
        else:
            if is_attack:  self.fn += 1
            else:          self.tn += 1

        # Construir siguiente estado con fp_rate actualizado
        pred_idx   = self.rev_mapping.get(predicted_label, 1)
        new_fp     = self.mongo_window.fp_rate()
        next_state = build_state(pred_idx, predicted_proba, new_fp)

        info = {
            'true_label':  true_label,
            'predicted':   predicted_label,
            'action_name': ACTIONS[action],
            'reward':      reward,
            'is_fp':       is_fp,
        }
        return next_state, reward, info

    def system_recall(self) -> float:
        total_attacks = self.tp + self.fn
        if total_attacks == 0:
            return 1.0
        return self.tp / total_attacks

    def episode_cot(self) -> float:
        return self.total_cost


# ══════════════════════════════════════════════════════════════════════════════
# 5. Loop de entrenamiento
# ══════════════════════════════════════════════════════════════════════════════

class RLTrainer:
    """
    Entrena el agente Q-Learning sobre los episodios de train.
    Cada epoch = una pasada completa por train (en orden aleatorio).
    """

    def __init__(self, agent: QLearningAgent, env: AlertEnvironment,
                 config: dict, seed: int = 42):
        self.agent  = agent
        self.env    = env
        self.config = config
        self.rng    = np.random.default_rng(seed)

    def train(self, predictions_df: pd.DataFrame, n_epochs: int = 10,
              verbose: bool = True) -> dict:
        """
        Entrena el agente.

        predictions_df debe tener columnas:
          - true_label      (str): etiqueta real del dataset
          - predicted_label (str): predicción del mejor modelo ML
          - predicted_proba (float): probabilidad máxima de la clase predicha
          - predicted_class (int): índice de clase predicha
        """
        print("\n" + "="*55)
        print("ENTRENAMIENTO Q-LEARNING — Alert Triage Agent")
        print("="*55)
        print(f"  Episodios (epochs): {n_epochs}")
        print(f"  Alertas por epoch:  {len(predictions_df):,}")
        print(f"  Estados: {N_STATES}  |  Acciones: {N_ACTIONS}")
        print(f"  α={self.agent.alpha}  γ={self.agent.gamma}  ε={self.agent.epsilon}")

        history = {'cot': [], 'recall': [], 'epsilon': []}

        for epoch in range(n_epochs):
            # Mezclar orden de alertas
            df_epoch = predictions_df.sample(frac=1, random_state=int(epoch)).reset_index(drop=True)
            self.env.reset()

            ep_reward = 0.0
            fp_rate_now = 0.0

            for _, row in df_epoch.iterrows():
                true_lbl  = row['true_label']
                pred_lbl  = row['predicted_label']
                pred_prob = float(row['predicted_proba'])
                pred_cls  = int(row['predicted_class'])

                state  = build_state(pred_cls, pred_prob, fp_rate_now)
                action = self.agent.select_action(state, training=True)

                next_state, reward, info = self.env.step(
                    state, action, true_lbl, pred_lbl, pred_prob
                )
                self.agent.update(state, action, reward, next_state)

                ep_reward  += reward
                fp_rate_now = self.env.mongo_window.fp_rate()

            self.agent.decay_epsilon()
            recall = self.env.system_recall()
            cot    = self.env.episode_cot()

            history['cot'].append(cot)
            history['recall'].append(recall)
            history['epsilon'].append(self.agent.epsilon)

            if verbose:
                recall_flag = '' if recall >= self.env.recall_threshold else ' ⚠ RECALL BAJO'
                print(f"  Epoch {epoch+1:3d}/{n_epochs} | "
                      f"COT={cot:8.1f} | "
                      f"Recall={recall:.4f}{recall_flag} | "
                      f"ε={self.agent.epsilon:.4f}")

        print(f"\n✓ Entrenamiento completado — ε final: {self.agent.epsilon:.4f}")
        return history


# ══════════════════════════════════════════════════════════════════════════════
# 6. Políticas baseline
# ══════════════════════════════════════════════════════════════════════════════

class BaselineEscalateAll:
    """Política 1: ESCALAR todas las alertas (upper bound de recall)."""
    name = "Escalar Todo"

    def act(self, *args, **kwargs) -> int:
        return 2  # siempre ESCALAR


class BaselineThreshold:
    """Política 2: ESCALAR si probabilidad de ataque ≥ threshold."""
    name = "Threshold (p≥0.85)"

    def __init__(self, threshold: float = 0.85, normal_label: int = 1):
        self.threshold    = threshold
        self.normal_label = normal_label   # índice numérico de 'Normal'

    def act(self, predicted_class: int, predicted_proba: float) -> int:
        if predicted_class == self.normal_label and predicted_proba >= self.threshold:
            return 0   # IGNORAR: Normal con alta confianza
        if predicted_proba >= self.threshold:
            return 2   # ESCALAR: ataque con alta confianza
        return 1       # MONITOREAR: baja confianza


class BaselineGBTArgmax:
    """Política 3: ESCALAR si GBT predice cualquier ataque (sin RL)."""
    name = "GBT Argmax"

    def __init__(self, normal_label: int = 1):
        self.normal_label = normal_label

    def act(self, predicted_class: int, **kwargs) -> int:
        if predicted_class == self.normal_label:
            return 0  # IGNORAR
        return 2      # ESCALAR (cualquier ataque)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Evaluador de políticas
# ══════════════════════════════════════════════════════════════════════════════

class RLEvaluator:
    """
    Evalúa una política (agente RL o baseline) sobre un dataset.
    Retorna: COT, recall_sistema, precision, f1_binario, distribución_acciones.
    """

    def __init__(self, config: dict, label_mapping: dict):
        self.costs          = config['costs']
        self.label_mapping  = label_mapping
        self.normal_label   = [k for k, v in label_mapping.items() if v == 'Normal'][0]
        self.recall_thresh  = config.get('recall_threshold', 0.90)

    def _compute_reward(self, action: int, true_label: str) -> float:
        """Misma tabla de costos que AlertEnvironment."""
        is_attack = (true_label != 'Normal')
        if action == 0:
            if not is_attack:
                return -self.costs['tn_saving']
            return -self.costs['fn_dos'] if true_label == 'DoS' else -self.costs['fn_attack']
        elif action == 1:
            return 0.0 if not is_attack else -self.costs['fn_attack'] / 3.0
        else:
            r = -self.costs['escalation']
            if not is_attack:
                r -= self.costs['fp_normal']
            return r

    def evaluate_policy(self, policy, predictions_df: pd.DataFrame,
                        dataset_name: str = 'Test') -> dict:
        """
        Evalúa la política sobre predictions_df.

        policy puede ser:
          - QLearningAgent (con método select_action)
          - Cualquier baseline (con método act)
        """
        tp = fp = tn = fn = 0
        total_cot = 0.0
        action_counts = {0: 0, 1: 0, 2: 0}
        fp_rate_now = 0.0
        recent = []   # ventana manual para fp_rate (sin MongoDB en eval)

        is_agent = isinstance(policy, QLearningAgent)
        rev_map  = {v: k for k, v in self.label_mapping.items()}

        for _, row in predictions_df.iterrows():
            true_lbl  = row['true_label']
            pred_lbl  = row['predicted_label']
            pred_prob = float(row['predicted_proba'])
            pred_cls  = int(row['predicted_class'])

            # Seleccionar acción
            if is_agent:
                state  = build_state(pred_cls, pred_prob, fp_rate_now)
                action = policy.select_action(state, training=False)
            else:
                # Baseelines: pasan pred_class y proba
                try:
                    action = policy.act(predicted_class=pred_cls,
                                        predicted_proba=pred_prob)
                except TypeError:
                    action = policy.act()

            action_counts[action] += 1
            reward     = self._compute_reward(action, true_lbl)
            total_cot += (-reward)

            # Recall binario (ataque vs normal)
            is_attack = (true_lbl != 'Normal')
            if action == 2:
                if is_attack: tp += 1
                else:         fp += 1
            else:
                if is_attack: fn += 1
                else:         tn += 1

            # Actualizar fp_rate manual (ventana 100)
            is_fp = (action == 2 and not is_attack)
            recent.append({'action': action, 'is_fp': is_fp})
            if len(recent) > 100:
                recent.pop(0)
            escalated_r = [r for r in recent if r['action'] == 2]
            fp_rate_now = (sum(1 for r in escalated_r if r['is_fp']) /
                           len(escalated_r)) if escalated_r else 0.0

        recall    = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        f1        = (2 * recall * precision / (recall + precision)
                     if (recall + precision) > 0 else 0.0)
        n_total   = len(predictions_df)

        result = {
            'policy':        getattr(policy, 'name', type(policy).__name__),
            'dataset':       dataset_name,
            'COT':           round(total_cot, 2),
            'COT_por_alerta':round(total_cot / max(n_total, 1), 4),
            'recall_sistema':round(recall, 4),
            'precision':     round(precision, 4),
            'f1_binario':    round(f1, 4),
            'pct_IGNORAR':   round(action_counts[0] / n_total, 4),
            'pct_MONITOREAR':round(action_counts[1] / n_total, 4),
            'pct_ESCALAR':   round(action_counts[2] / n_total, 4),
            'recall_OK':     recall >= self.recall_thresh,
        }
        return result

    def compare(self, results: list) -> pd.DataFrame:
        """Genera tabla comparativa de políticas."""
        df = pd.DataFrame(results)
        df = df.sort_values('COT')
        return df

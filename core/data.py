import numpy as np
AU_IN_KM = 149597870.7
# --- CONFIGURAZIONE ARCHITETTURALE ---
DT = 1
WIDTH = 1200
HEIGHT = 800
MAX_BODIES = 1
VOID_VAL = -64*AU_IN_KM* 1e10 * 0.9
# --- COSTANTI FISICHE ---
G = 6.67430e-20 # Costante universale in Km
G_SI = 6.67430e-11
C_LIGHT = 299792.458 # km/s
# Costanti precalcolate
INV_C_DT = 1.0 / (C_LIGHT * DT)
INV_C = 1.0 / C_LIGHT
INV_DT = 1.0 / DT
C_SQ = C_LIGHT*C_LIGHT
THRESHOLD_SOLVER_SQ = 0.5 * C_SQ
RS_FACTOR = (2.0 * G) / C_SQ

# --- MEMORIA SCIE (ADATTIVE / KERNEL) ---

# --- CONFIGURAZIONE SCIE DINAMICHE ---
TRAIL_POINTS_BUDGET = 0  # Non usato: il budget reale (2^17) è calcolato in simulation_manager.rebuild_simulation
TRAIL_LEN_CAP_MAX   = 0  # Non usato: cap per-corpo gestito in simulation_manager
TRAIL_LEN_CAP_MIN   = 0  # Non usato: cap per-corpo gestito in simulation_manager

# Questo diventa il valore di default, ma verrà sovrascritto dal Manager in base al budget e a max_bodies
TRAIL_LENGTH = 1
TRAIL_SENSITIVITY = 5.0
# 1. Buffer Circolare (N_BODIES, LEN, 2)
# Inizializzato a VOID_VAL così il kernel grafico ignora i punti vuoti
TRAIL_BUFFER = np.full((MAX_BODIES, TRAIL_LENGTH, 2), VOID_VAL, dtype=np.float64)

# 2. Testine di scrittura (N_BODIES)
TRAIL_HEADS = np.zeros(MAX_BODIES, dtype=np.int32)

# 3. Cache Ultima Posizione Registrata (N_BODIES, 2)
# Inizializziamo a -1e20 (lontanissimo) per forzare la scrittura del primo punto al tick 1
TRAIL_LAST_POS = np.full((MAX_BODIES, 2), -1e20, dtype=np.float64)

# --- ANALISI MEMORIA E SCELTA METODO ---

L3_CACHE_LIMIT = 18.0 # Mb (per stare larghi)

# Assegnazione variabili 
LEN_L0 = int(0)
LEN_L1 = int(0)
LEN_L2 = int(0)
MASK_L0 = int(0)
MASK_L1 = int(0)
MASK_L2 = int(0)

# Allocazione Memoria Reale

HISTORY_L0 = np.zeros((MAX_BODIES, LEN_L0, 5), dtype=np.float64) if LEN_L0 > 0 else None
HISTORY_L1 = np.zeros((MAX_BODIES, LEN_L1, 5), dtype=np.float64) if LEN_L1 > 0 else None
HISTORY_L2 = np.zeros((MAX_BODIES, LEN_L2, 5), dtype=np.float64) if LEN_L2 > 0 else None
# --- INDICI DI SCRITTURA (HEADS) ---
# Anche le "testine" di scrittura devono essere separate
HEADS_L0 = np.zeros(MAX_BODIES, dtype=np.int32)
HEADS_L1 = np.zeros(MAX_BODIES, dtype=np.int32)
HEADS_L2 = np.zeros(MAX_BODIES, dtype=np.int32)


# --- MASTER ARRAYS (TENSORONI HEAP) ---

POS = np.zeros((MAX_BODIES, 2), dtype=np.float64)
VEL = np.zeros((MAX_BODIES, 2), dtype=np.float64)
ACC = np.zeros((MAX_BODIES, 2), dtype=np.float64) 
ART = np.zeros((MAX_BODIES, 2), dtype=np.float64) # Artificial Acceleration
# Dati Scalari
MASS = np.zeros(MAX_BODIES, dtype=np.float64)
RAD  = np.zeros(MAX_BODIES, dtype=np.float64)

# --- DATI DI RENDERING E LOGICA ---
COLORS = np.zeros((MAX_BODIES, 3), dtype=np.uint8)
FLAGS  = np.zeros(MAX_BODIES, dtype=np.int32)
FLAG_ALIVE = 1
FLAG_DYING = 2
TOP_ATTRACTOR = np.full(MAX_BODIES, -1, dtype=np.int32)
COLLISION_COOLDOWN = np.zeros(1, dtype=np.int32)

# >>> NUOVE VARIABILI CACHE RENDERING (LOD) <<<
# Calcolate una volta sola dal Manager, lette 60 volte/sec dal Renderer
# >>> NUOVE VARIABILI CACHE RENDERING (LOD) <<<
TOP_MASS = 1.0 
LOD_MASK = np.ones(MAX_BODIES, dtype=bool) 
# Cache degli indici per evitare ricalcoli nel render frame
ACTIVE_INDICES_ALL = np.zeros(0, dtype=np.int64) 
ACTIVE_INDICES_LOD = np.zeros(0, dtype=np.int64) 
PHYS_ACTIVE_INDICES = np.zeros(MAX_BODIES, dtype=np.int32)


# =====================================================================
# --- SONDA LIGO (SPETTROGRAMMA E TELEMETRIA) ---
# =====================================================================
# Usiamo 2^21 (20971522) per poter usare la bitmask efficiente
# Costo RAM: ~16 Mb. RAW Data puro.
PROBE_LEN = 2**21  
PROBE_MASK = PROBE_LEN - 1

# Buffer circolare per i valori grezzi di DPHI
PROBE_BUFFER = np.zeros(1, dtype=np.float64)

# Array monoelemento per il controllo di stato in Numba
PROBE_HEAD = np.zeros(1, dtype=np.int32)
PROBE_POS = np.zeros(2, dtype=np.float64)
PROBE_ACTIVE = np.zeros(1, dtype=np.bool_)

# --- CALIBRAZIONE DINAMICA ONDE GRAVITAZIONALI (2.5PN) ---
# Moltiplicatore universale basato sulla Massa Chirp. 
# Calcolato dal Simulation Manager per la singola coppia relativistica più estrema.
M_CHIRP_MULT = np.array([1.0], dtype=np.float64)

# Flag UI per notificare al main thread che si sta svolgendo un evento 2.5PN (GW)
RADAR_WARNING_TRIGGERED = False


def ensure_capacity(needed_size):
    """Espande dinamicamente i vettori di base per evitare IndexError durante get_preset()."""
    global MAX_BODIES, POS, VEL, ACC, ART, MASS, RAD, FLAGS, TOP_ATTRACTOR, COLORS, LOD_MASK, PHYS_ACTIVE_INDICES, HEADS_L0, HEADS_L1, HEADS_L2
    if needed_size > MAX_BODIES:
        pad = needed_size - MAX_BODIES
        POS = np.vstack([POS, np.zeros((pad, 2), dtype=np.float64)])
        VEL = np.vstack([VEL, np.zeros((pad, 2), dtype=np.float64)])
        ACC = np.vstack([ACC, np.zeros((pad, 2), dtype=np.float64)])
        ART = np.vstack([ART, np.zeros((pad, 2), dtype=np.float64)])
        MASS = np.concatenate([MASS, np.zeros(pad, dtype=np.float64)])
        RAD = np.concatenate([RAD, np.zeros(pad, dtype=np.float64)])
        FLAGS = np.concatenate([FLAGS, np.zeros(pad, dtype=np.int32)])
        TOP_ATTRACTOR = np.concatenate([TOP_ATTRACTOR, np.full(pad, -1, dtype=np.int32)])
        COLORS = np.vstack([COLORS, np.zeros((pad, 3), dtype=np.uint8)])
        LOD_MASK = np.concatenate([LOD_MASK, np.zeros(pad, dtype=bool)])
        PHYS_ACTIVE_INDICES = np.concatenate([PHYS_ACTIVE_INDICES, np.zeros(pad, dtype=np.int32)])
        HEADS_L0 = np.concatenate([HEADS_L0, np.zeros(pad, dtype=np.int32)])
        HEADS_L1 = np.concatenate([HEADS_L1, np.zeros(pad, dtype=np.int32)])
        HEADS_L2 = np.concatenate([HEADS_L2, np.zeros(pad, dtype=np.int32)])
        MAX_BODIES = needed_size

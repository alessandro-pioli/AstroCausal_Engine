import math
import numpy as np
from core.data import G, C_LIGHT


def solve_pw_circular_velocity(M, r):
    """Velocità circolare esatta per il potenziale di Paczyński-Wiita (forma chiusa)."""
    if M <= 0 or r <= 0:
        return 0.0
    rs = 2.0 * G * M / (C_LIGHT ** 2)
    if r <= rs:
        return 0.0  # dentro l'orizzonte degli eventi

    # Condizione di circolarità: v^2 / r = G M / (r - rs)^2
    #   ->  v = sqrt(G M r) / (r - rs)
    return math.sqrt(G * M * r) / (r - rs)


def solve_velocity_from_apocenter(M, r_apo, r_peri):
    """
    Calcola la velocità al punto più LONTANO (apocentro)
    in modo che l'orbita 'cada' esattamente fino al pericentro desiderato.

    Forma chiusa (conservazione di energia + momento angolare nel potenziale PW),
    speculare a solve_velocity_from_pericenter:
      L = v_apo * r_apo = v_peri * r_peri  ->  v_peri = v_apo * (r_apo / r_peri)
      0.5 v_apo^2 - GM/(r_apo-rs) = 0.5 v_peri^2 - GM/(r_peri-rs)
    """
    if M <= 0 or r_apo <= 0 or r_peri <= 0:
        return 0.0
    rs = 2.0 * G * M / (C_LIGHT ** 2)
    v_circ = math.sqrt(G * M / r_apo)  # fallback fisicamente sensato
    if r_apo <= rs or r_peri <= rs:
        return v_circ

    term_pot = (r_apo - r_peri) / ((r_apo - rs) * (r_peri - rs))
    term_k = (r_apo / r_peri) ** 2 - 1.0  # > 0 perché r_apo > r_peri

    if term_k <= 0 or term_pot <= 0:
        return v_circ

    v_apo_sq = (2.0 * G * M * term_pot) / term_k
    return math.sqrt(v_apo_sq)


def solve_velocity_from_pericenter(M, r_peri, r_apo):
    """
    Calcola la velocità al punto più VICINO (pericentro)
    in modo che l'orbita raggiunga esattamente l'apocentro (usando potenziale perturbato per precisione).
    """
    if M <= 0 or r_peri <= 0 or r_apo <= 0:
        return 0.0
    rs = 2.0 * G * M / (C_LIGHT ** 2)
    v_circ = math.sqrt(G * M / r_peri)
    if r_apo <= rs or r_peri <= rs:
        return v_circ

    term_pot = (r_apo - r_peri) / ((r_apo - rs) * (r_peri - rs))
    term_k = 1.0 - (r_peri / r_apo) ** 2

    if term_k <= 0 or term_pot <= 0:
        return v_circ

    v_peri_sq = (2.0 * G * M * term_pot) / term_k
    return math.sqrt(v_peri_sq)


def solve_escape_velocity(M, r):
    """Velocità di fuga esatta nel potenziale di Paczyński-Wiita (forma chiusa)."""
    if M <= 0 or r <= 0:
        return 0.0
    rs = 2.0 * G * M / (C_LIGHT ** 2)
    if r <= rs:
        return 0.0

    # Condizione di fuga (E = 0): 0.5 v^2 = G M / (r - rs)
    #   ->  v = sqrt(2 G M / (r - rs))
    return math.sqrt(2.0 * G * M / (r - rs))


def solve_pair_circular_velocity(m1, m2, r):
    """
    Velocità relativa circolare ESATTA per una coppia stretta, calcolata contro
    la forza che il kernel applica davvero: Paczyński-Wiita PER-SORGENTE (rs del
    corpo sorgente, non della massa totale) più il softening del kernel.
    Replica compute_relativistic_force in regime GW (posizioni presenti):
    omega^2 = G*m2/(d*(d-rs2)^2) + G*m1/(d*(d-rs1)^2), con d = sqrt(r^2 + soft).

    Usare QUESTA (e non solve_pw_circular_velocity con la massa totale) per il
    lancio di binarie compatte: l'rs totale sovrastima la forza di ~3.5%, cioè
    ~1.8% di velocità in eccesso, cioè eccentricità spuria e~3% al lancio.
    """
    if m1 <= 0 or m2 <= 0 or r <= 0:
        return 0.0
    SOFTENING_SQ = 100.0
    d = math.sqrt(r * r + SOFTENING_SQ)
    rs1 = 2.0 * G * m1 / (C_LIGHT ** 2)
    rs2 = 2.0 * G * m2 / (C_LIGHT ** 2)
    d1 = max(d - rs1, 1.0)
    d2 = max(d - rs2, 1.0)
    omega_sq = (G * m2) / (d * d2 * d2) + (G * m1) / (d * d1 * d1)
    return r * math.sqrt(omega_sq)


def get_lagrange_points(m1, pos1, m2, pos2, vel1=None, vel2=None):
    """
    Coordinate dei 5 punti di Lagrange per la coppia (pos1, m1) e (pos2, m2).

    MODALITÀ FULL TEORICA: espressioni analitiche chiuse del problema ristretto
    dei 3 corpi CIRCOLARE, nessuna iterazione numerica (niente fsolve). Sono un
    riferimento di orientamento grossolano; la caccia ai nulli reali del campo
    (sensibili a eccentricità e perturbazioni, quindi disallineati da questi
    marker quanto più il sistema è eccentrico/perturbato) la fa la Lagrange heatmap.

    - L1/L2: espansione del raggio di Hill al second'ordine in alpha=(mu/3)^(1/3).
             Il termine (1 -/+ alpha/3) rompe correttamente la simmetria L1/L2
             attorno a m2 (L1 leggermente più vicino, L2 più lontano).
    - L3:    espansione classica al prim'ordine in mu, lato opposto oltre m1.
    - L4/L5: vertici equilateri esatti a +-60° (verso dato dal momento angolare).

    Validità: l'espansione assume mu = m2/(m1+m2) piccolo (m2 << m1). Per masse
    comparabili degrada, ma resta numericamente sicura (nessuna divisione per zero).
    """
    p1 = np.array(pos1, dtype=np.float64)
    p2 = np.array(pos2, dtype=np.float64)
    r_vec = p2 - p1
    r = np.linalg.norm(r_vec)
    if r == 0.0:
        return None

    m_tot = m1 + m2
    if m_tot <= 0.0:
        return None

    u = r_vec / r
    v_norm = np.array([-u[1], u[0]])

    mu = m2 / m_tot            # frazione di massa del secondo corpo
    x2 = (1.0 - mu) * r        # posizione di m2 rispetto al baricentro (lungo u)

    # --- Punti collineari (analitici, forma chiusa) ---
    alpha = (mu / 3.0) ** (1.0 / 3.0)
    hill = r * alpha
    x_L1 = x2 - hill * (1.0 - alpha / 3.0)   # tra i due corpi, lato m1
    x_L2 = x2 + hill * (1.0 + alpha / 3.0)   # oltre m2
    x_L3 = -r * (1.0 + 5.0 / 12.0 * mu)      # lato opposto, oltre m1

    bary = p1 + mu * r_vec
    L1 = bary + u * x_L1
    L2 = bary + u * x_L2
    L3 = bary + u * x_L3

    # --- Verso di rotazione (orario / antiorario) per posizionare L4 e L5 ---
    is_clockwise = False
    if vel1 is not None and vel2 is not None:
        v1 = np.array(vel1, dtype=np.float64)
        v2 = np.array(vel2, dtype=np.float64)
        v_rel = v2 - v1
        cross_prod = r_vec[0] * v_rel[1] - r_vec[1] * v_rel[0]
        if cross_prod < 0:
            is_clockwise = True

    angle_l4 = math.pi / 3 if is_clockwise else -math.pi / 3
    angle_l5 = -math.pi / 3 if is_clockwise else math.pi / 3

    L4 = p1 + r * (u * math.cos(angle_l4) + v_norm * math.sin(angle_l4))
    L5 = p1 + r * (u * math.cos(angle_l5) + v_norm * math.sin(angle_l5))

    return [L1.tolist(), L2.tolist(), L3.tolist(), L4.tolist(), L5.tolist()]


def solve_lagrange_boot_velocity(m1, pos1, vel1, m2, pos2, vel2, spawn_pos):
    """
    Calcola la velocità corotante per un satellite respawnato su un punto di Lagrange
    o genericamente a distanza dal baricentro di un sistema binario.
    """

    p1 = np.array(pos1, dtype=np.float64)
    v1 = np.array(vel1, dtype=np.float64)
    p2 = np.array(pos2, dtype=np.float64)
    v2 = np.array(vel2, dtype=np.float64)
    sp = np.array(spawn_pos, dtype=np.float64)

    m_tot = m1 + m2
    bary_pos = (p1*m1 + p2*m2) / m_tot
    bary_vel = (v1*m1 + v2*m2) / m_tot

    r_vec = p2 - p1
    r = np.linalg.norm(r_vec)
    if r == 0:
        return bary_vel.tolist()

    # Velocità angolare del sistema: ω = (v2_rel x r_rel) / |r_rel|^2
    v_rel = v2 - v1
    cross_prod = r_vec[0]*v_rel[1] - r_vec[1]*v_rel[0]
    omega = cross_prod / (r**2)

    R_bary = sp - bary_pos
    # V_corotating = ω x R_bary
    v_corot = np.array([-omega * R_bary[1], omega * R_bary[0]])

    return (bary_vel + v_corot).tolist()

import numpy as np
import threading
from core import data
import config
from core.bodies import CelestialBody
import math
from utils.formatting import format_dt


# ---------------------------------------------------------------------------
# Funzioni di utilità (standalone helpers)
# ---------------------------------------------------------------------------

def _show_oom_error(total_mb: float, n_bodies: int) -> None:
    """Mostra una finestra di errore OOM e termina il processo in modo sicuro."""
    import os
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()  # nasconde la finestra radice vuota
    messagebox.showerror(
        "Out of Memory — Buffer Allocation Failed",
        f"The simulator could not find enough RAM to allocate\n"
        f"the causal history buffers and/or the orbital trails.\n\n"
        f"Estimated RAM required: {total_mb / 1024:.2f} GB\n"
        f"Bodies in the scenario: {n_bodies}\n\n"
        "How to fix it:\n"
        "  1. Raise DT in the launcher before starting\n"
        "     (doubling DT halves the L0/L1/L2 slot count).\n"
        "  2. At runtime: avoid pushing DT too low with the\n"
        "     T key in scenarios with many bodies.\n"
        "  3. Pick a scenario with a smaller Sim Radius."
    )
    root.destroy()
    os._exit(1)


def _get_safe_power_2(raw_val, min_val=32):
    """Arrotonda raw_val alla potenza di 2 >= min_val. Usata per dimensionare i ring-buffer storici L0/L1/L2."""
    exponent = 0
    while True:
        check = 2**exponent
        if check >= raw_val and check >= min_val:
            return check
        exponent += 1


def _detect_body_timeline(body_idx: int, old_dt: float, void_val: float) -> tuple:
    """
    Ricostruisce la timeline causale assoluta di un corpo.
    I buffer storici (L0, L1, L2) si sovrappongono temporalmente (L1 parte da t=0 ma
    è sottocampionato, ecc.). Per evitare artefatti, ispezioniamo una singola linea
    temporale continua, saltando nei buffer di livello inferiore le celle ridondanti
    già coperte dai livelli a risoluzione maggiore.
    
    In questo modo:
    1. La morte causale profonda (t_dead > span di L0) viene tracciata correttamente in L1/L2.
    2. La nascita recente non viene falsata dalle celle VOID iniziali di L1 dovute allo stride.
    """
    threshold = void_val * 0.9
    t_dead = 0.0
    t_alive = -1.0

    found_valid = False
    found_birth = False

    # --- FASE 1: L0 ---
    if data.HISTORY_L0 is not None:
        head = data.HEADS_L0[body_idx]
        for k in range(data.LEN_L0):
            ptr = (head - k) & data.MASK_L0
            is_void = data.HISTORY_L0[body_idx, ptr, 0] <= threshold
            current_time = k * old_dt

            if not found_valid:
                if is_void:
                    t_dead = current_time + old_dt
                else:
                    found_valid = True
            elif is_void:
                t_alive = current_time
                found_birth = True
                break

    if found_birth:
        return t_dead, t_alive

    # --- FASE 2: L1 (Solo la parte più vecchia di L0) ---
    if data.HISTORY_L1 is not None:
        head = data.HEADS_L1[body_idx]
        start_k = data.LEN_L0 // 32 if data.HISTORY_L0 is not None else 0
        for k in range(start_k, data.LEN_L1):
            ptr = (head - k) & data.MASK_L1
            is_void = data.HISTORY_L1[body_idx, ptr, 0] <= threshold
            current_time = k * 32 * old_dt

            if not found_valid:
                if is_void:
                    t_dead = current_time + 32 * old_dt
                else:
                    found_valid = True
            elif is_void:
                t_alive = current_time
                found_birth = True
                break

    if found_birth:
        return t_dead, t_alive

    # --- FASE 3: L2 (Solo la parte più vecchia di L1) ---
    if data.HISTORY_L2 is not None:
        head = data.HEADS_L2[body_idx]
        start_k = (data.LEN_L1 * 32) // 256 if data.HISTORY_L1 is not None else 0
        for k in range(start_k, data.LEN_L2):
            ptr = (head - k) & data.MASK_L2
            is_void = data.HISTORY_L2[body_idx, ptr, 0] <= threshold
            current_time = k * 256 * old_dt

            if not found_valid:
                if is_void:
                    t_dead = current_time + 256 * old_dt
                else:
                    found_valid = True
            elif is_void:
                t_alive = current_time
                found_birth = True
                break

    return t_dead, t_alive


def _calculate_universal_gw_boost(m1, m2):
    """
    Calcola il moltiplicatore universale 2.5PN basato sulla Massa Chirp.
    Nuovo paradigma calibrato empiricamente su GW170817 (15.000s) e GW150914.
    """
    # Questo è deadcode addormentato, in futuro potrebbe tornare in qualche forma.
    if True:
        return 1

    M_SUN = 1.98847e30

    # --- I NUOVI PILASTRI (Il Paradigma Definitivo) ---
    M_CHIRP_REF = 1.188          # Massa Chirp GW170817 (Nuovo Punto Zero)
    B_REF = 1.0
    # precalcolato K_EXP = math.log(B_BH / B_NS) / math.log(M_CHIRP_BH / M_CHIRP_NS)
    K_EXP = 0.3226               # Esponente di curvatura inter-scalare

    # 1. Calcolo Massa Chirp della Simulazione
    m1_sol = m1 / M_SUN
    m2_sol = m2 / M_SUN
    m_tot_sol = m1_sol + m2_sol

    if m_tot_sol <= 0.0:
        return 0.0

    m_chirp_sim = (math.pow(m1_sol * m2_sol, 0.6)) / (math.pow(m_tot_sol, 0.2))
    print("m_chirp_sim", m_chirp_sim)

    boost_mass = math.pow(m_chirp_sim / M_CHIRP_REF, K_EXP)

    m_chirp_mult = B_REF * boost_mass

    return m_chirp_mult 


def _fill_hist_vectorized(hist, mask, length, stride, idx, pos, vel, t_dead, t_alive, mass, active_dt):
    """Riempimento vettorizzato NumPy: O(1) kernel calls invece di O(N) loop Python."""
    if hist is None or length == 0: return
    dt_level = active_dt * stride

    # k = [0, 1, 2, ..., length-1]
    k_arr = np.arange(length, dtype=np.float64)
    t_past_arr = k_arr * dt_level

    # Indici circolari: ptr = (-k) & mask
    ptr_arr = ((-k_arr.astype(np.int64)) & mask).astype(np.int64)

    # Maschera validità: void se morto-prima o nato-dopo
    void_mask = np.zeros(length, dtype=bool)
    if t_dead > 0.0:
        void_mask |= (t_past_arr < t_dead)
    if t_alive >= 0.0:
        void_mask |= (t_past_arr >= t_alive)

    # Tempo di moto effettivo (sottraiamo t_dead se esiste)
    moving_time = t_past_arr - (t_dead if t_dead > 0.0 else 0.0)

    # Riempiamo tutto come se fosse valido (veloce)
    hist[idx, ptr_arr, 0] = pos[0] - vel[0] * moving_time
    hist[idx, ptr_arr, 1] = pos[1] - vel[1] * moving_time
    hist[idx, ptr_arr, 2] = vel[0]
    hist[idx, ptr_arr, 3] = vel[1]
    hist[idx, ptr_arr, 4] = mass

    # Sovrascriviamo con VOID dove richiesto (solo le celle invalide)
    if np.any(void_mask):
        hist[idx, ptr_arr[void_mask], 0] = data.VOID_VAL


def _get_cpu_details(default_l3=16.0):
    """
    Rileva dinamicamente nome CPU e dimensioni cache L1 (KB), L2 (MB) e L3 (MB).
    Supporta Windows, Linux e macOS con fallback a valori di default.
    """
    import platform
    import subprocess
    import json
    import re

    cpu_name = "Processore Generico"
    l1_kb = 0.0
    l2_mb = 0.0
    l3_mb = default_l3

    system = platform.system()
    try:
        if system == "Windows":
            # 1. Rileva nome CPU
            cmd_name = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"]
            out_name = subprocess.check_output(cmd_name, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            if out_name:
                cpu_name = out_name

            # 2. Rileva cache
            cmd_cache = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_CacheMemory | Select-Object Level, InstalledSize | ConvertTo-Json"]
            out_cache = subprocess.check_output(cmd_cache, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            if out_cache:
                # FIX: rinominato da `data` a `cache_data` per evitare shadowing del modulo `data`
                cache_data = json.loads(out_cache)
                if not isinstance(cache_data, list):
                    cache_data = [cache_data]

                l1_sizes = [item.get("InstalledSize", 0) for item in cache_data if item.get("Level") == 3]
                l2_sizes = [item.get("InstalledSize", 0) for item in cache_data if item.get("Level") == 4]
                l3_sizes = [item.get("InstalledSize", 0) for item in cache_data if item.get("Level") == 5]

                if l1_sizes: l1_kb = float(sum(l1_sizes))
                if l2_sizes: l2_mb = float(sum(l2_sizes)) / 1024.0
                if l3_sizes: l3_mb = float(max(l3_sizes)) / 1024.0

        elif system == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_name = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

            def read_sysfs_cache(index_str):
                """Legge la dimensione di una cache Linux da /sys e la normalizza sempre
                in KB, qualunque sia il suffisso (K/M/G) scritto nel file."""
                try:
                    with open(f"/sys/devices/system/cpu/cpu0/cache/{index_str}/size", "r") as f:
                        size_str = f.read().strip().upper()
                        match = re.match(r"(\d+)\s*([KMG]?)", size_str)
                        if match:
                            val = float(match.group(1))
                            unit = match.group(2)
                            if unit == "K": return val
                            elif unit == "M": return val * 1024.0
                            elif unit == "G": return val * 1024.0 * 1024.0
                            else: return val / 1024.0
                except Exception:
                    pass
                return 0.0

            l1_kb = read_sysfs_cache("index0") + read_sysfs_cache("index1")
            l2_mb = read_sysfs_cache("index2") / 1024.0
            l3_mb = read_sysfs_cache("index3") / 1024.0
            if l3_mb == 0.0:
                l3_mb = default_l3

        elif system == "Darwin":
            out_brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            if out_brand:
                cpu_name = out_brand

            out_l1i = subprocess.check_output(["sysctl", "-n", "hw.l1icachesize"], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            out_l1d = subprocess.check_output(["sysctl", "-n", "hw.l1dcachesize"], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            out_l2  = subprocess.check_output(["sysctl", "-n", "hw.l2cachesize"],  stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            out_l3  = subprocess.check_output(["sysctl", "-n", "hw.l3cachesize"],  stderr=subprocess.DEVNULL, timeout=5).decode().strip()

            if out_l1i and out_l1d:
                l1_kb = (float(out_l1i) + float(out_l1d)) / 1024.0
            if out_l2:
                l2_mb = float(out_l2) / (1024.0 * 1024.0)
            if out_l3:
                l3_mb = float(out_l3) / (1024.0 * 1024.0)
            else:
                l3_mb = default_l3
    except Exception:
        pass

    return cpu_name, l1_kb, l2_mb, l3_mb


# Rilevamento dinamico globale delle specifiche della CPU all'importazione
CPU_FORMAL_NAME, L1_CACHE_KB, L2_CACHE_MB, L3_PHYSICAL_CACHE_MB = _get_cpu_details(default_l3=16.0)
L3_CACHE_LIMIT = L3_PHYSICAL_CACHE_MB * 0.7
_CPU_INFO_PRINTED = False


# ---------------------------------------------------------------------------
# Fasi private di rebuild_simulation
# ---------------------------------------------------------------------------

def _print_cpu_info_once() -> None:
    """Stampa le specifiche CPU rilevate, solo al primo avvio."""
    global _CPU_INFO_PRINTED
    if not _CPU_INFO_PRINTED:
        print(f"[CPU INFO] Detected CPU: {CPU_FORMAL_NAME}")
        print(f"[CPU INFO] Detected caches — L1: {L1_CACHE_KB:.1f} KB | L2: {L2_CACHE_MB:.1f} MB | L3 CACHE: {L3_PHYSICAL_CACHE_MB:.1f} MB (70% limit threshold: {L3_CACHE_LIMIT:.1f} MB)")
        _CPU_INFO_PRINTED = True


def _take_snapshot(current_bodies, old_dt: float) -> tuple:
    """
    Fase 1 — Salva lo stato completo di tutti i corpi attivi e dei buffer di supporto
    (scie orbitali e sonda LIGO) prima di deallocare e ricostruire la simulazione.

    Returns:
        snapshots (list[dict]): Stato di ogni corpo vivo (massa, pos, vel, timeline causale...).
        backups (dict): Copie profonde dei buffer di trail, LIGO probe e buffer storici L0/L1/L2.
    """
    backups = {
        'trails_buffer': np.copy(data.TRAIL_BUFFER),
        'trails_heads': np.copy(data.TRAIL_HEADS),
        'trails_last': np.copy(data.TRAIL_LAST_POS),
        'probe_was_active': False,
        'old_L0_len': data.LEN_L0,
        'old_L1_len': data.LEN_L1,
        'old_L2_len': data.LEN_L2,
        'h0': np.copy(data.HISTORY_L0) if data.HISTORY_L0 is not None else None,
        'h1': np.copy(data.HISTORY_L1) if data.HISTORY_L1 is not None else None,
        'h2': np.copy(data.HISTORY_L2) if data.HISTORY_L2 is not None else None,
        'hd0': np.copy(data.HEADS_L0),
        'hd1': np.copy(data.HEADS_L1),
        'hd2': np.copy(data.HEADS_L2),
    }

    if hasattr(data, 'PROBE_ACTIVE') and data.PROBE_ACTIVE[0]:
        backups['probe_was_active'] = True
        backups['probe_buffer'] = np.copy(data.PROBE_BUFFER)
        backups['probe_head'] = data.PROBE_HEAD[0]
        backups['probe_pos'] = np.copy(data.PROBE_POS)

    has_art = hasattr(data, 'ART') and data.ART is not None
    snapshots = []

    for b in current_bodies:
        if b.pos[0] <= data.VOID_VAL:
            continue

        t_dead, t_alive = _detect_body_timeline(b.idx, old_dt, data.VOID_VAL)

        art_val = np.array([0.0, 0.0], dtype=np.float64)
        if has_art and b.idx < len(data.ART):
            art_val = np.copy(data.ART[b.idx])

        snapshots.append({
            'mass':       b.mass,
            'pos':        np.copy(b.pos),
            'vel':        np.copy(b.vel),
            'rad':        b.radius,
            'col':        b.color,
            'name':       b.name,
            'old_idx':    b.idx,
            'flags':      data.FLAGS[b.idx],
            'time_dead':  t_dead,
            'time_alive': t_alive,
            'art':        art_val,
        })

    return snapshots, backups


def _apply_new_params(new_dt, new_sim_rad) -> tuple:
    """
    Fase 2 — Aggiorna DT, raggio simulativo e tutte le costanti derivate in data e config.

    Returns:
        (active_dt, active_rad)
    """
    active_dt = new_dt if new_dt is not None else data.DT
    active_rad = new_sim_rad if new_sim_rad is not None else data.SIMULATION_RADIUS_KM

    config.SIMULATION_RADIUS_KM = active_rad
    data.DT = active_dt
    data.SIMULATION_RADIUS_KM = active_rad
    data.INV_DT = 1.0 / active_dt
    data.INV_C_DT = 1.0 / (data.C_LIGHT * active_dt)

    return active_dt, active_rad


def _plan_buffer_architecture(is_causal_info_on: bool, n_existing: int, new_body_params) -> float:
    """
    Fase 3 — Sceglie la modalità buffer (SINGLE / DOUBLE / TRIPLE) in base alla
    dimensione della L3 cache e al raggio simulativo, poi scrive le costanti
    LEN_*, MASK_*, METHOD e MAX_BODIES in data. Stampa il report memoria.

    Returns:
        total_mb (float): RAM stimata richiesta, usata per la protezione OOM in Fase 4.
    """
    needed_capacity = n_existing + (1 if new_body_params else 0)
    data.MAX_BODIES = max(1, needed_capacity)
    N = data.MAX_BODIES

    if is_causal_info_on:
        raw_len_needed = data.SIMULATION_RADIUS_KM * data.INV_C_DT
        slots_single = _get_safe_power_2(raw_len_needed)
    else:
        raw_len_needed = 1
        slots_single = 1

    mb_single = (slots_single * 40) / (1024 * 1024) * N

    final_method = "SINGLE"
    final_L0, final_L1, final_L2 = slots_single, 0, 0

    if mb_single >= L3_CACHE_LIMIT:
        # Calcola il fattore di riduzione dinamico per far stare L0 in L3 Cache
        l0_base_cap = 16384
        n_exp = 0
        while True:
            current_l0_cap = l0_base_cap // (2 ** n_exp)
            mb_l0_cap = (current_l0_cap * 40) / (1024 * 1024) * N
            if mb_l0_cap < L3_CACHE_LIMIT or current_l0_cap <= 1024:
                break
            n_exp += 1
        reduction_factor = 2 ** n_exp

        l0_double_cap = 16384 // reduction_factor
        slots_L1 = _get_safe_power_2(raw_len_needed / 32.0)
        mb_double = ((l0_double_cap + slots_L1) * 40) / (1024 * 1024) * N

        if mb_double < L3_CACHE_LIMIT:
            final_method = "DOUBLE"
            final_L0, final_L1 = l0_double_cap, slots_L1
            print(f"[CPU INFO] DOUBLE Mode Selected: Buffer L0+L1 footprint = {mb_double:.3f} MB (CACHE L3 Limit Threshold = {L3_CACHE_LIMIT:.3f} MB)")
        else:
            slots_L2 = _get_safe_power_2(raw_len_needed / 256.0)
            # Budget dinamico L2: max 2^28 celle totali divise per numero di corpi
            # Ogni slot = 5 × float64 = 40 byte → 2^28 × 40 B ≈ 10 GB totali
            slots_L2_budget_raw = (2 ** 28) // max(1, needed_capacity)
            p2_exp = max(5, int(math.floor(math.log2(max(32, slots_L2_budget_raw)))))
            slots_L2 = min(slots_L2, 2 ** p2_exp)

            final_method = "TRIPLE"
            final_L0 = 16384 // reduction_factor
            final_L1 = 2048
            final_L2 = slots_L2

            mb_l0_l1 = (final_L0 + final_L1) * 40 / (1024 * 1024) * N
            print(f"[CPU INFO] TRIPLE Mode Selected: Buffer L0+L1 footprint = {mb_l0_l1:.3f} MB (CACHE L3 Limit Threshold = {L3_CACHE_LIMIT:.3f} MB)")
    else:
        print(f"[CPU INFO] SINGLE Mode Selected: Buffer L0 footprint = {mb_single:.3f} MB (CACHE L3 Limit Threshold = {L3_CACHE_LIMIT:.3f} MB)")

    data.METHOD = final_method
    data.LEN_L0, data.LEN_L1, data.LEN_L2 = final_L0, final_L1, final_L2
    data.MASK_L0 = final_L0 - 1 if final_L0 > 0 else 0
    data.MASK_L1 = final_L1 - 1 if final_L1 > 0 else 0
    data.MASK_L2 = final_L2 - 1 if final_L2 > 0 else 0

    # --- Report memoria (usa TRAIL_LENGTH corrente, non ancora aggiornato) ---
    DT = data.DT
    F8 = 8          # float64 = 8 byte
    l0_mb = N * final_L0 * 5 * F8 / 1024**2
    l1_mb = N * final_L1 * 5 * F8 / 1024**2
    l2_mb = N * final_L2 * 5 * F8 / 1024**2
    trail_mb = N * data.TRAIL_LENGTH * 2 * F8 / 1024**2
    total_mb = l0_mb + l1_mb + l2_mb + trail_mb

    W = 72
    print(f"\033[93;1mACTUAL SIMULATION DT: {DT} seconds/step\033[0m")
    print(f"[MEM CHECK] Mode: {final_method} | CPU L3 Cache: {L3_PHYSICAL_CACHE_MB:.1f} MB (70% Threshold: {L3_CACHE_LIMIT:.1f} MB)")
    print(f"  {'Buffer':<12}  {'Slots/body':>12}  {'Total slots':>14}  {'Temporal resolution':<24}  {'RAM':>10}")
    print(f"  {'-'*W}")
    if final_L0 > 0:
        print(f"  {'HISTORY_L0':<12}  {final_L0:>12,}  {final_L0*N:>14,}  {f'1×DT = {format_dt(DT)}':<24}  {l0_mb:>8.2f} MB")
    if final_L1 > 0:
        print(f"  {'HISTORY_L1':<12}  {final_L1:>12,}  {final_L1*N:>14,}  {f'32×DT = {format_dt(DT*32)}':<24}  {l1_mb:>8.2f} MB")
    if final_L2 > 0:
        print(f"  {'HISTORY_L2':<12}  {final_L2:>12,}  {final_L2*N:>14,}  {f'256×DT = {format_dt(DT*256)}':<24}  {l2_mb:>8.2f} MB")
    print(f"  {'Trail':<12}  {data.TRAIL_LENGTH:>12,}  {data.TRAIL_LENGTH*N:>14,}  {'(graphics)':<24}  {trail_mb:>8.2f} MB")
    print(f"  {'-'*W}")
    print(f"  {'TOTAL':<12}  {'':>12}  {'':>14}  {'':24}  {total_mb:>8.2f} MB  ({total_mb/1024:.3f} GB)")
    print(f"[DATA ALLOC] L0={final_L0}, L1={final_L1}, L2={final_L2} | Trail={data.TRAIL_LENGTH} | Bodies={N}")

    return total_mb


def _wipe_and_alloc(total_mb: float) -> None:
    """
    Fase 4 — Azzera e ri-alloca tutti gli array NumPy in data usando le dimensioni
    calcolate in Fase 3. Intercetta MemoryError e mostra il dialogo OOM.
    Disattiva anche la sonda LIGO (verrà ripristinata in Fase 5 se necessario).
    """
    N = data.MAX_BODIES

    data.POS = np.zeros((N, 2), dtype=np.float64)
    data.VEL = np.zeros((N, 2), dtype=np.float64)
    data.ACC = np.zeros((N, 2), dtype=np.float64)
    data.ART = np.zeros((N, 2), dtype=np.float64)
    data.MASS = np.zeros(N, dtype=np.float64)
    data.RAD = np.zeros(N, dtype=np.float64)
    data.FLAGS = np.zeros(N, dtype=np.int32)
    data.TOP_ATTRACTOR = np.full(N, -1, dtype=np.int32)
    data.COLORS = np.zeros((N, 3), dtype=np.uint8)
    data.LOD_MASK = np.zeros(N, dtype=bool)

    try:
        data.HISTORY_L0 = np.zeros((N, data.LEN_L0, 5), dtype=np.float64) if data.LEN_L0 > 0 else None
        data.HISTORY_L1 = np.zeros((N, data.LEN_L1, 5), dtype=np.float64) if data.LEN_L1 > 0 else None
        data.HISTORY_L2 = np.zeros((N, data.LEN_L2, 5), dtype=np.float64) if data.LEN_L2 > 0 else None

        data.HEADS_L0 = np.zeros(N, dtype=np.int32)
        data.HEADS_L1 = np.zeros(N, dtype=np.int32)
        data.HEADS_L2 = np.zeros(N, dtype=np.int32)

        data.VOID_VAL = -data.SIMULATION_RADIUS_KM * 1e10 * 0.9

        # Trail dinamico: budget totale 2^17 slot, min 2^10, max 2^17 per corpo
        trail_budget_raw = (2**17) // max(1, N)
        trail_p2 = max(10, min(17, int(math.floor(math.log2(max(1, trail_budget_raw))))))
        data.TRAIL_LENGTH = 2 ** trail_p2

        data.TRAIL_BUFFER = np.full((N, data.TRAIL_LENGTH, 2), data.VOID_VAL, dtype=np.float64)
        data.TRAIL_HEADS = np.zeros(N, dtype=np.int32)
        data.TRAIL_LAST_POS = np.full((N, 2), -1e20, dtype=np.float64)
        data.PHYS_ACTIVE_INDICES = np.zeros(N, dtype=np.int32)
        data.COLLISION_COOLDOWN = np.zeros(1, dtype=np.int32)
        data.PROBE_BUFFER = np.zeros(data.PROBE_LEN, dtype=np.float64)

    except MemoryError:
        _show_oom_error(total_mb, N)

    # Spegni la sonda in modo sicuro (verrà riattivata in _restore_bodies se era attiva)
    if hasattr(data, 'PROBE_ACTIVE'):
        data.PROBE_ACTIVE[0] = False


def _restore_bodies(snapshots: list, backups: dict, active_dt: float, old_dt: float, new_body_params) -> list:
    """
    Fase 5 — Rinietta ogni corpo negli array appena allocati, preservando la storia
    orbitale tramite deep copy (se DT e dimensioni buffer non sono cambiati) o
    interpolazione lineare vettorizzata. Ripristina scie orbitali e sonda LIGO.

    Returns:
        new_bodies_list (list[CelestialBody])
    """
    new_bodies_list = []
    idx_counter = 0

    can_deep_copy = (
        active_dt == old_dt
        and data.LEN_L0 == backups['old_L0_len']
        and data.LEN_L1 == backups['old_L1_len']
        and data.LEN_L2 == backups['old_L2_len']
    )

    if can_deep_copy:
        print("[SIM MANAGER] Executing SMART COPY: historical orbits will be preserved intact.")
    else:
        print("[SIM MANAGER] Parameter change detected. Executing LINEAR INTERPOLATION on historical buffers.")

    for snap in snapshots:
        b = CelestialBody(
            idx_counter, snap['mass'], snap['pos'], snap['vel'],
            radius=snap['rad'], color=snap['col'], pre_existed=False,
            name=snap['name']
        )

        data.ART[idx_counter] = snap['art']
        data.FLAGS[idx_counter] = snap['flags']

        old_idx = snap['old_idx']
        t_dead = snap['time_dead']
        t_alive = snap['time_alive']
        pos = snap['pos']
        vel = snap['vel']

        if can_deep_copy:
            if backups['h0'] is not None and data.HISTORY_L0 is not None:
                data.HISTORY_L0[idx_counter] = backups['h0'][old_idx]
                data.HEADS_L0[idx_counter] = backups['hd0'][old_idx]
            if backups['h1'] is not None and data.HISTORY_L1 is not None:
                data.HISTORY_L1[idx_counter] = backups['h1'][old_idx]
                data.HEADS_L1[idx_counter] = backups['hd1'][old_idx]
            if backups['h2'] is not None and data.HISTORY_L2 is not None:
                data.HISTORY_L2[idx_counter] = backups['h2'][old_idx]
                data.HEADS_L2[idx_counter] = backups['hd2'][old_idx]
        else:
            _fill_hist_vectorized(data.HISTORY_L0, data.MASK_L0, data.LEN_L0, 1, idx_counter, pos, vel, t_dead, t_alive, snap['mass'], active_dt)
            _fill_hist_vectorized(data.HISTORY_L1, data.MASK_L1, data.LEN_L1, 32, idx_counter, pos, vel, t_dead, t_alive, snap['mass'], active_dt)
            _fill_hist_vectorized(data.HISTORY_L2, data.MASK_L2, data.LEN_L2, 256, idx_counter, pos, vel, t_dead, t_alive, snap['mass'], active_dt)

        # --- Ripristino scie orbitali ---
        if old_idx < len(backups['trails_buffer']):
            old_tl = backups['trails_buffer'].shape[1]
            new_tl = data.TRAIL_LENGTH
            old_buf = backups['trails_buffer'][old_idx]
            old_head = int(backups['trails_heads'][old_idx])

            if old_tl == new_tl:
                # Stesso size: copia diretta
                data.TRAIL_BUFFER[idx_counter] = old_buf
                data.TRAIL_HEADS[idx_counter] = old_head
            else:
                # Size cambiato: copia i min(old, new) punti più recenti
                n_copy = min(old_tl, new_tl)
                for k in range(n_copy):
                    src_ptr = (old_head - k) % old_tl
                    dst_ptr = (new_tl - 1 - k) % new_tl
                    data.TRAIL_BUFFER[idx_counter, dst_ptr] = old_buf[src_ptr]
                data.TRAIL_HEADS[idx_counter] = new_tl - 1

            data.TRAIL_LAST_POS[idx_counter] = backups['trails_last'][old_idx]

        new_bodies_list.append(b)
        idx_counter += 1

    # --- Corpo appena spawnato (se presente) ---
    if new_body_params:
        new_name = new_body_params.get('name', f"Spawned_Body_{idx_counter}")
        b_new = CelestialBody(
            idx_counter, new_body_params['mass'], new_body_params['pos'], new_body_params['vel'],
            radius=new_body_params['rad'], color=new_body_params['col'], pre_existed=False,
            name=new_name
        )
        new_bodies_list.append(b_new)
        idx_counter += 1

    # --- Ripristino sonda LIGO ---
    if backups['probe_was_active']:
        data.PROBE_ACTIVE[0] = True
        data.PROBE_POS[:] = backups['probe_pos']

        if can_deep_copy:
            data.PROBE_HEAD[0] = backups['probe_head']
            data.PROBE_BUFFER[:] = backups['probe_buffer']
            print("[SIM MANAGER] LIGO Probe RAW telemetry preserved intact.")
        else:
            print("[SIM MANAGER] Parameter change detected. Triggering LIGO dump and buffer reset...")
            ordered = np.roll(backups['probe_buffer'], -backups['probe_head'])

            import os
            import time
            output_dir = os.path.join("ligo_output", "data_npy")
            os.makedirs(output_dir, exist_ok=True)
            timestamp = int(time.time())
            filename = os.path.join(output_dir, f"ligo_dump_DT_{old_dt}_{timestamp}.npy")

            def _dump_task(data_arr, fname):
                """Salva il buffer della sonda LIGO su disco in un thread daemon separato,
                per non bloccare il rebuild sull'I/O di un array potenzialmente grande."""
                try:
                    np.save(fname, data_arr)
                    print(f"[LIGO PROBE] Previous history saved in {fname}")
                except Exception as e:
                    print(f"[LIGO PROBE] Save error: {e}")

            threading.Thread(target=_dump_task, args=(ordered, filename), daemon=True).start()

            data.PROBE_BUFFER.fill(0.0)
            data.PROBE_HEAD[0] = 0

    return new_bodies_list


def _update_lod_and_indices(n_bodies: int) -> None:
    """
    Fase 6 — Aggiorna la cache statica LOD (Level of Detail) e gli indici di rendering
    attivi (ACTIVE_INDICES_ALL e ACTIVE_INDICES_LOD) in base alle masse e allo stato
    FLAG_ALIVE dei corpi appena ripristinati.
    """
    current_masses = data.MASS[:n_bodies]
    data.TOP_MASS = np.max(current_masses) if len(current_masses) > 0 else 1.0

    data.LOD_MASK[:] = False
    data.LOD_MASK[:n_bodies] = (data.MASS[:n_bodies] * 1_000_000.0 >= data.TOP_MASS)

    base_mask = (
        (data.POS[:n_bodies, 0] > data.VOID_VAL) &
        (data.FLAGS[:n_bodies] & data.FLAG_ALIVE != 0)
    )
    data.ACTIVE_INDICES_ALL = np.where(base_mask)[0].astype(np.int64)

    lod_mask = base_mask & data.LOD_MASK[:n_bodies]
    if not np.any(lod_mask):
        lod_mask = base_mask
    data.ACTIVE_INDICES_LOD = np.where(lod_mask)[0].astype(np.int64)


def _run_relativistic_radar() -> None:
    """
    Fase 7 — RADAR Relativistico.
    Individua coppie di corpi in regime relativistico estremo per il monitoraggio.
    Nota: L'auto-taratura della massa chirp è disattivata (boost fisso a 1.0).
    """
    data.M_CHIRP_MULT[0] = 1.0  # Reset al default

    n_active = len(data.ACTIVE_INDICES_ALL)
    if n_active < 2:
        return

    THRESHOLD_GW = 0.0025 * data.C_SQ  # ~5% della velocità della luce al quadrato

    for i in range(n_active):
        idx1 = data.ACTIVE_INDICES_ALL[i]
        m1 = data.MASS[idx1]
        p1x, p1y = data.POS[idx1]
        v1x, v1y = data.VEL[idx1]

        for j in range(i + 1, n_active):
            idx2 = data.ACTIVE_INDICES_ALL[j]
            m2 = data.MASS[idx2]
            dx = data.POS[idx2][0] - p1x
            dy = data.POS[idx2][1] - p1y
            dist = math.sqrt(dx*dx + dy*dy)
            dvx = data.VEL[idx2][0] - v1x
            dvy = data.VEL[idx2][1] - v1y
            v_rel_sq = dvx*dvx + dvy*dvy
            r_s_tot = (m1 + m2) * data.RS_FACTOR

            if v_rel_sq > THRESHOLD_GW and dist < (r_s_tot * 100.0):
                data.M_CHIRP_MULT[0] = _calculate_universal_gw_boost(m1, m2)
                if not data.RADAR_WARNING_TRIGGERED:
                    data.RADAR_WARNING_TRIGGERED = True
                    print(f"\n[RADAR 2.5PN] Relativistic Trigger! M={data.M_CHIRP_MULT[0]:.2e}")
                return  # Basta la prima coppia relativistica trovata


def _compute_top_attractors(n_bodies: int) -> None:
    """
    Fase 8 — Calcola TOP_ATTRACTOR per ogni corpo: l'indice del corpo più massiccio
    che esercita la forza di marea (M/r³) più intensa. Usato per il sistema
    co-rotante del Lagrange Hunter e dei Lobi di Roche.
    Gestisce il caso limite («il Re») in cui il corpo più massiccio non ha un
    attrattore superiore a sé: lo si fa puntare al secondo più massiccio.
    """
    # 8.1 — Trova i due corpi più massicci per il Fallback
    top1_idx, top2_idx = -1, -1
    for i in range(n_bodies):
        if (data.FLAGS[i] & data.FLAG_ALIVE) == 0:
            continue
        if top1_idx == -1 or data.MASS[i] > data.MASS[top1_idx]:
            top2_idx = top1_idx
            top1_idx = i
        elif top2_idx == -1 or data.MASS[i] > data.MASS[top2_idx]:
            top2_idx = i

    # 8.2 — Assegna l'attrattore dominante a ciascun corpo
    for i in range(n_bodies):
        if (data.FLAGS[i] & data.FLAG_ALIVE) == 0:
            continue

        best_attr = -1
        max_pull = -1.0
        px, py = data.POS[i]

        for j in range(n_bodies):
            if i == j:
                continue
            if (data.FLAGS[j] & data.FLAG_ALIVE) == 0:
                continue
            # L'attrattore deve essere più massiccio del corpo corrente
            if data.MASS[j] <= data.MASS[i]:
                continue

            dx = data.POS[j, 0] - px
            dy = data.POS[j, 1] - py
            dist_sq = max(dx*dx + dy*dy, 1.0)

            # Forza di Marea: M / r³ — identifica la sfera di Hill locale
            pull = data.MASS[j] / (dist_sq * math.sqrt(dist_sq))

            if pull > max_pull:
                max_pull  = pull
                best_attr = j

        # Fallback: il corpo più massiccio non ha un attrattore superiore
        if best_attr == -1:
            if i == top1_idx and top2_idx != -1:
                best_attr = top2_idx   # «Il Re» punta al «Principe»
            elif top1_idx != -1 and i != top1_idx:
                best_attr = top1_idx   # Gli orfani puntano al «Re»

        data.TOP_ATTRACTOR[i] = best_attr


def _prime_initial_accelerations() -> None:
    """
    Fase 9 — Priming delle accelerazioni iniziali (warm-start del Verlet).
    Dopo ogni rebuild data.ACC è azzerato: il primissimo half-kick del Velocity
    Verlet partirebbe con a=0, iniettando un piccolo transiente di velocità
    (~0.5*a*DT) a ogni avvio, cambio DT o spawn. Qui le accelerazioni
    gravitazionali (Newton + Paczyński-Wiita + ART) vengono precalcolate in un
    colpo solo via broadcasting NumPy, così il primo tick parte già "caldo".

    Approssimazioni deliberate (di secondo ordine sul transiente eliminato):
    - posizioni PRESENTI per tutti: a t=0 lo storico è backfillato a velocità
      costante, quindi coincide con la stima del dead reckoning;
    - niente Liénard-Wiechert né 2.5PN.
    Cold path: gira una volta per rebuild. A N=200 i temporanei pesano ~1.5 MB,
    liberati dal reference counting al return della funzione.
    """
    from core.jit_kernels.kernel_helper_inline import SOFTENING_SQ

    alive = np.where(((data.FLAGS & data.FLAG_ALIVE) != 0) & ((data.FLAGS & data.FLAG_DYING) == 0) & (data.MASS > 0.0))[0]
    n = len(alive)
    if n < 2:
        return

    pos = data.POS[alive]        # (n, 2)
    mass = data.MASS[alive]      # (n,)

    d = pos[None, :, :] - pos[:, None, :]                    # (n, n, 2): vettore i -> j
    r = np.sqrt(d[:, :, 0]**2 + d[:, :, 1]**2 + SOFTENING_SQ)
    rs = mass * data.RS_FACTOR                               # R_s della sorgente j
    r_pw = np.maximum(r - rs[None, :], 1.0)                  # stesso clamp del kernel
    scalar = (data.G * mass[None, :]) / (r * r_pw * r_pw)    # come sezione 3 del kernel
    np.fill_diagonal(scalar, 0.0)                            # nessuna auto-attrazione

    data.ACC[alive, 0] = np.sum(scalar * d[:, :, 0], axis=1) + data.ART[alive, 0]
    data.ACC[alive, 1] = np.sum(scalar * d[:, :, 1], axis=1) + data.ART[alive, 1]


# ---------------------------------------------------------------------------
# Orchestratore principale
# ---------------------------------------------------------------------------

def rebuild_simulation(current_bodies, is_causal_info_on, new_dt=None, new_sim_rad=None, new_body_params=None):
    """
    Ricostruisce l'intera simulazione preservando la storia causale, le scie orbitali
    e la telemetria della sonda LIGO. Sequenza di 8 fasi:

      1. Snapshot   — salva lo stato corrente prima di deallocare
      2. Params     — aggiorna DT, raggio e costanti derivate
      3. Planning   — sceglie la modalità buffer (SINGLE/DOUBLE/TRIPLE)
      4. Alloc      — azzera e ri-alloca tutti gli array NumPy
      5. Restore    — rinietta corpi, storia e sonde negli array freschi
      6. LOD        — ricalcola indici di rendering e cache LOD
      7. Radar      — auto-taratura 2.5PN del moltiplicatore M_CHIRP
      8. Attractors — calcola TOP_ATTRACTOR per ogni corpo
      9. Priming    — accelerazioni iniziali per il warm-start del Verlet
    """
    print("\n[SIM MANAGER] --- REBUILD START (PRESERVING DEATH, BIRTH, TRAILS & ART) ---")
    _print_cpu_info_once()

    old_dt = data.DT

    snapshots, backups = _take_snapshot(current_bodies, old_dt) # 1
    active_dt, active_rad = _apply_new_params(new_dt, new_sim_rad) # 2
    total_mb = _plan_buffer_architecture(is_causal_info_on, len(snapshots), new_body_params) # 3
    _wipe_and_alloc(total_mb) # 4
    new_bodies_list = _restore_bodies(snapshots, backups, active_dt, old_dt, new_body_params) # 5
    _update_lod_and_indices(len(new_bodies_list)) # 6
    _run_relativistic_radar() # 7
    _compute_top_attractors(len(new_bodies_list)) # 8
    _prime_initial_accelerations() # 9

    print(f"[SIM MANAGER] Reconstruction completed. DT={active_dt} | Rad={active_rad:.1e} | TopMass={data.TOP_MASS:.2e}")
    return new_bodies_list, active_dt


if __name__ == "__main__":
    # ---------------------------------------------------------------------------
    # TEST: verifica il dialogo OOM senza consumare RAM reale.
    # Simula il caso in cui un utente con RAM insufficiente avvii un preset pesante.
    # Lancia con: python -m core.simulation_manager
    # ---------------------------------------------------------------------------
    print("[TEST OOM] Artificially triggering _show_oom_error...")
    _show_oom_error(total_mb=65536.0, n_bodies=1)  # 64 GB — chiunque va OOM qui

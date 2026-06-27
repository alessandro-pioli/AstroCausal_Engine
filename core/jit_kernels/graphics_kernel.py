import numpy as np
import math
from numba import njit, prange
from core.jit_kernels import kernel_helper_inline

# Costanti Colore (Invariate)
C_BLUE_BASE = np.array([0, 0, 40], dtype=np.float64)
C_BLUE_TOP  = np.array([80, 0, 100], dtype=np.float64)
C_MID_LOW   = np.array([80, 0, 100], dtype=np.float64)
C_MID_HIGH  = np.array([255, 100, 0], dtype=np.float64)
C_CORE_LOW  = np.array([255, 100, 0], dtype=np.float64)
C_CORE_HIGH = np.array([255, 255, 255], dtype=np.float64)

@njit(parallel=True, fastmath=True, cache=True)
def render_frame_kernel(
    output_img, width, height, cam_scale, cam_off_x, cam_off_y,
    p_pos, p_vel, p_mass, p_rad, 
    p_idx, num_active,
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    c_sq, void_val, inv_c, inv_dt,
    min_exp, max_exp, inv_cutoff_sq
):
    range_exp = max_exp - min_exp
    if range_exp < 0.1: range_exp = 0.1
    inv_range_exp = 1.0 / range_exp
    
    cx = width >> 1
    cy = height >> 1
    c_threshold_sq = 0.25 * c_sq 
  
    for x in prange(width):
        w_x = (x - cx) * cam_scale + cam_off_x
        for y in range(height):
            w_y = (y - cy) * cam_scale + cam_off_y
            total_phi = 0.0
            
            for k in range(num_active):
                i = p_idx[k]
                px = p_pos[k, 0]
                py = p_pos[k, 1]
                vx = p_vel[k, 0]
                vy = p_vel[k, 1]
                mass = p_mass[k]
                
                if px <= void_val:
                    last_ptr = (heads_L0[i] - 1) & mask_L0
                    hx = h_L0[i, last_ptr, 0]
                    if hx <= void_val: continue
                    px = hx
                    py = h_L0[i, last_ptr, 1]
                    vx = h_L0[i, last_ptr, 2]
                    vy = h_L0[i, last_ptr, 3]
                    mass = h_L0[i, last_ptr, 4]
                        
                phi_contrib = kernel_helper_inline.calculate_potential_contribution(
                            w_x, w_y,
                            px, py, 
                            vx, vy, 
                            mass, p_rad[k],
                            h_L0, heads_L0, mask_L0, len_L0,
                            h_L1, heads_L1, mask_L1, len_L1,
                            h_L2, heads_L2, mask_L2, len_L2,
                            i,
                            c_sq, c_threshold_sq, inv_c, inv_dt, void_val
                        )
                total_phi += phi_contrib

            # Colorazione (Invariata)
            val = np.log10(total_phi + 1.0)
            norm = (val - min_exp) * inv_range_exp
            if norm < 0.0: norm = 0.0
            if norm > 1.0: norm = 1.0
            
            r, g, b = 0.0, 0.0, 0.0
            if norm < 0.4:
                n = norm * 2.5
                r = C_BLUE_BASE[0] + (C_BLUE_TOP[0] - C_BLUE_BASE[0]) * n
                g = C_BLUE_BASE[1] + (C_BLUE_TOP[1] - C_BLUE_BASE[1]) * n
                b = C_BLUE_BASE[2] + (C_BLUE_TOP[2] - C_BLUE_BASE[2]) * n
            elif norm < 0.7:
                n = (norm - 0.4) * 3.333
                r = C_MID_LOW[0] + (C_MID_HIGH[0] - C_MID_LOW[0]) * n
                g = C_MID_LOW[1] + (C_MID_HIGH[1] - C_MID_LOW[1]) * n
                b = C_MID_LOW[2] + (C_MID_HIGH[2] - C_MID_LOW[2]) * n
            else:
                n = (norm - 0.7) * 3.333
                r = C_CORE_LOW[0] + (C_CORE_HIGH[0] - C_CORE_LOW[0]) * n
                g = C_CORE_LOW[1] + (C_CORE_HIGH[1] - C_CORE_LOW[1]) * n
                b = C_CORE_LOW[2] + (C_CORE_HIGH[2] - C_CORE_LOW[2]) * n
            
            output_img[x, y, 0] = np.uint8(r)
            output_img[x, y, 1] = np.uint8(g)
            output_img[x, y, 2] = np.uint8(b)

@njit(fastmath=True, cache=True)
def probe_field_value(
    probe_x, probe_y,
    p_pos, p_vel, p_mass, p_rad, 
    p_idx,
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    c_sq, void_val, inv_c, inv_dt, g
):
    total_phi = 0.0
    c_threshold_sq = 0.25 * c_sq 
    num_active = len(p_idx)

    for k in range(num_active):
        i = p_idx[k]
        px = p_pos[k, 0]
        py = p_pos[k, 1]
        vx = p_vel[k, 0]
        vy = p_vel[k, 1]
        mass = p_mass[k]
        
        if px <= void_val:
            last_ptr = (heads_L0[i] - 1) & mask_L0
            hx = h_L0[i, last_ptr, 0]
            if hx <= void_val: continue
            px = hx
            py = h_L0[i, last_ptr, 1]
            vx = h_L0[i, last_ptr, 2]
            vy = h_L0[i, last_ptr, 3]
            mass = h_L0[i, last_ptr, 4]
        phi_contrib = kernel_helper_inline.calculate_potential_contribution(
            probe_x, probe_y,
            px, py, 
            vx, vy,
            mass, p_rad[k],
            h_L0, heads_L0, mask_L0, len_L0,
            h_L1, heads_L1, mask_L1, len_L1,
            h_L2, heads_L2, mask_L2, len_L2,
            i, c_sq, c_threshold_sq, inv_c, inv_dt, void_val
        )
        total_phi += phi_contrib

    return total_phi * g * -1.0 

@njit(fastmath=True, cache=True)
def probe_dphi_at_point(
    probe_x, probe_y,
    p_pos, p_vel, p_mass, p_rad, 
    p_idx,
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    c_sq, void_val, inv_c, inv_dt, g
):
    dphi_total = 0.0
    num_active = len(p_idx)

    for k in range(num_active):
        i = p_idx[k]
        px = p_pos[k, 0]
        py = p_pos[k, 1]
        mass = p_mass[k]
        
        if px <= void_val:
            last_ptr = (heads_L0[i] - 1) & mask_L0
            hx = h_L0[i, last_ptr, 0]
            if hx <= void_val: continue
            px = hx
            py = h_L0[i, last_ptr, 1]
            mass = h_L0[i, last_ptr, 4]
            
        dphi_contrib = kernel_helper_inline.calculate_dphi_contribution(
            probe_x, probe_y,
            px, py, 
            mass, p_rad[k],
            h_L0, heads_L0, mask_L0, len_L0,
            h_L1, heads_L1, mask_L1, len_L1,
            h_L2, heads_L2, mask_L2, len_L2,
            i,
            inv_c, inv_dt, void_val
        )
        dphi_total += dphi_contrib
        
    return dphi_total * g

@njit(parallel=True, fastmath=True, cache=True)
def render_dphi_dt_kernel(
    output_img, width, height, cam_scale, cam_off_x, cam_off_y,
    p_pos, p_vel, p_mass, p_rad, 
    p_idx, num_active,
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    c_sq, void_val, inv_c, inv_dt,
    sensitivity 
):
    cx = width >> 1
    cy = height >> 1

    for x in prange(width):
        w_x = (x - cx) * cam_scale + cam_off_x
        for y in range(height):
            w_y = (y - cy) * cam_scale + cam_off_y
            
            dphi_total = 0.0
            
            for k in range(num_active):
                i = p_idx[k]
                px = p_pos[k, 0]
                py = p_pos[k, 1]
                mass = p_mass[k]
                
                if px <= void_val:
                    last_ptr = (heads_L0[i] - 1) & mask_L0
                    hx = h_L0[i, last_ptr, 0]
                    if hx <= void_val: continue
                    px = hx
                    py = h_L0[i, last_ptr, 1]
                    mass = h_L0[i, last_ptr, 4]
                
                # --- CHIAMATA INLINE ---
                dphi_contrib = kernel_helper_inline.calculate_dphi_contribution(
                    w_x, w_y,
                    px, py, 
                    mass, p_rad[k],
                    h_L0, heads_L0, mask_L0, len_L0,
                    h_L1, heads_L1, mask_L1, len_L1,
                    h_L2, heads_L2, mask_L2, len_L2,
                    i,
                    inv_c, inv_dt, void_val
                )
                
                dphi_total += dphi_contrib

            # Colorazione
            val = dphi_total * sensitivity
            norm = math.tanh(val)
            
            r, g, b = 0, 0, 0
            if norm > 0: 
                g = int(norm * 180); b = int(norm * 255)
            else: 
                v = -norm
                r = int(v * 255); g = int(v * 60)
            
            output_img[x, y, 0] = np.uint8(r)
            output_img[x, y, 1] = np.uint8(g)
            output_img[x, y, 2] = np.uint8(b)

            
@njit(parallel=True, fastmath=True)
def render_roche_du_kernel(
    output_img, width, height, cam_scale, cam_off_x, cam_off_y,
    pos, vel, mass, num_active,
    target_idx, attr_idx,
    G, max_F, inv_f_norm, contrast
):
    cx = width >> 1
    cy = height >> 1
    
    # 1. Coordinate Baricentrate e Frequenza Naturale Dinamica (Omega Quadrato)
    if target_idx < 0 or attr_idx < 0 or target_idx >= num_active or attr_idx >= num_active:
        C_x, C_y = 0.0, 0.0
        omega_sq = 0.0
    else:
        m1 = mass[attr_idx]
        m2 = mass[target_idx]
        p1_x, p1_y = pos[attr_idx, 0], pos[attr_idx, 1]
        p2_x, p2_y = pos[target_idx, 0], pos[target_idx, 1]
        
        M_tot = m1 + m2
        if M_tot > 0:
            inv_M_tot = 1.0 / M_tot
            C_x = (m1 * p1_x + m2 * p2_x) * inv_M_tot
            C_y = (m1 * p1_y + m2 * p2_y) * inv_M_tot
            
            dx = p2_x - p1_x
            dy = p2_y - p1_y
            dist_sq = dx*dx + dy*dy
            
            if dist_sq > 0.001:
                # Calcolo Cinematica
                vx_rel = vel[target_idx, 0] - vel[attr_idx, 0]
                vy_rel = vel[target_idx, 1] - vel[attr_idx, 1]
                
                # h = r x v (Momento angolare specifico)
                h = (dx * vy_rel) - (dy * vx_rel)
                
                # omega = h / r^2 -> omega_sq = h^2 / r^4
                omega_sq = (h * h) / (dist_sq * dist_sq)
            else:
                omega_sq = 0.0
        else:
            C_x, C_y = 0.0, 0.0
            omega_sq = 0.0
            
    # CALCOLO VETTORE DI TRASCINAMENTO
    A_x = 0.0
    A_y = 0.0
    
    if num_active > 0 and (target_idx >= 0 and attr_idx >= 0):
        for i in range(num_active):
            # Ignoriamo il target e l'attrattore locale
            if i == target_idx or i == attr_idx:
                continue
                
            dx = C_x - pos[i, 0]
            dy = C_y - pos[i, 1]
            r_sq = dx*dx + dy*dy + 0.001
            r_3 = r_sq * math.sqrt(r_sq)
            inv_r_3 = 1/r_3
            gm = G * mass[i]
            
            # Accelerazione subita da C verso i (Gravità attrattiva)
            A_x -= gm * dx * inv_r_3
            A_y -= gm * dy * inv_r_3

    for x in prange(width):
        w_x = (x - cx) * cam_scale + cam_off_x
        for y in range(height):
            w_y = (y - cy) * cam_scale + cam_off_y
            
            # --- SOTTRAZIONE DEL TRASCINAMENTO (Frame Inerziale Locale) ---
            # Invece di partire da 0.0, partiamo col vettore opposto.
            Phi_x = -A_x
            Phi_y = -A_y
            Phi_xx = 0.0
            Phi_yy = 0.0
            Phi_xy = 0.0
            
            # --- Perturbazione N-Body Totale ---
            for k in range(num_active):
                m_k = mass[k]
                dx = w_x - pos[k, 0]
                dy = w_y - pos[k, 1]
                r_sq = dx*dx + dy*dy + 0.001 # Softening anti-zerodivision
                r = math.sqrt(r_sq)
                r_3 = r_sq * r
                
                gm = G * m_k
                
                term_inv_r3 = 1.0 / r_3
                term_inv_r5 = term_inv_r3 / r_sq
                
                # Gradiente della Gravità
                Phi_x += gm * dx * term_inv_r3
                Phi_y += gm * dy * term_inv_r3
                
                # Hessiana della Gravità
                Phi_xx += gm * (term_inv_r3 - 3.0 * dx * dx * term_inv_r5)
                Phi_yy += gm * (term_inv_r3 - 3.0 * dy * dy * term_inv_r5)
                Phi_xy += gm * (-3.0 * dx * dy * term_inv_r5)

            # --- Termini Centrifughi (Nel sistema co-rotante) ---
            dx_c = w_x - C_x
            dy_c = w_y - C_y
            
            Phi_x -= omega_sq * dx_c
            Phi_y -= omega_sq * dy_c
            
            Phi_xx -= omega_sq
            Phi_yy -= omega_sq
            
            # 2. Magnitudo Forza (Luminosità)
            F_net = math.sqrt(Phi_x*Phi_x + Phi_y*Phi_y)
            F_net_norm = F_net * inv_f_norm
            
            # Visualizzazione Logaritmica (Svela i punti sub-pixel)
            log_F = math.log10(F_net_norm + 1e-20) 
            
            # Trasliamo la curva basandoci su max_F (sensibilità logaritmica)
            slope = contrast * 0.01
            norm_val = (log_F + math.log10(max_F)) * slope + 0.5
            
            bri = norm_val
            if bri > 1.0: bri = 1.0
            elif bri < 0.0: bri = 0.0
            
            # 3. Determinante Hessiana: segno = topologia, |D|/omega^4 = ripidita'
            D = (Phi_xx * Phi_yy) - (Phi_xy * Phi_xy)

            # Scala naturale del frame corotante: omega^4 adimensionalizza |D|
            # (l'Hessiana e' 1/tempo^2 -> D e' 1/tempo^4, come omega^4).
            D_scale = omega_sq * omega_sq
            if D_scale < 1e-30:
                D_scale = 1e-30
            log_D = math.log10(abs(D) / D_scale + 1e-20)
            # Clamp [-3, +3]: evita che i pochi pixel vicinissimi ai corpi
            # saturino tutta la dinamica della rampa. 0 = dolce (D~0), 1 = ripida.
            if log_D < -3.0: log_D = -3.0
            elif log_D > 3.0: log_D = 3.0
            t = (log_D + 3.0) / 6.0

            if D < 0.0:
                # Selle L1/L2/L3: cremisi -> rosso fuoco -> giallo neon (saturo)
                if t < 0.5:
                    u = t * 2.0
                    r_c = 120.0 + u * 135.0
                    g_c = u * 50.0
                    b_c = 30.0 - u * 30.0
                else:
                    u = (t - 0.5) * 2.0
                    r_c = 255.0
                    g_c = 50.0 + u * 180.0
                    b_c = 0.0
            else:
                # Cupole L4/L5: indaco -> blu elettrico -> ciano (saturo)
                if t < 0.5:
                    u = t * 2.0
                    r_c = 40.0 - u * 40.0
                    g_c = u * 90.0
                    b_c = 90.0 + u * 165.0
                else:
                    u = (t - 0.5) * 2.0
                    r_c = 0.0
                    g_c = 90.0 + u * 140.0
                    b_c = 255.0

            # 4. Luminosita' = pura traduzione fisica della forza (Opzione 1).
            # Nessuna ombreggiatura artificiale: ogni livello di luminanza
            # corrisponde a una grandezza reale. Il nucleo nero NON e' un'ombra
            # su un cono immaginario, e' letteralmente "F_net ~ 0 qui".
            output_img[x, y, 0] = np.uint8(r_c * bri)
            output_img[x, y, 1] = np.uint8(g_c * bri)
            output_img[x, y, 2] = np.uint8(b_c * bri)


@njit(fastmath=True, cache=True)
def transform_trail_kernel(buffer_array, head_idx, is_full, cam_off_x, cam_off_y, cam_scale, screen_w, screen_h, void_val):
    """
    KERNEL VISIVO ADATTIVO (2px Rule + Culling)
    1. Visual Optimization: Se il punto dista < 2px dal precedente, lo salta.
    2. Smart Culling: Se il punto è TROPPO fuori schermo (margine largo), lo salta (ma con cautela per non spezzare linee).
    3. Anchor Fix: Assicura che la linea arrivi sempre al corpo.
    """
    capacity = len(buffer_array)
    raw_count = capacity if is_full else head_idx
    
    if raw_count < 2: return np.empty((0, 2), dtype=np.int32)
    
    # Allocazione Pessimistica (Max possibile), poi facciamo slice alla fine
    # Nella pratica ne useremo molti meno grazie al filtro 2px
    res = np.empty((raw_count + 1, 2), dtype=np.int32)
    
    cx = screen_w >> 1 
    cy = screen_h >> 1
    inv_scale = 1.0 / cam_scale
    
    # Parametri Ottimizzazione
    MIN_DIST_SQ = 4  # (2 pixel)^2. Se spostamento < 2px, ignora.
    
    # Culling Margins (Molto larghi per permettere linee che attraversano lo schermo)
    # Se tagliamo troppo stretto, le linee che entrano ed escono spariscono.
    MARGIN = 2000 
    min_x, max_x = -MARGIN, screen_w + MARGIN
    min_y, max_y = -MARGIN, screen_h + MARGIN
    
    out_idx = 0
    start_idx = head_idx if is_full else 0
    
    # Cache dell'ultimo punto SCRITTO (Screen Space)
    # Inizializziamo a valori impossibili per forzare la scrittura del primo punto
    last_sx = void_val
    last_sy = void_val
    
    # --- 1. LOOP DI FILTRAGGIO VISIVO ---
    for k in range(raw_count):
        # Indice Circolare
        ptr = start_idx + k
        if ptr >= capacity: ptr -= capacity 
        
        wx = buffer_array[ptr, 0]
        if wx <= void_val: continue
        
        # Trasformazione World -> Screen
        # Usiamo float temporanei per evitare overflow int32 immediato su zoom estremi
        raw_sx = (wx - cam_off_x) * inv_scale + cx
        raw_sy = (buffer_array[ptr, 1] - cam_off_y) * inv_scale + cy
        
        # Culling "Safe" (Evita Overflow Int32 di Pygame)
        # Se siamo nell'iper-spazio (coordinate > 2 miliardi), Pygame crasha.
        # Clamppiamo o saltiamo. Saltare è meglio qui.
        if not (min_x < raw_sx < max_x and min_y < raw_sy < max_y):
            # SE siamo fuori, DOBBIAMO comunque disegnare se il punto PRECEDENTE era dentro
            # per chiudere la linea in uscita. 
            # Per semplicità in Numba: se siamo MOLTO fuori, saltiamo. 
            # Il MARGIN gestisce l'entrata/uscita.
            continue

        sx = int(raw_sx)
        sy = int(raw_sy)
        
        # REGOLA ETERNA: 2px Check
        dx = sx - last_sx
        dy = sy - last_sy
        dist_sq = dx*dx + dy*dy
        
        # Scriviamo solo se ci siamo mossi abbastanza O se è il primo punto
        if dist_sq >= MIN_DIST_SQ:
            res[out_idx, 0] = sx
            res[out_idx, 1] = sy
            out_idx += 1
            last_sx = sx
            last_sy = sy
            
    # --- 2. ANCORA FINALE (The Connector) ---
    # L'ultimo punto fisico (quello più recente) DEVE esserci sempre,
    # altrimenti la scia si stacca dal pianeta se l'ultimo movimento è < 2px.
    last_ptr = head_idx - 1
    if last_ptr < 0: last_ptr = capacity - 1
    
    wx_last = buffer_array[last_ptr, 0]
    if wx_last > void_val:
        raw_sx = (wx_last - cam_off_x) * inv_scale + cx
        raw_sy = (buffer_array[last_ptr, 1] - cam_off_y) * inv_scale + cy
        
        # Check Culling anche qui
        if min_x < raw_sx < max_x and min_y < raw_sy < max_y:
            sx_last = int(raw_sx)
            sy_last = int(raw_sy)
            
            # Aggiungi solo se diverso dall'ultimo scritto
            if out_idx == 0 or (res[out_idx-1, 0] != sx_last or res[out_idx-1, 1] != sy_last):
                res[out_idx, 0] = sx_last
                res[out_idx, 1] = sy_last
                out_idx += 1

    return res[:out_idx]

@njit(parallel=True, fastmath=True)
def render_roche_lagrange_filter_kernel(
    output_img, width, height, cam_scale, cam_off_x, cam_off_y,
    pos, vel, mass, num_active,
    target_idx, attr_idx,
    G, max_F, f_norm
):
    cx = width >> 1
    cy = height >> 1
    
    # 1. Coordinate Baricentrate e Frequenza Naturale Dinamica (Omega Quadrato)
    if target_idx < 0 or attr_idx < 0 or target_idx >= num_active or attr_idx >= num_active:
        C_x, C_y = 0.0, 0.0
        omega_sq = 0.0
    else:
        m1 = mass[attr_idx]
        m2 = mass[target_idx]
        p1_x, p1_y = pos[attr_idx, 0], pos[attr_idx, 1]
        p2_x, p2_y = pos[target_idx, 0], pos[target_idx, 1]
        
        M_tot = m1 + m2
        if M_tot > 0:
            C_x = (m1 * p1_x + m2 * p2_x) / M_tot
            C_y = (m1 * p1_y + m2 * p2_y) / M_tot
            
            dx = p2_x - p1_x
            dy = p2_y - p1_y
            dist_sq = dx*dx + dy*dy
            
            if dist_sq > 0.001:
                # Calcolo Cinematica Reale (Cross Product per l'Angular Momentum)
                vx_rel = vel[target_idx, 0] - vel[attr_idx, 0]
                vy_rel = vel[target_idx, 1] - vel[attr_idx, 1]
                
                # h = r x v (Momento angolare specifico)
                h = (dx * vy_rel) - (dy * vx_rel)
                
                # omega = h / r^2 -> omega_sq = h^2 / r^4
                omega_sq = (h * h) / (dist_sq * dist_sq)
            else:
                omega_sq = 0.0
        else:
            C_x, C_y = 0.0, 0.0
            omega_sq = 0.0
            
    # --- CALCOLO VETTORE DI TRASCINAMENTO (Freefall Reference Frame) ---
    A_x = 0.0
    A_y = 0.0
    
    if num_active > 0 and (target_idx >= 0 and attr_idx >= 0):
        for i in range(num_active):
            # Ignoriamo il target e l'attrattore locale
            if i == target_idx or i == attr_idx:
                continue
                
            dx = C_x - pos[i, 0]
            dy = C_y - pos[i, 1]
            r_sq = dx*dx + dy*dy + 0.001
            r_3 = r_sq * math.sqrt(r_sq)
            
            gm = G * mass[i]
            
            # Accelerazione subita da C verso i (Gravità attrattiva)
            A_x -= gm * dx / r_3
            A_y -= gm * dy / r_3

    for x in prange(width):
        w_x = (x - cx) * cam_scale + cam_off_x
        for y in range(height):
            w_y = (y - cy) * cam_scale + cam_off_y
            
            # --- SOTTRAZIONE DEL TRASCINAMENTO (Frame Inerziale Locale) ---
            Phi_x = 0.0 # -A_x Non serve più perché in Lagrange Hunter consideriamo solo 2 corpi
            Phi_y = 0.0 # -A_y
            Phi_xx = 0.0
            Phi_yy = 0.0
            Phi_xy = 0.0
            
            # --- Perturbazione 2-Body Isolato ---
            for k_idx in range(2):
                k = target_idx if k_idx == 0 else attr_idx
                if k < 0 or k >= num_active: continue
                m_k = mass[k]
                dx = w_x - pos[k, 0]
                dy = w_y - pos[k, 1]
                r_sq = dx*dx + dy*dy + 0.001 # Softening anti-zerodivision
                r = math.sqrt(r_sq)
                r_3 = r_sq * r
                
                gm = G * m_k
                
                term_inv_r3 = 1.0 / r_3
                term_inv_r5 = term_inv_r3 / r_sq
                
                # Gradiente della Gravità
                Phi_x += gm * dx * term_inv_r3
                Phi_y += gm * dy * term_inv_r3
                
                # Hessiana della Gravità
                Phi_xx += gm * (term_inv_r3 - 3.0 * dx * dx * term_inv_r5)
                Phi_yy += gm * (term_inv_r3 - 3.0 * dy * dy * term_inv_r5)
                Phi_xy += gm * (-3.0 * dx * dy * term_inv_r5)

            # --- Termini Centrifughi (Nel sistema co-rotante) ---
            dx_c = w_x - C_x
            dy_c = w_y - C_y
            
            Phi_x -= omega_sq * dx_c
            Phi_y -= omega_sq * dy_c
            
            Phi_xx -= omega_sq
            Phi_yy -= omega_sq
            
            # Determinante e Traccia Hessiana
            D = (Phi_xx * Phi_yy) - (Phi_xy * Phi_xy)
            trace = Phi_xx + Phi_yy
            
            # Stimatore di distanza Newton-Raphson: r_est = |H^-1 * grad Phi|
            inv_D = 1.0 / (abs(D) + 1e-30)
            dx_est = (Phi_yy * Phi_x - Phi_xy * Phi_y) * inv_D
            dy_est = (-Phi_xy * Phi_x + Phi_xx * Phi_y) * inv_D
            r_est = math.sqrt(dx_est*dx_est + dy_est*dy_est)
            
            # Distanza in pixel dello schermo
            pixel_dist = r_est / cam_scale
            
            # F_net normalizzata sulla scala L4/L5: fader=0 -> max_F=1 -> L4/L5 al default
            F_net = math.sqrt(Phi_x*Phi_x + Phi_y*Phi_y)
            F_net_norm = F_net / f_norm

            # dot_radius calibrato sulla scala normalizzata (exp_val~0 al default)
            # se exp_val è -8 -> r=2.6, se è 0 -> r=5.0, se è +8 -> r=7.4
            exp_val = math.log10(max_F + 1e-30)
            dot_radius = max(1.5, 5.0 + exp_val * 0.3)

            # Soglia normalizzata: F_net_norm < max_F * margine
            # max_F~1 al default, margine 1e6 per non tagliare mai L4/L5 al centro
            F_thresh = max_F * 1e6

            # Il filtro principale (su forza normalizzata):
            if pixel_dist < dot_radius and F_net_norm < F_thresh:
                # Applichiamo una curva a campana per disegnare il punto luminoso netto
                intensity = math.exp(-2.0 * (pixel_dist / dot_radius)**2)
                
                # Selettore Regola Matriciale: escludiamo i minimi locali del potenziale (D > 0, Tr(H) > 0)
                is_lagrange = True
                if D > 0 and trace > 0:
                    is_lagrange = False
                    
                if is_lagrange:
                    val = int(255 * intensity)
                    if D > 0:
                        # Autovalori concordi (L4, L5) -> Positivi -> Blu intenso brillante
                        output_img[x, y, 0] = np.uint8(int(val * 0.1))
                        output_img[x, y, 1] = np.uint8(int(val * 0.4))
                        output_img[x, y, 2] = np.uint8(val)
                    else:
                        # Autovalori discordi (L1, L2, L3) -> Negativi -> Rosso brillante
                        output_img[x, y, 0] = np.uint8(val)
                        output_img[x, y, 1] = np.uint8(int(val * 0.1))
                        output_img[x, y, 2] = np.uint8(int(val * 0.1))
                else:
                    output_img[x, y, 0] = np.uint8(0)
                    output_img[x, y, 1] = np.uint8(0)
                    output_img[x, y, 2] = np.uint8(0)
            else:
                output_img[x, y, 0] = np.uint8(0)
                output_img[x, y, 1] = np.uint8(0)
                output_img[x, y, 2] = np.uint8(0)

@njit(parallel=True, fastmath=True)
def render_tidal_stress_kernel(
    output_img, width, height, cam_scale, cam_off_x, cam_off_y,
    pos, mass, num_active, G, log_offset
):
    cx = width >> 1
    cy = height >> 1
    
    for x in prange(width):
        w_x = (x - cx) * cam_scale + cam_off_x
        for y in range(height):
            w_y = (y - cy) * cam_scale + cam_off_y
            
            Phi_xx = 0.0
            Phi_yy = 0.0
            Phi_xy = 0.0
            
            for i in range(num_active):
                m_i = mass[i]
                dx = w_x - pos[i, 0]
                dy = w_y - pos[i, 1]
                r_sq = dx*dx + dy*dy + 0.001
                r = math.sqrt(r_sq)
                r_3 = r_sq * r
                
                gm = G * m_i
                
                term_inv_r3 = 1.0 / r_3
                term_inv_r5 = term_inv_r3 / r_sq
                
                Phi_xx += gm * (term_inv_r3 - (3.0 * dx * dx) * term_inv_r5)
                Phi_yy += gm * (term_inv_r3 - (3.0 * dy * dy) * term_inv_r5)
                Phi_xy += gm * (-3.0 * dx * dy * term_inv_r5)
                
            # Il tensore ha unità 1/s^2 (G in km^3/(kg*s^2), m in kg, r in km).
            # Un valore in 1/s^2 equivale *esattamente* a un gradiente in (m/s^2) / metro.
            # Non serve moltiplicare per 1000! Il fattore x1000 spostava la scala di log(1000) = +3,
            # rendendo tutto innaturalmente "rosso" o "giallo".
            tidal_stress = math.sqrt((Phi_xx - Phi_yy)**2 + 4.0 * Phi_xy**2)
            log_stress = math.log10(tidal_stress + 1e-30) + log_offset
            
            r_col = 0
            g_col = 0
            b_col = 0
            
            if log_stress < -10.5:
                pass
            elif log_stress < -9.0:
                # Nero -> Blu Scuro / Viola profondo
                t = (log_stress - (-10.5)) / 1.5
                r_col = 0
                g_col = 0
                b_col = int(128 * t)
            elif log_stress < -7.5:
                # Blu scuro -> Ciano (Limite di Roche Comete)
                t = (log_stress - (-9.0)) / 1.5
                r_col = 0
                g_col = int(255 * t)
                b_col = int(128 + 127 * t)
            elif log_stress < -6.0:
                # Ciano -> Giallo (Limite di Disgregazione silicati/roccia)
                t = (log_stress - (-7.5)) / 1.5
                r_col = int(255 * t)
                g_col = 255
                b_col = int(255 * (1.0 - t))
            elif log_stress < 1.0:
                # Giallo -> Rosso (Spaghettificatione strutturale/biologica)
                t = (log_stress - (-6.0)) / 7.0
                r_col = 255
                g_col = int(255 * (1.0 - t))
                b_col = 0
            elif log_stress < 4.0:
                # Rosso -> Bianco (Disgregazione Estrema / Vicinanze Singolarità)
                t = min(1.0, (log_stress - 1.0) / 3.0)
                r_col = 255
                g_col = int(255 * t)
                b_col = int(255 * t)
            else:
                r_col = 255
                g_col = 255
                b_col = 255
                
            output_img[x, y, 0] = np.uint8(r_col)
            output_img[x, y, 1] = np.uint8(g_col)
            output_img[x, y, 2] = np.uint8(b_col)

@njit(fastmath=True, cache=True)
def probe_tidal_stress_at_point(
    w_x, w_y,
    pos, mass, active_indices, G, log_offset
):
    Phi_xx = 0.0
    Phi_yy = 0.0
    Phi_xy = 0.0
    
    num_active = len(active_indices)
    for k in range(num_active):
        i = active_indices[k]
        m_i = mass[i]
        dx = w_x - pos[i, 0]
        dy = w_y - pos[i, 1]
        r_sq = dx*dx + dy*dy + 0.001
        r = math.sqrt(r_sq)
        r_3 = r_sq * r
        
        gm = G * m_i
        
        term_inv_r3 = 1.0 / r_3
        term_inv_r5 = term_inv_r3 / r_sq
        
        Phi_xx += gm * (term_inv_r3 - (3.0 * dx * dx) * term_inv_r5)
        Phi_yy += gm * (term_inv_r3 - (3.0 * dy * dy) * term_inv_r5)
        Phi_xy += gm * (-3.0 * dx * dy * term_inv_r5)
        
    tidal_stress = math.sqrt((Phi_xx - Phi_yy)**2 + 4.0 * Phi_xy**2)
    log_stress = math.log10(tidal_stress + 1e-30) + log_offset
    return tidal_stress, log_stress


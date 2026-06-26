from numba import njit, prange
from core.jit_kernels import kernel_helper_inline
import math

# Costanti Fisiche / Logiche
FLAG_ALIVE = 1
FLAG_DYING = 2
# --- COSTANTI DI COMPRESSIONE (STRIDES) ---

# ==============================================================================
# MAIN KERNEL TRIPLE
# ==============================================================================
@njit(parallel=True, fastmath=True, cache=True)
def update_step_single_par(
    n_bodies, pos_arr, vel_arr, acc_arr, mass_arr, rad_arr, flags_arr,
    hist_L0, heads_L0, mask_L0, len_L0,
    
    # ARGOMENTI PER SCIE
    trail_buf, trail_heads, trail_last_pos,
    
    # --- INIEZIONE SONDA LIGO ---
    probe_buf, probe_head, probe_pos, probe_active, probe_mask, 
    
    dt, g_const, inv_c, inv_c_dt, c_sq, rs_factor, threshold_solver_sq, VOID_VAL,
    steps, active_indices, num_active, art_engine, m_chirp_mult, sim_time,
    collision_cooldown,
):
    
    for step_idx in range(steps):
        # --- FASE 1: UPDATE & WRITE ---
        for i in range(n_bodies):
            if (flags_arr[i] & FLAG_ALIVE) == 0: continue 

            # 1. AVANZAMENTO INDICI
            head_0 = (heads_L0[i] + 1) & mask_L0
            heads_L0[i] = head_0
            
            

                

            # 2. GESTIONE MORTE
            if (flags_arr[i] & FLAG_DYING) != 0:
                hist_L0[i, head_0, 0] = VOID_VAL
                continue 

            # 3. FISICA
            vel_arr[i, 0] += 0.5 * acc_arr[i, 0] * dt
            vel_arr[i, 1] += 0.5 * acc_arr[i, 1] * dt
            pos_arr[i, 0] += vel_arr[i, 0] * dt
            pos_arr[i, 1] += vel_arr[i, 1] * dt

            # 4. SCRITTURA
            hist_L0[i, head_0, 0] = pos_arr[i, 0]
            hist_L0[i, head_0, 1] = pos_arr[i, 1]
            hist_L0[i, head_0, 2] = vel_arr[i, 0]
            hist_L0[i, head_0, 3] = vel_arr[i, 1]
            hist_L0[i, head_0, 4] = mass_arr[i]

                

        # --- FASE 1.5: COLLISIONI (SEQUENZIALE) ---
        kernel_helper_inline.resolve_collisions_step(
            n_bodies, pos_arr, vel_arr, acc_arr, mass_arr, rad_arr, flags_arr, VOID_VAL, g_const, rs_factor, dt, collision_cooldown
        )

        # --- FASE 2 + 3: FORZE, INERZIA, MOTO, SCIE ---
        for idx_i in prange(num_active):
            i = active_indices[idx_i]
            if (flags_arr[i] & 2) != 0: continue
            
            total_ax = 0.0
            total_ay = 0.0
            my_x = pos_arr[i, 0]
            my_y = pos_arr[i, 1]
            my_vx = vel_arr[i, 0]
            my_vy = vel_arr[i, 1]
            my_rad = rad_arr[i]

            my_v_sq = my_vx*my_vx + my_vy*my_vy
            
            for idx_j in range(num_active):
                j = active_indices[idx_j]
                if i == j: continue
                if (flags_arr[j] & 2) != 0: continue
                
                src_x = pos_arr[j, 0]
                src_y = pos_arr[j, 1]
                src_rad = rad_arr[j]
                
                # --- 1. PRIMA STIMA (basata sul presente) ---
                dx_now = src_x - my_x
                dy_now = src_y - my_y
                dist_est = math.sqrt(dx_now*dx_now + dy_now*dy_now)
                ticks_est = int(dist_est * inv_c_dt)
                
                old_x, old_y = 0.0, 0.0
                found_est = False
                
                if ticks_est < len_L0:
                    idx = (heads_L0[j] - ticks_est) & mask_L0
                    old_x = hist_L0[j, idx, 0]
                    if old_x > VOID_VAL: 
                        old_y = hist_L0[j, idx, 1]
                        found_est = True

                            
                final_x, final_y, final_vx, final_vy, final_ax, final_ay, final_mass = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, mass_arr[j]
                found_final = False
                
                if found_est:
                    # --- 2. RICALCOLO CAUSALE VERO ---
                    dx_true = old_x - my_x
                    dy_true = old_y - my_y
                    dist_true = math.sqrt(dx_true*dx_true + dy_true*dy_true)
                    true_ticks = int(dist_true * inv_c_dt)
                
                    if true_ticks < len_L0:
                        idx = (heads_L0[j] - true_ticks) & mask_L0
                        final_x = hist_L0[j, idx, 0]
                        if final_x > VOID_VAL: 
                            final_y, final_vx, final_vy, final_mass = hist_L0[j, idx, 1], hist_L0[j, idx, 2], hist_L0[j, idx, 3], hist_L0[j, idx, 4]
                            
                            if true_ticks > 0:
                                idx_future = (heads_L0[j] - (true_ticks - 1)) & mask_L0
                                fut_x = hist_L0[j, idx_future, 0]
                                if fut_x > VOID_VAL:
                                    final_ax = (hist_L0[j, idx_future, 2] - final_vx) / dt
                                    final_ay = (hist_L0[j, idx_future, 3] - final_vy) / dt
                            elif true_ticks + 1 < len_L0:
                                idx_past = (heads_L0[j] - (true_ticks + 1)) & mask_L0
                                past_x = hist_L0[j, idx_past, 0]
                                if past_x > VOID_VAL:
                                    final_ax = (final_vx - hist_L0[j, idx_past, 2]) / dt
                                    final_ay = (final_vy - hist_L0[j, idx_past, 3]) / dt
                                    
                            found_final = True
                            
                if not found_final:
                    final_x, final_y = pos_arr[j, 0], pos_arr[j, 1]
                    final_vx, final_vy = vel_arr[j, 0], vel_arr[j, 1]
                    final_mass = mass_arr[j]
                    final_ax, final_ay = 0.0, 0.0

                ax, ay = kernel_helper_inline.compute_relativistic_force(my_x, my_y, my_vx, my_vy, my_rad, final_x, final_y, final_vx, final_vy, final_ax, final_ay, final_mass, rad_arr[j], pos_arr[j, 0], pos_arr[j, 1], mass_arr, inv_c, c_sq, g_const, rs_factor, m_chirp_mult, i, sim_time + step_idx * dt, dt)
                total_ax += ax
                total_ay += ay

            # --- Correttore Inerzia Relativistica ---

            if my_v_sq > threshold_solver_sq:
                if my_v_sq < (c_sq * 0.999):
                    inv_gamma = math.sqrt(1.0 - (my_v_sq * inv_c * inv_c))
                    total_ax *= inv_gamma
                    total_ay *= inv_gamma
                else:
                    total_ax, total_ay = 0.0, 0.0

            acc_arr[i, 0] = total_ax + art_engine[i, 0]
            acc_arr[i, 1] = total_ay + art_engine[i, 1]

            # --- Kick Finale e Scie ---
            vel_arr[i, 0] += 0.5 * acc_arr[i, 0] * dt
            vel_arr[i, 1] += 0.5 * acc_arr[i, 1] * dt

            kernel_helper_inline.update_trail_logic(
                i, pos_arr[i, 0], pos_arr[i, 1], 
                vel_arr[i, 0], vel_arr[i, 1], 
                rad_arr[i],
                trail_buf, trail_heads, trail_last_pos
            )
            
        # =========================================================================
        # FASE 3: SONDA LIGO (Versione Parallela Triple)
        # =========================================================================
        kernel_helper_inline.update_ligo_probe_step(
                    n_bodies, pos_arr, vel_arr, mass_arr, flags_arr,
                    probe_active, probe_pos, probe_buf, probe_head, probe_mask
                )
@njit(fastmath=True, cache=True)
def update_step_single_seq(
    n_bodies, pos_arr, vel_arr, acc_arr, mass_arr, rad_arr, flags_arr,
    hist_L0, heads_L0, mask_L0, len_L0,
    trail_buf, trail_heads, trail_last_pos,
    
    # --- INIEZIONE SONDA LIGO ---
    probe_buf, probe_head, probe_pos, probe_active, probe_mask, 
    
    dt, g_const, inv_c, inv_c_dt, c_sq, rs_factor, threshold_solver_sq, VOID_VAL,
    steps, active_indices, num_active, art_engine, m_chirp_mult, sim_time,
    collision_cooldown,
):
    # Logica Sequenziale (copia esatta della parallela senza prange)
    for step_idx in range(steps):
        # Fase 1: Posizione e Scrittura
        for i in range(n_bodies):
            if (flags_arr[i] & FLAG_ALIVE) == 0: continue 
            head_0 = (heads_L0[i] + 1) & mask_L0
            heads_L0[i] = head_0

            if (flags_arr[i] & FLAG_DYING) != 0:
                hist_L0[i, head_0, 0] = VOID_VAL
                continue 

            vel_arr[i, 0] += 0.5 * acc_arr[i, 0] * dt
            vel_arr[i, 1] += 0.5 * acc_arr[i, 1] * dt
            pos_arr[i, 0] += vel_arr[i, 0] * dt
            pos_arr[i, 1] += vel_arr[i, 1] * dt

            hist_L0[i, head_0, 0], hist_L0[i, head_0, 1] = pos_arr[i, 0], pos_arr[i, 1]
            hist_L0[i, head_0, 2], hist_L0[i, head_0, 3] = vel_arr[i, 0], vel_arr[i, 1]
            hist_L0[i, head_0, 4] = mass_arr[i]


        # Fase 1.5: Collisioni
        kernel_helper_inline.resolve_collisions_step(
            n_bodies, pos_arr, vel_arr, acc_arr, mass_arr, rad_arr, flags_arr, VOID_VAL, g_const, rs_factor, dt, collision_cooldown
        )

        # Fase 2 + 3: Forze, Inerzia e Moto
        for idx_i in range(num_active):
            i = active_indices[idx_i]
            if (flags_arr[i] & 2) != 0: continue
            
            total_ax, total_ay = 0.0, 0.0
            my_x, my_y = pos_arr[i, 0], pos_arr[i, 1]
            my_vx, my_vy = vel_arr[i, 0], vel_arr[i, 1]
            my_rad = rad_arr[i]

            my_v_sq = my_vx*my_vx + my_vy*my_vy
            
            for idx_j in range(num_active):
                j = active_indices[idx_j]
                if i == j: continue
                if (flags_arr[j] & 2) != 0: continue
                
                src_x, src_y = pos_arr[j, 0], pos_arr[j, 1]
                
                # --- 1. PRIMA STIMA ---
                dx_now = src_x - my_x
                dy_now = src_y - my_y
                dist_est = math.sqrt(dx_now*dx_now + dy_now*dy_now)
                ticks_est = int(dist_est * inv_c_dt)
                
                old_x, old_y = 0.0, 0.0
                found_est = False
                
                if ticks_est < len_L0:
                    idx = (heads_L0[j] - ticks_est) & mask_L0
                    old_x = hist_L0[j, idx, 0]
                    if old_x > VOID_VAL: 
                        old_y = hist_L0[j, idx, 1]
                        found_est = True

                            
                final_x, final_y, final_vx, final_vy, final_ax, final_ay, final_mass = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, mass_arr[j]
                found_final = False
                
                if found_est:
                    # --- 2. RICALCOLO CAUSALE VERO ---
                    dx_true = old_x - my_x
                    dy_true = old_y - my_y
                    dist_true = math.sqrt(dx_true*dx_true + dy_true*dy_true)
                    true_ticks = int(dist_true * inv_c_dt)
                
                    if true_ticks < len_L0:
                        idx = (heads_L0[j] - true_ticks) & mask_L0
                        final_x = hist_L0[j, idx, 0]
                        if final_x > VOID_VAL: 
                            final_y, final_vx, final_vy, final_mass = hist_L0[j, idx, 1], hist_L0[j, idx, 2], hist_L0[j, idx, 3], hist_L0[j, idx, 4]
                            
                            if true_ticks > 0:
                                idx_future = (heads_L0[j] - (true_ticks - 1)) & mask_L0
                                fut_x = hist_L0[j, idx_future, 0]
                                if fut_x > VOID_VAL:
                                    final_ax = (hist_L0[j, idx_future, 2] - final_vx) / dt
                                    final_ay = (hist_L0[j, idx_future, 3] - final_vy) / dt
                            elif true_ticks + 1 < len_L0:
                                idx_past = (heads_L0[j] - (true_ticks + 1)) & mask_L0
                                past_x = hist_L0[j, idx_past, 0]
                                if past_x > VOID_VAL:
                                    final_ax = (final_vx - hist_L0[j, idx_past, 2]) / dt
                                    final_ay = (final_vy - hist_L0[j, idx_past, 3]) / dt
                                    
                            found_final = True
                            
                if not found_final:
                    final_x, final_y = pos_arr[j, 0], pos_arr[j, 1]
                    final_vx, final_vy = vel_arr[j, 0], vel_arr[j, 1]
                    final_mass = mass_arr[j]
                    final_ax, final_ay = 0.0, 0.0

                ax, ay = kernel_helper_inline.compute_relativistic_force(my_x, my_y, my_vx, my_vy, my_rad, final_x, final_y, final_vx, final_vy, final_ax, final_ay, final_mass, rad_arr[j], pos_arr[j, 0], pos_arr[j, 1], mass_arr, inv_c, c_sq, g_const, rs_factor, m_chirp_mult, i, sim_time + step_idx * dt, dt)
                total_ax += ax
                total_ay += ay

            if my_v_sq > threshold_solver_sq:
                if my_v_sq < (c_sq * 0.999):
                    inv_gamma = math.sqrt(1.0 - (my_v_sq * inv_c * inv_c))
                    total_ax *= inv_gamma
                    total_ay *= inv_gamma
                else:
                    total_ax, total_ay = 0.0, 0.0

            acc_arr[i, 0] = total_ax + art_engine[i, 0]
            acc_arr[i, 1] = total_ay + art_engine[i, 1]
            vel_arr[i, 0] += 0.5 * acc_arr[i, 0] * dt
            vel_arr[i, 1] += 0.5 * acc_arr[i, 1] * dt

            kernel_helper_inline.update_trail_logic(
                i, pos_arr[i, 0], pos_arr[i, 1], 
                vel_arr[i, 0], vel_arr[i, 1], 
                rad_arr[i],
                trail_buf, trail_heads, trail_last_pos
            )
            
        # =========================================================================
        # FASE 3: SONDA LIGO (Versione Sequenziale Triple)
        # =========================================================================
        kernel_helper_inline.update_ligo_probe_step(
                    n_bodies, pos_arr, vel_arr, mass_arr, flags_arr,
                    probe_active, probe_pos, probe_buf, probe_head, probe_mask
                )

from core.jit_kernels import graphics_kernel 
import numpy as np
import pygame
import math
from core import data 
import config

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

class GravityRenderer:
    """Classe responsabile della generazione e del rendering delle heatmap del campo gravitazionale."""

    def __init__(self, width, height, resolution_div=1):
        """
        Inizializza il renderer allocando il buffer dei pixel.
        resolution_div: 
          1 = Full HD (Pesante ma dettagliato)
          2 = Mezza risoluzione (Ottimo compromesso)
          4 = Performance mode (div = 8 o superiore)
        """
        self.w = width
        self.h = height
        self.div = resolution_div
        
        # Buffer Grafico Persistente (Array Numpy WxH)
        self.render_w = width // resolution_div
        self.render_h = height // resolution_div
        self.pixel_buffer = np.zeros((self.render_w, self.render_h, 3), dtype=np.uint8)
        
        self.surface = None
        self.debug_mode_str = "JIT PACKED-DATA (CACHED)"
        
        # --- PACKED BUFFERS (Pre-allocated Matrix Pattern) ---
        # Evitano il "scattered reading" all'interno dei loop del kernel
        self.p_pos = np.zeros((data.MAX_BODIES, 2), dtype=np.float64)
        self.p_vel = np.zeros((data.MAX_BODIES, 2), dtype=np.float64)
        self.p_mass = np.zeros(data.MAX_BODIES, dtype=np.float64)
        self.p_rad = np.zeros(data.MAX_BODIES, dtype=np.float64)
        self.p_idx = np.zeros(data.MAX_BODIES, dtype=np.int32)

        # --- DUMMY STATIC (Allocazione singola all'avvio) ---
        self.dummy_hist = np.zeros((1, 1, 4), dtype=np.float64)
        self.dummy_hist.fill(data.VOID_VAL) 
        self.dummy_heads = np.zeros(1, dtype=np.int32)
        self.sensitivity = self.calculate_auto_sensitivity()

    def render(self, screen, camera, mode="PHI", **kwargs): 
            """Genera e disegna a schermo la heatmap selezionata (potenziale, onde, stress o Roche/Lagrange)."""
            # 1. SELEZIONE INDICI (Zero-Allocation Pointer)
            if mode in ("DPHI", "LAGRANGE_HUNTER", "ROCHE_DU", "TIDAL_STRESS", "GW_STRAIN"):
                active_indices = data.ACTIVE_INDICES_ALL
            else:
                active_indices = data.ACTIVE_INDICES_LOD
            
            # Se la lista è vuota, usciamo subito
            if len(active_indices) == 0: return

            # ---------------------------------------------------------
            # 2. CALCOLO PARAMETRI GLOBALI (Iride Dinamica)
            # ---------------------------------------------------------
            active_masses = data.MASS[active_indices]
            
            if len(active_masses) > 0:
                local_top_idx = np.argmax(active_masses)
                global_top_idx = active_indices[local_top_idx]
                
                top_mass = data.MASS[global_top_idx]
                top_rad = data.RAD[global_top_idx]
                
                # Cinematic Floor: Main Sequence Ratio (150.000x Rs)
                rs_val = (2.0 * data.G * top_mass) / data.C_SQ
                cinematic_rad_min = min(rs_val * 150000.0, 400000.0) 
                
                eff_rad = max(top_rad, cinematic_rad_min)
                max_phi = top_mass / eff_rad
            else:
                max_phi = 1.0
            
            global_max_exp = math.log10(max_phi + 1.0)
            global_min_exp = global_max_exp - 6.0 

            # Fix Cutoff
            safe_min_exp = global_min_exp - 1.0 
            phi_threshold = 10.0 ** safe_min_exp
            
            if phi_threshold > 1e-100: 
                inv_cutoff_sq = 1.0 / (phi_threshold * phi_threshold)
            else:
                inv_cutoff_sq = 0.0

            # ---------------------------------------------------------
            # 3. PACKING DEI DATI (Matrix Pattern Optimization)
            # ---------------------------------------------------------
            num_active = len(active_indices)
            self.p_pos[:num_active] = data.POS[active_indices]
            self.p_vel[:num_active] = data.VEL[active_indices]
            self.p_mass[:num_active] = data.MASS[active_indices]
            self.p_rad[:num_active] = data.RAD[active_indices]
            self.p_idx[:num_active] = active_indices

            # ---------------------------------------------------------
            # 4. SELEZIONE BUFFER (Zero Allocation Logic)
            # ---------------------------------------------------------
            if data.HISTORY_L1 is not None:
                h_L1, heads_L1, len_L1 = data.HISTORY_L1, data.HEADS_L1, data.LEN_L1
            else:
                h_L1, heads_L1, len_L1 = self.dummy_hist, self.dummy_heads, 0
            
            if data.HISTORY_L2 is not None:
                h_L2, heads_L2, len_L2 = data.HISTORY_L2, data.HEADS_L2, data.LEN_L2
            else:
                h_L2, heads_L2, len_L2 = self.dummy_hist, self.dummy_heads, 0
            
            # ---------------------------------------------------------
            # 5. CHIAMATA AL KERNEL (SWITCH MODE)
            # ---------------------------------------------------------
            if mode == "PHI":
                graphics_kernel.render_frame_kernel(
                    self.pixel_buffer,
                    self.render_w, self.render_h,
                    camera.scale * self.div, 
                    camera.offset_x, camera.offset_y,
                    self.p_pos, self.p_vel, self.p_mass, self.p_rad, 
                    self.p_idx, num_active,
                    data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
                    h_L1, heads_L1, data.MASK_L1, len_L1,
                    h_L2, heads_L2, data.MASK_L2, len_L2,  
                    data.C_SQ, data.VOID_VAL, data.INV_C, data.INV_DT,
                    global_min_exp, global_max_exp, inv_cutoff_sq
                )
            
            elif mode == "DPHI":
                final_sensitivity = self.sensitivity * (10.0 ** config.USER_SENSITIVITY_MAG)
                
                graphics_kernel.render_dphi_dt_kernel(
                    self.pixel_buffer,
                    self.render_w, self.render_h,
                    camera.scale * self.div, 
                    camera.offset_x, camera.offset_y,
                    self.p_pos, self.p_vel, self.p_mass, self.p_rad, 
                    self.p_idx, num_active,
                    data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
                    h_L1, heads_L1, data.MASK_L1, len_L1,
                    h_L2, heads_L2, data.MASK_L2, len_L2,
                    data.C_SQ, data.VOID_VAL, data.INV_C, data.INV_DT,
                    final_sensitivity 
                )
            elif mode in ("LAGRANGE_HUNTER", "ROCHE_DU"):
                # Cerca l'indice *locale* dei target passati nei kwargs
                t_local = -1
                a_local = -1
                
                lagrange_tgt = kwargs.get('lagrange_tgt', -1)
                lagrange_attr = kwargs.get('lagrange_attr', -1)
                
                for i in range(num_active):
                    if self.p_idx[i] == lagrange_tgt: t_local = i
                    if self.p_idx[i] == lagrange_attr: a_local = i
                
                # --- PRE-CALCOLO F_NORM (costo: ~6 op scalari, trascurabile) ---
                # Calibra la soglia/offset sulla forza caratteristica di L4/L5:
                # F_L4L5 ~ (27/4) * q*(1-q) * omega^2 * r
                # dove q = m2/(m1+m2), omega e r dalla cinematica reale.
                f_norm = 1.0  # fallback
                if t_local >= 0 and a_local >= 0:
                    m1_n = self.p_mass[a_local]
                    m2_n = self.p_mass[t_local]
                    M_tot_n = m1_n + m2_n
                    if M_tot_n > 0.0:
                        dx_n = self.p_pos[t_local, 0] - self.p_pos[a_local, 0]
                        dy_n = self.p_pos[t_local, 1] - self.p_pos[a_local, 1]
                        r_n = math.sqrt(dx_n*dx_n + dy_n*dy_n)
                        if r_n > 0.001:
                            vx_n = self.p_vel[t_local, 0] - self.p_vel[a_local, 0]
                            vy_n = self.p_vel[t_local, 1] - self.p_vel[a_local, 1]
                            h_n = dx_n * vy_n - dy_n * vx_n
                            omega_sq_n = (h_n * h_n) / (r_n ** 4)
                            # (27.0 / 4.0) è il coefficiente analitico per normalizzare il lobo di Roche critico nei sistemi circolari
                            f_norm_candidate = (27.0 / 4.0) * r_n * (1.0 - r_n) * omega_sq_n * r_n
                            if f_norm_candidate > 1e-300:
                                f_norm = f_norm_candidate

                exp_val = config.ROCHE_SENSITIVITY_MAG
                max_F = 10.0 ** exp_val

                if mode == "LAGRANGE_HUNTER":
                    graphics_kernel.render_roche_lagrange_filter_kernel(
                        self.pixel_buffer,
                        self.render_w, self.render_h,
                        camera.scale * self.div, 
                        camera.offset_x, camera.offset_y,
                        self.p_pos, self.p_vel, self.p_mass, num_active,
                        t_local, a_local,
                        data.G, max_F, f_norm
                    )
                else:
                    graphics_kernel.render_roche_du_kernel(
                        self.pixel_buffer,
                        self.render_w, self.render_h,
                        camera.scale * self.div, 
                        camera.offset_x, camera.offset_y,
                        self.p_pos, self.p_vel, self.p_mass, num_active,
                        t_local, a_local,
                        data.G, max_F, 1.0 / f_norm, config.ROCHE_CONTRAST
                    )
                
            elif mode == "GW_STRAIN":
                t_local = -1
                a_local = -1
                lagrange_tgt = kwargs.get('lagrange_tgt', -1)
                lagrange_attr = kwargs.get('lagrange_attr', -1)
                for i in range(num_active):
                    if self.p_idx[i] == lagrange_tgt: t_local = i
                    if self.p_idx[i] == lagrange_attr: a_local = i
                
                final_sensitivity = (10.0 ** config.ROCHE_SENSITIVITY_MAG) * 1e-36
                graphics_kernel.render_gw_strain_kernel(
                    self.pixel_buffer,
                    self.render_w, self.render_h,
                    camera.scale * self.div, 
                    camera.offset_x, camera.offset_y,
                    self.p_pos, self.p_vel, self.p_mass, self.p_rad, 
                    self.p_idx, num_active,
                    data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
                    h_L1, heads_L1, data.MASK_L1, len_L1,
                    h_L2, heads_L2, data.MASK_L2, len_L2,
                    data.C_SQ, data.VOID_VAL, data.INV_C, data.INV_DT,
                    t_local, a_local,
                    final_sensitivity
                )
                
            elif mode == "TIDAL_STRESS":
                log_offset = kwargs.get('log_offset', 0.0)
                graphics_kernel.render_tidal_stress_kernel(
                    self.pixel_buffer,
                    self.render_w, self.render_h,
                    camera.scale * self.div, 
                    camera.offset_x, camera.offset_y,
                    self.p_pos, self.p_mass, num_active,
                    data.G, log_offset
                )

            # ---------------------------------------------------------
            # 5. VISUALIZZAZIONE
            # ---------------------------------------------------------
            if self.div > 1:
                if HAS_CV2:
                    # CV2.resize si aspetta (target_width, target_height) che corrisponde a (colonne, righe).
                    # Il nostro pixel_buffer è (W, H, 3). CV2 interpreta W come righe e H come colonne.
                    # Per scalare fluidamente e riottenere un (Target_W, Target_H, 3), impostiamo cols=H, rows=W.
                    resized_buffer = cv2.resize(self.pixel_buffer, (self.h, self.w), interpolation=cv2.INTER_LINEAR)
                    
                    if self.surface is None or self.surface.get_size() != (self.w, self.h):
                        self.surface = pygame.surfarray.make_surface(resized_buffer)
                    else:
                        pygame.surfarray.blit_array(self.surface, resized_buffer)
                    
                    screen.blit(self.surface, (0, 0))
                else:
                    # Fallback Pygame smoothscale
                    if self.surface is None or self.surface.get_size() != (self.render_w, self.render_h):
                        self.surface = pygame.surfarray.make_surface(self.pixel_buffer)
                    else:
                        pygame.surfarray.blit_array(self.surface, self.pixel_buffer)
                        
                    scaled_surf = pygame.transform.smoothscale(self.surface, (self.w, self.h))
                    screen.blit(scaled_surf, (0, 0))
            else:
                # Full Resolution path: natively in (W, H) format!
                if self.surface is None or self.surface.get_size() != (self.render_w, self.render_h):
                    self.surface = pygame.surfarray.make_surface(self.pixel_buffer)
                else:
                    pygame.surfarray.blit_array(self.surface, self.pixel_buffer)
                    
                screen.blit(self.surface, (0, 0))

    def calculate_auto_sensitivity(self, target_vel_kms=10.0):
            if data.MAX_BODIES == 0: return 1.0e-13 
            
            top_idx = np.argmax(data.MASS[:data.MAX_BODIES])
            top_mass = data.MASS[top_idx]
            
            if top_mass <= 0: return 1.0e-13
        
            AU = data.AU_IN_KM 
            sim_radius = data.SIMULATION_RADIUS_KM
            # Target Proporzionale (calibrazione manuale)
            target_dist = sim_radius / 8.0
            r_test = max(1.0 * AU, min(target_dist, 64.0 * AU))
            # 3. Calcolo Segnale Inverso
            # (Se a questa distanza 'r_test' passa un corpo 'top_mass' a 10km/s, voglio vedere 1.0)
            raw_signal = (top_mass * target_vel_kms) / (r_test ** 2)
            
            if raw_signal < 1e-100: return 1.0e-13
            
            return 1.0 / raw_signal

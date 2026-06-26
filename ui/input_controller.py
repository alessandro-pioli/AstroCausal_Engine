import pygame
import math
import numpy as np
from core.jit_kernels import graphics_kernel
from core import data
from core.simulation_manager import rebuild_simulation
from ui.gravity_renderer import GravityRenderer
from ui.ui_state import ui_state 
from core.data import AU_IN_KM
import config
 
 
class InputController:
    """
    Gestisce l'input utente per il simulatore.
    Legge e scrive direttamente su ui_state — nessun argomento app necessario.
    """
    def __init__(self):
        self.last_click_time = 0
 
    def register(self, event_handler):
        event_handler.add_interceptor(self.intercept_tutorial)
        event_handler.add_interceptor(self.intercept_spawner)
        event_handler.add_interceptor(self.intercept_faders)
        event_handler.add_interceptor(self.intercept_console)
        event_handler.add_interceptor(self.intercept_camera)
 
        event_handler.register(pygame.QUIT, self.on_quit)
        event_handler.register(pygame.MOUSEMOTION, self.on_mouse_motion)
        event_handler.register(pygame.MOUSEBUTTONDOWN, self.on_mouse_button_down)
        event_handler.register(pygame.KEYDOWN, self.on_key_down)
 
    # ------------------------------------------------------------------
    # INTERCEPTORS
    # ------------------------------------------------------------------
 
    def intercept_tutorial(self, event):
        return ui_state.tutorial_manager.update_events(event)
 
    def intercept_spawner(self, event):
        spawn_evt = ui_state.spawner.handle_event(event)
        if isinstance(spawn_evt, bool) and spawn_evt:
            return True
        elif isinstance(spawn_evt, dict):
            sx, sy = spawn_evt['pos']
            s_rad = spawn_evt['rad']
            for b in ui_state.bodies:
                if b.active:
                    bx, by = b.pos
                    dist_sq = (bx - sx)**2 + (by - sy)**2
                    if math.sqrt(dist_sq) <= (b.radius + s_rad):
                        b.set_dying()
                        print(f"[SPAWN] Corpo {b.name} marcato per la morte prima dell'inserimento.")
 
            locked_name = None
            if ui_state.locked_body_idx is not None and ui_state.locked_body_idx < len(ui_state.bodies):
                locked_name = ui_state.bodies[ui_state.locked_body_idx].name

            tgt_name = None
            if ui_state.lagrange_target_idx != -1 and ui_state.lagrange_target_idx < len(ui_state.bodies):
                tgt_name = ui_state.bodies[ui_state.lagrange_target_idx].name

            attr_name = None
            if ui_state.lagrange_attr_idx != -1 and ui_state.lagrange_attr_idx < len(ui_state.bodies):
                attr_name = ui_state.bodies[ui_state.lagrange_attr_idx].name
 
            new_bodies, _ = rebuild_simulation(ui_state.bodies, ui_state.gstate.show_info_causality, new_dt=None, new_body_params=spawn_evt)
 
            if locked_name is not None:
                ui_state.locked_body_idx = next((b.idx for b in new_bodies if b.name == locked_name), None)
            if tgt_name is not None:
                ui_state.lagrange_target_idx = next((b.idx for b in new_bodies if b.name == tgt_name), -1)
            if attr_name is not None:
                ui_state.lagrange_attr_idx = next((b.idx for b in new_bodies if b.name == attr_name), -1)
 
            ui_state.bodies = new_bodies
            ui_state.engine.bodies = new_bodies
            ui_state.engine.refresh_kernel()
            ui_state.renderer = GravityRenderer(data.WIDTH, data.HEIGHT, ui_state.resolution_div)
            print(f"Spawn eseguito via OrbitalSpawner. Corpi attivi: {len(new_bodies)}")
            return True
        return False
 
    def intercept_faders(self, event):
        if ui_state.gstate.view_mode == 2 and ui_state.fader_dphi.handle_event(event):
            config.USER_SENSITIVITY_MAG = ui_state.fader_dphi.get_value()
            return True
        elif ui_state.gstate.view_mode in (3, 4) and ui_state.fader_roche.handle_event(event):
            config.ROCHE_SENSITIVITY_MAG = ui_state.fader_roche.get_value()
            return True
        elif ui_state.gstate.view_mode == 4 and ui_state.fader_contrast.handle_event(event):
            config.ROCHE_CONTRAST = ui_state.fader_contrast.get_value()
            return True
        return False
 
    def intercept_console(self, event):
        return ui_state.game_console.handle_event(event, data.WIDTH)
 
    def intercept_camera(self, event):
        if ui_state.game_console.expanded:
            # Consumiamo l'evento (restituendo True) solo se è un input di scorrimento con la rotella del mouse.
            # Questo evita lo zoom simultaneo della telecamera mentre si scorre la console.
            if event.type == pygame.MOUSEWHEEL:
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                return True
            
            # Impediamo alla telecamera di muoversi (drag/click) se il mouse si trova dentro l'area della console.
            # Non restituiamo True in modo da far propagare il click alla console stessa (es. per il bottone di chiusura).
            screen = pygame.display.get_surface()
            win_w, win_h = screen.get_size() if screen else (1280, 720)
            w = int(win_w * 0.9)
            h = int(win_h * 0.9)
            x = (win_w - w) // 2
            y = (win_h - h) // 2
            bg_rect = pygame.Rect(x, y, w, h)
            
            if hasattr(event, 'pos') and bg_rect.collidepoint(event.pos):
                return False
                
        ui_state.camera.handle_input(event)
        return False
 
    # ------------------------------------------------------------------
    # CALLBACKS STANDARD
    # ------------------------------------------------------------------
 
    def on_quit(self, event):
        ui_state.running = False
 
    def on_mouse_motion(self, event):
        if event.buttons[0]:
            if ui_state.locked_body_idx is not None:
                ui_state.locked_body_idx = None
 
    def on_mouse_button_down(self, event):
        if event.button != 1:
            return
 
        current_time = pygame.time.get_ticks()
        is_double_click = (current_time - self.last_click_time) < 400
        self.last_click_time = current_time
        WIDTH, HEIGHT = data.WIDTH, data.HEIGHT
 
        if not is_double_click:
            return
 
        mx, my = pygame.mouse.get_pos()
        cx, cy = WIDTH // 2, HEIGHT // 2
        c_off_x = ui_state.camera.offset_x
        c_off_y = ui_state.camera.offset_y
        c_scale = ui_state.camera.scale
        inv_scale = 1.0 / c_scale
 
        # --- HIT TEST CORPI ---
        hit_body = None
        min_dist_pixel = float('inf')
 
        for i in range(data.MAX_BODIES):
            if (data.FLAGS[i] & data.FLAG_ALIVE) == 0:
                continue
            px, py = data.POS[i, 0], data.POS[i, 1]
            sx = (px - c_off_x) * inv_scale + cx
            sy = (py - c_off_y) * inv_scale + cy
            dx = mx - sx
            dy = my - sy
            dist_sq_pixel = dx*dx + dy*dy
            hitbox_rad = max(15.0, data.RAD[i] * inv_scale)
            if dist_sq_pixel < hitbox_rad * hitbox_rad and dist_sq_pixel < min_dist_pixel:
                min_dist_pixel = dist_sq_pixel
                hit_body = i
 
        if hit_body is not None:
            ui_state.locked_body_idx = hit_body
            self._update_lagrange_target_on_lock(hit_body)
            body_obj = next((b for b in ui_state.bodies if b.idx == hit_body), None)
            b_name = body_obj.name if body_obj else f"Unknown_{hit_body}"
            b_mass = data.MASS[hit_body]
            b_speed = math.sqrt(data.VEL[hit_body, 0]**2 + data.VEL[hit_body, 1]**2)
            b_acc_m_s2 = math.sqrt(data.ACC[hit_body, 0]**2 + data.ACC[hit_body, 1]**2) * 1000.0
            print(f"\n==========================================")
            print(f"[CAMERA] LOCKED ON: {b_name} (ID: {hit_body})")
            print(f"         Mass     : {b_mass:.4e} kg")
            print(f"         Speed    : {b_speed:.2f} km/s")
            print(f"         Accel    : {b_acc_m_s2:.4f} m/s^2")
            print(f"==========================================")
        else:
            # --- SONDA CAMPO (click su spazio vuoto) ---
            ui_state.locked_body_idx = None
            wx = (mx - cx) * c_scale + c_off_x
            wy = (my - cy) * c_scale + c_off_y
            active_indices = np.where(data.FLAGS & data.FLAG_ALIVE)[0].astype(np.int64)
 
            # Array dummy: Numba richiede sempre tipo concreto float64[::3], mai None
            _dummy = np.zeros((1, 1, 5), dtype=np.float64)
            _h_L0 = data.HISTORY_L0 if data.HISTORY_L0 is not None else _dummy
            _h_L1 = data.HISTORY_L1 if data.HISTORY_L1 is not None else _dummy
            _h_L2 = data.HISTORY_L2 if data.HISTORY_L2 is not None else _dummy

            phi_val = graphics_kernel.probe_field_value(
                wx, wy,
                data.POS, data.VEL, data.MASS, data.RAD, active_indices,
                _h_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
                _h_L1, data.HEADS_L1, data.MASK_L1, data.LEN_L1,
                _h_L2, data.HEADS_L2, data.MASK_L2, data.LEN_L2,
                data.C_SQ, data.VOID_VAL, data.INV_C, data.INV_DT, data.G
            )
            dphi_val = graphics_kernel.probe_dphi_at_point(
                wx, wy,
                data.POS, data.VEL, data.MASS, data.RAD, active_indices,
                _h_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
                _h_L1, data.HEADS_L1, data.MASK_L1, data.LEN_L1,
                _h_L2, data.HEADS_L2, data.MASK_L2, data.LEN_L2,
                data.C_SQ, data.VOID_VAL, data.INV_C, data.INV_DT, data.G
            )
            tidal_str, log_str = graphics_kernel.probe_tidal_stress_at_point(
                wx, wy, data.POS, data.MASS, active_indices, data.G, 0.0
            )
            print(f"[SONDA] Pixel: ({mx},{my}) -> World: ({wx/AU_IN_KM:.2f} AU, {wy/AU_IN_KM:.2f} AU)")
            print(f"        Phi  : {phi_val:.6e} km²/s²")
            print(f"        DPhi : {dphi_val * 1e3:.6e} kW/kg  (km²/s³)")
            print(f"        Tidal: {tidal_str:.4e} s^-2  (log10: {log_str:.2f})")
 

    def on_key_down(self, event):
        # --- GESTIONE CONFERMA LIGO ---
        if ui_state.ligo_confirm_active:
            if event.key == pygame.K_y:
                if ui_state.ligo_pending_pos:
                    ui_state.ligo_probe.activate_at(ui_state.ligo_pending_pos)
                    print("RADAR: LIGO PROBE DEPLOYED")
                ui_state.ligo_confirm_active = False
                ui_state.ligo_pending_pos = None
                if ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
            elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                ui_state.ligo_confirm_active = False
                ui_state.ligo_pending_pos = None
                print("RADAR: LIGO PROBE DEPLOYMENT CANCELLED")
                if ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
            return
 
        # --- GESTIONE CONFERMA KILL ---
        if ui_state.kill_confirm_active:
            if event.key == pygame.K_y:
                if ui_state.kill_target_idx is not None:
                    victim = next((b for b in ui_state.bodies if b.idx == ui_state.kill_target_idx), None)
                    if victim:
                        victim.set_dying()
                        print(f"KILL COMMAND: Corpo {victim.name} marcato per la morte causale.")
                ui_state.kill_confirm_active = False
                ui_state.kill_target_idx = None
                if ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
            elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                ui_state.kill_confirm_active = False
                ui_state.kill_target_idx = None
                if ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
            return
 
        # --- GESTIONE CONFERMA CAUSALITA ---
        if ui_state.causality_confirm_active:
            if event.key in (pygame.K_y, pygame.K_RETURN):
                # Eseguiamo il ricalcolo e flaggiamo state
                ui_state.gstate.show_info_causality = not ui_state.gstate.show_info_causality
                mode_str = "CAUSALE (RELATIVISTICO)" if ui_state.gstate.show_info_causality else "NEWTONIANO (PURO)"
                print(f"[REBUILD] Switch in corso alla modalità: {mode_str}")
                
                # trigger rebuild as we do in self._rebuild_dt with data.DT as dt parameter
                self._rebuild_dt(data.DT, f"cambio modalità in {mode_str}")
                
                ui_state.causality_confirm_active = False
                if ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
            elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                ui_state.causality_confirm_active = False
                print("SIMULATION MODE SWITCH CANCELLED")
                if ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
            return

        # --- TASTI PRINCIPALI ---
        if event.key == pygame.K_TAB:
            if ui_state.gstate.view_mode in (3, 4):
                active_b = [i for i in range(data.MAX_BODIES)
                            if (data.FLAGS[i] & data.FLAG_ALIVE) and not (data.FLAGS[i] & data.FLAG_DYING)
                            and data.TOP_ATTRACTOR[i] != -1]
            else:
                active_b = [i for i in range(data.MAX_BODIES)
                            if (data.FLAGS[i] & data.FLAG_ALIVE) and not (data.FLAGS[i] & data.FLAG_DYING)]
            if active_b:
                if ui_state.locked_body_idx is None:
                    ui_state.locked_body_idx = active_b[0]
                else:
                    try:
                        c = active_b.index(ui_state.locked_body_idx)
                        ui_state.locked_body_idx = active_b[(c + 1) % len(active_b)]
                    except ValueError:
                        ui_state.locked_body_idx = active_b[0]
                self._update_lagrange_target_on_lock(ui_state.locked_body_idx)
 
        elif event.key == pygame.K_SPACE:
            ui_state.gstate.toggle_pause()
 
        elif event.key == pygame.K_BACKSPACE:
            ui_state.running = False
            print("[GUI] Chiusura Pygame richiesta. Ritorno al Launcher...")
 
        elif event.key == pygame.K_1: ui_state.speed_multiplier = 1
        elif event.key == pygame.K_2: ui_state.speed_multiplier = 10
        elif event.key == pygame.K_3: ui_state.speed_multiplier = 100
        elif event.key == pygame.K_4: ui_state.speed_multiplier = 1000
        elif event.key == pygame.K_5: ui_state.speed_multiplier = 10000
 
        elif event.key == pygame.K_f:
            ui_state.gstate.help_active = not ui_state.gstate.help_active
 
        elif event.key == pygame.K_g:
            if ui_state.gstate.resolution_mode == "AUTO":
                ui_state.gstate.resolution_mode = 1
            elif ui_state.gstate.resolution_mode == 16:
                ui_state.gstate.resolution_mode = "AUTO"
            else:
                ui_state.gstate.resolution_mode *= 2
 
            ui_state.perf_manager.perf_memory.clear()
 
            if ui_state.gstate.resolution_mode != "AUTO":
                ui_state.resolution_div = ui_state.gstate.resolution_mode
            else:
                ui_state.resolution_div = 2
                ui_state.perf_manager.last_res_check = pygame.time.get_ticks()
 
            if not hasattr(ui_state.renderer, 'ctx'):
                ui_state.renderer = GravityRenderer(data.WIDTH, data.HEIGHT, ui_state.resolution_div)
 
            msg = "AUTO" if ui_state.gstate.resolution_mode == "AUTO" else f"1/{ui_state.gstate.resolution_mode}"
            print(f"MAP RES: {msg}")
 
        elif event.key == pygame.K_h:
            if ui_state.gstate.view_mode == 0:
                ui_state.gstate.view_mode = 1
                print("FIELD: PHI (STANDARD)")
            elif ui_state.gstate.view_mode == 1:
                ui_state.gstate.view_mode = 2
                print("FIELD: WAVES (DPHI)")
            elif ui_state.gstate.view_mode == 2:
                ui_state.gstate.view_mode = 5
                print("FIELD: TIDAL STRESS")
            else:
                ui_state.gstate.view_mode = 0
                print("FIELD: OFF")
 
        elif event.key == pygame.K_m:
            if ui_state.gstate.view_mode == 5:
                ui_state.gstate.show_legend = not ui_state.gstate.show_legend
            elif ui_state.gstate.view_mode == 3:
                ui_state.gstate.draw_lagrange = not ui_state.gstate.draw_lagrange
            elif ui_state.gstate.view_mode == 4:
                ui_state.gstate.draw_roche_orbit = not ui_state.gstate.draw_roche_orbit
 
        elif event.key == pygame.K_r:
            ui_state.gstate.show_paths = not ui_state.gstate.show_paths
 
        elif event.key == pygame.K_n:
            mx, my = pygame.mouse.get_pos()
            wx = (mx - data.WIDTH // 2) * ui_state.camera.scale + ui_state.camera.offset_x
            wy = (my - data.HEIGHT // 2) * ui_state.camera.scale + ui_state.camera.offset_y
            ui_state.spawner.activate(wx, wy, ui_state.bodies)
            if not ui_state.gstate.paused:
                ui_state.gstate.toggle_pause()
 
        elif event.key == pygame.K_l:
            if ui_state.gstate.view_mode == 3:
                ui_state.gstate.view_mode = 4
                print("FIELD: ROCHE DU (GRADIENT)")
            elif ui_state.gstate.view_mode == 4:
                ui_state.gstate.view_mode = 1
                print("FIELD: PHI (STANDARD)")
            else:
                if ui_state.locked_body_idx is not None and ui_state.locked_body_idx < len(data.TOP_ATTRACTOR):
                    locked_idx = ui_state.locked_body_idx
                    if data.MASS[locked_idx] >= 1e18:
                        attr_idx = data.TOP_ATTRACTOR[locked_idx]
                        if attr_idx != -1:
                            ui_state.lagrange_target_idx = locked_idx
                            ui_state.lagrange_attr_idx = attr_idx
                            ui_state.gstate.view_mode = 3
                            print("FIELD: LAGRANGE HUNTER")
                        else:
                            print("L-SYSTEM: NO TOP ATTRACTOR FOUND")
                    else:
                        # Ricerca di un corpo alternativo compatibile se quello corrente è troppo piccolo
                        print(f"L-SYSTEM: Target mass ({data.MASS[locked_idx]:.2e} kg) too small. Searching alternative...")
                        alternative_idx = None
                        for i in range(len(data.FLAGS)):
                            if (data.FLAGS[i] & 1) and data.MASS[i] >= 1e18:
                                attr = data.TOP_ATTRACTOR[i] if i < len(data.TOP_ATTRACTOR) else -1
                                if attr != -1:
                                    alternative_idx = i
                                    break
                        if alternative_idx is not None:
                            ui_state.lagrange_target_idx = alternative_idx
                            ui_state.lagrange_attr_idx = data.TOP_ATTRACTOR[alternative_idx]
                            ui_state.gstate.view_mode = 3
                            body_name = next((b.name for b in ui_state.bodies if b.idx == alternative_idx), f"Body {alternative_idx}")
                            print(f"L-SYSTEM: Lagrange Hunter activated on alternative target: {body_name}")
                        else:
                            print("L-SYSTEM: Cannot activate. No body with mass >= 1.0e18 kg and valid attractor found.")
                else:
                    if ui_state.gstate.view_mode in (3, 4):
                        ui_state.gstate.view_mode = 1
                        print("FIELD: PHI (STANDARD)")
 
        elif event.key == pygame.K_p:
            if ui_state.ligo_probe.active:
                ui_state.ligo_probe.deactivate()
                print("RADAR: LIGO PROBE OFF")
            else:
                mx, my = pygame.mouse.get_pos()
                wx = (mx - data.WIDTH // 2) * ui_state.camera.scale + ui_state.camera.offset_x
                wy = (my - data.HEIGHT // 2) * ui_state.camera.scale + ui_state.camera.offset_y
                ui_state.ligo_pending_pos = [wx, wy]
                ui_state.ligo_confirm_active = True
                if not ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
 
        elif event.key == pygame.K_k:
            if ui_state.locked_body_idx is not None:
                ui_state.kill_target_idx = ui_state.locked_body_idx
            else:
                active_b = [i for i in range(data.MAX_BODIES)
                            if (data.FLAGS[i] & data.FLAG_ALIVE) and not (data.FLAGS[i] & data.FLAG_DYING)]
                if active_b:
                    ui_state.kill_target_idx = max(active_b, key=lambda idx: data.MASS[idx])
            if ui_state.kill_target_idx is not None:
                ui_state.kill_confirm_active = True
                if not ui_state.gstate.paused:
                    ui_state.gstate.toggle_pause()
                
        elif event.key == pygame.K_c:
            ui_state.causality_confirm_active = True
            if not ui_state.gstate.paused:
                ui_state.gstate.toggle_pause()
 
        elif event.key == pygame.K_t:
            self._rebuild_dt(data.DT / 2.0, "aumento precisione")
 
        elif event.key == pygame.K_y:
            self._rebuild_dt(data.DT * 2.0, "riduzione precisione")
 
    def _update_lagrange_target_on_lock(self, new_locked_idx):
        if new_locked_idx is None:
            return
        
        # Se siamo in modalità Lagrange Hunter (view_mode == 3) o Roche DU (view_mode == 4)
        if ui_state.gstate.view_mode in (3, 4):
            if new_locked_idx < len(data.FLAGS) and (data.FLAGS[new_locked_idx] & 1):
                attr_idx = data.TOP_ATTRACTOR[new_locked_idx] if new_locked_idx < len(data.TOP_ATTRACTOR) else -1
                
                # Regola speciale per Roche DU se il target bloccato è un satellite/veicolo con massa piccolissima (es. Artemis, ISS)
                if ui_state.gstate.view_mode == 4 and data.MASS[new_locked_idx] < 1e15:
                    if attr_idx != -1:
                        # Cerchiamo un corpo celeste (massa >= 1e15) che ha come attrattore il nostro stesso attrattore
                        alternative_tgt = -1
                        for i in range(len(data.FLAGS)):
                            if i != new_locked_idx and (data.FLAGS[i] & 1) and data.MASS[i] >= 1e15:
                                if i < len(data.TOP_ATTRACTOR) and data.TOP_ATTRACTOR[i] == attr_idx and data.MASS[i] < data.MASS[attr_idx]:
                                    alternative_tgt = i
                                    break
                        if alternative_tgt != -1:
                            ui_state.lagrange_target_idx = alternative_tgt
                            ui_state.lagrange_attr_idx = attr_idx
                            print(f"L-SYSTEM (Roche DU): Target spacecraft rilevato. Coppia impostata su: {ui_state.bodies[alternative_tgt].name} - {ui_state.bodies[attr_idx].name}")
                            return
                        else:
                            # In assenza, usiamo la coppia: attrattore - attrattore dell'attrattore
                            parent_attr_idx = data.TOP_ATTRACTOR[attr_idx] if attr_idx < len(data.TOP_ATTRACTOR) else -1
                            if parent_attr_idx != -1:
                                ui_state.lagrange_target_idx = attr_idx
                                ui_state.lagrange_attr_idx = parent_attr_idx
                                print(f"L-SYSTEM (Roche DU): Target spacecraft rilevato. Coppia impostata su parent: {ui_state.bodies[attr_idx].name} - {ui_state.bodies[parent_attr_idx].name}")
                                return
                
                # Regola standard per corpi celesti normali
                mass_ok = (ui_state.gstate.view_mode == 4) or (data.MASS[new_locked_idx] >= 1e18)
                if mass_ok and attr_idx != -1:
                    ui_state.lagrange_target_idx = new_locked_idx
                    ui_state.lagrange_attr_idx = attr_idx
                    print(f"L-SYSTEM: target aggiornato a: {ui_state.bodies[new_locked_idx].name}")
                    return
            
            # Coppia non valida (in Roche DU solo se manca l'attrattore): teniamo la precedente
            prev_target_name = "None"
            if ui_state.lagrange_target_idx != -1 and ui_state.lagrange_target_idx < len(ui_state.bodies):
                prev_target_name = ui_state.bodies[ui_state.lagrange_target_idx].name
            print(f"L-SYSTEM: lock non compatibile. Heatmap mantenuta su: {prev_target_name}")

    # ------------------------------------------------------------------
    # HELPER PRIVATO
    # ------------------------------------------------------------------
 
    def _rebuild_dt(self, new_target_dt, label):
        """Ricostruisce la simulazione con un nuovo DT. Usato da T e Y."""
        ui_state.spawner.deactivate()
        print(f"[INPUT] Richiesto {label}. DT: {data.DT} -> {new_target_dt}")
 
        locked_name = None
        if ui_state.locked_body_idx is not None and ui_state.locked_body_idx < len(ui_state.bodies):
            locked_name = ui_state.bodies[ui_state.locked_body_idx].name

        tgt_name = None
        if ui_state.lagrange_target_idx != -1 and ui_state.lagrange_target_idx < len(ui_state.bodies):
            tgt_name = ui_state.bodies[ui_state.lagrange_target_idx].name

        attr_name = None
        if ui_state.lagrange_attr_idx != -1 and ui_state.lagrange_attr_idx < len(ui_state.bodies):
            attr_name = ui_state.bodies[ui_state.lagrange_attr_idx].name
 
        new_bodies, _ = rebuild_simulation(ui_state.bodies, ui_state.gstate.show_info_causality,  new_dt=new_target_dt)
 
        if locked_name is not None:
            ui_state.locked_body_idx = next(
                (b.idx for b in new_bodies if b.name == locked_name), None
            )
        if tgt_name is not None:
            ui_state.lagrange_target_idx = next((b.idx for b in new_bodies if b.name == tgt_name), -1)
        if attr_name is not None:
            ui_state.lagrange_attr_idx = next((b.idx for b in new_bodies if b.name == attr_name), -1)
 
        ui_state.bodies = new_bodies
        ui_state.engine.bodies = new_bodies
        ui_state.engine.refresh_kernel()
        ui_state.renderer = GravityRenderer(data.WIDTH, data.HEIGHT, ui_state.resolution_div)

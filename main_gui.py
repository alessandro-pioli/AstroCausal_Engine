import config
import pygame
import numpy as np 
import sys
import time
from ui.game_console import GameConsole
from ui.tutorial_popup import TutorialPopupManager
from core import data 
from core.global_state import GlobalState
from core.engine import Engine
from core.space_probe import SpaceProbeController
from core.event_handler import EventHandler
from ui.hud_components import VerticalFader
from ui.tutorial_texts import push_default_tutorials, push_radar_warnings
from ui.gravity_renderer import GravityRenderer
from ui.input_controller import InputController
from ui.overlay_renderer import OverlayRenderer 
from ui.master_renderer import MasterRenderer
from ui.ui_state import ui_state
from ui.camera import Camera
from utils.formatting import format_unit, format_acc
from utils.performance_manager import PerformanceManager
from core.simulation_manager import rebuild_simulation
from utils.loading_splash import show_splash_and_load, flush_deferred_prints
from ui.orbital_spawner import OrbitalSpawner
from utils.event_logger import DeathTracker
from utils.gc_worker import GCWorker


def main(preset_name="solar_system", w=1200, h=800, dt_val=None):
    """Entry point del processo simulatore: esegue in sequenza la bootstrap a nove
    fasi (§9.3 di ARCHITECTURE_DEEP_DIVE.md, dalla splash Tkinter fino al frame
    zero in pausa) e poi entra nel game loop a ordine fisso (eventi → fisica →
    rendering, §9.1). Ogni 60 frame controlla morti e avvia lo scan GC asincrono
    (§6); quando il GC certifica un'estinzione causale, il rebuild successivo
    riaggancia camera e coppia Lagrange per nome, non per indice, perché il rebuild
    compatta gli indici dei corpi superstiti."""
    data.WIDTH = w
    data.HEIGHT = h

    data.RADAR_WARNING_TRIGGERED = False

    # --- FASE 1: CARICAMENTO (Tkinter splash, PRIMA di pygame) ---
    gstate = GlobalState()
    bodies, new_dt, new_sim_rad, step, _deferred_prints = show_splash_and_load(
        preset_name, gstate, dt_val
    )
    # [LAUNCHER OVERRIDE] va nel buffer differito, non a terminale
    if dt_val is not None:
        _deferred_prints.append(f"[LAUNCHER OVERRIDE] DT imposto a {dt_val}")
    data.DT = new_dt

    # --- FASE 2: INIT PYGAME (schermo non più nero a freddo) ---
    pygame.display.init()
    pygame.font.init() # Audio non inizializzato perché assente

    # --- CONSOLE INTERCEPTOR ---
    game_console = GameConsole(sys.stdout)
    sys.stdout = game_console

    # --- FLUSH LOG DIFFERITI (prodotti durante la splash, ora vanno nella GameConsole) ---
    flush_deferred_prints(_deferred_prints)

    if w == -1 and h == -1:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        data.WIDTH, data.HEIGHT = screen.get_size()
        w, h = data.WIDTH, data.HEIGHT
    else:
        screen = pygame.display.set_mode((data.WIDTH, data.HEIGHT))
    pygame.display.set_caption("AstroCausal Engine")
    clock = pygame.time.Clock()

    # --- FONTS ---
    font_top_left       = pygame.font.SysFont("monospace", 14)
    font_console        = pygame.font.SysFont("monospace", 14)
    font_tutorial       = pygame.font.SysFont("monospace", 18)
    font_tutorial_title = pygame.font.SysFont("monospace", 24, bold=True)
    font_legend_title   = pygame.font.SysFont("monospace", 14, bold=True)
    font_legend_text    = pygame.font.SysFont("monospace", 12)

    overlay_renderer = OverlayRenderer(font_top_left, font_tutorial, font_tutorial_title, font_legend_title, font_legend_text)
    master_renderer  = MasterRenderer(font_top_left, font_tutorial, font_tutorial_title, font_console, overlay_renderer)

    camera = Camera(data.WIDTH, data.HEIGHT)
    engine = Engine(bodies)
    # --- AUTO-FOCUS INITIALIZATION SUL CORPO PIU MASSICCIO ---
    # Usiamo data.TOP_MASS già calcolato da simulation_manager.py
    top_body = next((b for b in bodies if b.mass >= data.TOP_MASS * 0.999), bodies[0]) if bodies else None
    if top_body:
        camera.offset_x = top_body.pos[0]
        camera.offset_y = top_body.pos[1]
        # Dato che: screen_px = world_km / scale
        # Vogliamo width = 20px per due volte il raggio (diametro).
        # Quindi 20px = (2 * radius) / scale  =>  scale = radius / 10.0
        # Aggiungiamo un clamp minimo per evitare scale a 0
        camera.scale = max(top_body.radius / 10.0, 0.001)
    
    # --- INIZIALIZZAZIONE CONTROLLER LIGO ---
    ligo_probe = SpaceProbeController()
    
    renderer = GravityRenderer(w, h, resolution_div=1)
    running = True
    speed_multiplier = step

    # --- UI SETUP ---
    ui_refresh_rate = 20  
    frame_count = 0       
    resolution_div = 2
    
    lagrange_target_idx = -1
    lagrange_attr_idx = -1
    
    # Fader del Guadagno (Gain) per le modalità DPHI e ROCHE (lato destro)
    fader_dphi = VerticalFader(data.WIDTH - 50, data.HEIGHT // 2 - 75, 4, 150, min_val=-4.0, max_val=2.0, default_val=0.0)
    fader_roche = VerticalFader(data.WIDTH - 50, data.HEIGHT // 2 - 75, 4, 150, min_val=-8.0, max_val=8.0, default_val=0.0)
    
    # Fader del Contrasto per la modalità ROCHE (lato sinistro)
    fader_contrast = VerticalFader(50, data.HEIGHT // 2 - 75, 4, 150, min_val=0.0, max_val=100.0, default_val=15.0)

    perf_manager = PerformanceManager()
    
    # --- VARIABILI INTERAZIONE CAMERA ---
    locked_body_idx = None 
    
    radar_popups_shown = False
    tutorial_manager = TutorialPopupManager(font_tutorial, font_tutorial_title)
    
    kill_confirm_active = False
    kill_target_idx = None
    ligo_confirm_active = False
    ligo_pending_pos = None
    causality_confirm_active = False
    spawner = OrbitalSpawner()
    
    # --- EVENT HANDLER SETUP ---
    event_handler = EventHandler()


    # Inizializziamo ui_state
    ui_state.bodies = bodies
    ui_state.engine = engine
    ui_state.renderer = renderer
    ui_state.camera = camera
    ui_state.spawner = spawner
    ui_state.gstate = gstate
    ui_state.fader_dphi = fader_dphi
    ui_state.fader_roche = fader_roche
    ui_state.fader_contrast = fader_contrast
    ui_state.game_console = game_console
    ui_state.tutorial_manager = tutorial_manager
    ui_state.locked_body_idx = locked_body_idx
    ui_state.speed_multiplier = speed_multiplier
    ui_state.resolution_div = resolution_div
    ui_state.perf_manager = perf_manager
    ui_state.screen = screen
    ui_state.ligo_confirm_active = ligo_confirm_active
    ui_state.ligo_pending_pos = ligo_pending_pos
    ui_state.ligo_probe = ligo_probe
    ui_state.kill_confirm_active = kill_confirm_active
    ui_state.kill_target_idx = kill_target_idx
    ui_state.lagrange_target_idx = lagrange_target_idx
    ui_state.lagrange_attr_idx = lagrange_attr_idx
    ui_state.causality_confirm_active = causality_confirm_active
    ui_state.running = running

    # Liberiamo i riferimenti locali ora che ui_state è il punto di accesso unico
    del (bodies, engine, renderer, camera, spawner, gstate,
         fader_dphi, fader_roche, fader_contrast, game_console, tutorial_manager,
         locked_body_idx, speed_multiplier, resolution_div, perf_manager, screen,
         ligo_confirm_active, ligo_pending_pos, ligo_probe,
         kill_confirm_active, kill_target_idx,
         lagrange_target_idx, lagrange_attr_idx,
         causality_confirm_active, running)

    death_tracker = DeathTracker()
    gc_worker = GCWorker()
    sim_frames = 0

    input_ctrl = InputController()
    input_ctrl.register(event_handler)

    # --- TRIGGER TUTORIAL POPUPS AL FRAME ZERO ---
    ui_state.gstate.paused = True
    push_default_tutorials(ui_state.tutorial_manager)
    
    # ::: LOOP PRINCIPALE :::
    while ui_state.running:
        # --- 1. EVENTI ---
        event_handler.handle_events()

        # WASD e frecce direzionali gestiti a parte
        keys = pygame.key.get_pressed()
        ui_state.camera.update(keys)

        # --- 2. FISICA (METRONOME SAMPLING) ---
        if not ui_state.gstate.paused:
            # A. ESECUZIONE FISICA
            ui_state.engine.tick(ui_state.speed_multiplier)
            if isinstance(sys.stdout, GameConsole):
                sys.stdout.current_sim_time = ui_state.engine.sim_time
            
            # --- IMPATTI IN CONSOLE E GC PIGRO ---
            if sim_frames % 60 == 0:
                death_tracker.check_deaths(ui_state.bodies, ui_state.engine.sim_time)
                gc_worker.start_collection()
            sim_frames += 1

            # >>> B. GARBAGE COLLECTOR ASINCRONO <<<
            dead_indices = gc_worker.get_and_clear_results()
            if dead_indices:
                bodies_to_keep = [b for b in ui_state.bodies if b.idx not in dead_indices]
                print(f"[GC] Bodies causally faded away {dead_indices}. Removing permanently.")
                print(f"[GC] Rebuilding the universe... ({len(ui_state.bodies)} -> {len(bodies_to_keep)})")
                
                locked_name = ui_state.bodies[ui_state.locked_body_idx].name if ui_state.locked_body_idx is not None and ui_state.locked_body_idx < len(ui_state.bodies) else None
                tgt_name = ui_state.bodies[ui_state.lagrange_target_idx].name if ui_state.lagrange_target_idx != -1 and ui_state.lagrange_target_idx < len(ui_state.bodies) else None
                attr_name = ui_state.bodies[ui_state.lagrange_attr_idx].name if ui_state.lagrange_attr_idx != -1 and ui_state.lagrange_attr_idx < len(ui_state.bodies) else None

                ui_state.bodies, _ = rebuild_simulation(bodies_to_keep, ui_state.gstate.show_info_causality, new_dt=None)
                if locked_name is not None:
                    ui_state.locked_body_idx = next((b.idx for b in ui_state.bodies if b.name == locked_name), None)
                if tgt_name is not None:
                    ui_state.lagrange_target_idx = next((b.idx for b in ui_state.bodies if b.name == tgt_name), -1)
                if attr_name is not None:
                    ui_state.lagrange_attr_idx = next((b.idx for b in ui_state.bodies if b.name == attr_name), -1)
                ui_state.engine.bodies = ui_state.bodies
                ui_state.engine.refresh_kernel()
                ui_state.renderer = GravityRenderer(w, h, ui_state.resolution_div)

        # --- LOGICA AUTO-LOCK CAMERA ---
        if ui_state.locked_body_idx is not None:
            # Controlla se il corpo è ancora vivo (con protezione bounds)
            if ui_state.locked_body_idx >= len(data.FLAGS) or (data.FLAGS[ui_state.locked_body_idx] & data.FLAG_ALIVE) == 0:
                ui_state.locked_body_idx = None # Corpo morto, sblocca
            else:
                # Sovrascrivi offset camera
                ui_state.camera.offset_x = data.POS[ui_state.locked_body_idx, 0]
                ui_state.camera.offset_y = data.POS[ui_state.locked_body_idx, 1]
                
                # Tracking Dinamico ROCHE 
                if ui_state.gstate.view_mode in (3, 4):
                     locked_idx = ui_state.locked_body_idx
                     
                     # Regola speciale per Roche DU se il corpo bloccato è un satellite/veicolo con massa piccolissima (es. Artemis, ISS)
                     if ui_state.gstate.view_mode == 4 and locked_idx < len(data.MASS) and data.MASS[locked_idx] < 1e15:
                          attr_idx = data.TOP_ATTRACTOR[locked_idx] if locked_idx < len(data.TOP_ATTRACTOR) else -1
                          if attr_idx != -1:
                               # Cerchiamo un corpo celeste (massa >= 1e15) che ha come attrattore il nostro stesso attrattore
                               alternative_tgt = -1
                               for i in range(len(data.FLAGS)):
                                   if i != locked_idx and (data.FLAGS[i] & 1) and data.MASS[i] >= 1e15:
                                       if i < len(data.TOP_ATTRACTOR) and data.TOP_ATTRACTOR[i] == attr_idx and data.MASS[i] < data.MASS[attr_idx]:
                                           alternative_tgt = i
                                           break
                               if alternative_tgt != -1:
                                    ui_state.lagrange_target_idx = alternative_tgt
                                    ui_state.lagrange_attr_idx = attr_idx
                               else:
                                    # In assenza, usiamo la coppia: attrattore - attrattore dell'attrattore
                                    parent_attr_idx = data.TOP_ATTRACTOR[attr_idx] if attr_idx < len(data.TOP_ATTRACTOR) else -1
                                    if parent_attr_idx != -1:
                                         ui_state.lagrange_target_idx = attr_idx
                                         ui_state.lagrange_attr_idx = parent_attr_idx
                     
                     # Regola standard per corpi celesti normali
                     elif (locked_idx < len(data.MASS) and 
                           data.MASS[locked_idx] >= 1e18 and 
                           data.TOP_ATTRACTOR[locked_idx] != -1):
                          ui_state.lagrange_target_idx = locked_idx
                          ui_state.lagrange_attr_idx = data.TOP_ATTRACTOR[locked_idx]
                     else:
                          # Altrimenti manteniamo il target di Lagrange precedente,
                          # ma aggiorniamo comunque il suo attrattore dinamico se cambia.
                          prev_tgt = ui_state.lagrange_target_idx
                          if prev_tgt != -1 and prev_tgt < len(data.TOP_ATTRACTOR):
                               ui_state.lagrange_attr_idx = data.TOP_ATTRACTOR[prev_tgt]
                     
                     if ui_state.lagrange_attr_idx == -1:
                          ui_state.gstate.view_mode = 1 # Uscita dalla modalità se non c'è attrattore
                          
        if ui_state.gstate.view_mode in (3, 4):
            # Check se i corpi di riferimento per ROCHE esistono ancora (con protezione bounds)
            if ui_state.lagrange_target_idx != -1 and ui_state.lagrange_attr_idx != -1:
                num_flags = len(data.FLAGS)
                if (ui_state.lagrange_target_idx >= num_flags or 
                    ui_state.lagrange_attr_idx >= num_flags or 
                    (data.FLAGS[ui_state.lagrange_target_idx] & data.FLAG_ALIVE) == 0 or 
                    (data.FLAGS[ui_state.lagrange_attr_idx] & data.FLAG_ALIVE) == 0):
                    ui_state.gstate.view_mode = 1 # Force exit se muore o svanisce uno dei due corpi base
                    ui_state.lagrange_target_idx = -1
                    ui_state.lagrange_attr_idx = -1



        if data.RADAR_WARNING_TRIGGERED and not radar_popups_shown:
            radar_popups_shown = True
            ui_state.gstate.paused = True
            push_radar_warnings(ui_state.tutorial_manager)

        # --- 3. RENDERING ---
        frame_count += 1
        master_renderer.render_all(
            frame_count, ui_refresh_rate, clock, 
        )
        clock.tick(config.TARGET_FPS)
        
        # --- AUTO-TUNER GRAFICO (Ogni 5000ms) ---
        now = pygame.time.get_ticks()
        current_body_count = int(np.count_nonzero(data.FLAGS & data.FLAG_ALIVE))
        fps = clock.get_fps()
        new_div, changed = ui_state.perf_manager.update_auto_tuner(now, ui_state.gstate, fps, current_body_count, ui_state.resolution_div, ui_state.speed_multiplier, data.DT)
        if changed:
            ui_state.resolution_div = new_div
            if not hasattr(ui_state.renderer, 'ctx'):
                ui_state.renderer = GravityRenderer(w, h, ui_state.resolution_div)

    pygame.quit()

    # --- SALVATAGGIO FINALE LIGO (ALL'USCITA) ---
    if ui_state.ligo_probe.active:
        print("\n[SHUTDOWN] Saving LIGO data before closing...")
        ui_state.ligo_probe.dump_session(filename="ligo_dump_EXIT", dt_used=data.DT)
        
        # Diamo al thread in background 1 secondo per finire di scrivere sul disco
        # prima che Python termini definitivamente il processo principale.
        time.sleep(1.0)
        print("[SHUTDOWN] Shutdown complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AstroCausal Engine")
    parser.add_argument("--preset", type=str, default="solar_system")
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--dt", type=float, default=None)
    
    args = parser.parse_args()
    main(preset_name=args.preset, w=args.width, h=args.height, dt_val=args.dt)

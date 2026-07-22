from ui.ui_theme import UITheme
from utils.formatting import format_time, format_rate, format_unit

class HudRenderer:
    def __init__(self, font_top_left, font_tutorial):
        self.font_top_left = font_top_left
        self.font_tutorial = font_tutorial
        self.hud_bg = UITheme.get_alpha_surface(300, 320, UITheme.COLOR_BLACK, 150)
        self.cached_lines = []

    def draw_hud(self, screen, WIDTH, HEIGHT, gstate, camera, bodies, data, ligo_probe,
                 frame_count, ui_refresh_rate, clock, speed_multiplier, engine_sim_time, DT,
                 locked_body_idx, lagrange_attr_idx, resolution_div):
        
        if frame_count % ui_refresh_rate == 0 or not self.cached_lines:
            fps = clock.get_fps()
            real_tps = fps * speed_multiplier
            
            sim_time = engine_sim_time
            time_formatted = format_time(sim_time)
            
            sim_seconds_per_real_sec = real_tps * DT
            speed_str = format_rate(sim_seconds_per_real_sec)

            if locked_body_idx is not None:
                b_name = next((b.name for b in bodies if b.idx == locked_body_idx), str(locked_body_idx))
                if gstate.view_mode == 3 and lagrange_attr_idx != -1:
                    a_name = next((b.name for b in bodies if b.idx == lagrange_attr_idx), str(lagrange_attr_idx))
                    lock_str = f"L-PAIR: {b_name} -> {a_name}"
                else:
                    lock_str = f"LOCKED: {b_name}"
            else:
                lock_str = "FREE CAM"
                
            mode_names = ["OFF", "PHI", "WAVES (dPhi/dT)", "LAGRANGE HUNTER", "ROCHE TOPOLOGY", "TIDAL STRESS", "GW STRAIN (QUADRUPOLE)"]
            field_status = mode_names[gstate.view_mode] if 0 <= gstate.view_mode < len(mode_names) else f"UNKNOWN ({gstate.view_mode})"
            
            fov_w_km = WIDTH * camera.scale
            fov_h_km = HEIGHT * camera.scale
            
            div_mode_str = f"AUTO (Curr: {resolution_div})" if gstate.resolution_mode == 'AUTO' else f"{gstate.resolution_mode}"
            
            self.cached_lines = [
                (time_formatted, UITheme.COLOR_WHITE),
                (f"DT  : {DT} s", UITheme.COLOR_WHITE),
                (f"SPEED: {speed_multiplier}x ({speed_str})", UITheme.COLOR_WHITE),
                (f"TPS: {int(real_tps)} | FPS: {fps:.1f}", UITheme.HIGHLIGHT_MAIN),
                (f"Scale: 1px = {format_unit(camera.scale)}", UITheme.HIGHLIGHT_MAIN),
                (f"FOV  : {format_unit(fov_w_km)} x {format_unit(fov_h_km)}", UITheme.COLOR_WHITE),
                (f"Bodies: {len(bodies)} | {lock_str}", UITheme.HIGHLIGHT_MAIN),
                ("----------------", UITheme.COLOR_WHITE),
                (f"View Mode: {field_status}", UITheme.COLOR_WHITE),
                (f"DIV MODE: {div_mode_str}", UITheme.COLOR_WHITE),
                ("[F] CONTROL OVERLAY", (0, 255, 150)),  # Colore Mint acceso unico e distinto
                ("----------------", UITheme.COLOR_WHITE)
            ]

            if ligo_probe.active:
                strain = ligo_probe.get_current_strain()
                self.cached_lines.append((f"LIGO STRAIN: {strain:+.3e}", UITheme.INFO))
            else:
                self.cached_lines.append(("[P] Place LIGO Probe", UITheme.COLOR_WHITE))

            # Suggerimento heatmap: sempre visibile quando un corpo e' bloccato,
            # a prescindere dalla heatmap corrente.
            if locked_body_idx is not None:
                hint_col = (255, 210, 0)  # giallo-oro acceso, distinto dal mint di [F]
                self.cached_lines.append(("[L] x1  Lagrange Hunter mode", hint_col))
                self.cached_lines.append(("[L] x2  Roche Topology", hint_col))
                self.cached_lines.append(("[L] x3  GW Strain", hint_col))

        screen.blit(self.hud_bg, (10,10))
        
        if not hasattr(self, 'cached_surfaces') or frame_count % ui_refresh_rate == 0:
            self.cached_surfaces = []
            for txt, col in self.cached_lines:
                self.cached_surfaces.append(self.font_top_left.render(txt, True, col))
                
        for i, surf in enumerate(self.cached_surfaces):
            screen.blit(surf, (20, 20+i*18))
            
        if gstate.view_mode == 5:
            txt_help = self.font_tutorial.render("[M] Toggle Tidal Stress Map Legend", True, (150, 200, 255))
            screen.blit(txt_help, (15, 335))
        elif gstate.view_mode == 3:
            txt_help = self.font_tutorial.render("[M] Toggle Lagrange Overlays", True, UITheme.SUCCESS)
            screen.blit(txt_help, (15, 335))
        elif gstate.view_mode == 4:
            txt_help = self.font_tutorial.render("[M] Toggle Ideal Circular Orbit", True, (200, 200, 255))
            screen.blit(txt_help, (15, 335))

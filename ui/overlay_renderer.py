import pygame
import math
import numpy as np
from ui.ui_theme import UITheme
from utils.formatting import format_unit, format_acc, format_dist_pair

class OverlayRenderer:
    def __init__(self, font_top_left, font_tutorial, font_tutorial_title, font_legend_title, font_legend_text):
        self.font_top_left = font_top_left
        self.font_tutorial = font_tutorial
        self.font_tutorial_title = font_tutorial_title
        self.font_legend_title = font_legend_title
        self.font_legend_text = font_legend_text

    def draw_pause_overlay(self, screen, width):
        margin_y = 20
        pause_surface_shadow = self.font_tutorial_title.render("PAUSED", True, (0, 0, 0))
        pause_surface = self.font_tutorial_title.render("PAUSED", True, (255, 255, 255))
        x_pos = (width - pause_surface.get_width()) // 2
        screen.blit(pause_surface_shadow, (x_pos + 2, margin_y + 2))
        screen.blit(pause_surface, (x_pos, margin_y))
        
    def draw_kill_confirmation(self, screen, width, height, kill_target_idx, bodies, locked_body_idx):
        victim_name = "Unknown"
        vbody = next((b for b in bodies if b.idx == kill_target_idx), None)
        if vbody: 
            victim_name = vbody.name

        pw, ph = 650, 220
        px, py = (width - pw) // 2, (height - ph) // 2
        
        overlay = UITheme.get_alpha_surface(width, height, UITheme.COLOR_BLACK, 150)
        screen.blit(overlay, (0,0))
        
        pbox = UITheme.get_alpha_surface(pw, ph, (30, 20, 20), 240)
        screen.blit(pbox, (px, py))
        pygame.draw.rect(screen, UITheme.DANGER, (px, py, pw, ph), 2, border_radius=5)
        
        txt_title = self.font_tutorial_title.render("DELETE CONFIRMATION", True, UITheme.DANGER)
        screen.blit(txt_title, (px + (pw - txt_title.get_width())//2, py + 20))
        
        txt_q = self.font_top_left.render(f"Are you sure you want to causally delete: {victim_name}?", True, UITheme.TEXT_SECONDARY)
        screen.blit(txt_q, (px + (pw - txt_q.get_width())//2, py + 70))
        
        if locked_body_idx is None:
            txt_warn = self.font_top_left.render("If this is not the body you want to delete, double-click", True, UITheme.TEXT_DIMMED)
            txt_warn2 = self.font_top_left.render("to lock a body and press K again.", True, UITheme.TEXT_DIMMED)
            screen.blit(txt_warn, (px + (pw - txt_warn.get_width())//2, py + 105))
            screen.blit(txt_warn2, (px + (pw - txt_warn2.get_width())//2, py + 130))
            
        txt_opt = self.font_top_left.render("[Y] Yes  |  [N/ESC] No", True, (255, 200, 100))
        screen.blit(txt_opt, (px + (pw - txt_opt.get_width())//2, py + 175))

    def draw_causality_confirmation(self, screen, width, height, current_mode):
        pw, ph = 700, 350
        px, py = (width - pw) // 2, (height - ph) // 2
        
        overlay = UITheme.get_alpha_surface(width, height, UITheme.COLOR_BLACK, 150)
        screen.blit(overlay, (0,0))
        
        pbox = UITheme.get_alpha_surface(pw, ph, (20, 20, 30), 240)
        screen.blit(pbox, (px, py))
        
        color_theme = (100, 200, 255)
        pygame.draw.rect(screen, color_theme, (px, py, pw, ph), 2, border_radius=5)
        
        target_mode = "NEWTONIAN PURE" if current_mode else "CAUSAL RELATIVISTIC"
        txt_title = self.font_tutorial_title.render(f"SIMULATION MODE SWITCH: {target_mode}", True, color_theme)
        screen.blit(txt_title, (px + (pw - txt_title.get_width())//2, py + 20))
        
        if current_mode:
            lines = [
                "You are switching to Newtonian Pure Mode.",
                "This will set the causality simulation radius effectively to zero.",
                "Gravity will propagate instantaneously without relativistic delays.",
                "This creates a huge performance boost, but disables causal features",
                "like gravitational waves and event horizons."
            ]
        else:
            lines = [
                "You are switching to Causal Relativistic Mode.",
                "This will restore the causality simulation radius.",
                "Gravity will propagate at the speed of light.",
                "This consumes significantly more memory and processing power,",
                "but enables deep gravitational interactions and waves."
            ]
            
        y_offset = 80
        for line in lines:
            txt_warn = self.font_top_left.render(line, True, UITheme.TEXT_SECONDARY)
            screen.blit(txt_warn, (px + (pw - txt_warn.get_width())//2, py + y_offset))
            y_offset += 30
            
        txt_opt = self.font_top_left.render("[Y/ENTER] Confirm  |  [N/ESC] Cancel", True, (255, 255, 100))
        screen.blit(txt_opt, (px + (pw - txt_opt.get_width())//2, py + ph - 40))

    def draw_ligo_confirmation(self, screen, width, height, pending_pos):
        pw, ph = 650, 400
        px, py = (width - pw) // 2, (height - ph) // 2
        
        overlay = UITheme.get_alpha_surface(width, height, UITheme.COLOR_BLACK, 150)
        screen.blit(overlay, (0,0))
        
        pbox = UITheme.get_alpha_surface(pw, ph, UITheme.BG_POPUP, 240)
        screen.blit(pbox, (px, py))
        pygame.draw.rect(screen, UITheme.INFO, (px, py, pw, ph), 2, border_radius=5)
        
        txt_title = self.font_tutorial_title.render("📡 DEPLOY LIGO PROBE? 📡", True, UITheme.INFO)
        screen.blit(txt_title, (px + (pw - txt_title.get_width())//2, py + 20))
        
        lines = [
            "You are about to deploy a stationary LIGO Probe.",
            "",
            "It continuously records local gravitational strain and energy flux.",
            "",
            "Only extraordinary events like Neutron Star or Black Hole binary collapses",
            "generate macroscopic waves detectable by this probe.",
            "",
            "To consult the results, exit the simulation. A menu will appear",
            "to build the strain graph and spectrogram."
        ]
        
        dy = py + 70
        for line in lines:
            txt = self.font_top_left.render(line, True, UITheme.COLOR_WHITE)
            screen.blit(txt, (px + 30, dy))
            dy += 25
            
        txt_opt = self.font_top_left.render("[Y] Confirm Deploy  |  [N/ESC] Cancel", True, (255, 200, 100))
        screen.blit(txt_opt, (px + (pw - txt_opt.get_width())//2, py + ph - 40))



    def draw_help_overlay(self, screen, width, height):
        help_lines = [
            (UITheme.HIGHLIGHT_MAIN, "[Mouse Drag / WASD / Arrows] Pan Camera"),
            (UITheme.HIGHLIGHT_MAIN, "[Mouse Wheel] Zoom"),
            (UITheme.HIGHLIGHT_MAIN, "[Double Click] Lock to Body / Probe Void"),
            ((255, 200, 100), "[TAB] Lock to Next Body"),
            ((255, 200, 100), "[N] Spawn Random Body"),
            (UITheme.DANGER, "[K] Mark Target for Causal Deletion"),
            ((255, 200, 100), "[SPACE] Pause Simulation"),
            (UITheme.DANGER, "[BACKSPACE] Exit to Launcher / Quit"),
            (UITheme.TEXT_DIMMED, "--------------------------------------------------"),
            (UITheme.INFO, "[1-5] Engine Speed (Raw Physics Ticks per Frame)"),
            (UITheme.INFO, "[T/Y] Precision (Simulation Time Atom dt)"),
            (UITheme.INFO, "[G] Grid Res (Auto/Manual)"),
            (UITheme.TEXT_DIMMED, "--------------------------------------------------"),
            ((200, 200, 220), "[H] Toggle Heatmaps"),
            ((200, 200, 220), "[R] Toggle Trails"),
            (UITheme.INFO, "[P] Deploy LIGO Probe"),
            (UITheme.WARNING, "[L] Cycle Field Modes (Requires Locked Target):"),
            (UITheme.TEXT_SECONDARY, "    > Mode 1: Emergent Lagrange Points (Use Faders)"),
            (UITheme.TEXT_SECONDARY, "    > Mode 2: Hill Sphere / Roche Limit")
        ]
        
        hw = max([self.font_top_left.size(txt)[0] for _, txt in help_lines]) + 30
        hh = len(help_lines) * 22 + 20
        hx = width - hw - 10
        hy = height - hh - 10
        help_bg = UITheme.get_alpha_surface(hw, hh, UITheme.BG_DARK, 220)
        
        screen.blit(help_bg, (hx, hy))
        pygame.draw.rect(screen, (50, 50, 80), (hx, hy, hw, hh), 1, border_radius=4)
        
        for i, (col, line) in enumerate(help_lines):
            txt = self.font_top_left.render(line, True, col)
            screen.blit(txt, (hx + 15, hy + 10 + i * 22))

    def draw_tidal_legend(self, screen, width, height):
        legend_w, legend_h = 960, 580
        legend_x = (width - legend_w) // 2
        legend_y = (height - legend_h) // 2
        
        overlay = UITheme.get_alpha_surface(width, height, UITheme.COLOR_BLACK, 180)
        screen.blit(overlay, (0, 0))
        
        legend_bg = UITheme.get_alpha_surface(legend_w, legend_h, UITheme.BG_POPUP, 240)
        screen.blit(legend_bg, (legend_x, legend_y))
        pygame.draw.rect(screen, (100, 100, 255), (legend_x, legend_y, legend_w, legend_h), 2, border_radius=8)
        
        title = self.font_tutorial_title.render("TIDAL STRESS MAP LEGEND [M to close]", True, UITheme.BORDER_SELECTED)
        screen.blit(title, (legend_x + (legend_w - title.get_width()) // 2, legend_y + 20))
        
        subtitle = self.font_tutorial.render("Log10(Gradient) [m/s² per km]", True, UITheme.TEXT_DIMMED)
        screen.blit(subtitle, (legend_x + (legend_w - subtitle.get_width()) // 2, legend_y + 60))
        
        items = [
            (UITheme.COLOR_WHITE, ">  1.0", 
             "MICRO-SCALE DISRUPTION (Singularity Proximity)\n"
             "Extreme gradient. Lethal spaghettification for human biology and structural\n"
             "failure of reinforced vessels. Values > 10^4 imply molecular dissociation."),
            
            (UITheme.DANGER, "-6.0 to  1.0", 
             "MACRO-SCALE DISRUPTION (Severe Shear Zone)\n"
             "Critical stress for high-density dwarf planets and metallic asteroids.\n"
             "Metals yield; large artificial macrostructures collapse under their own mass."),
            
            ((255, 255, 0),  "-7.5 to -6.0", 
             "PLANETARY ROCHE LIMIT (Terrestrial Planets & Rock)\n"
             "Exceeds the tensile strength of solid rock and silicates. Terrestrial bodies\n"
             "and moons fracture, generating permanent planetary ring systems."),
            
            ((0,   255, 0),  "-8.5 to -7.5", 
             "CRUSTAL FRACTURE ZONE (Ice Moons & Tectonics)\n"
             "Fracture threshold for icy crusts (e.g., Europa) and porous moons.\n"
             "Triggers global tectonic splitting and exposes subsurface oceans."),
            
            ((0,   255, 255),"-10.0 to -8.5", 
             "FRAGILE ROCHE LIMIT (Comets & Rubble Piles)\n"
             "Disruption of unbound matter and comets (e.g., Shoemaker-Levy 9).\n"
             "In solid moons, induces extreme internal friction and tidal volcanism."),
            
            ((50,  50,  200),"< -10.0", 
             "ORBITAL EQUILIBRIUM (Safe Space / Void)\n"
             "Spatially flat environment. Differential gravitational curvature is negligible.\n"
             "No perceptible tidal effects on macrostructures or celestial bodies.")
        ]
        
        yy = legend_y + 110
        for col, rng, desc in items:
            pygame.draw.rect(screen, col, (legend_x + 40, yy, 24, 24), border_radius=4)
            pygame.draw.rect(screen, UITheme.COLOR_WHITE, (legend_x + 40, yy, 24, 24), 1, border_radius=4)
            
            txt_rng = self.font_legend_title.render(rng, True, UITheme.COLOR_WHITE)
            screen.blit(txt_rng, (legend_x + 80, yy + 2))
            
            lines = desc.split('\n')
            line_y = yy
            for i, line in enumerate(lines):
                is_title = (i == 0)
                line_color = col if is_title else UITheme.TEXT_SECONDARY
                used_font = self.font_legend_title if is_title else self.font_legend_text
                txt_desc = used_font.render(line, True, line_color)
                screen.blit(txt_desc, (legend_x + 280, line_y))
                line_y += 20 if is_title else 15
            
            yy += 70

    def draw_target_hud(self, screen, width, height, locked_body_idx, camera, data, bodies):
        l_idx = locked_body_idx
        if l_idx is None or l_idx >= len(data.FLAGS):
            return
        b_px, b_py = data.POS[l_idx, 0], data.POS[l_idx, 1]
        b_vx, b_vy = data.VEL[l_idx, 0], data.VEL[l_idx, 1]
        b_ax, b_ay = data.ACC[l_idx, 0], data.ACC[l_idx, 1]
        b_rad = data.RAD[l_idx]
        
        sx, sy = camera.world_to_screen((b_px, b_py))
        base_r_px = max(2.0, b_rad / camera.scale)
        
        v_mag = math.sqrt(b_vx**2 + b_vy**2)
        if v_mag > 0:
            nv_x, nv_y = b_vx/v_mag, b_vy/v_mag
            v_log = max(0.5, (math.log10(v_mag + 1) / math.log10(299793.0)) * 5.0)
            line_len = base_r_px + (15.0 * v_log)
            pygame.draw.line(screen, (50, 255, 50), (sx, sy), (sx + nv_x * line_len, sy + nv_y * line_len), 2)
            pygame.draw.circle(screen, (50, 255, 50), (int(sx + nv_x * line_len), int(sy + nv_y * line_len)), 3)

        a_mag = math.sqrt(b_ax**2 + b_ay**2)
        if a_mag > 0:
            na_x, na_y = b_ax/a_mag, b_ay/a_mag
            a_log = max(0.5, (math.log10(a_mag * 1000.0 + 1) / 5.0) * 3.0)
            line_len = base_r_px + (12.0 * a_log)
            pygame.draw.line(screen, (215, 60, 255), (sx, sy), (sx + na_x * line_len, sy + na_y * line_len), 2)
            pygame.draw.circle(screen, (215, 60, 255), (int(sx + na_x * line_len), int(sy + na_y * line_len)), 3)

        ref_body_idx = data.TOP_ATTRACTOR[l_idx] if hasattr(data, 'TOP_ATTRACTOR') else -1
        
        ref_dist_cc = 0.0
        ref_dist_ss = 0.0
        ref_name = "None"
        has_ref = False
        rel_vx, rel_vy = b_vx, b_vy
        rel_ax, rel_ay = b_ax, b_ay  
        
        if ref_body_idx >= 0 and ref_body_idx < len(data.FLAGS) and (data.FLAGS[ref_body_idx] & 1) != 0 and (data.FLAGS[ref_body_idx] & 2) == 0:
            has_ref = True
            r_px, r_py = data.POS[ref_body_idx, 0], data.POS[ref_body_idx, 1]
            r_vx, r_vy = data.VEL[ref_body_idx, 0], data.VEL[ref_body_idx, 1]
            r_ax, r_ay = data.ACC[ref_body_idx, 0], data.ACC[ref_body_idx, 1]

            # Doppia distanza: CC = centro-centro (come effemeridi/libri),
            # SS = superficie-superficie (gap fisico = CC meno entrambi i raggi).
            center_dist = math.sqrt((b_px - r_px)**2 + (b_py - r_py)**2)
            ref_dist_cc = center_dist
            ref_dist_ss = max(0.0, center_dist - data.RAD[ref_body_idx] - b_rad)
            rel_vx = b_vx - r_vx
            rel_vy = b_vy - r_vy
            rel_ax = b_ax - r_ax
            rel_ay = b_ay - r_ay
            
            for b in bodies:
                if b.idx == ref_body_idx:
                    ref_name = b.name
                    break
        
        rel_v_mag = math.sqrt(rel_vx**2 + rel_vy**2)
        rel_a_mag = math.sqrt(rel_ax**2 + rel_ay**2)

        hud_w, hud_h = width - 20, 80
        hud_x = 10
        hud_y = height - hud_h - 10
        
        surf = UITheme.get_alpha_surface(hud_w, hud_h, UITheme.BG_HUD, 180)
        screen.blit(surf, (hud_x, hud_y))
        pygame.draw.rect(screen, (70, 130, 180), (hud_x, hud_y, hud_w, hud_h), 1, border_radius=4) 
        
        b_name = "Unknown"
        b_color = UITheme.COLOR_WHITE
        for b in bodies:
            if b.idx == l_idx:
                b_name = b.name
                b_color = b.color
                break
                
        txt_name = self.font_top_left.render(f"TARGET: {b_name}", True, b_color)
        txt_mass = self.font_top_left.render(f"Mass : {data.MASS[l_idx]:.4e} kg", True, UITheme.TEXT_SECONDARY)
        if has_ref:
            dist_str = f"{ref_name[:6]} {format_dist_pair(ref_dist_cc, ref_dist_ss)}"
        else:
            dist_str = "Dist: --"
        txt_dist = self.font_top_left.render(dist_str, True, UITheme.TEXT_SECONDARY)
        
        txt_px = self.font_top_left.render(f"PX: {format_unit(b_px)}", True, UITheme.TEXT_SECONDARY)
        txt_py = self.font_top_left.render(f"PY: {format_unit(b_py)}", True, UITheme.TEXT_SECONDARY)

        txt_vx = self.font_top_left.render(f"VX (Abs): {b_vx:+.2f} km/s", True, (50, 150, 100))
        txt_vy = self.font_top_left.render(f"VY (Abs): {b_vy:+.2f} km/s", True, (50, 150, 100))
        txt_v  = self.font_top_left.render(f"V  (Abs): {v_mag:.2f} km/s", True, (100, 150, 100))

        txt_rel_x = self.font_top_left.render(f"VX (Rel): {rel_vx:+.2f} km/s", True, (50, 255, 50))
        txt_rel_y = self.font_top_left.render(f"VY (Rel): {rel_vy:+.2f} km/s", True, (50, 255, 50))
        txt_rel_v = self.font_top_left.render(f"V  (Rel): {rel_v_mag:.2f} km/s", True, UITheme.SUCCESS)

        txt_ax = self.font_top_left.render(f"AX (Abs): {format_acc(b_ax)}", True, (215, 60, 255))
        txt_ay = self.font_top_left.render(f"AY (Abs): {format_acc(b_ay)}", True, (215, 60, 255))
        txt_a  = self.font_top_left.render(f"A  (Abs): {format_acc(a_mag)}", True, (230, 100, 255))
        
        txt_rel_ax = self.font_top_left.render(f"AX (Rel): {format_acc(rel_ax)}", True, (255, 150, 255))
        txt_rel_ay = self.font_top_left.render(f"AY (Rel): {format_acc(rel_ay)}", True, (255, 150, 255))
        txt_rel_a  = self.font_top_left.render(f"A  (Rel): {format_acc(rel_a_mag)}", True, (255, 200, 255))

        # Colonne proporzionali alla larghezza del riquadro (responsive) ma con LARGHEZZE
        # NON uniformi: etichette (col1) e posizione (col2) sono strette perché il loro
        # testo è corto; le 4 colonne velocità/accelerazione (col3-col6) prendono la fetta
        # più grossa perché ad alte velocità i valori sono lunghi (es. +38691.40 km/s).
        # Così sparisce il buco dopo PX/PY e i parametri non si sovrappongono.
        col1 = hud_x + int(hud_w * 0.010)   # etichette + distanza CC/SS
        col2 = hud_x + int(hud_w * 0.210)   # posizione PX/PY (stretta)
        param_x0 = hud_x + hud_w * 0.310    # inizio delle 4 colonne parametri
        param_step = (hud_w * (1.0 - 0.310)) / 4.0
        col3 = int(param_x0)
        col4 = int(param_x0 + param_step)
        col5 = int(param_x0 + param_step * 2)
        col6 = int(param_x0 + param_step * 3)

        screen.blit(txt_name, (col1, hud_y + 10))
        screen.blit(txt_mass, (col1, hud_y + 30))
        screen.blit(txt_dist, (col1, hud_y + 50))
        
        screen.blit(txt_px, (col2, hud_y + 10))
        screen.blit(txt_py, (col2, hud_y + 35))
        
        screen.blit(txt_vx, (col3, hud_y + 10))
        screen.blit(txt_vy, (col3, hud_y + 30))
        screen.blit(txt_v,  (col3, hud_y + 50))
        
        screen.blit(txt_rel_x, (col4, hud_y + 10))
        screen.blit(txt_rel_y, (col4, hud_y + 30))
        screen.blit(txt_rel_v,  (col4, hud_y + 50))

        screen.blit(txt_ax, (col5, hud_y + 10))
        screen.blit(txt_ay, (col5, hud_y + 30))
        screen.blit(txt_a,  (col5, hud_y + 50))
        
        screen.blit(txt_rel_ax, (col6, hud_y + 10))
        screen.blit(txt_rel_ay, (col6, hud_y + 30))
        screen.blit(txt_rel_a,  (col6, hud_y + 50))

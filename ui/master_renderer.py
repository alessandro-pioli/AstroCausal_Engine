import pygame
import config
import core.data as data
from ui.ui_theme import UITheme
from ui.renderers.trail_renderer import TrailRenderer
from ui.renderers.body_renderer import BodyRenderer
from ui.renderers.ligo_renderer import LIGORenderer
from ui.renderers.lagrange_renderer import LagrangeRenderer
from ui.renderers.hud_renderer import HudRenderer
from ui.ui_state import ui_state

class MasterRenderer:
    def __init__(self, font_top_left, font_tutorial, font_tutorial_title, font_console, overlay_renderer):
        self.font_top_left = font_top_left
        self.font_tutorial = font_tutorial
        self.font_tutorial_title = font_tutorial_title
        self.font_console = font_console
        self.overlay_renderer = overlay_renderer
        self.hud_renderer = HudRenderer(font_top_left, font_tutorial)

    def render_all(self, frame_count, ui_refresh_rate, clock):
        screen = ui_state.screen
        gstate = ui_state.gstate
        camera = ui_state.camera
        bodies = ui_state.bodies
        renderer = ui_state.renderer
        ligo_probe = ui_state.ligo_probe
        lagrange_target_idx = ui_state.lagrange_target_idx
        lagrange_attr_idx = ui_state.lagrange_attr_idx
        locked_body_idx = ui_state.locked_body_idx
        game_console = ui_state.game_console
        fader_dphi = ui_state.fader_dphi
        fader_roche = ui_state.fader_roche
        fader_contrast = ui_state.fader_contrast
        tutorial_manager = ui_state.tutorial_manager
        spawner = ui_state.spawner
        kill_confirm_active = ui_state.kill_confirm_active
        kill_target_idx = ui_state.kill_target_idx
        ligo_confirm_active = ui_state.ligo_confirm_active
        ligo_pending_pos = ui_state.ligo_pending_pos
        causality_confirm_active = ui_state.causality_confirm_active

        WIDTH = data.WIDTH
        HEIGHT = data.HEIGHT
        
        
        screen.fill(UITheme.COLOR_BLACK)

        # 1. Campo gravitazionale
        if gstate.view_mode == 1:
            renderer.render(screen, camera, mode="PHI")
        elif gstate.view_mode == 2:
            renderer.render(screen, camera, mode="DPHI")  
        elif gstate.view_mode == 3:
            renderer.render(screen, camera, mode="LAGRANGE_HUNTER", lagrange_tgt=lagrange_target_idx, lagrange_attr=lagrange_attr_idx)
        elif gstate.view_mode == 4:
            renderer.render(screen, camera, mode="ROCHE_DU", lagrange_tgt=lagrange_target_idx, lagrange_attr=lagrange_attr_idx)
        elif gstate.view_mode == 5:
            renderer.render(screen, camera, mode="TIDAL_STRESS")

        # 2. Scie
        if gstate.show_paths:
            TrailRenderer.draw_trails(screen, camera, bodies, data, WIDTH, HEIGHT)
            
        # 3. Corpi
        BodyRenderer.draw_bodies(screen, camera, bodies, data, WIDTH, HEIGHT)

        # 4. Sonda LIGO
        LIGORenderer.draw(screen, camera, ligo_probe, bodies, data, WIDTH, HEIGHT)

        # 5. Lagrange Hunter teorico overlay
        if gstate.draw_lagrange and gstate.view_mode == 3:
            LagrangeRenderer.draw_lagrange_hunter(screen, camera, data, lagrange_target_idx, lagrange_attr_idx, self.font_top_left)

        if gstate.draw_roche_orbit and gstate.view_mode == 4:
            LagrangeRenderer.draw_roche_circular_orbit(screen, camera, data, lagrange_target_idx, lagrange_attr_idx, self.font_top_left)

        # 6. HUD testuale
        self.hud_renderer.draw_hud(screen, WIDTH, HEIGHT, gstate, camera, bodies, data, ligo_probe,
                                   frame_count, ui_refresh_rate, clock, ui_state.speed_multiplier, 
                                   ui_state.engine.sim_time, data.DT,
                                   ui_state.locked_body_idx, lagrange_attr_idx, ui_state.resolution_div)

        # 7. Overlays delegati
        if gstate.paused:
            self.overlay_renderer.draw_pause_overlay(screen, WIDTH)
            
        if locked_body_idx is not None:
            self.overlay_renderer.draw_target_hud(screen, WIDTH, HEIGHT, locked_body_idx, camera, data, bodies)
            
        if kill_confirm_active and kill_target_idx is not None:
            self.overlay_renderer.draw_kill_confirmation(screen, WIDTH, HEIGHT, kill_target_idx, bodies, locked_body_idx)
            
        if ligo_confirm_active:
            self.overlay_renderer.draw_ligo_confirmation(screen, WIDTH, HEIGHT, ligo_pending_pos)
            
        if causality_confirm_active:
            self.overlay_renderer.draw_causality_confirmation(screen, WIDTH, HEIGHT, gstate.show_info_causality)
            
        game_console.draw(screen, self.font_console, WIDTH)
        
        if gstate.view_mode == 2:
            fader_dphi.draw(screen)
        elif gstate.view_mode in (3, 4):
            fader_roche.draw(screen)
            debug_text = f"SENSITIVITY: 10^{config.ROCHE_SENSITIVITY_MAG:.2f} = {10.0**config.ROCHE_SENSITIVITY_MAG:.2e}"
            debug_surface = self.font_top_left.render(debug_text, True, UITheme.DANGER)
            screen.blit(debug_surface, (WIDTH - debug_surface.get_width() - 80, HEIGHT // 2 - debug_surface.get_height()//2))
            
            if gstate.view_mode == 4:
                fader_contrast.draw(screen)
                contrast_text = f"CONTRAST: {config.ROCHE_CONTRAST:.1f}"
                contrast_surf = self.font_top_left.render(contrast_text, True, UITheme.SUCCESS)
                screen.blit(contrast_surf, (80, HEIGHT // 2 - contrast_surf.get_height()//2))
                
        if gstate.show_legend and gstate.view_mode == 5:
            self.overlay_renderer.draw_tidal_legend(screen, WIDTH, HEIGHT)
            
        tutorial_manager.draw(screen, WIDTH, HEIGHT)
        
        # 8. Spawner preview
        if spawner.active:
            if spawner.state == 3 and getattr(spawner, 'lagrange_secondary_idx', None) is not None:
                s_idx = spawner.lagrange_secondary_idx
                if (data.FLAGS[s_idx] & 1):
                    sx, sy = camera.world_to_screen((data.POS[s_idx, 0], data.POS[s_idx, 1]))
                    s_rad = max(4.0, data.RAD[s_idx] / camera.scale) + 10.0
                    pygame.draw.circle(screen, UITheme.SUCCESS, (sx, sy), int(s_rad), 2)
            elif spawner.state == 4:
                markers = spawner.get_ghost_markers()
                if markers:
                    for i, pt in enumerate(markers):
                        mx, my = camera.world_to_screen(pt)
                        pygame.draw.line(screen, (255, 150, 0), (mx - 6, my), (mx + 6, my), 2)
                        pygame.draw.line(screen, (255, 150, 0), (mx, my - 6), (mx, my + 6), 2)
                        lbl = self.font_top_left.render(f"L{i+1}", True, UITheme.WARNING)
                        screen.blit(lbl, (mx + 8, my - 8))
        spawner.draw(screen, WIDTH, HEIGHT, self.font_tutorial, self.font_tutorial_title)

        if gstate.help_active:
            self.overlay_renderer.draw_help_overlay(screen, WIDTH, HEIGHT)

        pygame.display.flip()

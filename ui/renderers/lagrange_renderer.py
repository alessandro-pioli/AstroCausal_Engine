import pygame
import math
from utils.orbital_math import get_lagrange_points
from ui.ui_theme import UITheme

class LagrangeRenderer:
    @staticmethod
    def draw_lagrange_hunter(screen, camera, data, lagrange_target_idx, lagrange_attr_idx, font_top_left):
        if lagrange_target_idx is None or lagrange_target_idx == -1 or lagrange_attr_idx is None or lagrange_attr_idx == -1:
            return
            
        num_flags = len(data.FLAGS)
        if lagrange_target_idx >= num_flags or lagrange_attr_idx >= num_flags:
            return
            
        if not ((data.FLAGS[lagrange_target_idx] & 1) and (data.FLAGS[lagrange_attr_idx] & 1)):
            return
            
        pts = get_lagrange_points(data.MASS[lagrange_attr_idx], data.POS[lagrange_attr_idx], 
                                  data.MASS[lagrange_target_idx], data.POS[lagrange_target_idx],
                                  data.VEL[lagrange_attr_idx], data.VEL[lagrange_target_idx])
        if pts:
            # We only need L2, L3 coordinates for drawing the bounding line,
            # plus positions for attractor (p) and target (s)
            sx_l2, sy_l2 = camera.world_to_screen(pts[1])
            sx_l3, sy_l3 = camera.world_to_screen(pts[2])
            sx_p, sy_p = camera.world_to_screen(data.POS[lagrange_attr_idx])
            sx_s, sy_s = camera.world_to_screen(data.POS[lagrange_target_idx])
            
            line_col = UITheme.SUCCESS
            
            # Draws a reference axis through the main points (L3 to L2 passing through M1 and M2)
            pygame.draw.line(screen, line_col, (sx_l3, sy_l3), (sx_l2, sy_l2), 2)
            
            # Draw projection lines for L4 and L5 to the two main bodies
            for pt_idx in [3, 4]:
                px, py = camera.world_to_screen(pts[pt_idx])
                pygame.draw.line(screen, line_col, (sx_p, sy_p), (px, py), 2)
                pygame.draw.line(screen, line_col, (sx_s, sy_s), (px, py), 2)
                
            # Draw all 5 points and labels
            for i, pt in enumerate(pts):
                mx, my = camera.world_to_screen(pt)
                pygame.draw.circle(screen, line_col, (int(mx), int(my)), 4)
                lbl = font_top_left.render(f"L{i+1}", True, line_col)
                screen.blit(lbl, (mx + 8, my - 8))

    @staticmethod
    def _dashed_circle(screen, color, center, radius, width=2, dash_deg=7, gap_deg=7):
        """Disegna un cerchio tratteggiato approssimando l'arco con brevi segmenti."""
        cx, cy = center
        if radius < 1.0:
            pygame.draw.circle(screen, color, (int(cx), int(cy)), 3)
            return
        a = 0.0
        step = dash_deg + gap_deg
        while a < 360.0:
            r1 = math.radians(a)
            r2 = math.radians(min(a + dash_deg, 360.0))
            x1 = cx + radius * math.cos(r1); y1 = cy + radius * math.sin(r1)
            x2 = cx + radius * math.cos(r2); y2 = cy + radius * math.sin(r2)
            pygame.draw.line(screen, color, (x1, y1), (x2, y2), width)
            a += step

    @staticmethod
    def draw_roche_circular_orbit(screen, camera, data, target_idx, attr_idx, font):
        """
        Overlay teorico per la Topologia di Roche: cerchio tratteggiato (centrato sul
        baricentro) che mostra a quale raggio il target orbiterebbe circolarmente, dato
        il suo momento angolare specifico corrente h. Confronto col campo emergente,
        analogo ai marker di Lagrange analitici.
          D_g = h^2 / (G M_tot)        (separazione circolare per quel h)
          r_g = D_g * m_attr / M_tot   (raggio del target dal baricentro)
        """
        if target_idx is None or attr_idx is None or target_idx == -1 or attr_idx == -1:
            return
        num_flags = len(data.FLAGS)
        if target_idx >= num_flags or attr_idx >= num_flags:
            return
        if not ((data.FLAGS[target_idx] & 1) and (data.FLAGS[attr_idx] & 1)):
            return

        m1 = data.MASS[attr_idx]    # attrattore
        m2 = data.MASS[target_idx]  # target
        M_tot = m1 + m2
        if M_tot <= 0.0:
            return

        p1x, p1y = data.POS[attr_idx, 0], data.POS[attr_idx, 1]
        p2x, p2y = data.POS[target_idx, 0], data.POS[target_idx, 1]
        dx = p2x - p1x
        dy = p2y - p1y
        vx = data.VEL[target_idx, 0] - data.VEL[attr_idx, 0]
        vy = data.VEL[target_idx, 1] - data.VEL[attr_idx, 1]
        h = dx * vy - dy * vx  # momento angolare specifico relativo

        D_g = (h * h) / (data.G * M_tot)
        r_g = D_g * (m1 / M_tot)

        c_wx = (m1 * p1x + m2 * p2x) / M_tot
        c_wy = (m1 * p1y + m2 * p2y) / M_tot
        cx, cy = camera.world_to_screen((c_wx, c_wy))

        if camera.scale <= 0.0:
            return
        radius_px = r_g / camera.scale
        if radius_px > 60000.0:
            return  # orbita ideale enormemente fuori scena

        col = (200, 200, 255)
        # anello continuo: gap_deg=0 rende i segmenti contigui (cerchio liscio a ogni raggio)
        LagrangeRenderer._dashed_circle(screen, col, (cx, cy), radius_px, width=2, dash_deg=4, gap_deg=0)
        lbl = font.render("IDEAL CIRCULAR ORBIT", True, col)
        ly = max(5, int(cy - radius_px) - 18)
        screen.blit(lbl, (int(cx) - lbl.get_width() // 2, ly))

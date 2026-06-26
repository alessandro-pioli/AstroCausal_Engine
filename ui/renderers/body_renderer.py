import pygame
import math

class BodyRenderer:
    @staticmethod
    def draw_bodies(screen, camera, bodies, data, WIDTH, HEIGHT):
        for body in bodies:
            if data.FLAGS[body.idx] == 0: continue
            # Se è DYING (Bit 2), SALTA IL DISEGNO. 
            if (data.FLAGS[body.idx] & 2) != 0: 
                continue 
            if body.pos[0] <= data.VOID_VAL:
                continue
            if not (math.isfinite(body.pos[0]) and math.isfinite(body.pos[1]) and math.isfinite(body.vel[0])):
                body.set_dying()
                continue
                
            sx, sy = camera.world_to_screen(body.pos)
            draw_col = body.color
            
            rad = max(3, min(int(body.radius / camera.scale), 20000))
            if -10000 < sx < WIDTH + 10000 and -10000 < sy < HEIGHT + 10000:
                pygame.draw.circle(screen, draw_col, (sx, sy), rad)

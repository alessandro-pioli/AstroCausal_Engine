import pygame

class LIGORenderer:
    @staticmethod
    def draw(screen, camera, ligo_probe, bodies, data, width, height):
        if not ligo_probe.active: return
        px, py = ligo_probe.pos
        sx, sy = camera.world_to_screen((px, py))
        
        if -10000 < sx < width + 10000 and -10000 < sy < height + 10000:
            soglia_massa = data.TOP_MASS * 0.001 
            for body in bodies:
                if (data.FLAGS[body.idx] & 1) == 0 or (data.FLAGS[body.idx] & 2) != 0: continue
                if body.pos[0] <= data.VOID_VAL: continue
                
                if data.MASS[body.idx] > soglia_massa:
                    bsx, bsy = camera.world_to_screen(body.pos)
                    if -10000 < bsx < width + 10000 and -10000 < bsy < height + 10000:
                        pygame.draw.aaline(screen, (0, 100, 100), (sx, sy), (bsx, bsy))
            
            pygame.draw.rect(screen, (0, 255, 255), (sx - 5, sy - 5, 10, 10), 1)
            pygame.draw.line(screen, (0, 255, 255), (sx - 15, sy), (sx + 15, sy), 1)
            pygame.draw.line(screen, (0, 255, 255), (sx, sy - 15), (sx, sy + 15), 1)

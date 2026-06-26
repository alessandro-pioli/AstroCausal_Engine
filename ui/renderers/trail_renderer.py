import pygame
from core.jit_kernels import graphics_kernel

class TrailRenderer:
    @staticmethod
    def draw_trails(screen, camera, bodies, data, WIDTH, HEIGHT):
        c_off_x = camera.offset_x
        c_off_y = camera.offset_y
        c_scale = camera.scale
        
        for body in bodies:
            if (data.FLAGS[body.idx] & 1) == 0: continue
            if data.POS[body.idx, 0] <= (data.VOID_VAL): continue

            screen_points = graphics_kernel.transform_trail_kernel(
                data.TRAIL_BUFFER[body.idx], 
                data.TRAIL_HEADS[body.idx],  
                True,                        
                c_off_x, c_off_y, c_scale,
                WIDTH, HEIGHT,
                data.VOID_VAL
            )
            
            if len(screen_points) > 1:
                col = body.color
                if (data.FLAGS[body.idx] & 2) != 0: col = (100, 100, 100)
                pygame.draw.lines(screen, col, False, screen_points, 1) 

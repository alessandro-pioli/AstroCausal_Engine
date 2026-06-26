import pygame

INITIAL_SCALE = 5000.0  

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale = INITIAL_SCALE
        self.zoom_speed = 1.1
        self.is_dragging = False
        self.last_mouse_pos = (0, 0)

    def world_to_screen(self, world_pos):
        screen_x = (world_pos[0] - self.offset_x) / self.scale + self.width // 2
        screen_y = (world_pos[1] - self.offset_y) / self.scale + self.height // 2
        return int(screen_x), int(screen_y)

    def handle_input(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0: self.scale /= self.zoom_speed
            elif event.y < 0: self.scale *= self.zoom_speed
            
            # Limite massimo di zoom (1 px = 1 km)
            self.scale = max(1.0, self.scale)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                self.is_dragging = True
                self.last_mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: self.is_dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                mx, my = event.pos
                dx = mx - self.last_mouse_pos[0]
                dy = my - self.last_mouse_pos[1]
                self.offset_x -= dx * self.scale
                self.offset_y -= dy * self.scale
                self.last_mouse_pos = (mx, my)
    
    def update(self, keys): 
        pan_speed = 10 * self.scale 
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.offset_x -= pan_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.offset_x += pan_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.offset_y -= pan_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.offset_y += pan_speed
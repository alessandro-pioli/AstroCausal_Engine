import pygame

class VerticalFader:
    def __init__(self, x, y, width, height, min_val, max_val, default_val=0.0):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = default_val
        
        self.is_dragging = False
        self.font = pygame.font.SysFont("Courier", 14, bold=True)
        self.font_small = pygame.font.SysFont("Courier", 12)
        
        # Determine the knob position initially
        self._update_knob_from_val()

    def _update_knob_from_val(self):
        # Val goes from min_val to max_val
        # Map it to 0.0 -> 1.0 (where 0.0 is bottom, 1.0 is top)
        ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, ratio))
        # Top of the fader is rect.y, bottom is rect.bottom
        self.knob_y = self.rect.bottom - (ratio * self.rect.height)

    def _update_val_from_knob(self):
        # Calculate ratio from knob position
        ratio = (self.rect.bottom - self.knob_y) / self.rect.height
        ratio = max(0.0, min(1.0, ratio))
        self.current_val = self.min_val + ratio * (self.max_val - self.min_val)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Check if click is around the fader line/rectangle
                padding = 15
                click_rect = pygame.Rect(self.rect.x - padding, self.rect.y, self.rect.width + padding*2, self.rect.height)
                if click_rect.collidepoint(event.pos):
                    self.is_dragging = True
                    self.knob_y = max(self.rect.top, min(self.rect.bottom, event.pos[1]))
                    self._update_val_from_knob()
                    return True # Event handled
                
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging = False
                
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                self.knob_y = max(self.rect.top, min(self.rect.bottom, event.pos[1]))
                self._update_val_from_knob()
                return True
                
        return False

    def get_value(self):
        return self.current_val

    def draw(self, screen):
        # Background track
        pygame.draw.line(screen, (100, 100, 100), (self.rect.centerx, self.rect.top), (self.rect.centerx, self.rect.bottom), 3)
        
        # Zero line marker if it exists in range
        if self.min_val <= 0.0 <= self.max_val:
            zero_ratio = (0.0 - self.min_val) / (self.max_val - self.min_val)
            zero_y = self.rect.bottom - (zero_ratio * self.rect.height)
            pygame.draw.line(screen, (200, 200, 200), (self.rect.centerx - 8, zero_y), (self.rect.centerx + 8, zero_y), 1)

        # Knob
        knob_rect = pygame.Rect(0, 0, 16, 8)
        knob_rect.center = (self.rect.centerx, self.knob_y)
        pygame.draw.rect(screen, (255, 200, 50), knob_rect)
        pygame.draw.polygon(screen, (255, 255, 200), [
            (self.rect.centerx - 12, self.knob_y),
            (self.rect.centerx - 5, self.knob_y - 5),
            (self.rect.centerx - 5, self.knob_y + 5)
        ])
        
        # Labels
        title_surf = self.font.render("GAIN", True, (255, 200, 100))
        val_surf = self.font.render(f"{self.current_val:+.1f}", True, (255, 255, 255))
        
        screen.blit(title_surf, (self.rect.centerx - title_surf.get_width()//2, self.rect.top - 20))
        screen.blit(val_surf, (self.rect.centerx - val_surf.get_width()//2, self.rect.bottom + 5))

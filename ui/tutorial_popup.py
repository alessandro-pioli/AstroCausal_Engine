import pygame
from ui.ui_theme import UITheme

class TutorialPopupManager:
    def __init__(self, font_hud, font_title):
        self.font = font_hud
        self.font_title = font_title
        self.popups = []
        self.active = False
        
    def enqueue(self, title, lines, color=UITheme.COLOR_WHITE):
        self.popups.append({"title": title, "lines": lines, "color": color})
        self.active = True
        
    def update_events(self, event):
        if not self.active or len(self.popups) == 0:
            return False
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.popups.pop(0)
            if len(self.popups) == 0:
                self.active = False
            return True
            
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.popups.pop(0)
                if len(self.popups) == 0:
                    self.active = False
                return True
            elif event.key == pygame.K_ESCAPE:
                self.popups.clear()
                self.active = False
                return True
            
        return False
        
    def draw(self, screen, width, height):
        if not self.active or len(self.popups) == 0:
            return
            
        popup = self.popups[0]
        
        w = max(450, max([self.font.size(l)[0] for l in popup["lines"]]) + 60)
        h = 100 + len(popup["lines"]) * 26 + 20
        
        x = (width - w) // 2
        y = (height - h) // 2
        
        overlay = UITheme.get_alpha_surface(width, height, UITheme.COLOR_BLACK, 100)
        screen.blit(overlay, (0,0))
        
        box = UITheme.get_alpha_surface(w, h, UITheme.BG_POPUP, 230)
        screen.blit(box, (x, y))
        
        pygame.draw.rect(screen, popup["color"], (x, y, w, h), 2, border_radius=8)
        
        title_surf = self.font_title.render(popup["title"], True, popup["color"])
        screen.blit(title_surf, (x + (w - title_surf.get_width())//2, y + 20))
        
        dy = y + 70
        for line in popup["lines"]:
            l_surf = self.font.render(line, True, (220, 220, 220))
            screen.blit(l_surf, (x + 30, dy))
            dy += 26
            
        prompt = self.font.render("[SPACE/Click: Next]   [ESC: Skip All]", True, UITheme.TEXT_DIMMED)
        screen.blit(prompt, (x + (w - prompt.get_width())//2, y + h - 35))

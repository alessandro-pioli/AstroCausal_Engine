import sys
import time
import pygame
from ui.ui_theme import UITheme
from utils.formatting import format_time

class GameConsole:
    def __init__(self, original_stdout):
        """Proxy su `sys.stdout` (§10 di ARCHITECTURE_DEEP_DIVE.md, pattern Duck
        Typing + Proxy): intercetta ogni `print()` del progetto senza che nessun
        modulo debba conoscere l'esistenza della console in-game, inoltrando sempre
        anche al terminale reale tramite `original_stdout`."""
        self.original_stdout = original_stdout
        self.messages = []
        self.expanded = True
        self.current_sim_time = 0.0
        self.scroll_y = 999999
        self.auto_scroll = True
        self.max_messages = 1000
        
    def write(self, msg):
        """Chiamato da ogni `print()` del progetto. Inoltra sempre al terminale
        originale, poi ripulisce i codici ANSI di colore (utili al terminale,
        sporcherebbero il rendering pygame) e prepende il **tempo simulato**
        corrente, non quello di sistema: un impatto all'anno 2.150.847 della
        simulazione riporta esattamente quell'anno in log. Il buffer è circolare
        (tronca a `max_messages`) e lo scroll resta ancorato in fondo se
        `auto_scroll` è attivo."""
        self.original_stdout.write(msg)
        text = str(msg).strip()
        if text:
            text = text.replace("\033[93;1m", "").replace("\033[0m", "")
            for line in text.split('\n'):
                line = line.strip()
                if line:
                    if hasattr(self, 'current_sim_time') and self.current_sim_time is not None:
                        time_str = f"[{format_time(self.current_sim_time)}] "
                        # Evita il doppio prefisso se già aggiunto manualmente
                        if not line.startswith("[TIME:"):
                            line = time_str + line
                    self.messages.append({"text": line, "time": time.time()})
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages:]
            if self.auto_scroll:
                self.scroll_y = 999999

    def get_msg_color(self, text):
        """Colora ogni riga per parole chiave nel testo, non per una categoria
        esplicita passata dal chiamante: l'ordine dei controlli è significativo,
        il secondo blocco (warning/collisione, GC, radar) sovrascrive il primo,
        così un log di collisione resta rosso anche se contenesse anche "DESTROYED"."""
        text_up = text.upper()
        color = UITheme.COLOR_WHITE
        
        if "ACTUAL SIMULATION DT" in text_up or "ACTUAL DT" in text_up:
            color = UITheme.STAR_PROBE
        elif "REAME RELATIVISTICO" in text_up or "DEEP SPACE" in text_up or "RELATIVISTIC" in text_up:
            color = UITheme.FLUO_RELATIVISTIC
        elif "DESTROYED" in text_up or "ABSORBED" in text_up or "MORT" in text_up or "DYING" in text_up:
            color = UITheme.FLUO_DEATH
        elif "SONDA" in text_up or "PROBE" in text_up or "TITLE" in text_up or ("[" in text_up and "]" in text_up and "TIME" not in text_up):
            color = UITheme.STAR_PROBE
            
        if "🚨" in text_up or "WARNING" in text_up or "COLLISION" in text_up:
            color = UITheme.DANGER
        elif "GC" in text_up:
            color = UITheme.SUCCESS
        elif "RADAR" in text_up:
            color = UITheme.STAR_PROBE
            
        return color

    def flush(self):
        self.original_stdout.flush()

    def handle_event(self, event, width):
        """Due modalità: collassata (un'intestazione cliccabile in alto a destra) ed
        espansa (pannello scrollabile al 90% della finestra). Lo scroll manuale
        disattiva `auto_scroll`; riattivarlo richiede di scrollare fino in fondo,
        non un semplice tasto, così la vista non salta via da sotto l'utente mentre
        legge un log vecchio anche se ne arrivano di nuovi."""
        screen = pygame.display.get_surface()
        win_w, win_h = screen.get_size() if screen else (1280, 720)
        
        if not self.expanded:
            header_rect = pygame.Rect(width - 150, 10, 140, 25)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if header_rect.collidepoint(event.pos):
                    self.expanded = True
                    self.scroll_y = 999999
                    self.auto_scroll = True
                    return True
        else:
            w = int(win_w * 0.9)
            h = int(win_h * 0.9)
            x = (win_w - w) // 2
            y = (win_h - h) // 2
            header_rect = pygame.Rect(x, y, w, 25)
            bg_rect = pygame.Rect(x, y, w, h)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and header_rect.collidepoint(event.pos):
                    self.expanded = False
                    return True
                elif event.button in (4, 5) and bg_rect.collidepoint(event.pos):
                    if event.button == 4:
                        self.scroll_y -= 40
                        self.auto_scroll = False
                    elif event.button == 5:
                        self.scroll_y += 40
                        padding_top = 5
                        padding_bottom = 10
                        content_h = len(self.messages) * 16 + padding_top + padding_bottom
                        view_h = h - 25
                        max_scroll = max(0, content_h - view_h)
                        if self.scroll_y >= max_scroll:
                            self.auto_scroll = True
                    return True
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if bg_rect.collidepoint((mx, my)):
                    self.scroll_y -= event.y * 40
                    if event.y > 0:
                        self.auto_scroll = False
                    elif event.y < 0:
                        padding_top = 5
                        padding_bottom = 10
                        content_h = len(self.messages) * 16 + padding_top + padding_bottom
                        view_h = h - 25
                        max_scroll = max(0, content_h - view_h)
                        if self.scroll_y >= max_scroll:
                            self.auto_scroll = True
                    return True
        return False
        
    def draw(self, screen, font, width):
        win_w, win_h = screen.get_size()
        
        if not self.expanded:
            # Riquadro [+] Event log e possibilmente ultimo massaggio
            header_rect = pygame.Rect(width - 150, 10, 140, 25)
            surf_h = UITheme.get_alpha_surface(140, 25, UITheme.MENU_HOVER_BG, 150)
            screen.blit(surf_h, (width - 150, 10))
            pygame.draw.rect(screen, (100, 100, 100), header_rect, 1, border_radius=2)
            txt = font.render("[+] Event Log", True, UITheme.TEXT_SECONDARY)
            screen.blit(txt, (width - 140, 15))

            # Notifica del messaggio più recente a dissolvenza
            if self.messages:
                last_msg = self.messages[-1]
                age = time.time() - last_msg["time"]
                fade_duration = 5.0  # seconds
                if age < fade_duration:
                    alpha = int(255 * (1.0 - (age / fade_duration)))
                    preview_txt = str(last_msg["text"])
                    # Limita lunghezza per non uscire dallo schermo
                    if len(preview_txt) > 80:
                        preview_txt = preview_txt[:77] + "..."
                    
                    preview_color = self.get_msg_color(preview_txt)
                    msg_surf = font.render(preview_txt, True, preview_color)
                    msg_surf.set_alpha(alpha)
                    # Disegna alla sinistra dell'intestazione
                    msg_x = width - 155 - msg_surf.get_width()
                    screen.blit(msg_surf, (msg_x, 15))

            return
            
        w = int(win_w * 0.9)
        h = int(win_h * 0.9)
        x = (win_w - w) // 2
        y = (win_h - h) // 2
        
        bg_rect = pygame.Rect(x, y, w, h)
        surf = UITheme.get_alpha_surface(w, h, (10, 10, 10), 240)
        screen.blit(surf, (x, y))
        pygame.draw.rect(screen, (100, 100, 100), bg_rect, 1, border_radius=2)
        
        header_rect = pygame.Rect(x, y, w, 25)
        surf_h = UITheme.get_alpha_surface(w, 25, UITheme.MENU_SELECTED_BG, 200)
        screen.blit(surf_h, (x, y))
        pygame.draw.rect(screen, UITheme.TEXT_DIMMED, header_rect, 1, border_radius=2)
        txt = font.render("[-] System Messages Log (Scroll to View)", True, UITheme.COLOR_WHITE)
        screen.blit(txt, (x + 10, y + 5))
        
        padding_top = 5
        padding_bottom = 10
        content_h = len(self.messages) * 16 + padding_top + padding_bottom
        view_h = h - 25
        max_scroll = max(0, content_h - view_h)
        self.scroll_y = max(0, min(self.scroll_y, max_scroll))
        
        clip_rect = pygame.Rect(x, y + 25, w, view_h)
        original_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        
        msg_y = y + 25 + padding_top - self.scroll_y
        for msg in self.messages:
            if msg_y + 16 > y + 25 and msg_y < y + 25 + view_h:
                color = self.get_msg_color(msg["text"])
                    
                txt_surf = font.render(msg["text"], True, color)
                screen.blit(txt_surf, (x + 10, int(msg_y)))
            msg_y += 16
            
        screen.set_clip(original_clip)
        
        if max_scroll > 0:
            thumb_h = max(20, view_h * (view_h / content_h))
            thumb_y = y + 25 + (self.scroll_y / max_scroll) * (view_h - thumb_h)
            sb_rect = pygame.Rect(x + w - 12, int(thumb_y), 8, int(thumb_h))
            pygame.draw.rect(screen, (150, 150, 150), sb_rect, border_radius=4)

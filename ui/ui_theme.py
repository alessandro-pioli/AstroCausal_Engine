import pygame

class UITheme:
    # --- PALETTE COLORI (RGBA/RGB) ---
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLACK = (0, 0, 0)
    COLOR_BLUE = (50, 150, 255)
    
    # Colori Testo Base
    TEXT_PRIMARY = (240, 240, 240)       # Bianchino morbido per maggiore leggibilità rispetto al bianco puro
    TEXT_SECONDARY = (200, 200, 200)     # Grigio chiaro per testi meno rilevanti
    TEXT_DIMMED = (150, 150, 150)        # Grigio scuro per dettagli secondari
    
    # Significati Semantici / Feedback
    SUCCESS = (100, 255, 100)            # Azioni corrette / Attivazioni
    WARNING = (255, 200, 0)              # Avvisi / Stato 3D / Ghost
    DANGER = (255, 50, 50)               # Errori / Uccisioni corporee
    INFO = (50, 200, 255)                # Notifiche neutre / Dati scentifici (es. Strain Ligo)
    
    # Deep/Fluo Highlights
    FLUO_RELATIVISTIC = (0, 255, 255)    # Ciano fluo per relatività
    FLUO_DEATH = (255, 50, 150)          # Rosa/Rosso fluo per morte/distruzione
    STAR_PROBE = (255, 255, 50)          # Giallo brillante per titoli/sonde
    
    # Highlight
    HIGHLIGHT_MAIN = (255, 204, 0)       # Giallo dorato per titoli HUD o Main Popups
    
    # --- SFONDI DEI RIQUADRI INTERFACCIA ---
    # Colori pieni (poi Pygame userà set_alpha())
    BG_DARK = (15, 15, 20)               # Usato spesso per Console, Overlay, popup standard
    BG_POPUP = (20, 20, 25)              # Appena più luminoso per staccare dallo sfondo
    BG_HUD = (10, 15, 20)                # Sfondo per le statistiche in alto a sinistra
    
    # Livelli di Trasparenza (Alpha 0-255)
    ALPHA_OVERLAY = 100                  # Per lo sfondo scurento dei menu (modale)
    ALPHA_CONSOLE = 180                  # Console deve restare leggibile senza coprire
    ALPHA_HUD = 200                      # HUD un pelo più marcato per il testo piccolo
    ALPHA_POPUP = 230                    # I menu/popup quasi coprenti
    
    # --- BORDI E ACCENTI ---
    BORDER_DEFAULT = (80, 80, 150)       # Violaceo/Bluastro sci-fi tenue per HUD
    BORDER_HOVER = (150, 150, 255)       # Molto luminoso per selezione UI
    BORDER_SELECTED = (200, 200, 255)

    # --- ELEMENTI INTERATTIVI ---
    MENU_HOVER_BG = (40, 40, 40)
    MENU_SELECTED_BG = (60, 60, 60)
    
    @classmethod
    def get_alpha_surface(cls, width, height, color, alpha):
        """Metodo di utilità per non ripetere .set_alpha() 1000 volte nei draw"""
        surf = pygame.Surface((width, height))
        surf.fill(color)
        surf.set_alpha(alpha)
        return surf

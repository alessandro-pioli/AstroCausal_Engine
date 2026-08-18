import pygame
from typing import Callable, Dict, List

class EventHandler:
    """
    Gestore di eventi per Pygame.
    Permette di registrare funzioni di callback per tipi di eventi specifici,
    mantenendo il ciclo principale pulito e modulare.
    """
    def __init__(self):
        # Dizionario che mappa un tipo di evento (es. pygame.QUIT) 
        # a una lista di funzioni da chiamare.
        self._callbacks: Dict[int, List[Callable[[pygame.event.Event], None]]] = {}
        # Lista di callback globali (interceptors) che elaborano ogni evento
        self._interceptors: List[Callable[[pygame.event.Event], bool]] = []

    def add_interceptor(self, callback: Callable[[pygame.event.Event], bool]) -> None:
        """
        Aggiunge un interceptor che riceverà tutti gli eventi.
        Se l'interceptor restituisce True, l'evento viene considerato "consumato"
        e non verrà propagato agli altri interceptor o alle callback specifiche.
        """
        if callback not in self._interceptors:
            self._interceptors.append(callback)

    def remove_interceptor(self, callback: Callable[[pygame.event.Event], bool]) -> None: # AL MOMENTO NON IN USO
        if callback in self._interceptors:
            self._interceptors.remove(callback)

    def register(self, event_type: int, callback: Callable[[pygame.event.Event], None]) -> None:
        """
        Registra una funzione callback per un determinato tipo di evento.
        
        :param event_type: Il tipo di evento Pygame (es. pygame.KEYDOWN)
        :param callback: La funzione da eseguire. Deve accettare l'oggetto evento come parametro.
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        if callback not in self._callbacks[event_type]:
            self._callbacks[event_type].append(callback)

    def unregister(self, event_type: int, callback: Callable[[pygame.event.Event], None]) -> None: # AL MOMENTO NON IN USO
        """
        Rimuove una funzione callback per un determinato tipo di evento.
        """
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            if not self._callbacks[event_type]:
                del self._callbacks[event_type]

    def handle_events(self) -> None:
        """Elabora e smista la coda degli eventi di Pygame."""
        for event in pygame.event.get():
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                if hasattr(event, 'key'):
                    # Mappa i tasti del tastierino numerico ai tasti numerici standard
                    numpad_map = {
                        pygame.K_KP0: pygame.K_0,
                        pygame.K_KP1: pygame.K_1,
                        pygame.K_KP2: pygame.K_2,
                        pygame.K_KP3: pygame.K_3,
                        pygame.K_KP4: pygame.K_4,
                        pygame.K_KP5: pygame.K_5,
                        pygame.K_KP6: pygame.K_6,
                        pygame.K_KP7: pygame.K_7,
                        pygame.K_KP8: pygame.K_8,
                        pygame.K_KP9: pygame.K_9,
                    }
                    if event.key in numpad_map:
                        event.key = numpad_map[event.key]
            
            consumed = False
            # 1. Passa l'evento agli interceptors
            for interceptor in self._interceptors:
                if interceptor(event):
                    consumed = True
                    break
            
            if consumed:
                continue

            # 2. Se non consumato, esegui le callback specifiche per tipo
            if event.type in self._callbacks:
                for callback in self._callbacks[event.type]:
                    callback(event)


# ESEMPIO DI UTILIZZO
if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Test Event Handler")

    # Istanziamo il nostro event handler
    event_handler = EventHandler()

    # Variabile di controllo per il loop
    running = True

    # Definiamo alcune funzioni di callback
    def quit_game(event):
        global running
        print("Simulation ended...")
        running = False

    def handle_keys(event):
        if event.key == pygame.K_ESCAPE:
            print("ESC pressed, exiting...")
            global running
            running = False
        elif event.key == pygame.K_SPACE:
            print("SPACE pressed!")

    def handle_mouse_click(event):
        print(f"Mouse click at position: {event.pos}")

    # Registriamo le callback assegnandole ai tipi di evento di Pygame
    event_handler.register(pygame.QUIT, quit_game)
    event_handler.register(pygame.KEYDOWN, handle_keys)
    event_handler.register(pygame.MOUSEBUTTONDOWN, handle_mouse_click)

    # Main Loop
    clock = pygame.time.Clock()
    while running:
        # Usa l'event handler al posto del classico for event in pygame.event.get()
        event_handler.handle_events()

        screen.fill((30, 30, 30))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

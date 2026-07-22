import numpy as np
import core.data as data
from utils.formatting import format_time

class DeathTracker:
    def __init__(self):
        self.logged_deaths = set()

    def check_deaths(self, bodies, current_sim_time):
        """Stampa un log d'impatto una sola volta per corpo, nella finestra tra la
        morte fisica (`FLAG_DYING` in testa) e l'estinzione causale (coda del buffer
        più profondo ancora non `VOID_VAL`): usa `logged_deaths` per non ripetere il
        log a ogni tick durante quella finestra, e lo ripulisce quando il corpo esce
        dal limbo (coda spenta, dominio del GC asincrono, o tornato vivo)."""
        for b in bodies:
            idx = b.idx
            
            # Testa (flaggato attualmente in memoria/kernel)
            head_dying = (data.FLAGS[idx] & 2) != 0
            
            # Coda (ultimo elemento del buffer più profondo)
            tail_is_void = False
            if data.HISTORY_L2 is not None and data.LEN_L2 > 0:
                tail_ptr = (data.HEADS_L2[idx] + 1) % data.LEN_L2
                if data.HISTORY_L2[idx, tail_ptr, 0] <= data.VOID_VAL * 0.9:
                    tail_is_void = True
            elif data.HISTORY_L1 is not None and data.LEN_L1 > 0:
                tail_ptr = (data.HEADS_L1[idx] + 1) % data.LEN_L1
                if data.HISTORY_L1[idx, tail_ptr, 0] <= data.VOID_VAL * 0.9:
                    tail_is_void = True
            elif data.HISTORY_L0 is not None and data.LEN_L0 > 0:
                tail_ptr = (data.HEADS_L0[idx] + 1) % data.LEN_L0
                if data.HISTORY_L0[idx, tail_ptr, 0] <= data.VOID_VAL * 0.9:
                    tail_is_void = True
            else:
                tail_is_void = True

            # Impatto Rilevato: Testa è morta, ma la coda ha ancora frammenti di causalità (ALIVE)
            if head_dying and not tail_is_void:
                if idx not in self.logged_deaths:
                    time_str = format_time(current_sim_time)
                    print(f"[IMPACT LOG] {time_str} -> {b.name} was destroyed or absorbed!")
                    self.logged_deaths.add(idx)
                    
            # Pulizia Set: se la coda è morta definitivamente o il corpo è tornato ALIVE (nato causalmente in espansione)
            if (not head_dying) or tail_is_void:
                if idx in self.logged_deaths:
                    self.logged_deaths.remove(idx)


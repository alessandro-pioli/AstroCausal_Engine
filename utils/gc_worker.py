import threading
import numpy as np
import core.data as data

class GCWorker:
    def __init__(self):
        """Collector asincrono dei corpi causalmente morti: pattern fire-and-forget,
        un thread daemon per scansione (mai un worker persistente), risultato scritto
        sotto lock e consumato dal main thread (§6 di ARCHITECTURE_DEEP_DIVE.md)."""
        self._thread = None
        self._pending_results = None
        self._lock = threading.Lock()
        
    def start_collection(self):
        """Lancia una nuova scansione, a meno che una precedente non sia ancora in
        corso: se lo scan dura più del periodo di trigger, la frequenza del GC
        scala automaticamente al ritmo che riesce a sostenere."""
        # Evita sovrapposizioni
        if self._thread is not None and self._thread.is_alive():
            return
            
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
    def _run(self):
        """Corpo dello scan, eseguito nel thread daemon: per ogni corpo `FLAG_DYING`
        controlla la coda del buffer storico più profondo disponibile (L2 se esiste,
        altrimenti L1, altrimenti L0). Se quella coda è ormai `VOID_VAL`, il fronte
        di vuoto ha spazzato l'intero orizzonte causale e il corpo può essere
        rimosso: nessun corpo nell'universo può più riceverne informazione
        gravitazionale."""
        # Controllo rapido per gli oggetti in fase di rimozione
        if not np.any(data.FLAGS[:data.MAX_BODIES] & 2):
            return
            
        dead_indices = []
        for idx in range(data.MAX_BODIES):
            if (data.FLAGS[idx] & 2) != 0:
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
                    tail_is_void = True # Ripristino (fallback) se lo storico non esiste

                if tail_is_void:
                    dead_indices.append(idx)
                
        if dead_indices:
            with self._lock:
                self._pending_results = dead_indices

    def get_and_clear_results(self):
        """Consuma il risultato dell'ultimo scan completato (`None` se ancora in
        corso o se non ha trovato morti causali), azzerandolo per non riconsumarlo."""
        with self._lock:
            res = self._pending_results
            self._pending_results = None
            return res

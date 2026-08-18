import numpy as np
import core.data as data
import time
import os

class SpaceProbeController:
    """
    Telecomando per l'unica Sonda LIGO dell'universo (Singleton).
    Non 'crea' nulla in RAM, gestisce solo gli array pre-allocati in data.py.
    """
    def __init__(self):
        """Non possiede dati (tutti vivono in data.py, §7 di ARCHITECTURE_DEEP_DIVE.md):
        si limita a garantire che all'avvio la sonda sia parcheggiata a VOID_VAL, così
        nessun calcolo accidentale produce strain spurio prima della prima attivazione."""
        # All'avvio del programma, ci assicuriamo che la sonda sia disattiva e nel VOID
        if not data.PROBE_ACTIVE[0]:
            data.PROBE_POS[:] = data.VOID_VAL

    def activate_at(self, position):
        """Accende la sonda e la teletrasporta alle coordinate richieste."""
        data.PROBE_POS[:] = np.array(position[:2], dtype=np.float64)
        data.PROBE_ACTIVE[0] = True
        self.clear_buffer()
        print(f"[LIGO] Probe activated at coordinates {position}")

    def deactivate(self):
        """Spegne la sonda e la spedisce nel VOID geometrico per sicurezza."""
        data.PROBE_ACTIVE[0] = False
        data.PROBE_POS[:] = data.VOID_VAL
        print("[LIGO] Probe deactivated (sent to the VOID).")

    def clear_buffer(self):
        """Pulisce la memoria e azzera la testina."""
        data.PROBE_BUFFER.fill(0.0)
        data.PROBE_HEAD[0] = 0

    @property
    def pos(self): 
        return data.PROBE_POS
    
    @property
    def active(self): 
        return data.PROBE_ACTIVE[0]
    
    @property
    def current_fs(self): 
        """Frequenza di campionamento (Hz) per SciPy."""
        return 1.0 / data.DT
    
    def get_current_strain(self):
        """Legge l'ultimissimo valore DPHI registrato per l'HUD."""
        if not self.active: return 0.0
        idx = (data.PROBE_HEAD[0] - 1) & data.PROBE_MASK
        return data.PROBE_BUFFER[idx]

    def dump_session(self, filename="ligo_dump", dt_used=0.0):
        """
        Estrae l'array circolare nell'ordine temporale corretto e lo salva.
        """
        if not self.active: return
        
        # 1. Copiamo i dati grezzi e l'head
        head = data.PROBE_HEAD[0]
        raw_buffer = np.copy(data.PROBE_BUFFER)
        
        # 2. Srotoliamo l'array circolare
        ordered_data = np.roll(raw_buffer, -head)
        
        # Aggiungiamo l'orario (in secondi) per non sovrascrivere mai i vecchi log
        timestamp = int(time.time())
        os.makedirs(os.path.join("ligo_output", "data_npy"), exist_ok=True)
        final_filename = os.path.join("ligo_output", "data_npy", f"{filename}_DT_{dt_used}_{timestamp}.npy")
        
        # 3. Salvataggio sincrono (Evita file da 0KB se l'app si chiude)
        try:
            np.save(final_filename, ordered_data)
            print(f"[LIGO PROBE] Data saved successfully to {final_filename}")
        except Exception as e:
            print(f"[LIGO PROBE] Save error: {e}")

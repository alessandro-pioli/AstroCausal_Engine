import numpy as np
from core import data  


class CelestialBody:
    def __init__(self, index, mass, position, velocity,  radius=6371.0, color=(255, 255, 255), artificial_engine = [0.0 , 0.0], pre_existed=False , name = ""):
        """
        Interfaccia Python per manipolare i dati nel Kernel Numba.
        Adattata per il Multi-Buffer System (L0, L1, L2).
        """
        self.idx = int(index)
        data.ensure_capacity(self.idx + 1)
        self.color = color
        if name == "":
            self.name = f"Celestial body n. {self.idx}"
        else:
            self.name = name
        # 1. SCRITTURA DATI STATICI
        data.MASS[self.idx] = float(mass)
        data.RAD[self.idx]  = float(radius)
        
        # Scrittura vettori (Numpy copy)
        data.POS[self.idx] = np.array(position[:2], dtype=np.float64)
        data.VEL[self.idx] = np.array(velocity[:2], dtype=np.float64)
        data.ART[self.idx] = np.array(artificial_engine[:2], dtype=np.float64)
        data.ACC[self.idx].fill(0.0)

        
        # 2. LOGICA FLAGS
        # Bit 0 (valore 1): ALIVE
        # Iniziamo come VIVO (1)
        data.FLAGS[self.idx] = data.FLAG_ALIVE 
        
        # 3. RESET TESTINE SCRITTURA (Tutte quelle che esistono)
        # Non importa se L1/L2 non sono usati (array vuoti o None), resettiamo tutto per sicurezza
        data.HEADS_L0[self.idx] = 0
        data.HEADS_L1[self.idx] = 0
        data.HEADS_L2[self.idx] = 0
        
        # 4. INIZIALIZZAZIONE CAUSALITÀ (Multi-Level)
        self._initialize_history(pre_existed)

    def _initialize_history(self, pre_existed):
        """
        Riempie i buffer storici (L0, L1, L2) se allocati.
        Gestisce la dilatazione temporale per i livelli compressi.
        """
        pos_now = data.POS[self.idx]
        vel_now = data.VEL[self.idx]
        my_mass = data.MASS[self.idx]
        
        # --- LIVELLO 0 (Alta risoluzione, DT) ---
        if data.HISTORY_L0 is not None:
            self._fill_buffer(data.HISTORY_L0, data.LEN_L0, pos_now, vel_now, my_mass, pre_existed, time_stride=1)

        # --- LIVELLO 1 (Media risoluzione, DT * 32) ---
        if data.HISTORY_L1 is not None:
            self._fill_buffer(data.HISTORY_L1, data.LEN_L1, pos_now, vel_now, my_mass, pre_existed, time_stride=32)

        # --- LIVELLO 2 (Bassa risoluzione, DT * 256) ---
        if data.HISTORY_L2 is not None:
            self._fill_buffer(data.HISTORY_L2, data.LEN_L2, pos_now, vel_now, my_mass, pre_existed, time_stride=256)

    def _fill_buffer(self, buffer_ref, length, pos_now, vel_now, my_mass, pre_existed, time_stride):
        """
        Helper function per riempire un singolo buffer specifico.
        time_stride: 1 per L0, 32 per L1, 256 per L2.
        """
        if pre_existed:
            # CASO ETERNO: Proiettiamo il passato linearmente
            effective_dt = data.DT * time_stride
            
            # 1. Creiamo gli indici dell'array [0, 1, 2, ... N]
            indices = np.arange(length, dtype=np.float64)
            
            # 2. MAPPING FONDAMENTALE (Indice -> Ritardo)
            # Il kernel legge: idx = (head - delay) & mask
            # Con head=0 -> idx = (-delay) % length
            # Quindi il ritardo associato a un indice 'i' è: delay = (length - i) % length
            # Esempio su len=8:
            # Index 0 -> Delay 0 (Presente)
            # Index 1 -> Delay 7 (Passato remoto)
            # Index 7 -> Delay 1 (Passato prossimo)
            delays_in_ticks = (length - indices) % length
            
            times = delays_in_ticks * effective_dt
            
            # Calcolo retroattivo vettorizzato: Pos_past = Pos_now - V * t
            past_x = pos_now[0] - (vel_now[0] * times)
            past_y = pos_now[1] - (vel_now[1] * times)
            
            # Scrittura
            buffer_ref[self.idx, :, 0] = past_x
            buffer_ref[self.idx, :, 1] = past_y
            buffer_ref[self.idx, :, 2] = vel_now[0]
            buffer_ref[self.idx, :, 3] = vel_now[1]
            buffer_ref[self.idx, :, 4] = my_mass 
            
        else:
            # CASO SHOCKWAVE: Tutto il passato è Vuoto (VOID_VAL)
            buffer_ref[self.idx, :, :].fill(data.VOID_VAL)
            
            # Tranne il presente (indice 0) che è l'unica cosa vera
            buffer_ref[self.idx, 0, 0] = pos_now[0]
            buffer_ref[self.idx, 0, 1] = pos_now[1]
            buffer_ref[self.idx, 0, 2] = vel_now[0]
            buffer_ref[self.idx, 0, 3] = vel_now[1]
            buffer_ref[self.idx, 0, 4] = my_mass 

    def set_dying(self):
        """Attiva la morte causale tramite bitmask."""
        data.FLAGS[self.idx] |= data.FLAG_DYING 
        data.ACC[self.idx, 0] = 0.0
        data.ACC[self.idx, 1] = 0.0


    # --- PROPERTIES ---
    @property
    def mass(self): return data.MASS[self.idx]
    
    @property
    def radius(self): return data.RAD[self.idx]

    @property
    def pos(self): return data.POS[self.idx]
    
    @property
    def vel(self): return data.VEL[self.idx]
    
    @property
    def acc(self): return data.ACC[self.idx]

    @property
    def art(self): return data.ART[self.idx]

    @property
    def active(self): return bool(data.FLAGS[self.idx] & data.FLAG_ALIVE)

    @property
    def is_causally_dead(self):
        """
        Controlla se il veleno VOID_VAL ha riempito tutto il buffer PIÙ PROFONDO.
        Se L2 esiste, controlliamo quello. Se no L1, se no L0.
        """
        # Selezioniamo il buffer più "vecchio" disponibile
        target_buffer = None
        
        if data.HISTORY_L2 is not None:
            target_buffer = data.HISTORY_L2
        elif data.HISTORY_L1 is not None:
            target_buffer = data.HISTORY_L1
        else:
            target_buffer = data.HISTORY_L0
            
        # Se siamo morti, dobbiamo controllare se TUTTO il buffer è diventato VOID.
        # Check veloce: basta controllare la coordinata X <= soglia
        return np.all(target_buffer[self.idx, :, 0] <= (data.VOID_VAL * 0.9))
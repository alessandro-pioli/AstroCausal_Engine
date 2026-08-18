from core import data
class Engine:
    """Motore di calcolo che coordina l'esecuzione dei kernel fisici Numba."""
    
    def __init__(self, celestial_bodies):
        """
        Inizializza l'Engine delegando il calcolo pesante ai kernel Numba.
        """
        self.bodies = celestial_bodies
        self.sim_time = 0.0
        
        self._kernel_module = None
        self.tick = None
        
        # Configurazione iniziale della pipeline
        self.refresh_kernel()

    def refresh_kernel(self):
        """
        Rilegge data.METHOD e riconfigura la pipeline di calcolo.
        Da chiamare ogni volta che SimulationManager cambia architettura o DT.
        """
        # Recuperiamo il verdetto fresco da data.py
        current_method = data.METHOD
        check = data.MAX_BODIES >= 35 # Dato ideale di Switch ricavato empiricamente (calibrato un un i5 13400f)
        print(f"[ENGINE] Kernel refresh requested. New active method: {current_method}")

        if current_method == "SINGLE":
            # Caso Base: Buffer singolo (L0)
            from core.jit_kernels import kernel_single 
            self._kernel_module = kernel_single
            if check:
                self.tick = self._tick_single_wrapper_par
            else:
                self.tick = self._tick_single_wrapper_seq
            
        elif current_method == "DOUBLE":
            # Caso Intermedio: Buffer doppio (L0 + L1)
            from core.jit_kernels import kernel_double
            self._kernel_module = kernel_double
            if check:
                self.tick = self._tick_double_wrapper_par
            else: 
                self.tick = self._tick_double_wrapper_seq
            
        elif current_method == "TRIPLE":
            # Caso Avanzato: Buffer triplo (L0 + L1 + L2)
            from core.jit_kernels import kernel_triple
            self._kernel_module = kernel_triple
            if check:
                self.tick = self._tick_triple_wrapper_par
            else:
                self.tick = self._tick_triple_wrapper_seq             
        else:
            raise ValueError(f"[FATAL] Metodo memoria sconosciuto: {current_method}")

    # --- WRAPPERS SPECIFICI (ADAPTERS) ---
    # Adattano i dati globali di 'data' alla firma specifica del kernel.
    # Usano data.DT per garantire che la velocità sia quella attuale (Live).

    def _tick_single_wrapper_par(self, steps):
        """Wrapper per il Single Buffer (L0 fa tutto) in parallelo."""
        num_active = 0
        for i in range(data.MAX_BODIES):
            f = data.FLAGS[i]
            if (f & 1) != 0:
                data.PHYS_ACTIVE_INDICES[num_active] = i
                num_active += 1

        self._kernel_module.update_step_single_par(
            data.MAX_BODIES, data.POS, data.VEL, data.ACC, 
            data.MASS, data.RAD, data.FLAGS,

            data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,

            data.TRAIL_BUFFER, data.TRAIL_HEADS, data.TRAIL_LAST_POS, 
            
            # --- INIEZIONE SONDA LIGO ---
            data.PROBE_BUFFER, data.PROBE_HEAD, data.PROBE_POS, data.PROBE_ACTIVE, data.PROBE_MASK,
            
            data.DT, data.G, data.INV_C, data.INV_C_DT, data.C_SQ, data.RS_FACTOR, data.THRESHOLD_SOLVER_SQ, data.VOID_VAL,
            steps, data.PHYS_ACTIVE_INDICES, num_active, data.ART, data.M_CHIRP_MULT[0], self.sim_time, data.COLLISION_COOLDOWN   
        )
        self.sim_time += data.DT * steps

    def _tick_single_wrapper_seq(self, steps):
        """Wrapper per il Single Buffer (L0 fa tutto) in sequenziale."""
        num_active = 0
        for i in range(data.MAX_BODIES):
            f = data.FLAGS[i]
            if (f & 1) != 0:
                data.PHYS_ACTIVE_INDICES[num_active] = i
                num_active += 1

        self._kernel_module.update_step_single_seq(
            data.MAX_BODIES, data.POS, data.VEL, data.ACC, 
            data.MASS, data.RAD, data.FLAGS,

            data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,

            data.TRAIL_BUFFER, data.TRAIL_HEADS, data.TRAIL_LAST_POS,
            
            # --- INIEZIONE SONDA LIGO ---
            data.PROBE_BUFFER, data.PROBE_HEAD, data.PROBE_POS, data.PROBE_ACTIVE, data.PROBE_MASK,
            
            data.DT, data.G, data.INV_C, data.INV_C_DT, data.C_SQ, data.RS_FACTOR, data.THRESHOLD_SOLVER_SQ, data.VOID_VAL,
            steps, data.PHYS_ACTIVE_INDICES, num_active, data.ART, data.M_CHIRP_MULT[0], self.sim_time, data.COLLISION_COOLDOWN  
        )
        self.sim_time += data.DT * steps

    def _tick_double_wrapper_par(self, steps):
        """Wrapper per il Double Buffer (L0 + L1) in parallelo."""
        num_active = 0
        for i in range(data.MAX_BODIES):
            f = data.FLAGS[i]
            if (f & 1) != 0:
                data.PHYS_ACTIVE_INDICES[num_active] = i
                num_active += 1

        self._kernel_module.update_step_double_par(
            data.MAX_BODIES, data.POS, data.VEL, data.ACC, 
            data.MASS, data.RAD, data.FLAGS,
            
            # Gruppo L0
            data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
            
            # Gruppo L1
            data.HISTORY_L1, data.HEADS_L1, data.MASK_L1, data.LEN_L1,
            
            data.TRAIL_BUFFER, data.TRAIL_HEADS, data.TRAIL_LAST_POS,
            
            # --- INIEZIONE SONDA LIGO ---
            data.PROBE_BUFFER, data.PROBE_HEAD, data.PROBE_POS, data.PROBE_ACTIVE, data.PROBE_MASK,
            
            data.DT, data.G, data.INV_C, data.INV_C_DT, data.C_SQ, data.RS_FACTOR, data.THRESHOLD_SOLVER_SQ, data.VOID_VAL,
            steps, data.PHYS_ACTIVE_INDICES, num_active, data.ART, data.M_CHIRP_MULT[0], self.sim_time, data.COLLISION_COOLDOWN       
        )
        self.sim_time += data.DT * steps

    def _tick_double_wrapper_seq(self, steps):
        """Wrapper per il Double Buffer (L0 + L1) in sequenziale."""
        num_active = 0
        for i in range(data.MAX_BODIES):
            f = data.FLAGS[i]
            if (f & 1) != 0:
                data.PHYS_ACTIVE_INDICES[num_active] = i
                num_active += 1

        self._kernel_module.update_step_double_seq(
            data.MAX_BODIES, data.POS, data.VEL, data.ACC, 
            data.MASS, data.RAD, data.FLAGS,
            
            # Gruppo L0
            data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
            
            # Gruppo L1
            data.HISTORY_L1, data.HEADS_L1, data.MASK_L1, data.LEN_L1,
            
            data.TRAIL_BUFFER, data.TRAIL_HEADS, data.TRAIL_LAST_POS,
            
            # --- INIEZIONE SONDA LIGO ---
            data.PROBE_BUFFER, data.PROBE_HEAD, data.PROBE_POS, data.PROBE_ACTIVE, data.PROBE_MASK,
            
            data.DT, data.G, data.INV_C, data.INV_C_DT, data.C_SQ, data.RS_FACTOR, data.THRESHOLD_SOLVER_SQ, data.VOID_VAL,
            steps, data.PHYS_ACTIVE_INDICES, num_active, data.ART, data.M_CHIRP_MULT[0], self.sim_time, data.COLLISION_COOLDOWN        
        )
        self.sim_time += data.DT * steps

    def _tick_triple_wrapper_par(self, steps):
        """Wrapper per il Triple Buffer (L0 + L1 + L2) in parallelo."""
        num_active = 0
        for i in range(data.MAX_BODIES):
            f = data.FLAGS[i]
            if (f & 1) != 0:
                data.PHYS_ACTIVE_INDICES[num_active] = i
                num_active += 1

        self._kernel_module.update_step_triple_par(
            data.MAX_BODIES, data.POS, data.VEL, data.ACC, 
            data.MASS, data.RAD, data.FLAGS,
            # Gruppo L0
            data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
            # Gruppo L1
            data.HISTORY_L1, data.HEADS_L1, data.MASK_L1, data.LEN_L1,
            # Gruppo L2
            data.HISTORY_L2, data.HEADS_L2, data.MASK_L2, data.LEN_L2,
            
            data.TRAIL_BUFFER, data.TRAIL_HEADS, data.TRAIL_LAST_POS,
            # --- INIEZIONE SONDA LIGO ---
            data.PROBE_BUFFER, data.PROBE_HEAD, data.PROBE_POS, data.PROBE_ACTIVE, data.PROBE_MASK,

            data.DT, data.G, data.INV_C, data.INV_C_DT, data.C_SQ, data.RS_FACTOR, data.THRESHOLD_SOLVER_SQ, data.VOID_VAL,
            steps, data.PHYS_ACTIVE_INDICES, num_active, data.ART, data.M_CHIRP_MULT[0], self.sim_time, data.COLLISION_COOLDOWN  
        )
        self.sim_time += data.DT * steps
    
    def _tick_triple_wrapper_seq(self, steps):
        """Wrapper per il Triple Buffer (L0 + L1 + L2) in sequenziale."""
        num_active = 0
        for i in range(data.MAX_BODIES):
            f = data.FLAGS[i]
            if (f & 1) != 0:
                data.PHYS_ACTIVE_INDICES[num_active] = i
                num_active += 1

        self._kernel_module.update_step_triple_seq(
            data.MAX_BODIES, data.POS, data.VEL, data.ACC, 
            data.MASS, data.RAD, data.FLAGS,    
            # Gruppo L0
            data.HISTORY_L0, data.HEADS_L0, data.MASK_L0, data.LEN_L0,
            # Gruppo L1
            data.HISTORY_L1, data.HEADS_L1, data.MASK_L1, data.LEN_L1,
            # Gruppo L2
            data.HISTORY_L2, data.HEADS_L2, data.MASK_L2, data.LEN_L2,
            
            data.TRAIL_BUFFER, data.TRAIL_HEADS, data.TRAIL_LAST_POS,
            # --- INIEZIONE SONDA LIGO ---
            data.PROBE_BUFFER, data.PROBE_HEAD, data.PROBE_POS, data.PROBE_ACTIVE, data.PROBE_MASK,
            
            data.DT, data.G, data.INV_C, data.INV_C_DT, data.C_SQ, data.RS_FACTOR, data.THRESHOLD_SOLVER_SQ, data.VOID_VAL,
            steps, data.PHYS_ACTIVE_INDICES, num_active, data.ART, data.M_CHIRP_MULT[0], self.sim_time, data.COLLISION_COOLDOWN   
        )
        self.sim_time += data.DT * steps

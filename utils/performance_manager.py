class PerformanceManager:
    def __init__(self):
        """Auto-tuner della risoluzione della heatmap: isteresi (soglie di discesa e
        salita diverse, §4 di ARCHITECTURE_DEEP_DIVE.md), streak di stabilità e
        cooldown prima di un upgrade, più una memoria per-configurazione che blocca
        un upgrade già fallito in passato con lo stesso carico."""
        self.FPS_LOW_LIMIT = 30   # Soglia di FPS minimi per l'adattamento della risoluzione
        self.FPS_HIGH_LIMIT = 58  # Soglia di FPS alti per incrementare la risoluzione
        self.COOLDOWN_MS = 5000
        
        self.stability_streak = 0
        self.last_downgrade_time = 0
        
        self.perf_memory = {}
        self.last_perf_body_count = 0
        
        self.last_res_check = 0
        
        self.gc_step_accumulator = 0
        self.GC_THRESHOLD = 1000000
        self.last_dt_auto_tune = None
        self.last_canceled_signature = None
    
    def update_auto_tuner(self, now, gstate, current_fps, current_body_count, resolution_div, speed_multiplier, current_dt):
        """Decide se cambiare `resolution_div`, girando ogni frame ma agendo raramente.
        Reset totale della memoria su cambio DT o numero di corpi (il carico è cambiato
        strutturalmente); tre view_mode (0, 3, 5) restano fuori dalla logica normale
        (OFF non ha griglia da scalare, Lagrange/Tidal sono forzati a div=1 per non
        perdere dettagli fini), Roche è cappato a div=2. Sotto FPS_LOW_LIMIT il
        downgrade è immediato; sopra FPS_HIGH_LIMIT serve una streak di 3 cicli oltre
        il cooldown, e anche allora la memoria può cancellare l'upgrade se quella
        stessa configurazione aveva già dato FPS bassi in passato."""
        if current_dt != self.last_dt_auto_tune:
            self.perf_memory.clear()
            self.last_dt_auto_tune = current_dt
            self.last_res_check = now
            return resolution_div, False
            
        if gstate.view_mode in (0, 3, 5):
            self.last_res_check = now
            if gstate.view_mode in (3, 5) and resolution_div != 1:
                return 1, True
            return resolution_div, False
            
        if now - self.last_res_check <= self.COOLDOWN_MS or gstate.resolution_mode != "AUTO":
            if gstate.view_mode == 4 and resolution_div > 2:
                return 2, True
            return resolution_div, False
            
        if current_body_count != self.last_perf_body_count:
            self.perf_memory.clear()
            self.last_perf_body_count = current_body_count
            
        self.perf_memory[(resolution_div, speed_multiplier, gstate.view_mode)] = current_fps
        new_div = resolution_div
        
        if current_fps < self.FPS_LOW_LIMIT:
            max_div = 2 if gstate.view_mode == 4 else 16
            new_div = min(max_div, resolution_div * 2)
            self.stability_streak = 0
            self.last_downgrade_time = now 
        elif current_fps > self.FPS_HIGH_LIMIT:
            time_since_downgrade = now - self.last_downgrade_time
            if resolution_div > 1 and time_since_downgrade > self.COOLDOWN_MS:
                self.stability_streak += 1
                if self.stability_streak >= 3:
                    target_div = max(1, int(resolution_div / 2))
                    mem_fps = self.perf_memory.get((target_div, speed_multiplier, gstate.view_mode), 999.0)
                    if mem_fps < self.FPS_LOW_LIMIT:
                        sig = (target_div, gstate.view_mode, float(f"{mem_fps:.1f}"))
                        if sig != self.last_canceled_signature:
                            print(f"[AUTO-TUNE] CANCELED upgrade to div={target_div} in mode={gstate.view_mode}. Past memory recorded {mem_fps:.1f} fps here.")
                            self.last_canceled_signature = sig
                        self.stability_streak = 0
                    else:
                        new_div = target_div
                        self.stability_streak = 0
                        self.last_canceled_signature = None
                        print(f"[AUTO-TUNE] Upgrade approved to div={target_div} in mode={gstate.view_mode}.")
            else:
                self.stability_streak = 0 
        else:
            self.stability_streak = 0

        self.last_res_check = now
        changed = (new_div != resolution_div)
        
        if gstate.view_mode == 4 and new_div > 2:
            new_div = 2
            changed = (new_div != resolution_div)
            
        if changed:
            print(f"[AUTO-GPU] FPS: {current_fps:.1f} -> Res change: 1/{resolution_div} -> 1/{new_div}")
            
        return new_div, changed


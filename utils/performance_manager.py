class PerformanceManager:
    def __init__(self):
        self.FPS_LOW_LIMIT = 30   # Sotto i 30 FPS l'esperienza degrada davvero: solo qui si scala marcia. Sopra resta fluido e si privilegia la risoluzione heatmap.
        self.FPS_HIGH_LIMIT = 58  # Vicino al cap di 60: c'e' headroom per alzare la risoluzione.
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
                        print(f"[AUTO-TUNE] Upgrade approvato verso div={target_div} in mode={gstate.view_mode}.")
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
            print(f"[AUTO-GPU] FPS: {current_fps:.1f} -> Cambio Res: 1/{resolution_div} -> 1/{new_div}")
            
        return new_div, changed


class UIState:
    def __init__(self):
        # App core references
        self.running = True
        self.screen = None
        
        # Managers & Global objects
        self.bodies = []
        self.engine = None
        self.renderer = None
        self.camera = None
        self.spawner = None
        self.gstate = None
        self.fader_dphi = None
        self.fader_roche = None
        self.fader_contrast = None
        self.game_console = None
        self.tutorial_manager = None
        self.perf_manager = None
        self.ligo_probe = None
        
        # Simple states
        self.locked_body_idx = None
        self.kill_target_idx = None
        self.kill_confirm_active = False
        self.ligo_confirm_active = False
        self.ligo_pending_pos = None
        self.lagrange_target_idx = -1
        self.lagrange_attr_idx = -1
        self.speed_multiplier = 1
        self.resolution_div = 2

# Singleton globale
ui_state = UIState()

import config

class GlobalState:
    def __init__(self):
        # Stati di tempo e simulazione
        self.paused = False
        self.simulation_running = True

        # Display/View Modes
        mode_map = {
            "off": 0,
            "phi_mode": 1,
            "dphi_dt_mode": 2,
            "tidal_mode": 5
        }
        self.view_mode = mode_map.get(config.STARTING_HEATMAP_MODE, 1)
        self.show_legend = False
        self.help_active = False
        self.hud_visible = True
        self.field_mode = "POTENTIAL"
        self.resolution_mode = "AUTO"
        
        # Mouse / Interaction
        self.mouse_dragging = False
        self.pan_active = False
        self.mouse_x = 0
        self.mouse_y = 0
        
        # Toggles
        self.show_paths = config.TRAILS_ENABLED
        self.show_text = True
        self.draw_lagrange = False
        self.draw_roche_orbit = False
        self.show_info_causality = True
        
        # Tracciamento dei tick (spostato da variabili locali in main)
        self.render_counter = 0

    def toggle_pause(self):
        self.paused = not self.paused
        
    def next_view_mode(self):
        self.view_mode = (self.view_mode + 1) % 4
        
    def toggle_legend(self):
        self.show_legend = not self.show_legend
        
    def toggle_help(self):
        self.help_active = not self.help_active

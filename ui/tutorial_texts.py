from ui.ui_theme import UITheme

def push_default_tutorials(manager):
    manager.enqueue(
        "🌌 ASTRO CAUSAL SIM: WELCOME 🌌",
        [
            "Welcome to the Hardcore N-Body Simulation Engine.",
            "",
            "MOUSEDOWN / DRAG : Pan across the universe.",
            "SCROLL WHEEL     : Zoom in and out.",
            "HINTS            : Observe events from macro or micro perspectives."
        ],
        UITheme.INFO
    )
    manager.enqueue(
        "⏱️ TIME & EXECUTION SPEED ⏱️",
        [
            "Simulation speed defines how fast time passes.",
            "",
            "Press keys [1] to [5] to change the speed multiplier.",
            "Higher multipliers execute more physics steps per render frame.",
        ],
        UITheme.HIGHLIGHT_MAIN
    )
    manager.enqueue(
        "⚛️ PRECISION & TIME-STEP (DT) ⚛️",
        [
            "Physical accuracy directly depends on the Integration Time-Step (DT).",
            "This engine uses a Verlet-based Integrator internally.",
            "",
            "Press [Y] to INCREASE DT: Runs faster, but fast bodies might 'cut corners',",
            "resulting in severe orbital drifts.",
            "Press [T] to DECREASE DT: Slower execution, but ensures absolute",
            "precision for tight orbits and close-encounters.",
        ],
        UITheme.DANGER
    )
    manager.enqueue(
        "🔧 BOTTLENECKS & PERFORMANCE 🔧",
        [
            "Physics calculations are heavy. If you experience low FPS:",
            "1. Lower the Speed Multiplier [1-5].",
            "2. To maintain the same fast-forward simulation time, you can",
            "   increase DT [Y] (if the scenario's orbits are stable enough).",
            "",
            "Finding the perfect balance between Speed and DT is the key",
            "to fluidly master this Causal Engine!"
        ],
        (255, 150, 50)
    )
    manager.enqueue(
        "🪐 GRAVITATIONAL FIELD MODES 🪐",
        [
            "Press [H] to cycle through GPU-accelerated field modes:",
            "",
            "0. OFF (Void / Trails mapping)",
            "1. PHI: Gravitational Potential Well Heatmap",
            "2. D-PHI: Space-Time Gradient (Gravitational Waves)",
            "5. TIDAL STRESS: Tidal spaghettification"
        ],
        (200, 100, 255)
    )
    manager.enqueue(
        "🔍 TELEMETRY, LOCKING & LOGS 🔍",
        [
            "DOUBLE-CLICK on any celestial body to lock the camera.",
            "This opens the Real-Time Telemetry HUD with physics vectors.",
            "",
            "You will also find a GAME CONSOLE in the top-right corner.",
            "Click its header [-] to expand or collapse system logs",
            "such as garbage collection rules or physical alerts."
        ],
        UITheme.SUCCESS
    )

def push_radar_warnings(manager):
    manager.enqueue(
        "🚨 RELATIVISTIC SYSTEM DETECTED 🚨",
        [
            "The system has detected an extreme gravitational interaction.",
            "Gravitational Waves (GW) generation is possible in this scenario.",
            "",
            "It is strongly recommended to observe this phenomenon",
            "in D-PHI mode. Press [H] to change visualization modes."
        ],
        UITheme.DANGER
    )
    manager.enqueue(
        "⚠️ PHOTOSENSITIVITY WARNING ⚠️",
        [
            "You can adjust the simulation speed using the keys [1-5].",
            "",
            "WARNING: At high velocities, the interference patterns",
            "created by gravitational waves will form highly strobing",
            "and psychedelic spiral patterns.",
            "Please be careful if you are sensitive to flashing lights!"
        ],
        UITheme.HIGHLIGHT_MAIN
    )
    manager.enqueue(
        "🛰️ REAL-TIME TELEMETRY 🛰️",
        [
            "Double-click on any body to TARGET it.",
            "",
            "This will open a real-time data HUD at the bottom.",
            "You can use this data (mass, velocity, local acceleration)",
            "and the distance to the dominant mass to gauge",
            "the precise moment of collision or merger."
        ],
        (50, 150, 255)
    )

def push_ligo_info(manager):
    manager.enqueue(
        "📡 LIGO PROBE PLACEMENT 📡",
        [
            "You are about to deploy a stationary LIGO Probe.",
            "",
            "It continuously records local gravitational strain and energy flux.",
            "",
            "Only extraordinary events like Neutron Star or Black Hole binary collapses",
            "generate macroscopic waves detectable by this probe.",
            "",
            "To consult the results, exit the simulation. A menu will appear",
            "to build the strain graph and spectrogram."
        ],
        UITheme.INFO
    )


from ui.ui_theme import UITheme

def push_default_tutorials(manager):
    manager.enqueue(
        " ESSENTIAL CONTROLS ",
        [
            "Welcome to AstroCausal Engine.",
            "",
            "Mouse Drag / WASD / Arrows : Pan the camera.",
            "Mouse Wheel / +/-          : Zoom in and out.",
            "[R]                        : Toggle body trails.",
            "Double-Click on a body     : Lock camera, open Telemetry HUD.",
            "Double-Click on empty space: Probe the field at that point.",
            "[TAB]                      : Cycle through active bodies.",
        ],
        UITheme.INFO
    )
    manager.enqueue(
        " SPEED & PRECISION ",
        [
            "[1] to [5] : Physics speed multiplier (more steps per frame).",
            "[T] / [Y]  : Halve / double the time-step (DT).",
            "",
            "Lower DT means more precision, at the cost of simulated speed.",
        ],
        UITheme.HIGHLIGHT_MAIN
    )
    manager.enqueue(
        " VISUALIZATION & TOOLS ",
        [
            "[H] : Cycle main heatmaps (Potential, dPhi/dt, Tidal Stress).",
            "[L] : Cycle paired heatmaps on a locked body",
            "      (Lagrange Hunter, Roche, GW Strain).",
            "[G] : Cycle heatmap resolution.",
            "[P] : Place or remove the LIGO probe.",
            "",
            "Press [F] anytime for the full key legend.",
        ],
        (200, 100, 255)
    )
    manager.enqueue(
        " CONSOLE & KEY STATS ",
        [
            "A log console lives in the top-right corner.",
            "Click its header [-] / [+] to collapse or expand it.",
            "",
            "Simulated time, DT, the speed multiplier and FOV",
            "stay pinned top-left at all times.",
        ],
        (100, 200, 255)
    )
    manager.enqueue(
        " LEARN MORE ",
        [
            "That covers the essentials to get moving.",
            "",
            "For heatmap physics and the full usage guide, see",
            "README.md and PHYSICS_AND_SCENARIO_GUIDE.md",
            "in the project folder.",
        ],
        UITheme.SUCCESS
    )

def push_radar_warnings(manager):
    manager.enqueue(
        " RELATIVISTIC SYSTEM DETECTED ",
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
        " PHOTOSENSITIVITY WARNING ",
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

def push_ligo_info(manager):
    manager.enqueue(
        " LIGO PROBE PLACEMENT ",
        [
            "You are about to deploy a stationary LIGO Probe.",
            "It records local gravitational strain, detectable mainly during",
            "Neutron Star or Black Hole binary collapses.",
            "",
            "Exit the simulation to analyze the recording (strain graph,",
            "spectrogram, chirp mass estimate) in the LIGO Analyzer.",
            "",
            "Full pipeline details in PHYSICS_AND_SCENARIO_GUIDE.md, §8.",
        ],
        UITheme.INFO
    )


import os
import configparser
from core.data import AU_IN_KM

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "astro_settings.ini")

parser = configparser.ConfigParser()

def create_default_config():
    """Crea o ripristina il file INI con commenti leggibili dall'utente."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write("; Per resettare ai valori predefiniti, eliminare il file prima dell'avvio\n")
        f.write("[Graphics]\n")
        f.write("; Attiva o disattiva le scie dei corpi (True/False)\n")
        f.write("trails_enabled = True\n\n")
        f.write("; Heatmap di partenza. Valori validi: off, phi_mode, dphi_dt_mode, tidal_mode\n")
        f.write("starting_heatmap_mode = phi_mode\n\n")
        f.write("; Sensibilita visiva della distorsione di Roche e contrasto globale\n")
        f.write("roche_sensitivity_mag = 0.0\n")
        f.write("roche_contrast = 15.0\n\n")
        f.write("; Offset manuale di sensibilita visiva dell'utente\n")
        f.write("user_sensitivity_mag = 0.0\n\n")
        f.write("; Framerate massimo di rendering\n")
        f.write("target_fps = 60\n\n")
        
        f.write("[Simulation]\n")
        f.write("; Raggio iniziale dell'universo simulato (in Unita Astronomiche)\n")
        f.write("; ATTENZIONE: Questo valore viene usato ESCLUSIVAMENTE per il preset 'Blank' (universo vuoto).\n")
        f.write("; Per gli altri preset, il raggio viene imposto automaticamente.\n")
        f.write("simulation_radius_au = 64.0\n")

# Auto-ripristino se il file non esiste
if not os.path.exists(CONFIG_FILE):
    create_default_config()

try:
    parser.read(CONFIG_FILE, encoding='utf-8')
    
    # Lettura parametri rigida: se manca qualcosa, va in eccezione e rigenera il file
    TRAILS_ENABLED = parser.getboolean("Graphics", "trails_enabled")
    STARTING_HEATMAP_MODE = parser.get("Graphics", "starting_heatmap_mode")
    ROCHE_SENSITIVITY_MAG = parser.getfloat("Graphics", "roche_sensitivity_mag")
    ROCHE_CONTRAST = parser.getfloat("Graphics", "roche_contrast")
    USER_SENSITIVITY_MAG = parser.getfloat("Graphics", "user_sensitivity_mag")
    TARGET_FPS = parser.getint("Graphics", "target_fps")
    
    SIMULATION_RADIUS_AU = parser.getfloat("Simulation", "simulation_radius_au")
    SIMULATION_RADIUS_KM = SIMULATION_RADIUS_AU * AU_IN_KM

except Exception as e:
    print(f"[CONFIG] Errore nella lettura di {CONFIG_FILE}: {e}. Ripristino impostazioni di fabbrica...")
    parser.clear()
    create_default_config()
    parser.read(CONFIG_FILE, encoding='utf-8')
    
    TRAILS_ENABLED = parser.getboolean("Graphics", "trails_enabled", fallback=True)
    STARTING_HEATMAP_MODE = parser.get("Graphics", "starting_heatmap_mode", fallback="phi_mode")
    ROCHE_SENSITIVITY_MAG = parser.getfloat("Graphics", "roche_sensitivity_mag", fallback=10.0)
    ROCHE_CONTRAST = parser.getfloat("Graphics", "roche_contrast", fallback=15.0)
    USER_SENSITIVITY_MAG = parser.getfloat("Graphics", "user_sensitivity_mag", fallback=0.0)
    TARGET_FPS = parser.getint("Graphics", "target_fps", fallback=60)
    
    SIMULATION_RADIUS_AU = parser.getfloat("Simulation", "simulation_radius_au", fallback=64.0)
    SIMULATION_RADIUS_KM = SIMULATION_RADIUS_AU * AU_IN_KM

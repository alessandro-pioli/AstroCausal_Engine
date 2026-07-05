from core.bodies import CelestialBody
from core.data import C_LIGHT, G, AU_IN_KM
import math
import random
import config

# COSTANTI
DEFAULT_DT = 1.0 
DEFAULT_RADIUS = 64 * AU_IN_KM
DEFAULT_STEP = 1

# COLOR PALETTE 
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 204, 0)
BLUE = (50, 150, 255)
RED = (255, 50, 50)


# =====================================================================
# --- Helper matematici orbitali ---
# =====================================================================

from utils.orbital_math import solve_pw_circular_velocity, solve_pair_circular_velocity, solve_velocity_from_apocenter, solve_velocity_from_pericenter, solve_escape_velocity

# =====================================================================
# =====================================================================


def get_preset(name="Sistema Solare Completo"):
    """
    WRAPPER (Factory).
    Seleziona lo scenario in base al nome stringa leggibile.
    Ritorna la tupla: (bodies, ideal_dt, ideal_sim_radius, ideal_step)
    """
    if name == "Sistema Solare Completo":
        return _make_solar_system()
    elif name == "Sistema Solare (Leggero)":
        return _make_solar_system_light()
    elif name == "Sistema Solare: Orbita Galattica (Sgr A*)":
        return _make_galactic_solar_system()
    elif name == "Ammasso Caotico (100 Corpi)":
        return _make_random_cluster(100)
    elif name == "Terra - Luna - ISS - Hubble":
        return _make_earth_moon_iss_hubble()
    elif name == "Sole - Terra - Luna - Artemis II (Motors Off)":
        return _make_sun_earth_moon_artemis2()
    elif name == "Sistema Gioviano Completo":
        return _make_jovian_system()
    elif name == "Approccio alla Velocità della Luce (ART) [0.999c -> c] - 20 gb RAM ver":
        return _make_Rspeed_test()
    elif name == "Approccio alla Velocità della Luce (ART) [0.9c -> c] - LIGHT 10 gb RAM ver":
        return _make_Rspeed_test_light()
    elif name == "Approccio alla Velocità della Luce (ART) [0.7c -> c] - ULTRA-LIGHT 5 gb RAM ver":
        return _make_Rspeed_test_ultralight()
    elif name == "Stelle di Neutroni Binarie: Orbita Stabile":
        return _make_binary_neutron_stars_stable()
    elif name == "Stelle di Neutroni Binarie: Eccentricità Estrema":
        return _make_extreme_eccentric_binary_ns()
    elif name == "Stelle di Neutroni Binarie: Pre-Collisione":
        return _make_binary_neutron_stars_pre_collision()
    elif name == "GW170817: Merger Stelle di Neutroni":
        return _make_GW170817_merger()
    elif name == "Alpha Centauri + Sistema Polyphemus (Avatar)":
        return _make_alpha_centauri_avatar()
    elif name == "GW150914: Merger Buchi Neri":
        return _make_GW150914_merger()
    elif name == "GW190814: Merger Asimmetrico (Mass Gap)":
        return _make_GW190814_merger()
    elif name == "Laboratorio Orbite Estreme":
        return _make_extreme_eccentricity_test()
    elif name == "EMRI: Plunge Relativistico":
        return _make_relativistic_plunge_test()
    elif name == "Scontro fra Galassie Nane":
        return _make_dual_cluster_collision()
    elif name == "Scenario Vuoto (Blank)":
        return _make_blank()
    else:
        print(f"[WARNING] Preset '{name}' non trovato. Carico Sistema Solare Completo.")
        return _make_solar_system()
    

# --- GENERATORI SPECIFICI ---
def _make_Rspeed_test():
    """
    Approccio alla Velocità della Luce: Test ART (Accelerazione Relativistica Artificiale).

    Il Sole viene lanciato a v = 0.999c con un vettore di accelerazione artificiale costante (ART)
    che VIOLA intenzionalmente il freno relativistico del motore (che richiederebbe energia infinita).
    Questo permette di osservare:
      - Lo schiacciamento del campo alla Liénard-Wiechert in modalità Phi scalare: man mano che v -> c,
        le isolinee di potenziale gravitazionale si comprimono in un disco perpendicolare alla direzione
        di moto, raggiungendo verticalmente l'infinito esattamente a c.
      - Il 'muro del Deep Space': la coda causale L0→L1→L2 si comprime fino a diventare
        una singolarità ottica al raggiungimento di c. Oltre, appare la coda 'fictiva',
        il boom sonico non più solo della luce, ma dell'informazione causale stessa.
      - L'uscita dal cono di Mach: la regione in cui il kernel grafico non riceve più informazioni
        causali dal Sole (zero contributo al campo) e vediamo il vuoto assoluto alle spalle.

    MODALITÀ CONSIGLIATA: Phi Scalare (per vedere la compressione del campo alla Liénard-Wiechert).
    Il sim_radius è impostato a ~1000 anni luce per permettere alla coda di memoria L2 di
    estendersi abbastanza da rendere visibile il collasso causale prima del muro.
    """
    bodies = []
    idx = 0

    # ART = [0.001, 0.0] è l'accelerazione artificiale costante che supera il limite c.
    bodies.append(CelestialBody(idx, 1.989e30, [0.0, 0.0], [C_LIGHT*0.999, 0.0], 696340.0, YELLOW, [0.001, 0.0], pre_existed=True, name="Sun"))
    idx += 1

    ideal_dt = 0.16 # tempo reale a Speed: 1x
    ideal_sim_radius = 20237120 * AU_IN_KM #320 anni luce
    ideal_step = DEFAULT_STEP
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_Rspeed_test_light():
    """
    Versione LIGHT (10 GB RAM di picco, 5 GB operativi).
    DT incrementato di 10x (DT = 1.6) per consentire un raggio di simulazione di 1742 anni luce
    sotto il vincolo di 2^27 slot di memoria L2.
    """
    bodies = []
    idx = 0
    bodies.append(CelestialBody(idx, 1.989e30, [0.0, 0.0], [C_LIGHT*0.9, 0.0], 696340.0, YELLOW, [0.001, 0.0], pre_existed=True, name="Sun"))
    idx += 1

    ideal_dt = 1.6
    ideal_sim_radius = 110170000 * AU_IN_KM
    ideal_step = DEFAULT_STEP
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_Rspeed_test_ultralight():
    """
    Versione ULTRA-LIGHT (5 GB RAM di picco, 2.5 GB operativi).
    DT incrementato di 100x (DT = 16.0) per consentire un raggio di simulazione di 8710 anni luce
    sotto il vincolo di 2^26 slot di memoria L2.
    """
    bodies = []
    idx = 0
    bodies.append(CelestialBody(idx, 1.989e30, [0.0, 0.0], [C_LIGHT*0.7, 0.0], 696340.0, YELLOW, [0.001, 0.0], pre_existed=True, name="Sun"))
    idx += 1

    ideal_dt = 16.0
    ideal_sim_radius = 550850000 * AU_IN_KM
    ideal_step = DEFAULT_STEP
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_solar_system():
    """
    Sistema Solare Completo: Meccanica Kepleriana Realistica.

    Riproduce il Sistema Solare con masse, semiaassi, eccentricità e raggi reali JPL.
    Include il Sole, tutti e otto i pianeti principali, Plutone, e le lune significative
    di Terra, Marte, Giove (galileiane + irregolari), Saturno, Urano e Nettuno (con
    Tritone in orbita retrograda, come nella realtà).
    Ogni orbita è inizializzata al pericentro con velocità kepleriana in forma
    chiusa, tenendo conto del potenziale di Paczyński-Wiita e della massa totale
    della coppia (genitore + satellite) che governa davvero l'orbita relativa.

    MODALITÀ CONSIGLIATA: Phi Scalare o Roche per esplorare le sfere di Hill planetarie.
    """
    bodies = []
    idx_counter = 0

    sun_mass = 1.989e30
    bodies.append(CelestialBody(idx_counter, sun_mass, [0.0, 0.0], [0.0, 0.0], 696340.0, YELLOW, pre_existed=True, name="Sun"))
    idx_counter += 1
    
    # Pianeti Principali: Nome, Massa, Semiasse (AU), Eccentricità, Raggio, Colore
    planets_data = [
        ("Mercury", 3.301e23, 0.387098, 0.205630, 2439.7, (180,180,180)),
        ("Venus",   4.867e24, 0.723332, 0.006772, 6051.8, (255,140,0)),
        ("Earth",   5.972e24, 1.000000, 0.016708, 6371.0, BLUE),
        ("Mars",    6.390e23, 1.523679, 0.093400, 3389.5, (255, 69, 0)),
        ("Jupiter", 1.898e27, 5.204400, 0.048900, 69911.0, (210, 180, 140)),
        ("Saturn",  5.683e26, 9.582600, 0.056500, 58232.0, (244, 235, 215)),
        ("Uranus",  8.681e25, 19.21840, 0.046381, 25362.0, (175, 238, 238)),
        ("Neptune", 1.024e26, 30.11000, 0.009456, 24622.0, (65, 105, 225)),
        ("Pluto",   1.303e22, 39.48000, 0.248800, 1188.3, (220, 210, 200))
    ]
    
    planet_state = {}

    for name, mass, a_au, e, rad, col in planets_data:
        a = a_au * AU_IN_KM
        r_peri = a * (1.0 - e)
        r_apo  = a * (1.0 + e)
        
        v_peri = solve_velocity_from_pericenter(sun_mass + mass, r_peri, r_apo)
        
        angle = random.uniform(0, 6.283)
        p_x = math.cos(angle) * r_peri
        p_y = math.sin(angle) * r_peri
        v_x = -math.sin(angle) * v_peri
        v_y = math.cos(angle) * v_peri
        
        planet_state[name] = {"pos": [p_x, p_y], "vel": [v_x, v_y], "mass": mass}
        bodies.append(CelestialBody(idx_counter, mass, [p_x, p_y], [v_x, v_y], rad, col, pre_existed=True, name=name))
        idx_counter += 1

    # --- LUNE: Aggiungiamo le eccentricità ove rilevanti e calcoliamo relativisticamente ---
    # Earth
    m_a, m_e = 384399.0, 0.0549
    m_r_peri = m_a * (1.0 - m_e)
    m_r_apo = m_a * (1.0 + m_e)
    moon_mass = 7.342e22
    v_peri_moon = solve_velocity_from_pericenter(planet_state["Earth"]["mass"] + moon_mass, m_r_peri, m_r_apo)
    ang = float(idx_counter) * 1.4
    epos, evel = planet_state["Earth"]["pos"], planet_state["Earth"]["vel"]
    pos_moon = [epos[0] + math.cos(ang)*m_r_peri, epos[1] + math.sin(ang)*m_r_peri]
    vel_moon = [evel[0] - math.sin(ang)*v_peri_moon, evel[1] + math.cos(ang)*v_peri_moon]
    bodies.append(CelestialBody(idx_counter, moon_mass, pos_moon, vel_moon, 1737.4, WHITE, pre_existed=True, name="Moon"))
    idx_counter += 1

    # Mars
    mars_moons = [
        ("Phobos", 1.06e16, 9376.0,  0.0151,  11.2, (200, 100, 100)),
        ("Deimos", 1.48e15, 23463.0, 0.0002,  6.2,  (150, 150, 150))
    ]
    for name, mass, m_a, m_e, rad, col in mars_moons:
        m_r_peri = m_a * (1.0 - m_e)
        m_r_apo = m_a * (1.0 + m_e)
        v_peri_rel = solve_velocity_from_pericenter(planet_state["Mars"]["mass"] + mass, m_r_peri, m_r_apo)
        ang = float(idx_counter) * 1.4
        ppos, pvel = planet_state["Mars"]["pos"], planet_state["Mars"]["vel"]
        pos = [ppos[0] + math.cos(ang)*m_r_peri, ppos[1] + math.sin(ang)*m_r_peri]
        vel = [pvel[0] - math.sin(ang)*v_peri_rel, pvel[1] + math.cos(ang)*v_peri_rel]
        bodies.append(CelestialBody(idx_counter, mass, pos, vel, rad, col, pre_existed=True, name=name))
        idx_counter += 1

    # Jupiter
    jup_moons_data = [
        ("Amalthea", 2.08e18, 181365.0,  0.0031, 83.5,   (50, 150, 255)),
        ("Io",       8.93e22, 421700.0,  0.0041, 1821.6, (255, 255, 0)),
        ("Europa",   4.80e22, 671000.0,  0.0094, 1560.8, (200, 200, 255)),
        ("Ganymede", 1.48e23, 1070400.0, 0.0013, 2634.1, (180, 180, 180)),
        ("Callisto", 1.08e23, 1882700.0, 0.0074, 2410.3, (100, 90, 80)),
        ("Himalia",  4.20e18, 11460000.0, 0.1623, 85.0,  (100, 100, 100))
    ]
    for name, mass, m_a, m_e, rad, col in jup_moons_data:
        m_r_peri = m_a * (1.0 - m_e)
        m_r_apo = m_a * (1.0 + m_e)
        v_peri_rel = solve_velocity_from_pericenter(planet_state["Jupiter"]["mass"] + mass, m_r_peri, m_r_apo)
        ang = float(idx_counter) * 1.4
        ppos, pvel = planet_state["Jupiter"]["pos"], planet_state["Jupiter"]["vel"]
        pos = [ppos[0] + math.cos(ang)*m_r_peri, ppos[1] + math.sin(ang)*m_r_peri]
        vel = [pvel[0] - math.sin(ang)*v_peri_rel, pvel[1] + math.cos(ang)*v_peri_rel]
        bodies.append(CelestialBody(idx_counter, mass, pos, vel, rad, col, pre_existed=True, name=name))
        idx_counter += 1

    # Saturn
    saturn_moons = [
        ("Mimas",     3.75e19, 185539.0, 0.0202, 198.2, (100, 100, 100)),
        ("Enceladus", 1.08e20, 237948.0, 0.0047, 252.1, (240, 255, 255)),
        ("Tethys",    6.17e20, 294619.0, 0.0001, 531.1, (200, 200, 200)),
        ("Dione",     1.10e21, 377396.0, 0.0022, 561.4, (180, 180, 190)),
        ("Rhea",      2.30e21, 527108.0, 0.0012, 763.8, (150, 150, 160)),
        ("Titan",     1.35e23, 1221870.0, 0.0288, 2574.7, (255, 140, 0)),
        ("Hyperion",  5.62e18, 1481009.0, 0.1042, 135.0, (160, 80, 80)),
        ("Iapetus",   1.80e21, 3560820.0, 0.0286, 734.5, (50, 50, 50)),
        ("Phoebe",    8.29e18, 12955759.0, 0.1640, 106.5, (80, 70, 60))
    ]
    for name, mass, m_a, m_e, rad, col in saturn_moons:
        m_r_peri = m_a * (1.0 - m_e)
        m_r_apo = m_a * (1.0 + m_e)
        v_peri_rel = solve_velocity_from_pericenter(planet_state["Saturn"]["mass"] + mass, m_r_peri, m_r_apo)
        ang = float(idx_counter) * 1.4  # Sfasamento deterministico per evitare allineamenti caotici letali al frame 0
        ppos, pvel = planet_state["Saturn"]["pos"], planet_state["Saturn"]["vel"]
        pos = [ppos[0] + math.cos(ang)*m_r_peri, ppos[1] + math.sin(ang)*m_r_peri]
        vel = [pvel[0] - math.sin(ang)*v_peri_rel, pvel[1] + math.cos(ang)*v_peri_rel]
        bodies.append(CelestialBody(idx_counter, mass, pos, vel, rad, col, pre_existed=True, name=name))
        idx_counter += 1

    # Uranus
    uranus_moons = [
        ("Miranda", 6.59e19, 129390.0, 0.0013, 235.8, (180,180,180)),
        ("Ariel",   1.35e21, 191020.0, 0.0012, 578.9, (230,230,230)),
        ("Umbriel", 1.17e21, 266300.0, 0.0039, 584.7, (40,40,40)),
        ("Titania", 3.52e21, 435910.0, 0.0011, 788.4, (200,190,180)),
        ("Oberon",  3.01e21, 583520.0, 0.0014, 761.4, (140,100,100))
    ]
    for name, mass, m_a, m_e, rad, col in uranus_moons:
        m_r_peri = m_a * (1.0 - m_e)
        m_r_apo = m_a * (1.0 + m_e)
        v_peri_rel = solve_velocity_from_pericenter(planet_state["Uranus"]["mass"] + mass, m_r_peri, m_r_apo)
        ang = float(idx_counter) * 1.4
        ppos, pvel = planet_state["Uranus"]["pos"], planet_state["Uranus"]["vel"]
        pos = [ppos[0] + math.cos(ang)*m_r_peri, ppos[1] + math.sin(ang)*m_r_peri]
        vel = [pvel[0] - math.sin(ang)*v_peri_rel, pvel[1] + math.cos(ang)*v_peri_rel]
        bodies.append(CelestialBody(idx_counter, mass, pos, vel, rad, col, pre_existed=True, name=name))
        idx_counter += 1

    # Neptune
    neptune_moons = [
        ("Proteus", 4.4e19,  117647.0,  0.0005,  210.0,  (60,60,60)),
        ("Triton",  2.14e22, 354759.0,  0.000016, 1353.4, (200,220,255)), 
        ("Nereid",  3.1e19,  5513818.0, 0.7507,  170.0,  (100,100,120))
    ]
    for name, mass, m_a, m_e, rad, col in neptune_moons:
        m_r_peri = m_a * (1.0 - m_e)
        m_r_apo = m_a * (1.0 + m_e)
        v_peri_rel = solve_velocity_from_pericenter(planet_state["Neptune"]["mass"] + mass, m_r_peri, m_r_apo)
        
        # L'orbita di Tritone è retrograda
        direction = -1 if name == "Triton" else 1

        ang = float(idx_counter) * 1.4
        ppos, pvel = planet_state["Neptune"]["pos"], planet_state["Neptune"]["vel"]
        pos = [ppos[0] + math.cos(ang)*m_r_peri, ppos[1] + math.sin(ang)*m_r_peri]
        vel = [pvel[0] - math.sin(ang)*v_peri_rel * direction, pvel[1] + math.cos(ang)*v_peri_rel * direction]
        bodies.append(CelestialBody(idx_counter, mass, pos, vel, rad, col, pre_existed=True, name=name))
        idx_counter += 1
        
    ideal_dt = 150.0
    ideal_sim_radius = DEFAULT_RADIUS
    ideal_step = 10
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_solar_system_light():
    """
    Sistema Solare (Versione Leggera): Solo Pianeti, Nessuna Luna.

    Identico al Sistema Solare Completo per masse, eccentricità e posizioni,
    ma privo di lune per ridurre drasticamente il numero di corpi simulati.
    DT accelerato (512 s/step) per una progressione visiva fluida anche su CPU deboli.
    Ideale per test di stabilità kepleriana o per macchine con risorse limitate.

    MODALITÀ CONSIGLIATA: Phi Scalare per visualizzare l'architettura del campo solare.
    """
    bodies = []
    idx_counter = 0 
    
    sun_mass = 1.989e30
    bodies.append(CelestialBody(idx_counter, sun_mass, [0.0, 0.0], [0.0, 0.0], 696340.0, YELLOW, pre_existed=True, name="Sun"))
    idx_counter += 1
    
    # Dati esatti dal JPL: Semi-Asse Maggiore (AU), Eccentricità reale, Massa, Raggio, Colore
    planets_data = [
        ("Mercury", 3.301e23, 0.387098, 0.205630, 2439.7, (180,180,180)),
        ("Venus",   4.867e24, 0.723332, 0.006772, 6051.8, (255,140,0)),
        ("Earth",   5.972e24, 1.000000, 0.016708, 6371.0, BLUE),
        ("Mars",    6.390e23, 1.523679, 0.093400, 3389.5, (255, 69, 0)),
        ("Jupiter", 1.898e27, 5.204400, 0.048900, 69911.0, (210, 180, 140)),
        ("Saturn",  5.683e26, 9.582600, 0.056500, 58232.0, (244, 235, 215)),
        ("Uranus",  8.681e25, 19.21840, 0.046381, 25362.0, (175, 238, 238)),
        ("Neptune", 1.024e26, 30.11000, 0.009456, 24622.0, (65, 105, 225)),
        ("Pluto",   1.303e22, 39.48000, 0.248800, 1188.3, (220, 210, 200))
    ]
    
    for name, mass, a_au, e, rad, col in planets_data:
        # Calcolo Pericentro e Apocentro perfetti
        a = a_au * AU_IN_KM
        r_peri = a * (1.0 - e)
        r_apo  = a * (1.0 + e)
        
        # Velocità VERA in forma chiusa (potenziale di Paczyński-Wiita, massa Sole+pianeta)
        v_peri = solve_velocity_from_pericenter(sun_mass + mass, r_peri, r_apo)
        
        # Posizioniamo il corpo ad un angolo random, ma alla distanza del *pericentro*
        # (questo manterrà l'orbita eccentrica esatta, l'argomento del pericentro è solo randomizzato)
        angle = random.uniform(0, 6.283)
        p_x = math.cos(angle) * r_peri
        p_y = math.sin(angle) * r_peri
        v_x = -math.sin(angle) * v_peri
        v_y = math.cos(angle) * v_peri
        bodies.append(CelestialBody(idx_counter, mass, [p_x, p_y], [v_x, v_y], rad, col, pre_existed=True, name=name))
        idx_counter += 1

    ideal_dt = 512.0
    ideal_sim_radius = DEFAULT_RADIUS
    ideal_step = 10
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_random_cluster(n):
    """
    Ammasso Caotico: Stress-Test N-Body con Buco Nero Ipermassiccio.

    Un buco nero supermassiccio (1000 masse solari) al centro circondato da N=100 corpi
    con masse, distanze, velocità e orientazioni randomizzate (con 15% di orbite retrograde).
    Velocità di lancio calibrate attorno alla circolare Paczyński-Wiita, con dispersione
    tra 0.6x e 1.25x per garantire un mix di orbite ellittiche, circolari e iperboliche.
    Lo scenario non ha uno stato finale prevedibile: è progettato per stressare il
    motore di collisioni, il GC asincrono e i ring buffer storici.

    MODALITÀ CONSIGLIATA: DPHI per osservare le onde gravitazionali impulsive delle collisioni.
    """
    bodies = []
    central_mass = 1.989e33
    rs = (2.0 * G * central_mass) / (C_LIGHT*C_LIGHT)
    
    bodies.append(CelestialBody(0, central_mass, [0, 0], [0, 0], rs, (100, 200, 255), name="Mass. Black Hole"))
    
    for i in range(1, n):
        dist_au = random.uniform(0.6, 9.0)
        dist_km = dist_au * AU_IN_KM
        angle = random.uniform(0, 6.28)
        pos_x = math.cos(angle) * dist_km
        pos_y = math.sin(angle) * dist_km
        
        v_circ_kms = solve_pw_circular_velocity(central_mass, dist_km)
        speed_factor = random.uniform(0.6, 1.25)
        angle_deviation = random.uniform(-0.35, 0.35)
        direction = -1 if random.random() < 0.15 else 1
        
        vel_angle = angle + (math.pi / 2) * direction + angle_deviation
        v_final_mag = v_circ_kms * speed_factor
        vel_x = math.cos(vel_angle) * v_final_mag
        vel_y = math.sin(vel_angle) * v_final_mag
        
        mass_exp = random.uniform(24, 28.5) 
        mass = 10 ** mass_exp
        
        if mass < 1e26:
            col = (random.randint(100,200), random.randint(50,100), 50)
            rad = random.randint(2000, 6000)
        elif mass < 1e28:
            col = (random.randint(50,100), random.randint(150,255), random.randint(150,255))
            rad = random.randint(8000, 25000)
        else:
            col = (255, random.randint(200,240), random.randint(200,240))
            rad = random.randint(30000, 50000)

        bodies.append(CelestialBody(i, mass, [pos_x, pos_y], [vel_x, vel_y], rad, col, pre_existed=random.choice([True, False]), name=f"Body n.{i}"))
        
    ideal_dt = DEFAULT_DT
    ideal_sim_radius = DEFAULT_RADIUS
    ideal_step = 100
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_earth_moon_iss_hubble():
    """
    Terra - Luna - ISS - Hubble: Scenario Geocentrico.

    Micro-scenario geocentrico con dati reali: la Terra al centro, la Luna in orbita
    ellittica (e=0.0549, a=384.400 km) e due satelliti artificiali:
      - ISS: orbita circolare a 408 km di quota con v=7.66 km/s, controllabile dal giocatore (motore attivo).
      - Hubble: orbita circolare passiva a 540 km di quota con v=7.594 km/s (motore spento/inerziale).
    
    MODALITÀ CONSIGLIATA: Roche/Lagrange per visualizzare i punti L1-L5 Terra-Luna.
    """
    bodies = []
    idx_counter = 0
    bodies.append(CelestialBody(idx_counter, 5.972e24, [0.0, 0.0], [0.0, 0.0], 6371.0, BLUE, pre_existed=True, name="Earth"))
    idx_counter += 1
    bodies.append(CelestialBody(idx_counter, 7.342e22, [363300, 0.0], [0.0, 30.862-29.78], 1737.4, WHITE, pre_existed=True, name="Moon"))
    idx_counter += 1

    # ISS (controllabile con motore attivo)
    bodies.append(CelestialBody(
        idx_counter, 4.5e5, [6791.0, 0.0], [0.0, 7.66], 0.5, (0, 255, 0),        
        artificial_engine=[0.0, 0.0], pre_existed=True, name="ISS"
    ))
    idx_counter += 1
    
    # Hubble (passivo, stabile)
    bodies.append(CelestialBody(
        idx_counter, 1.1e4, [6911.0, 0.0], [0.0, 7.594], 0.1, (180, 200, 220),
        artificial_engine=[0.0, 0.0], pre_existed=True, name="Hubble"
    ))
    idx_counter += 1
    
    ideal_dt = DEFAULT_DT
    ideal_sim_radius = AU_IN_KM
    ideal_step = 10
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_sun_earth_moon_artemis2():
    """
    Terra - Luna - Artemis II (Motors Off): Scenario Eliocentrico.

    Scenario eliocentrico reale: il Sole al centro, la Terra e la Luna in orbita
    attorno al Sole, e la navicella Artemis II (Orion) in crociera translunare passiva.

    Dati di navigazione originali estratti da JPL Horizons per l'epoca coerente
    2026-04-03 12:03:39.109 UTC (JD 2461134.002535984):

    --- VETTORI DI STATO ELIOCENTRICI ORIGINALI (AU e AU/d) ---
    Sole:
      r = [np.float64(0.0), np.float64(0.0), np.float64(0.0)]
      v = [np.float64(0.0), np.float64(0.0), np.float64(0.0)]
    Terra:
      r = [np.float64(-0.9726667212564777), np.float64(-0.2313679825546681), np.float64(2.157344580590326e-05)]
      v = [np.float64(0.003698846509695479), np.float64(-0.01679563670948357), np.float64(1.396204719212374e-06)]
    Luna:
      r = [np.float64(-0.9749760554876401), np.float64(-0.2326777540558539), np.float64(-0.0001660644871692822)]
      v = [np.float64(0.003965147236771252), np.float64(-0.01730156224762765), np.float64(-3.216281273505805e-05)]
    Artemis II:
      r = [np.float64(-0.9731635473014045), np.float64(-0.2321153262985418), np.float64(-5.141023617971355e-05)]
      v = [np.float64(0.003326115739047802), np.float64(-0.01791213633014949), np.float64(-0.0001010778353591379)]

    Nota sull'errore di epoca non valida in Horizons per la data originaria di novembre 2025:
    "Horizons Error: No ephemeris for target "Artemis II (spacecraft)" prior to A.D. 2026-APR-02 01:58:32.3050 TD"

    Proiezione 2D: Le componenti Z spaziali e di velocità sono proiettate sul piano XY
    ponendole a zero, in quanto la coordinata Z in piano eclittico J2000 è trascurabile.
    I valori sono stati convertiti in km e km/s moltiplicando rispettivamente per
    AU_TO_KM = 149597870.7 e AUD_TO_KMS = 149597870.7 / 86400.
    """
    bodies = []
    idx_counter = 0
    # Sole
    bodies.append(CelestialBody(idx_counter, 1.989e30, [0.0, 0.0], [0.0, 0.0], 696340.0, (255, 215, 0), pre_existed=True, name="Sun"))
    idx_counter += 1

    # Terra
    bodies.append(CelestialBody(
        idx_counter, 5.972e24, 
        [-145508870.40071946, -34612157.53833309], 
        [6.404393077506603, -29.080920009137685], 
        6371.0, BLUE, pre_existed=True, name="Earth"
    ))
    idx_counter += 1

    # Luna
    bodies.append(CelestialBody(
        idx_counter, 7.342e22, 
        [-145854341.884436, -34808096.56601403], 
        [6.865481292048241, -29.956908241071787], 
        1737.4, WHITE, pre_existed=True, name="Moon"
    ))
    idx_counter += 1

    # Artemis II (Orion + Service Module)
    bodies.append(CelestialBody(
        idx_counter, 2.6e4, 
        [-145583194.51914883, -34723958.57109757], 
        [5.759025836380879, -31.014090910630507], 
        0.2, (57, 255, 20),
        artificial_engine=[0.0, 0.0], pre_existed=True, name="Artemis II"
    ))
    idx_counter += 1
    
    ideal_dt = 0.16
    ideal_sim_radius = AU_IN_KM
    ideal_step = 1000
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_jovian_system():
    """
    Sistema Gioviano Completo: 13 lune in tre famiglie dinamiche.

    Giove al centro con le quattro lune interne, le quattro galileiane in risonanza
    di Laplace 1:2:4 (Io-Europa-Ganimede) e cinque irregolari esterne dei gruppi
    Himalia (prograde) e Pasiphae/Carme (retrograde, come nella realtà).
    Ogni orbita è inizializzata al pericentro con velocità kepleriana in forma chiusa
    (potenziale di Paczyński-Wiita, massa Giove + luna) ed eccentricità reali JPL.
    """
    bodies = []
    idx = 0
    
    jupiter_mass = 1.898e27
    bodies.append(CelestialBody(idx, jupiter_mass, [0.0, 0.0], [0.0, 0.0], 69911.0, (210, 180, 140), pre_existed=True, name="Jupiter"))
    idx += 1

    # Nome, Massa(kg), Semiasse(km), Eccentricità, Retrograda, Raggio(km), Colore
    inner_moons = [
        ("Metis",    3.6e16,  128000.0,   0.0002, False, 21.0, (100, 100, 100)),
        ("Adrastea", 2.0e16,  129000.0,   0.0015, False, 8.0,  (120, 120, 120)),
        ("Amalthea", 2.08e18, 181366.0,   0.0032, False, 83.5, (200, 50, 50)),
        ("Thebe",    4.3e17,  221889.0,   0.0176, False, 49.0, (150, 100, 100)),
    ]

    galilean_moons = [
        ("Io",       8.93e22, 421700.0,   0.0041, False, 1821.6, (255, 255, 0)),
        ("Europa",   4.80e22, 671034.0,   0.0094, False, 1560.8, (200, 200, 255)),
        ("Ganymede", 1.48e23, 1070412.0,  0.0013, False, 2634.1, (180, 180, 180)),
        ("Callisto", 1.08e23, 1882709.0,  0.0074, False, 2410.3, (100, 90, 80)),
    ]
    
    irregular_moons = [
        ("Himalia",  4.2e18,  11461000.0, 0.162, False, 85.0, (150, 150, 150)),
        ("Elara",    3.0e17,  11741000.0, 0.217, False, 30.0, (80, 80, 100)),
        ("Pasiphae", 7.5e16,  23624000.0, 0.409, True,  19.0, (70, 70, 70)),
        ("Carme",    1.3e17,  23404000.0, 0.253, True,  23.0, (90, 80, 80)),
        ("Sinope",   3.0e16,  23939000.0, 0.250, True,  14.0, (80, 90, 90)),
    ]

    all_named = inner_moons + galilean_moons + irregular_moons
    
    for name, mass, a_km, e, retro, rad, col in all_named:
        r_peri = a_km * (1.0 - e)
        r_apo  = a_km * (1.0 + e)
        v_peri = solve_velocity_from_pericenter(jupiter_mass + mass, r_peri, r_apo)
        direction = -1 if retro else 1
        angle = random.uniform(0, 6.283)
        p_x = math.cos(angle) * r_peri
        p_y = math.sin(angle) * r_peri
        v_x = -math.sin(angle) * v_peri * direction
        v_y =  math.cos(angle) * v_peri * direction
        bodies.append(CelestialBody(idx, mass, [p_x, p_y], [v_x, v_y], rad, col, pre_existed=True, name=name))
        idx += 1

    ideal_dt = 60.0
    ideal_sim_radius = AU_IN_KM
    ideal_step = DEFAULT_STEP
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_extreme_eccentric_binary_ns():
    """
    Stelle di Neutroni Binarie: Eccentricità Estrema.

    Due stelle di neutroni gemelle (~1.5 M_sol ciascuna) in orbite altamente
    eccentriche attorno al comune baricentro. Il baricentro corrisponde alla
    metà della distanza R che le separa al loro pericentro (200 km).
    """
    bodies = []
    
    mass = 3.0e30 
    m_tot = mass * 2.0
    
    dist_peri = 200.0
    dist_apo = 4000.0
    
    v_rel_apo = solve_velocity_from_apocenter(m_tot, dist_apo, dist_peri)
    v_orb = v_rel_apo / 2.0
    
    r_bary = dist_apo / 2.0  
    rad_visual = 12.0 

    bodies.append(CelestialBody(0, mass, [-r_bary, 0.0], [0.0, -v_orb], rad_visual, (0, 255, 255), pre_existed=False, name="NS Alpha"))
    bodies.append(CelestialBody(1, mass, [r_bary, 0.0], [0.0, v_orb], rad_visual, (255, 0, 255), pre_existed=False, name="NS Beta"))

    ideal_dt = 0.000001
    ideal_sim_radius = 3.0 * AU_IN_KM 
    ideal_step = 1000
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_binary_neutron_stars_stable():
    """
    Stelle di Neutroni Binarie: Orbita Circolare Stabile (Pre-Inspiral).

    Due stelle di neutroni identiche (~1.5 masse solari ciascuna) in orbita circolare
    perfetta a distanza reciproca di 40.000 km, con velocità kepleriana calcolata
    analiticamente. L'orbita è stabile nel breve termine: l'irraggiamento GW a questa
    distanza è fisicamente reale ma produce un inspiral su scale di milioni di anni.
    Serve come stato di riferimento e punto di partenza concettuale prima della
    Pre-Collisione (v. scenario successivo).

    MODALITÀ CONSIGLIATA: DPHI per visualizzare l'onda gravitazionale quadrupolare pura
    di un sistema binario in orbita circolare.
    """
    bodies = []

    mass = 3.0e30  # ~1.5 masse solari per stella
    dist_total = 40000.0  # km
    r_bary = dist_total / 2.0
    rad_visual = 800.0  # raggio visivo esagerato per la visualizzazione

    val_under_sqrt = (G * mass) / (2 * dist_total)
    v_orb = math.sqrt(val_under_sqrt)

    bodies.append(CelestialBody(0, mass, [-r_bary, 0.0], [0.0,  v_orb], rad_visual, (0, 255, 255), pre_existed=False, name="Neutron Star A"))
    bodies.append(CelestialBody(1, mass, [ r_bary, 0.0], [0.0, -v_orb], rad_visual, (255, 0, 255), pre_existed=False, name="Neutron Star B"))

    ideal_dt = 0.001
    ideal_sim_radius = 640 * AU_IN_KM
    ideal_step = 1000
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_binary_neutron_stars_pre_collision():
    """
    Stelle di Neutroni Binarie: Late Inspiral (Pre-Collisione).

    'Fotografia' del sistema a r = 375 km di separazione totale, corrispondente
    a una frequenza d'onda gravitazionale attesa di ~66.8 Hz (frequenza orbitale ~33 Hz).
    Le velocità orbitali (~21.700 km/s per stella) sono risolte numericamente tramite
    il potenziale Paczyński-Wiita per garantire circolarità perfetta al frame 0.
    Da questo punto, la reaction radiation 2.5PN porta al merger finale in decine di
    secondi simulati: l'onda GW accelera da ~66 Hz a oltre 1000 Hz nel momento dell'impatto.

    MODALITÀ CONSIGLIATA: DPHI per seguire il chirp gravitazionale in tempo reale.
    Attivare la Sonda LIGO prima del lancio per catturare il dump NPY completo.
    """
    bodies = []
    
    # Masse esatte (3.0e30 kg)
    mass = 3.0e30 
    m_tot = mass * 2.0
    
    # Distanze geometriche esatte
    dist_total = 375 
    r_bary = dist_total / 2.0  
    rad_visual = 12.0 
    
    # Calcoliamo la V esatta richiesta dal potenziale Paczynski-Wiita del motore
    # per questa distanza precisa, garantendo un'orbita perfettamente circolare al frame 0.
    # Il risultato sarà quasi identico ai 43,516 km/s teorici (21,758 km/s per stella).
    v_rel = solve_pw_circular_velocity(m_tot, dist_total)
    v_orb = v_rel / 2.0

    bodies.append(CelestialBody(0, mass, [-r_bary, 0.0], [0.0, v_orb], rad_visual, (0, 255, 255), pre_existed=False, name="NS Alpha"))
    bodies.append(CelestialBody(1, mass, [r_bary, 0.0], [0.0, -v_orb], rad_visual, (255, 0, 255), pre_existed=False, name="NS Beta"))

    # dt a 0.00001 per catturare dinamiche estreme e f_gw a 66+ Hz senza aliasing
    ideal_dt = 0.000001
    ideal_sim_radius = 2 * AU_IN_KM 
    ideal_step = DEFAULT_STEP
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_GW170817_merger():
    """
    GW170817, Kilonova: il Merger di Stelle di Neutroni più Famoso della Storia.

    Replica dell'evento rilevato da LIGO/Virgo il 17 agosto 2017, il primo merger
    di stelle di neutroni osservato sia in onde gravitazionali che in luce (kilonova).
    Masse asimmetriche in DETECTOR FRAME, centrate sulla massa chirp che governa
    davvero le frequenze misurate da H1: M_det = 1.1975 M_sol (GWTC-1, low-spin,
    incertezza +-0.0001; la source-frame e' 1.186 con z = 0.0099):
      - NS Primaria: 1.47168 M_sol
      - NS Secondaria: 1.28691 M_sol  (rapporto di massa conservato, q ~ 0.874)
    La 'fotografia' è scattata a f_GW = 50 Hz (f_orbitale = 25 Hz), saltando i primi
    ~85 secondi di accumulo d'errore floating point. Da questo punto mancano ~14-15
    secondi di simulazione prima dello schianto a oltre 1000 Hz.

    MODALITÀ CONSIGLIATA: DPHI per seguire il chirp. Attivare Sonda LIGO.
    """
    bodies = []
    
    # 1 Massa Solare = 1.98847e30 kg
    # Masse in DETECTOR FRAME (M_chirp = 1.1975 M_sol): il confronto con H1 avviene
    # sulle frequenze misurate al rivelatore, che sono redshiftate (z = 0.0099).
    # E' la massa chirp detector-frame, non la source-frame 1.186, a governarle.
    m1 = 1.47168 * 1.98847e30
    m2 = 1.28691 * 1.98847e30
    m_tot = m1 + m2
    
    # Distanza geometrica ricalcolata per avere F_orbita = 25 Hz (F_GW = 50 Hz)
    # Evita i primi 85 secondi di accumulo d'errore del float64
    dist_total = 248.4
    
    # Raggi baricentrici (la stella più leggera orbita più distante dal centro)
    r1 = dist_total * (m2 / m_tot)
    r2 = dist_total * (m1 / m_tot)
    
    # Raggio fisico tipico di una NS
    rad_visual = 12.0 
    
    # Calcolo della velocità orbitale coerente con il potenziale reale di Paczyński-Wiita (+ softening)
    v_rel = solve_pair_circular_velocity(m1, m2, dist_total)
    
    # Le singole velocità scalano inversamente alla massa per conservare il momento
    v1 = v_rel * (m2 / m_tot)
    v2 = v_rel * (m1 / m_tot)

    bodies.append(CelestialBody(0, m1, [-r1, 0.0], [0.0, -v1], rad_visual, (0, 255, 255), pre_existed=False, name="NS Primary"))
    bodies.append(CelestialBody(1, m2, [r2, 0.0], [0.0, v2], rad_visual, (255, 0, 255), pre_existed=False, name="NS Sec."))

    # dt intoccabile per non sfasare il ritardo causale a frazioni di c
    ideal_dt = 0.000001
    ideal_sim_radius = 3 * AU_IN_KM
    ideal_step = DEFAULT_STEP 
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_alpha_centauri_avatar():
    """
    Alpha Centauri + Sistema Polyphemus: Triplo Stellare Reale con Scenario Immaginario.

    Il sistema triplo stellare reale Alpha Centauri:
      - Alpha Centauri A (1.1 M_sol, stella simile al Sole, tipo G)
      - Alpha Centauri B (0.9 M_sol, stella arancione, tipo K) in orbita binaria
        con semiasse ~23 AU e periodo ~80 anni
      - Proxima Centauri (0.12 M_sol, nana rossa) in orbita esterna lentissima a ~13.000 AU

    A questo sistema reale è agganciato il Sistema Polyphemus (da Avatar, 2009):
    un gigante gassoso con luna abitabile (Pandora) e quattro lune aggiuntive
    (Cassandra, Hades, Dante, Chaos) in configurazione di phase-locking baricentrico
    con sfasamenti angolari forzati a multipli di 45° per massima stabilità.

    MODALITÀ CONSIGLIATA: Roche per vedere le sfere di Hill delle stelle binarie.
    Phi Scalare per ammirare i tre campi gravitazionali stellari sovrapposti.
    """
    bodies = []
    idx = 0
    
    # 1. PARAMETRI STELLARI E BINARI
    mass_A = 2.188e30  
    rad_A = 854000.0   
    mass_B = 1.804e30  
    rad_B = 602000.0   
    
    dist_AB = 23.0 * AU_IN_KM
    mass_tot = mass_A + mass_B
    r_A = dist_AB * (mass_B / mass_tot)
    r_B = dist_AB * (mass_A / mass_tot)
    
    v_base = math.sqrt(G * mass_tot / dist_AB)
    v_A = v_base * (mass_B / mass_tot)
    v_B = v_base * (mass_A / mass_tot)
    
    # --- Alpha Centauri A ---
    pos_A = [-r_A, 0.0]
    vel_A = [0.0, -v_A]
    bodies.append(CelestialBody(idx, mass_A, pos_A, vel_A, rad_A, (255, 240, 200), pre_existed=True, name="Alpha Centauri A"))
    idx += 1
    
    # --- Alpha Centauri B ---
    pos_B = [r_B, 0.0]
    vel_B = [0.0, v_B]
    bodies.append(CelestialBody(idx, mass_B, pos_B, vel_B, rad_B, (255, 180, 100), pre_existed=True, name="Alpha Centauri B"))
    idx += 1
    
    # --- Proxima Centauri ---
    dist_prox = 13000.0 * AU_IN_KM
    mass_prox = 2.446e29 
    rad_prox = 107000.0 
    v_prox = math.sqrt(G * mass_tot / dist_prox)
    bodies.append(CelestialBody(idx, mass_prox, [0.0, dist_prox], [-v_prox, 0.0], rad_prox, (255, 50, 50), pre_existed=True, name="Proxima Centauri"))
    idx += 1
    
    # 2. SISTEMA POLYPHEMUS (Niente Boost artificiale, solo matematica baricentrica pura)
    dist_poly = 1.2 * AU_IN_KM 
    mass_poly = 1.0e27 
    rad_poly = 65000.0
    
    mass_pan = 4.3e24
    mass_poly_sys = mass_poly + mass_pan # Le lune minori sono ininfluenti
    
    # Orbita circolare perfetta
    v_poly_rel = math.sqrt(G * (mass_A + mass_poly_sys) / dist_poly)
    
    ang_poly = random.uniform(0, 6.28)
    pos_poly = [pos_A[0] + math.cos(ang_poly)*dist_poly, pos_A[1] + math.sin(ang_poly)*dist_poly]
    vel_poly = [vel_A[0] - math.sin(ang_poly)*v_poly_rel, vel_A[1] + math.cos(ang_poly)*v_poly_rel]
    bodies.append(CelestialBody(idx, mass_poly, pos_poly, vel_poly, rad_poly, (100, 150, 200), pre_existed=True, name="Polyphemus"))
    idx += 1
    
    # --- Pandora (Luna dominante) ---
    rad_pan = 5723.0
    dist_pan = 300000.0 
    v_pan_rel = math.sqrt(G * (mass_poly + mass_pan) / dist_pan)
    
    ang_pan = 0.0 # Pandora parte a EST assoluto (0 gradi)
    pos_pan = [pos_poly[0] + math.cos(ang_pan)*dist_pan, pos_poly[1] + math.sin(ang_pan)*dist_pan]
    vel_pan = [vel_poly[0] - math.sin(ang_pan)*v_pan_rel, vel_poly[1] + math.cos(ang_pan)*v_pan_rel]
    bodies.append(CelestialBody(idx, mass_pan, pos_pan, vel_pan, rad_pan, (50, 200, 150), pre_existed=True, name="Pandora"))
    idx += 1
    
    # --- Altre lune: Risonanza di Laplace + PHASE LOCKING ---
    # Invece di angoli casuali, forziamo gli sfasamenti a 180°, 90°, 270° e 45°
    other_moons = [
        ("Cassandra", 1.0e20,  476220.0,  230.0, (180, 180, 180), math.pi),           # 180° (Opposta a Pandora)
        ("Hades",     5.0e19,  755950.0,  181.0, (100, 100, 120), math.pi / 2.0),     # 90° (Nord)
        ("Dante",     2.0e19, 1200000.0,  134.0, (150, 100, 100), 3.0 * math.pi / 2.0), # 270° (Sud)
        ("Chaos",     1.0e19, 1904880.0,  106.0, (120, 110, 100), math.pi / 4.0)      # 45° (Nord-Est)
    ]
    
    for name, m_m, d_m, r_m, c_m, ang_m in other_moons:
        v_m_rel = math.sqrt(G * (mass_poly + m_m) / d_m)
        p_m = [pos_poly[0] + math.cos(ang_m)*d_m, pos_poly[1] + math.sin(ang_m)*d_m]
        v_m = [vel_poly[0] - math.sin(ang_m)*v_m_rel, vel_poly[1] + math.cos(ang_m)*v_m_rel]
        bodies.append(CelestialBody(idx, m_m, p_m, v_m, r_m, c_m, pre_existed=True, name=name))
        idx += 1

    ideal_dt = 2.0
    ideal_sim_radius = 32 * AU_IN_KM
    ideal_step = 250
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_GW150914_merger():
    """
    GW150914: il Primo Segnale di Onde Gravitazionali mai Rilevato dall'Umanità.

    Replica dell'evento del 14 settembre 2015, annunciato da LIGO il 11 febbraio 2016
    (Abbott et al., PRL 116, 2016). Due buchi neri in fusione:
      - BH-A: 39.24 masse solari detector-frame (source 36, z = 0.09; r_s = 116 km)
      - BH-B: 31.61 masse solari detector-frame (source 29; r_s = 93 km)
    Le frequenze osservate da LIGO sono redshiftate del 9%: il confronto col dato
    va fatto in detector frame. Il sistema è inizializzato a ~60 secondi (Peters)
    prima del merger, con separazione di 4.000 km e velocità circolari esatte
    calcolate contro la forza reale del kernel (PW per-sorgente + softening).
    Al merger, circa il 4.6% della massa totale viene irradiata come energia GW pura
    (la stella 'fantasma' GW150914 è a 1.3 miliardi di anni luce dalla Terra).

    MODALITÀ CONSIGLIATA: DPHI per vedere il chirp dei buchi neri.
    Attivare Sonda LIGO prima del lancio per analisi post-processing con LIGO Analyzer.
    """
    bodies = []
    
    # 1. Masse in DETECTOR FRAME (source 36/29 x 1.09, z = 0.09): qui il redshift
    # pesa il 9%, nove volte quello di GW170817. E' la chirp detector-frame (~30.6)
    # a governare le frequenze misurate da H1.
    mass_A = 39.24 * 1.98847e30
    mass_B = 31.61 * 1.98847e30
    mass_tot = mass_A + mass_B

    # 2. Distanza a T-60 secondi secondo Peters con la chirp detector-frame
    dist_total = 4000.0
    r_A = dist_total * (mass_B / mass_tot)
    r_B = dist_total * (mass_A / mass_tot)

    # 3. Calcolo della velocità circolare coerente con lo pseudo-potenziale di Paczyński-Wiita
    v_base = solve_pair_circular_velocity(mass_A, mass_B, dist_total)
    v_A = v_base * (mass_B / mass_tot)
    v_B = v_base * (mass_A / mass_tot)

    # 4. Raggi visivi = raggi di Schwarzschild esatti delle masse detector-frame (km)
    rad_A = 115.9
    rad_B = 93.3

    # Colori distinti: Ciano e Magenta per tracciare bene le onde DPHI a schermo
    bodies.append(CelestialBody(0, mass_A, [-r_A, 0.0], [0.0, -v_A], rad_A, (0, 255, 255), pre_existed=False, name="BH GW15-A"))
    bodies.append(CelestialBody(1, mass_B, [r_B, 0.0], [0.0, v_B], rad_B, (255, 0, 255), pre_existed=False, name="BH GW15-B"))

    ideal_dt = 0.000001
    ideal_sim_radius = 3 * AU_IN_KM
    ideal_step = DEFAULT_STEP

    return bodies, ideal_dt, ideal_sim_radius, ideal_step


def _make_GW190814_merger():
    """
    GW190814: il Merger più Asimmetrico e l'Oggetto Misterioso del Mass Gap.

    Replica dell'evento del 14 agosto 2019, rivelato dalla rete LIGO-Virgo
    (Abbott et al., ApJL 896, L44, 2020). La coppia più asimmetrica osservata
    fino ad allora (rapporto di massa q = 0.112):
      - BH-A: 24.43 masse solari detector-frame (source 23.2, z = 0.053; r_s = 72 km)
      - Oggetto-B: 2.73 masse solari detector-frame (source 2.59; r_s = 8 km)
    L'oggetto secondario cade nel "mass gap" (2.5-5 masse solari): la stella di
    neutroni più pesante o il buco nero più leggero mai osservato, senza
    controparte elettromagnetica né firme mareali nel segnale.
    Il sistema è inizializzato a ~20 secondi (Peters, chirp detector-frame ~6.42)
    prima del merger, con separazione di 1.160 km (f_GW iniziale ~15 Hz, ISCO
    teorica a ~162 Hz) e velocità circolari esatte calcolate contro la forza
    reale del kernel (PW per-sorgente + softening).
    Il rapporto di massa estremo rende lo scenario un banco di prova della
    ripartizione (m_src/M) della reazione 2.5PN: quasi tutta la spinta
    dissipativa ricade sull'oggetto leggero, come in un piccolo EMRI.

    MODALITÀ CONSIGLIATA: DPHI o GW Strain per il chirp asimmetrico.
    Attivare Sonda LIGO prima del lancio per analisi post-processing con LIGO Analyzer.
    """
    bodies = []

    # 1. Masse in DETECTOR FRAME (source 23.2/2.59 x 1.053, z = 0.053): è la
    # chirp detector-frame (~6.42) a governare le frequenze misurate.
    mass_A = 24.43 * 1.98847e30
    mass_B = 2.727 * 1.98847e30
    mass_tot = mass_A + mass_B

    # 2. Separazione a T-20 secondi secondo Peters con la chirp detector-frame
    dist_total = 1160.0
    r_A = dist_total * (mass_B / mass_tot)
    r_B = dist_total * (mass_A / mass_tot)

    # 3. Calcolo della velocità circolare coerente con lo pseudo-potenziale di Paczyński-Wiita
    v_base = solve_pair_circular_velocity(mass_A, mass_B, dist_total)
    v_A = v_base * (mass_B / mass_tot)
    v_B = v_base * (mass_A / mass_tot)

    # 4. Raggi visivi = raggi di Schwarzschild esatti delle masse detector-frame (km).
    # Per l'oggetto misterioso B si adotta il raggio da buco nero: l'evento non
    # mostra firme mareali e la dinamica è indistinguibile da un BBH.
    rad_A = 72.1
    rad_B = 8.1

    # Colori distinti: Arancio e Verde per non confonderlo con GW150914 (ciano/magenta)
    bodies.append(CelestialBody(0, mass_A, [-r_A, 0.0], [0.0, -v_A], rad_A, (255, 150, 0), pre_existed=False, name="BH GW19-A"))
    bodies.append(CelestialBody(1, mass_B, [r_B, 0.0], [0.0, v_B], rad_B, (0, 255, 140), pre_existed=False, name="GW19-B (?)"))

    ideal_dt = 0.000001
    ideal_sim_radius = 3 * AU_IN_KM
    ideal_step = DEFAULT_STEP

    return bodies, ideal_dt, ideal_sim_radius, ideal_step


def _make_galactic_solar_system():
    """
    Il Sistema Solare in orbita galattica.
    Il Sole e i pianeti viaggiano in blocco a 230 km/s attorno a un 
    buco nero fantoccio con la massa di Sagittarius A*.
    Test definitivo per l'invarianza Galileiana del motore.
    """
    bodies = []
    idx_counter = 0
    
    # 1. IL BUCO NERO SUPERMASSICCIO (Sagittarius A*)
    mass_smbh = 4.1e6 * 1.989e30  # 4.1 milioni di masse solari
    v_sys = 230.0  # 230 km/s (Velocità orbitale del nostro Sistema Solare)
    
    # Calcolo la distanza esatta per un'orbita perfettamente stabile: r = GM / v^2
    dist_smbh = (G * mass_smbh) / (v_sys * v_sys)
    
    # Raggio fittizio per renderlo visibile, colore viola scuro minaccioso
    bodies.append(CelestialBody(
        idx_counter, mass_smbh, [0.0, 0.0], [0.0, 0.0], 
        2.0e7, (80, 0, 150), pre_existed=True, name="Sagittarius A*"
    ))
    idx_counter += 1
    
    # 2. OFFSET DEL SISTEMA Solare
    sys_x = dist_smbh
    sys_y = 0.0
    sys_vx = 0.0
    sys_vy = v_sys
    
    # 3. IL SOLE
    bodies.append(CelestialBody(
        idx_counter, 1.989e30, [sys_x, sys_y], [sys_vx, sys_vy], 
        696340.0, YELLOW, pre_existed=True, name="Sun"
    ))
    idx_counter += 1
    
    # 4. I PIANETI (Applicando la traslazione di sistema a posizioni e velocità)
    planets_data = [
        ("Mercury", 3.301e23, 0.387, 47.36, 2439.7, (180,180,180)),
        ("Venus",   4.867e24, 0.723, 35.02, 6051.8, (255,140,0)),
        ("Earth",   5.972e24, 1.0,   29.78, 6371.0, BLUE),
        ("Mars",    6.39e23,  1.524, 24.07, 3389.5, (255, 69, 0)),
        ("Jupiter", 1.898e27, 5.203, 13.07, 69911.0, (210, 180, 140)),
        ("Saturn",  5.683e26, 9.537, 9.69,  58232.0, (244, 235, 215)),
        ("Uranus",  8.681e25, 19.191, 6.81, 25362.0, (175, 238, 238)),
        ("Neptune", 1.024e26, 30.069, 5.43, 24622.0, (65, 105, 225))
    ]
    
    earth_pos = [0.0, 0.0]
    earth_vel = [0.0, 0.0]
    
    for name, mass, dist_au, vel_scalar, rad, col in planets_data:
        dist_km = dist_au * AU_IN_KM
        angle = random.uniform(0, 6.283)
        p_x = sys_x + math.cos(angle) * dist_km
        p_y = sys_y + math.sin(angle) * dist_km
        v_x = sys_vx - math.sin(angle) * vel_scalar
        v_y = sys_vy + math.cos(angle) * vel_scalar
        if name == "Earth":
            earth_pos = [p_x, p_y]
            earth_vel = [v_x, v_y]
        bodies.append(CelestialBody(idx_counter, mass, [p_x, p_y], [v_x, v_y], rad, col, pre_existed=True, name=name))
        idx_counter += 1

    # 5. LA LUNA
    moon_dist_rel = 363300.0
    moon_v_rel = 1.082 
    ang_moon = random.uniform(0, 6.283)
    pos_moon = [earth_pos[0] + math.cos(ang_moon)*moon_dist_rel, earth_pos[1] + math.sin(ang_moon)*moon_dist_rel]
    vel_moon = [earth_vel[0] - math.sin(ang_moon)*moon_v_rel, earth_vel[1] + math.cos(ang_moon)*moon_v_rel]
    bodies.append(CelestialBody(idx_counter, 7.342e22, pos_moon, vel_moon, 1737.4, WHITE, pre_existed=True, name="Moon"))
    idx_counter += 1

    ideal_dt = 512.0
    ideal_sim_radius = DEFAULT_RADIUS
    ideal_step = 100
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_extreme_eccentricity_test():
    """
    Laboratorio di Orbite Estreme: Didattica Astrodinamica.

    Un buco nero centrale (1000 masse solari) circondato da cinque 'particelle test'
    inizializzate su corsie orbitali deliberatamente separate per evitare collisioni:
      - Circolare (e=0.00): orbita circolare perfetta come riferimento.
      - Ellittica (e=0.60): orbit moderatamente eccentric con pericentro ravvicinato.
      - Altamente ellittica (e=0.95): quasi-parabolica, forte precessione del pericentro.
      - Iperbolica (e>1, fuga): velocità leggermente sopra quella di fuga, traiettoria aperta.
      - Retrograda circolare: orbita circolare nella direzione opposta alle altre.
    Tutte le velocità sono calcolate da scipy tramite il potenziale Paczyński-Wiita.
    Ottimo per confrontare visivamente l'effetto dell'eccentricità e dell'inversione d'orbita.

    MODALITÀ CONSIGLIATA: Phi Scalare per vedere le deformazioni delle isolinee.
    Nessuna Sonda LIGO necessaria (nessun merger previsto).
    """
    bodies = []
    idx = 0
    
    bh_mass = 1000.0 * 1.989e30
    bodies.append(CelestialBody(
        idx, bh_mass, [0.0, 0.0], [0.0, 0.0], 
        3000.0, (50, 0, 50), pre_existed=True, name="Central BH"
    ))
    idx += 1

    # Definizione delle "Corsie"
    r_circ     = 1.0  * AU_IN_KM
    r_ellipt   = 0.92 * AU_IN_KM  # Corsia interna 1
    r_high_ell = 0.85 * AU_IN_KM  # Corsia interna 2
    r_escape   = 1.0  * AU_IN_KM
    r_retro    = 1.3  * AU_IN_KM  # Corsia esterna
    
    v_circ  = solve_pw_circular_velocity(bh_mass, r_circ)
    v_retro = solve_pw_circular_velocity(bh_mass, r_retro)
    
    v_esc = solve_escape_velocity(bh_mass, r_escape)
    v_escape_actual = v_esc * 1.02 
    
    v_ellipt = solve_velocity_from_apocenter(bh_mass, r_ellipt, 0.23 * AU_IN_KM) 
    v_high_ell = solve_velocity_from_apocenter(bh_mass, r_high_ell, 0.0218 * AU_IN_KM)

    orbit_types = [
        ("Circular (e=0)",      5.97e24, r_circ,     v_circ,          0.0,           0.0,           BLUE),
        ("Elliptical (e=0.6)",  5.97e24, r_ellipt,   v_ellipt,        0.0,           math.pi / 4.0, YELLOW),
        ("Highly Ell (e=0.95)", 5.97e24, r_high_ell, v_high_ell,      0.0,           math.pi / 2.0, (255, 140, 0)),
        ("Hyperbolic Escape",   5.97e24, r_escape,   v_esc * 1.001,  math.pi / 3.2, math.pi,       WHITE),
        ("Retrograde Circular", 5.97e24, r_retro,   -v_retro,         0.0,           3.0*math.pi/2, (100, 255, 100)) 
    ]

    for name, mass, actual_r, v_exact, pitch, start_angle, col in orbit_types:
        v_mag = abs(v_exact)
        pos_x = math.cos(start_angle) * actual_r
        pos_y = math.sin(start_angle) * actual_r
        vel_angle = start_angle + (math.pi / 2.0) + pitch
        if v_exact < 0:
            vel_angle -= math.pi
        vel_x = math.cos(vel_angle) * v_mag
        vel_y = math.sin(vel_angle) * v_mag
        bodies.append(CelestialBody(idx, mass, [pos_x, pos_y], [vel_x, vel_y], 6000.0, col, pre_existed=True, name=name))
        idx += 1

    ideal_dt = 0.2 
    ideal_sim_radius = 2.0 * AU_IN_KM
    ideal_step = 10000
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step


def _make_dual_cluster_collision():
    """
    Scontro fra Galassie Nane: Impatto Quasi-Frontale Catastrofico.

    Due galassie nane con nucleo massiccio (65.000 masse solari ciascuno) + 100 stelle
    di disco ciascuna (200 corpi totali) si avvicinano in rotta di collisione quasi-frontale.
    La velocità tangenziale è ridotta al 15% di quella kepleriana circolare, mentre
    quella radiale è impostata al 40%: le galassie si interpenetrano anziché orbitarsi.
    I colori di ogni cluster (Ciano / Magenta) permettono di tracciare visivamente
    la rimescolazione delle popolazioni stellari durante la fusione gravitazionale.
    Scenario equivalente a una fusione galattica minore in cosmologia.

    MODALITÀ CONSIGLIATA: DPHI per vedere i burst gravitazionali durante le collisioni
    tra stelle. Phi Scalare per osservare la deformazione del potenziale combinato.
    """
    bodies = []
    idx = 0

    mass_A = 65000.0 * 1.989e30
    mass_B = 65000.0 * 1.989e30
    mass_tot = mass_A + mass_B

    dist_AB = 80.0 * AU_IN_KM
    r_A = dist_AB * 0.5
    r_B = dist_AB * 0.5

    v_base = math.sqrt(G * mass_tot / dist_AB)
    
    # Riduciamo drasticamente la velocità tangenziale e aggiungiamo
    # un generoso vettore velocità d'impatto radiale verso il centro!
    v_tangential = (v_base * 0.15) 
    v_radial = (v_base * 0.40)      

    # Core Alpha parte da "sinistra", velX positiva verso il centro
    pos_A = [-r_A, 0.0]
    vel_A = [v_radial, -v_tangential]
    
    # Core Beta parte da "destra", velX negativa verso il centro
    pos_B = [r_B, 0.0]
    vel_B = [-v_radial, v_tangential]

    bodies.append(CelestialBody(idx, mass_A, pos_A, vel_A, 28000.0, (0, 255, 255), pre_existed=True, name="Core Alpha"))
    idx += 1
    bodies.append(CelestialBody(idx, mass_B, pos_B, vel_B, 28000.0, (255, 0, 255), pre_existed=True, name="Core Beta"))
    idx += 1

    def spawn_cluster(bh_pos, bh_vel, bh_mass, n, color_theme):
        nonlocal idx
        for _ in range(n):
            dist_km = random.uniform(1.5, 20.0) * AU_IN_KM
            angle = random.uniform(0, 6.28)
            p_x = bh_pos[0] + math.cos(angle) * dist_km
            p_y = bh_pos[1] + math.sin(angle) * dist_km

            v_circ = solve_pw_circular_velocity(bh_mass, dist_km)
            direction = -1 if random.random() < 0.15 else 1 
            vel_angle = angle + (math.pi / 2) * direction
            
            # Aggiungiamo maggiore caos (dispersione dinamica) nei venti galattici
            speed_factor = random.uniform(0.7, 1.3)
            vel_angle += random.uniform(-0.15, 0.15)
            
            v_x = bh_vel[0] + math.cos(vel_angle) * (v_circ * speed_factor)
            v_y = bh_vel[1] + math.sin(vel_angle) * (v_circ * speed_factor)

            mass = 10 ** random.uniform(23.5, 26.5) 
            rad = random.randint(4000, 15000)
            
            if color_theme == "Cyan":
                col = (random.randint(50,200), random.randint(200,255), random.randint(200,255))
            else:
                col = (random.randint(200,255), random.randint(50,200), random.randint(200,255))

            bodies.append(CelestialBody(idx, mass, [p_x, p_y], [v_x, v_y], rad, col, pre_existed=True, name=f"Body n.{idx}"))
            idx += 1

    # Schieriamo ben 100 corpi (stelle) intorno ad ogni Core (200 in totale!)
    spawn_cluster(pos_A, vel_A, mass_A, 100, "Cyan")
    spawn_cluster(pos_B, vel_B, mass_B, 100, "Magenta")

    ideal_dt = 150.0
    ideal_sim_radius = DEFAULT_RADIUS
    ideal_step = 100
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

def _make_relativistic_plunge_test():
    """
    EMRI (Extreme Mass Ratio Inspiral): Plunge Relativistico.

    Un Extreme Mass Ratio Inspiral (EMRI) è un sistema in cui un buco nero di massa
    stellare (qui: 10 masse solari) spiraleggia verso un buco nero supermassiccio centrale
    (qui: 1000 masse solari). Il rapporto di massa è 1:100.
    Essendo entrambi buchi neri (oggetti compatti), il sistema è fisicamente protetto
    dalla distruzione mareale prima di raggiungere l'orizzonte degli eventi (superamento del limite di Roche).
    Il corpo viene lanciato con velocità tangenziale al 15% della circolare: questa
    sottovelocità garantisce un'orbita fortemente ellittica che porta rapidamente
    al plunge, la spirale finale nel pozzo di Paczyński-Wiita che produce
    onde gravitazionali concentriche di crescente frequenza e ampiezza.
    Gli EMRI reali sono una delle sorgenti target del futuro rivelatore spaziale LISA.

    MODALITÀ CONSIGLIATA: DPHI per visualizzare le onde GW concentriche irradiate.
    Attivare Sonda LIGO per catturare la forma d'onda dello strain durante la spirale.
    """
    bodies = []
    idx = 0

    bh_mass = 1000.0 * 1.989e30
    bodies.append(CelestialBody(
        idx, bh_mass, [0.0, 0.0], [0.0, 0.0], 
        3000.0, (128, 0, 128), pre_existed=True, name="Central BH"
    ))
    idx += 1

    mass = 10.0 * 1.989e30
    dist = 0.1 * AU_IN_KM
    
    v_circ = solve_pw_circular_velocity(bh_mass, dist)
    
    pos_x = dist
    pos_y = 0.0
    vel_x = 0.0
    vel_y = v_circ * 0.15

    # Raggio impostato al raggio di Schwarzschild di un BH da 10 masse solari (~29.5 km)
    bodies.append(CelestialBody(
        idx, mass, [pos_x, pos_y], [vel_x, vel_y], 
        29.5, (191, 255, 0), pre_existed=True, name="Plunging BH"
    ))
    idx += 1

    ideal_dt = 0.05  
    ideal_sim_radius = 3000 * AU_IN_KM 
    ideal_step = 1000
    
    return bodies, ideal_dt, ideal_sim_radius, ideal_step


def _make_blank():
    """
    Scenario Vuoto: Tela Bianca.

    Un universo completamente vuoto con parametri di default.
    Il raggio di simulazione causale dell'informazione è modificabile attraverso astro_settings.ini
    Nessun corpo pre-esistente. Ideale per costruire scenari personalizzati
    spawnando corpi manualmente durante la simulazione.
    """
    bodies = []
    ideal_dt = DEFAULT_DT          
    ideal_sim_radius = config.SIMULATION_RADIUS_KM   
    ideal_step = DEFAULT_STEP          
    return bodies, ideal_dt, ideal_sim_radius, ideal_step

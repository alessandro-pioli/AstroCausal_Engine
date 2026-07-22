import math
import pygame
import core.data as data
from utils.orbital_math import get_lagrange_points, solve_lagrange_boot_velocity, solve_velocity_from_apocenter, solve_pw_circular_velocity, get_lagrange_points

class OrbitalSpawner:
    """Gestore dell'interfaccia di spawn per inserire dinamicamente nuovi corpi in orbita durante la simulazione."""
    def __init__(self):
        """Catalogo paginato dei template spawnabili (4 pagine, da micro-oggetti a
        buchi neri ultramassivi), navigabile a runtime senza toccare il motore fisico:
        lo spawner calcola solo posizione e velocità, `intercept_spawner` in
        input_controller.py fa da adattatore verso `rebuild_simulation()`."""
        self.active = False
        self.state = 0 # 0: Inactive, 1: Choose Body, 2: Choose Orbit
        self.page = 1 # 0: Small, 1: Standard, 2: Massive
        
        self.spawn_wx = 0.0
        self.spawn_wy = 0.0
        
        self.selected_template = None
        
        self.pages = {
            0: {
                "name": "Micro & Iconic Objects",
                "options": {
                    pygame.K_1: {"name": "ISS (Space Station)", "mass": 4.2e5, "radius": 0.1, "color": (230, 230, 230)},
                    pygame.K_2: {"name": "Hubble Telescope", "mass": 1.1e4, "radius": 0.01, "color": (180, 200, 220)},
                    pygame.K_3: {"name": "Halley's Comet", "mass": 2.2e14, "radius": 5.5, "color": (200, 255, 255)},
                    pygame.K_4: {"name": "Bennu Asteroid", "mass": 7.3e10, "radius": 0.25, "color": (140, 130, 120)},
                }
            },
            1: {
                "name": "Small Space Objects",
                "options": {
                    pygame.K_1: {"name": "Artificial Satellite", "mass": 1000.0, "radius": 0.01, "color": (200, 200, 200)},
                    pygame.K_2: {"name": "Asteroid (C-Type)", "mass": 1e15, "radius": 5.0, "color": (150, 150, 150)},
                    pygame.K_3: {"name": "Moon-like", "mass": 7.34e22, "radius": 1737.0, "color": (220, 220, 220)},
                    pygame.K_4: {"name": "Mars-like", "mass": 6.4e23, "radius": 3389.0, "color": (200, 100, 50)},
                }
            },
            2: {
                "name": "Standard Planets & Stars",
                "options": {
                    pygame.K_1: {"name": "Earth-like", "mass": 5.97e24, "radius": 6371.0, "color": (50, 150, 255)},
                    pygame.K_2: {"name": "Jupiter-like", "mass": 1.898e27, "radius": 69911.0, "color": (200, 150, 100)},
                    pygame.K_3: {"name": "Sun-like", "mass": 1.989e30, "radius": 696340.0, "color": (255, 255, 100)},
                    pygame.K_4: {"name": "Sirius-like (A)", "mass": 4.0e30, "radius": 1.1e6, "color": (200, 220, 255)},
                }
            },
            3: {
                "name": "Heavyweights & Remnants",
                "options": {
                    pygame.K_1: {"name": "Pulsar (Neutron Star)", "mass": 2.8e30, "radius": 12.0, "color": (150, 255, 255)},
                    pygame.K_2: {"name": "Betelgeuse (Red Supergiant)", "mass": 3.28e31, "radius": 4.8e8, "color": (255, 100, 50)},
                    pygame.K_3: {"name": "Sagittarius A* (SMBH)", "mass": 8.5e36, "radius": 1.2e7, "color": (180, 120, 255)},
                    pygame.K_4: {"name": "TON 618 (Ultramassive BH)", "mass": 1.3e41, "radius": 1.9e11, "color": (200, 150, 220)},
                }
            }
        }

    @property
    def bodies(self):
        from ui.ui_state import ui_state
        return ui_state.bodies

    @bodies.setter
    def bodies(self, value):
        pass  # no-op: la lista vera vive solo in ui_state, questo setter esiste solo per simmetria

    @property
    def top_body(self):
        """Il corpo vivo di massa maggiore in scena, ricalcolato a ogni accesso: è
        l'attrattore di default proposto allo stato 2 dello spawner."""
        bodies_list = self.bodies
        if not bodies_list:
            return None
        active_indices = [b.idx for b in bodies_list if b.idx < len(data.FLAGS) and (data.FLAGS[b.idx] & 1)]
        if not active_indices:
            return None
        top_idx = max(active_indices, key=lambda idx: data.MASS[idx])
        return next((b for b in bodies_list if b.idx == top_idx), None)

    @top_body.setter
    def top_body(self, value):
        pass

    @property
    def closest_body(self):
        """Il corpo vivo geometricamente più vicino al punto di spawn: l'alternativa
        proposta a `top_body` quando l'attrattore locale conta più di quello globale."""
        bodies_list = self.bodies
        if not bodies_list:
            return None
        active_bodies = [b for b in bodies_list if b.idx < len(data.FLAGS) and (data.FLAGS[b.idx] & 1)]
        if not active_bodies:
            return None
        return min(active_bodies, key=lambda b: (self.spawn_wx - data.POS[b.idx, 0])**2 + (self.spawn_wy - data.POS[b.idx, 1])**2)

    @closest_body.setter
    def closest_body(self, value):
        pass
        
    def activate(self, wx, wy, bodies):
        """Apre la macchina a stati direttamente sullo stato 1 (scelta del corpo),
        pagina 1 (Standard) di default, congelando le coordinate del punto di spawn."""
        self.active = True
        self.state = 1
        self.page = 1
        self.spawn_wx = wx
        self.spawn_wy = wy

    def deactivate(self):
        """Riporta la macchina a stati allo stato 0 e scarta la selezione in corso:
        chiamato sia da ESC sia a fine spawn confermato."""
        self.active = False
        self.state = 0
        self.selected_template = None

    def handle_event(self, event):
        """Cuore della macchina a stati a cinque fasi (0-4). Ritorna `False` se lo
        spawner è inattivo, altrimenti sempre `True` (consuma l'evento) tranne nel
        caso di spawn confermato, dove ritorna direttamente il dizionario
        `new_params` invece di un booleano: un protocollo di ritorno non ortodosso
        ma deliberato (§9.2 di ARCHITECTURE_DEEP_DIVE.md), è `intercept_spawner` in
        input_controller.py a riconoscerlo e a tradurlo in un rebuild vero."""
        if not self.active:
            return False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.deactivate()
                return True
                
            if self.state == 1:
                # Page Navigation
                if event.key == pygame.K_0:
                    self.page = max(0, self.page - 1)
                    return True
                elif event.key == pygame.K_5:
                    self.page = min(len(self.pages) - 1, self.page + 1)
                    return True
                    
                # Setup
                opts = self.pages[self.page]["options"]
                if event.key in opts:
                    self.selected_template = opts[event.key]
                    self.state = 2
                    return True
                    
            elif self.state == 2:
                
                
                # Scelte orbitali:
                # 1: Stazionario
                # Attrattore principale
                # 2: Circolare principale
                # 3: Eccentrico principale
                # 4: Plunge principale
                # Attrattore più vicino (se valido)
                # 6: Circolare vicino
                # 7: Eccentrico vicino
                
                tmpl = self.selected_template
                if tmpl is None: return True
                
                new_params = {
                    'name': tmpl["name"],
                    'mass': tmpl["mass"],
                    'rad': tmpl["radius"],
                    'col': tmpl["color"],
                    'pos': [self.spawn_wx, self.spawn_wy],
                    'vel': [0.0, 0.0]
                }
                
                def calc_orbit(attractor, eccentricity):
                    """Calcola la velocità di lancio dato un attrattore e un codice di
                    eccentricità: 0.0 = circolare, un valore in (0,1) = ellittica
                    (assumendo il punto di spawn come apocentro), -1.0 = sentinella
                    per il plunge (spinta radiale dominante, tangenziale ridotta al 20%
                    della circolare, solo per non far collassare l'orbita a momento
                    angolare esattamente nullo)."""
                    if not attractor or attractor.idx >= len(data.POS): return [0.0, 0.0]
                    ax, ay = data.POS[attractor.idx]
                    avx, avy = data.VEL[attractor.idx]
                    amass = data.MASS[attractor.idx]
                    
                    dx = self.spawn_wx - ax
                    dy = self.spawn_wy - ay
                    r = math.sqrt(dx**2 + dy**2)
                    if r == 0: return [0.0, 0.0]
                    
                    # Vettore normale per la posizione
                    nx, ny = dx/r, dy/r
                    
                    # Vettore tangente per la velocità (antiorario)
                    tx, ty = -ny, nx
                    
                    if eccentricity == -1.0: # Plunge (caduta radiale con una minima velocità tangenziale)
                        # Vogliamo solo che cada all'interno, quindi con una bassa velocità tangenziale
                        v_circ = solve_pw_circular_velocity(amass, r)
                        v_mag = v_circ * 0.2
                        # Spinta leggermente in avanti e fortemente verso l'interno
                        return [avx + tx*v_mag - nx*v_circ*0.5, avy + ty*v_mag - ny*v_circ*0.5]
                        
                    elif eccentricity == 0.0: # Circular
                        v_mag = solve_pw_circular_velocity(amass, r)
                        return [avx + tx * v_mag, avy + ty * v_mag]
                        
                    else: # Eccentric
                        # Si assume che il punto di spawn sia l'apocentro, il pericentro è molto più vicino
                        r_peri = r * (1.0 - eccentricity) / (1.0 + eccentricity)
                        if r_peri < amass * data.G * 2.0 / (data.C_SQ) * 5.0: # Evita la singolarità se si è troppo vicini al buco nero
                            r_peri = r * 0.5
                        v_mag = solve_velocity_from_apocenter(amass, r, r_peri)
                        return [avx + tx * v_mag, avy + ty * v_mag]
                
                # Elaborazione scelte
                valid_choice = False
                
                if event.key == pygame.K_1:
                    # Stationary
                    valid_choice = True
                    
                elif event.key in (pygame.K_2, pygame.K_3, pygame.K_4) and self.top_body:
                    if tmpl["mass"] < data.MASS[self.top_body.idx]:
                        ecc = 0.0 if event.key == pygame.K_2 else (0.6 if event.key == pygame.K_3 else -1.0)
                        new_params['vel'] = calc_orbit(self.top_body, ecc)
                        valid_choice = True
                        
                elif event.key in (pygame.K_6, pygame.K_7) and self.closest_body and self.closest_body != self.top_body:
                    if tmpl["mass"] < data.MASS[self.closest_body.idx]:
                        ecc = 0.0 if event.key == pygame.K_6 else 0.6
                        new_params['vel'] = calc_orbit(self.closest_body, ecc)
                        valid_choice = True
                        
                elif event.key == pygame.K_8:
                    self.state = 3
                    num_bodies = len(data.FLAGS)
                    active_b = [i for i in range(num_bodies) if (data.FLAGS[i] & 1)]
                    self.available_secondaries = [i for i in active_b if getattr(data, 'TOP_ATTRACTOR', None) is not None and data.TOP_ATTRACTOR[i] != -1]
                    
                    if self.available_secondaries:
                        self.lagrange_secondary_list_idx = 0
                        self.lagrange_secondary_idx = self.available_secondaries[0]
                        self.lagrange_primary_idx = data.TOP_ATTRACTOR[self.lagrange_secondary_idx] if self.lagrange_secondary_idx < len(data.TOP_ATTRACTOR) else -1
                    else:
                        self.lagrange_secondary_idx = None
                        self.lagrange_primary_idx = -1
                    return True
                        
                if valid_choice:
                    self.deactivate()
                    return new_params # Restituisce i parametri per attivare la ricostruzione
                    
            elif self.state == 3:
                if event.key == pygame.K_TAB:
                    if hasattr(self, 'available_secondaries') and self.available_secondaries:
                        num_bodies = len(data.FLAGS)
                        self.available_secondaries = [i for i in self.available_secondaries if i < num_bodies and (data.FLAGS[i] & 1)]
                        if not self.available_secondaries:
                            self.lagrange_secondary_idx = None
                            self.lagrange_primary_idx = -1
                            return True
                        self.lagrange_secondary_list_idx = (self.lagrange_secondary_list_idx + 1) % len(self.available_secondaries)
                        self.lagrange_secondary_idx = self.available_secondaries[self.lagrange_secondary_list_idx]
                        self.lagrange_primary_idx = data.TOP_ATTRACTOR[self.lagrange_secondary_idx] if self.lagrange_secondary_idx < len(data.TOP_ATTRACTOR) else -1
                    return True
                elif event.key == pygame.K_y:
                    num_bodies = len(data.FLAGS)
                    if (hasattr(self, 'lagrange_secondary_idx') and self.lagrange_secondary_idx is not None and 
                        self.lagrange_secondary_idx < num_bodies and (data.FLAGS[self.lagrange_secondary_idx] & 1)):
                        self.state = 4
                    else:
                        self.state = 1
                    return True
                    
            elif self.state == 4:

                
                point_idx = None
                if event.key == pygame.K_1: point_idx = 0
                elif event.key == pygame.K_2: point_idx = 1
                elif event.key == pygame.K_3: point_idx = 2
                elif event.key == pygame.K_4: point_idx = 3
                elif event.key == pygame.K_5: point_idx = 4
                
                if point_idx is not None:
                    p_idx = self.lagrange_primary_idx
                    s_idx = self.lagrange_secondary_idx
                    num_bodies = len(data.FLAGS)
                    
                    if (p_idx != -1 and s_idx is not None and 
                        p_idx < num_bodies and s_idx < num_bodies and 
                        (data.FLAGS[p_idx] & 1) and (data.FLAGS[s_idx] & 1)):
                        
                        m1 = data.MASS[p_idx]
                        pos1 = data.POS[p_idx]
                        vel1 = data.VEL[p_idx]
                        
                        m2 = data.MASS[s_idx]
                        pos2 = data.POS[s_idx]
                        vel2 = data.VEL[s_idx]
                        
                        pts = get_lagrange_points(m1, pos1, m2, pos2, vel1, vel2)
                        if pts:
                            l_pos = pts[point_idx]
                            l_vel = solve_lagrange_boot_velocity(m1, pos1, vel1, m2, pos2, vel2, l_pos)
                            
                            tmpl = self.selected_template
                            new_params = {
                                'name': tmpl["name"],
                                'mass': tmpl["mass"],
                                'rad': tmpl["radius"],
                                'col': tmpl["color"],
                                'pos': l_pos,
                                'vel': l_vel
                            }
                            self.deactivate()
                            return new_params
                return True

        return True # Intercepted anyway
        
    def draw(self, screen, width, height, font_main, font_title):
        """Disegna la schermata modale corrispondente allo stato corrente (0-4) su
        un overlay semitrasparente: nessuna logica di simulazione qui dentro, solo
        la proiezione a schermo dello stato della macchina."""
        if not self.active: return
        
        # Transparent overlay
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        
        # Modal Box
        pw, ph = 900, 500
        px, py = (width - pw) // 2, (height - ph) // 2
        
        pygame.draw.rect(screen, (20, 20, 30), (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(screen, (100, 150, 255), (px, py, pw, ph), 2, border_radius=10)
        
        if self.state == 1:
            title = font_title.render(f"=== SPAWN NEW BODY ===", True, (255, 255, 255))
            screen.blit(title, (px + (pw - title.get_width())//2, py + 20))
            
            page_info = self.pages[self.page]
            cat_text = font_main.render(f"Category: {page_info['name']}", True, (200, 200, 255))
            screen.blit(cat_text, (px + 30, py + 70))
            
            y_off = 105
            
            nav_prev = font_main.render("[0] <-- Smaller Bodies", True, (130, 130, 130))
            screen.blit(nav_prev, (px + 40, py + y_off))
            y_off += 35

            for key, tmpl in page_info['options'].items():
                key_name = pygame.key.name(key).upper()
                mass_str = f"{tmpl['mass']:.1e} kg"
                rad_str = f"{tmpl['radius']} km"
                
                txt = font_main.render(f"[{key_name}] {tmpl['name']} (M: {mass_str}, R: {rad_str})", True, tmpl['color'])
                screen.blit(txt, (px + 40, py + y_off))
                y_off += 35
                
            nav_next = font_main.render("[5] --> Larger Bodies", True, (130, 130, 130))
            screen.blit(nav_next, (px + 40, py + y_off))
                
            nav_txt = font_main.render("[ESC] Cancel", True, (150, 150, 150))
            screen.blit(nav_txt, (px + (pw - nav_txt.get_width())//2, py + ph - 40))
            
        elif self.state == 2 and self.selected_template is not None:
            title = font_title.render(f"=== SELECT ORBIT FOR {self.selected_template['name'].upper()} ===", True, (255, 255, 255))
            screen.blit(title, (px + (pw - title.get_width())//2, py + 20))
            
            y_off = 80
            
            txt = font_main.render("[1] Stationary (Drop)", True, (200, 200, 200))
            screen.blit(txt, (px + 40, py + y_off)); y_off += 30
            
            # Top body
            y_off += 20
            if self.top_body:
                if self.selected_template['mass'] < data.MASS[self.top_body.idx]:
                    header = font_main.render(f"Around TOP MASS: {self.top_body.name}", True, (255, 200, 100))
                    screen.blit(header, (px + 30, py + y_off)); y_off += 30
                    
                    o1 = font_main.render("[2] Circular Orbit", True, (100, 255, 100))
                    screen.blit(o1, (px + 40, py + y_off)); y_off += 25
                    
                    o2 = font_main.render("[3] Eccentric Orbit", True, (255, 255, 100))
                    screen.blit(o2, (px + 40, py + y_off)); y_off += 25
                    
                    o3 = font_main.render("[4] Plunge Trajectory (Intersect)", True, (255, 100, 100))
                    screen.blit(o3, (px + 40, py + y_off)); y_off += 25
                else:
                    header = font_main.render(f"Cannot orbit TOP MASS (Spawn mass too high)", True, (150, 100, 100))
                    screen.blit(header, (px + 30, py + y_off)); y_off += 30
            
            # Closest body
            y_off += 20
            if self.closest_body and self.closest_body != self.top_body:
                if self.selected_template['mass'] < data.MASS[self.closest_body.idx]:
                    header = font_main.render(f"Around CLOSEST: {self.closest_body.name}", True, (100, 200, 255))
                    screen.blit(header, (px + 30, py + y_off)); y_off += 30
                    
                    o1 = font_main.render("[6] Circular Orbit", True, (100, 255, 100))
                    screen.blit(o1, (px + 40, py + y_off)); y_off += 25
                    
                    o2 = font_main.render("[7] Eccentric Orbit", True, (255, 255, 100))
                    screen.blit(o2, (px + 40, py + y_off)); y_off += 25
                else:
                    header = font_main.render(f"Cannot orbit CLOSEST (Spawn mass too high)", True, (150, 100, 100))
                    screen.blit(header, (px + 30, py + y_off)); y_off += 30
                    
            y_off += 20
            o_lagrange = font_main.render("[8] Lagrange Point Mode", True, (200, 150, 255))
            screen.blit(o_lagrange, (px + 40, py + y_off)); y_off += 25
                    
            nav_txt = font_main.render("[ESC] Cancel", True, (150, 150, 150))
            screen.blit(nav_txt, (px + (pw - nav_txt.get_width())//2, py + ph - 40))

        elif self.state == 3:
            title = font_title.render(f"=== LAGRANGE: SELECT PAIR ===", True, (255, 255, 255))
            screen.blit(title, (px + (pw - title.get_width())//2, py + 20))
            
            y_off = 80
            p_idx = getattr(self, 'lagrange_primary_idx', -1)
            s_idx = getattr(self, 'lagrange_secondary_idx', None)
            num_bodies = len(data.FLAGS)
            
            if p_idx != -1 and p_idx < num_bodies and (data.FLAGS[p_idx] & 1):
                p_mass = data.MASS[p_idx]
                p_name = next((b.name for b in getattr(self, 'bodies', []) if b.idx == p_idx), f"Body {p_idx}")
                t1 = font_main.render(f"Primary: {p_name} (Mass: {p_mass:.2e})", True, (255, 200, 100))
                screen.blit(t1, (px + 40, py + y_off)); y_off += 40
                
                if s_idx is not None and s_idx < num_bodies and (data.FLAGS[s_idx] & 1):
                    s_mass = data.MASS[s_idx]
                    s_name = next((b.name for b in getattr(self, 'bodies', []) if b.idx == s_idx), f"Body {s_idx}")
                    t2 = font_main.render(f"Target: {s_name} (Mass: {s_mass:.2e})", True, (100, 200, 255))
                    screen.blit(t2, (px + 40, py + y_off)); y_off += 40
                    
                    t3 = font_main.render("[TAB] Cycle Target", True, (200, 200, 200))
                    screen.blit(t3, (px + 40, py + y_off)); y_off += 30
                    
                    t4 = font_main.render("[Y] Confirm Pair", True, (100, 255, 100))
                    screen.blit(t4, (px + 40, py + y_off)); y_off += 30
                else:
                    t = font_main.render("No valid targets available.", True, (255, 100, 100))
                    screen.blit(t, (px + 40, py + y_off))
            else:
                t = font_main.render("Primary body not valid.", True, (255, 100, 100))
                screen.blit(t, (px + 40, py + y_off))
                
            nav_txt = font_main.render("[ESC] Cancel", True, (150, 150, 150))
            screen.blit(nav_txt, (px + (pw - nav_txt.get_width())//2, py + ph - 40))

        elif self.state == 4:
            title = font_title.render(f"=== LAGRANGE: SELECT POINT ===", True, (255, 255, 255))
            screen.blit(title, (px + (pw - title.get_width())//2, py + 20))
            
            y_off = 80
            for i in range(1, 6):
                t = font_main.render(f"[{i}] Point L{i}", True, (200, 200, 200))
                screen.blit(t, (px + 40, py + y_off)); y_off += 30
                
            nav_txt = font_main.render("[ESC] Cancel", True, (150, 150, 150))
            screen.blit(nav_txt, (px + (pw - nav_txt.get_width())//2, py + ph - 40))

    def get_ghost_markers(self):
        """Espone le cinque posizioni analitiche dei punti di Lagrange della coppia
        selezionata, per l'anteprima live disegnata a schermo prima della conferma
        (solo allo stato 4, il passo finale della diramazione Lagrange)."""
        if not self.active or self.state != 4: return None
        if getattr(self, 'lagrange_primary_idx', None) is not None and getattr(self, 'lagrange_secondary_idx', None) is not None:
            p_idx = self.lagrange_primary_idx
            s_idx = self.lagrange_secondary_idx
            num_bodies = len(data.FLAGS)
            
            if p_idx == -1 or s_idx == -1 or p_idx >= num_bodies or s_idx >= num_bodies:
                return None
                
            if not ((data.FLAGS[p_idx] & 1) and (data.FLAGS[s_idx] & 1)):
                return None
                
            m1 = data.MASS[p_idx]
            pos1 = data.POS[p_idx]
            vel1 = data.VEL[p_idx]
            m2 = data.MASS[s_idx]
            pos2 = data.POS[s_idx]
            vel2 = data.VEL[s_idx]
            
            return get_lagrange_points(m1, pos1, m2, pos2, vel1, vel2)
        return None

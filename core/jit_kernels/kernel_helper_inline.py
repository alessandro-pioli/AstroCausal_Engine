from numba import njit
import numpy as np
import math

SOFTENING_SQ = 100.0
# --- MATRICE DI CAMPIONAMENTO ---
# 1. CASO SOLE (Enorme + Lento): Dettaglio estremo per le cuspidi
STEP_SUN_SQ = 2000.0 * 2000.0 

# 2. CASO ORBITA (Veloce): Passo lungo per massimizzare la storia visibile
STEP_ORBIT_SQ = 20000.0 * 20000.0

# 3. CASO DRIFT (Piccolo + Lento): Passo lunghissimo per non sprecare buffer
STEP_DRIFT_SQ = 100000.0 * 100000.0

# Soglie di classificazione
RAD_HUGE = 40000.0  
VEL_FAST_SQ = 5.0  

# Costanti Flags (Duplicate qui per inline)
FLAG_ALIVE = 1
FLAG_DYING = 2

## ==============================================================================
# MOTORE DI COLLISIONE INLINE (SEQUENZIALE & SICURO)
# ==============================================================================
@njit(fastmath=True, cache=True)
def resolve_collisions_step(n_bodies, pos_arr, vel_arr, acc_arr, mass_arr, rad_arr, flags_arr, void_val, g_const, rs_factor, dt, collision_cooldown):
    """
    Risolve le collisioni con fisica ramificata (Singolarità vs Corpi Solidi).
    - Auto-detect Buchi Neri (se rs > 0.1% del raggio visivo).
    - Accretion Disk Hitbox differenziata.
    - Crescita del raggio Lineare per BH, Volumetrica per corpi normali.
    - Ancoraggio del Baricentro per ingestioni a distanza.
    - Pre-passo O(N): cache raggi reali + max_move per filtro spaziale.
      vel_arr viene toccato solo per le coppie che superano il filtro geometrico.
    """
    # EARLY EXIT: Se il cooldown è attivo, nessuna collisione è fisicamente possibile
    if collision_cooldown[0] > 0:
        collision_cooldown[0] -= 1
        return

    # A passo temporale ridotto (dt->0), BH_ACCRETION_MULT tende a 1.0 per orizzonti tangenti.
    # Limita l'accrescimento del BH: 10.0 * dt è il tasso di accrescimento dinamico scalato sul passo dt,
    # con un limite massimo fittizio di 100.0 per garantire stabilità numerica.
    BH_ACCRETION_MULT=max(1.0, min(10.0 * dt, 100.0))
    BH_THRESHOLD=0.001

    # EMRI guard: per una coppia a rapporto di massa >= 100:1 con un BH, il corpo grande
    # cattura il piccolo a 1.9*rs invece di 1.0*rs, assorbendolo PRIMA della fascia
    # singolare di Paczynski-Wiita. A DT finito quella fascia inietta energia e "spara via"
    # il corpo (cannone EMRI): assorbirlo prima e' una regolarizzazione-per-assorbimento.
    # Attivo solo col floor sotto 1.9 (DT piccolo); a DT grande il mult e' gia' >= 1.9 e
    # i BBH a massa comparabile restano a contatto fra orizzonti tangenti.
    # Guardia per assorbimento preventivo a 1.9 volte rs (limite orizzonte allargato prima dell'ISCO)
    emri_guard = BH_ACCRETION_MULT < 1.9
    emri_delta = (1.9 - BH_ACCRETION_MULT)    # * massa_grande = raggio extra

    # --- PRE-PASSO O(N): calcola real_r e is_bh UNA VOLTA per corpo ---
    # + trova la velocità massima per il filtro spaziale del CCD
    real_r_cache=np.empty(n_bodies, dtype=np.float64)
    is_bh_cache=np.zeros(n_bodies, dtype=np.bool_)
    max_v=0.0
    max_a_sq=0.0

    for i in range(n_bodies):
        if (flags_arr[i] & FLAG_ALIVE) == 0: continue
        if (flags_arr[i] & FLAG_DYING) != 0: continue
        if pos_arr[i, 0] <= void_val:        continue

        m=mass_arr[i]
        vis_r=rad_arr[i]
        rs=m * rs_factor
        is_bh=(rs >= vis_r * BH_THRESHOLD)
        is_bh_cache[i]=is_bh

        if is_bh:
            expanded_rs=rs * BH_ACCRETION_MULT
            # Limite massimo assoluto di 2.0e11 km per evitare che l'orizzonte di accrescimento di un SMBH esploda
            if expanded_rs > 2.0e11: expanded_rs=2.0e11
            real_r_cache[i]=expanded_rs
        else:
            real_r_cache[i]=vis_r

        vx=vel_arr[i, 0]
        vy=vel_arr[i, 1]
        v=math.sqrt(vx*vx + vy*vy)
        if v > max_v: max_v=v
        ax_i=acc_arr[i, 0]
        ay_i=acc_arr[i, 1]
        a_sq=ax_i*ax_i + ay_i*ay_i
        if a_sq > max_a_sq: max_a_sq=a_sq

    # Spostamento relativo massimo possibile in un tick (fattore 2: peggiore caso, corpi in rotta di collisione)
    max_move=max_v * dt * 2.0
    max_a=math.sqrt(max_a_sq)

    # --- CICLO O(N²): vel_arr NON viene toccato per le coppie lontane ---
    min_gap=1e30
    for i in range(n_bodies):
        if (flags_arr[i] & FLAG_ALIVE) == 0: continue
        if (flags_arr[i] & FLAG_DYING) != 0: continue
        if pos_arr[i, 0] <= void_val: continue

        real_r1=real_r_cache[i]
        is_bh1=is_bh_cache[i]
        px1=pos_arr[i, 0]
        py1=pos_arr[i, 1]
        m1=mass_arr[i]
        vis_r1=rad_arr[i]

        for j in range(i + 1, n_bodies):
            if (flags_arr[j] & FLAG_ALIVE) == 0: continue
            if (flags_arr[j] & FLAG_DYING) != 0: continue
            if pos_arr[j, 0] <= void_val: continue

            real_r2=real_r_cache[j]
            r_sum=real_r1 + real_r2

            # EMRI guard (loop-invariant: spento del tutto a DT grande): se la coppia ha
            # rapporto estremo, espandi il raggio di cattura del BH grande PRIMA del filtro.
            if emri_guard:
                m2j=mass_arr[j]
                # Soglia di rapporto di massa 90.0 per classificare il sistema come EMRI (Extreme Mass Ratio Inspiral)
                if is_bh1 and m1 > m2j * 90.0:
                    r_sum += r_sum*emri_delta
                elif is_bh_cache[j] and m2j > m1 * 90.0:
                    r_sum += r_sum*emri_delta

            dx=px1 - pos_arr[j, 0]

            # TRACKING MIN GAP: abs(dx)-r_sum è un lower bound sul gap reale
            gap_x=abs(dx) - r_sum
            if gap_x < min_gap: min_gap=gap_x

            # FILTRO SPAZIALE: equivalente a abs(dx) > r_sum + max_move
            if gap_x > max_move: continue
            dy=py1 - pos_arr[j, 1]
            if abs(dy) > r_sum + max_move: continue

            # Da qui: siamo potenzialmente vicini — procediamo con il check completo
            dist_sq=dx*dx + dy*dy
            real_touch_dist_sq=r_sum * r_sum

            collision_detected=False
            if dist_sq < real_touch_dist_sq:
                collision_detected=True
            else:
                # CCD: accediamo a vel_arr SOLO se il filtro spaziale è passato
                s_x=(vel_arr[i, 0] - vel_arr[j, 0]) * dt
                s_y=(vel_arr[i, 1] - vel_arr[j, 1]) * dt
                if (abs(dx) <= r_sum + abs(s_x)) and (abs(dy) <= r_sum + abs(s_y)):
                    s_len_sq=s_x*s_x + s_y*s_y
                    if s_len_sq > 0.0:
                        p0x=dx - s_x
                        p0y=dy - s_y
                        t=-(p0x * s_x + p0y * s_y) / s_len_sq
                        if 0.0 <= t <= 1.0:
                            c_x=p0x + t * s_x
                            c_y=p0y + t * s_y
                            if (c_x*c_x + c_y*c_y) < real_touch_dist_sq:
                                collision_detected=True

            if collision_detected:
                # --- COLLISIONE RILEVATA ---
                is_bh2=is_bh_cache[j]
                winner=i
                loser=j
                if mass_arr[j] > m1:
                    winner=j
                    loser=i

                idx_w=winner
                idx_l=loser

                mw=mass_arr[idx_w]
                ml=mass_arr[idx_l]
                rw=rad_arr[idx_w]
                rl=rad_arr[idx_l]

                is_winner_bh=is_bh1 if winner == i else is_bh2

                vw=vel_arr[idx_w]
                vl=vel_arr[idx_l]

                m_tot=mw + ml

                # --- CALCOLO PERDITA DI MASSA (Ejecta) ---
                if is_bh1 and is_bh2:
                    # Scontro BH-BH: Nessun detrito fisico. La massa persa è energia pura irradiata (GW).
                    # GW150914 ha irradiato ~4.6% della massa totale. Fissiamo un tetto relativistico empirico.
                    # Scontro BH-BH: 4.6% della massa totale convertita in energia gravitazionale (calibrato su GW150914)
                    loss_pct=0.046
                    m_new=m_tot * (1.0 - loss_pct)
                else:
                    # Scontro Materia Normale: Calcolo dei detriti basato sull'energia cinetica dell'impatto
                    dvx=vw[0] - vl[0]
                    dvy=vw[1] - vl[1]

                    v_imp_sq=dvx*dvx + dvy*dvy
                    r_tot=rw + rl
                    v_esc_sq=(2.0 * g_const * m_tot) / r_tot

                    violence=0.0
                    if v_esc_sq > 0.0000001:
                        violence=v_imp_sq / v_esc_sq

                    # Perdita di massa dinamica: 5% di base + 50% proporzionale alla violenza cinetica dell'impatto
                    loss_pct=0.05 + (0.50 * violence)
                    if loss_pct > 0.90: loss_pct=0.90

                    # La massa e il volume persi sono calcolati sul corpo più piccolo (Loser)
                    loss_mass=ml * loss_pct
                    m_new=mw + ml - loss_mass

                # --- FISICA FUSIONE (Inerzia e Baricentro) ---
                # Quantità di Moto sempre conservata
                vel_arr[idx_w, 0]=(vw[0] * mw + vl[0] * ml) / m_tot
                vel_arr[idx_w, 1]=(vw[1] * mw + vl[1] * ml) / m_tot

                # SPOSTAMENTO BARICENTRO: Avviene SOLO se c'è tocco tra i raggi visivi (Materia solida)
                vis_touch_dist_sq=(rw + rl) * (rw + rl)
                if dist_sq < vis_touch_dist_sq:
                    pos_arr[idx_w, 0]=(pos_arr[idx_w, 0] * mw + pos_arr[idx_l, 0] * ml) / m_tot
                    pos_arr[idx_w, 1]=(pos_arr[idx_w, 1] * mw + pos_arr[idx_l, 1] * ml) / m_tot
                # Else: Il BH ha fagocitato il corpo dal disco di accrescimento, rimane perfettamente immobile.

                mass_arr[idx_w]=m_new

                # --- EVOLUZIONE DEL RAGGIO (Biforcazione Fisica) ---
                if is_winner_bh:
                    # Relatività Generale: Il raggio di una singolarità scala linearmente con la massa
                    rad_arr[idx_w]=rw * (m_new / mw)
                else:
                    # Fisica Euclidea: Il raggio di un pianeta solido scala col volume
                    # La perdita di volume è *molto* più severa se il corpo è insignificante
                    mass_ratio=ml / mw
                    vol_loss_pct=loss_pct + (1.0 - mass_ratio)**3
                    if vol_loss_pct > 1.0: vol_loss_pct=1.0

                    v_w=rw*rw*rw
                    v_l=rl*rl*rl
                    loss_vol=v_l * vol_loss_pct
                    new_vol=v_w + v_l - loss_vol
                    rad_arr[idx_w]=new_vol**(1.0/3.0)

                flags_arr[idx_l] |= FLAG_DYING
                # Aggiornamento Variabili Locali per Catene di Collisioni
                if winner == i:
                    m1=mass_arr[i]
                    vis_r1=rad_arr[i]
                    rs1=m1 * rs_factor
                    is_bh1=(rs1 > vis_r1 * BH_THRESHOLD)
                    real_r1=max(vis_r1, rs1 * BH_ACCRETION_MULT) if is_bh1 else vis_r1
                    # Aggiorna la cache: i tick successivi del loop j vedono i valori corretti
                    real_r_cache[i]=real_r1
                    is_bh_cache[i]=is_bh1
                else:
                    break

    # --- CALCOLO COOLDOWN DINAMICO (Cinematica Quadratica) ---
    if min_gap > 0.0:
        max_v_rel=max_v * 2.0
        max_a_rel=max_a * 2.0
        if max_a_rel > 1e-30:
            safe_time=(-max_v_rel + math.sqrt(max_v_rel*max_v_rel + 2.0*max_a_rel*min_gap)) / max_a_rel
        elif max_v_rel > 1e-30:
            safe_time=min_gap / max_v_rel
        else:
            safe_time=1e15
        safe_ticks=int(safe_time / dt)
        # Cap di velocita' + clamp (anti-tunneling dei plunge frontali a L=0, che bypassano
        # l'espansione-raggio dei BH ed erano gli unici a tunnelare). La stima cinematica ad
        # accelerazione costante sovrastima il tempo al contatto in caduta 1/r^2 e, a passo
        # grosso, puo' saltare oltre l'urto. I corpi non si chiudono piu' veloci di ~0.75c
        # (relativo, per il freno relativistico), quindi non saltiamo oltre min_gap/(0.75c*dt)
        # tick: garantisce almeno un controllo CCD ogni 0.75c*dt di spazio percorribile. Il
        # clamp a 3e5 km evita che a dt grande (dove 0.75c*dt e' enorme) il CCD venga forzato
        # inutilmente su coppie ancora lontane. Sotto dt~1.33s il clamp non morde (reach =
        # 0.75c*dt < 3e5) e la protezione resta piena a 0.75c (es. pulsar nel blank a dt=1).
        ccd_reach = 0.75 * 299792.458 * dt
        # Limita il ccd_reach a 3.0e5 km (pari a 1 secondo-luce) per evitare controlli superflui a dt grandi
        if ccd_reach > 3.0e5: ccd_reach = 3.0e5
        ccd_cap = int(min_gap / ccd_reach)
        if ccd_cap < safe_ticks: safe_ticks = ccd_cap
        if safe_ticks > 10000: safe_ticks=10000
        collision_cooldown[0]=safe_ticks
# ==============================================================================
# HELPER: SCIE ADATTIVE (Zero Divisioni)
# ==============================================================================
@njit(inline='always', fastmath=True, cache=True)
def update_trail_logic(i, pos_x, pos_y, vel_x, vel_y, radius, trail_buf, trail_heads, trail_last_pos, force_write):
    """
    LOGICA MATRICE 2x2 (RAGGIO vs VELOCITÀ)
    """
    # 1. Recupera ultima posizione
    last_x = trail_last_pos[i, 0]
    last_y = trail_last_pos[i, 1]
    
    # 2. Calcola spostamento (Delta)
    dx = pos_x - last_x
    dy = pos_y - last_y
    dist_sq = dx*dx + dy*dy
    
    # 3. MATRICE DECISIONALE
    n_bodies = trail_buf.shape[0]
    if n_bodies < 5:
        # Se i corpi sono meno di 5, dettaglio massimo per tutti i corpi
        thresh_dist = STEP_SUN_SQ
    else:
        v_sq = vel_x*vel_x + vel_y*vel_y
        is_huge = radius > RAD_HUGE
        is_fast = v_sq > VEL_FAST_SQ
        
        if is_huge:
            if is_fast:
                # Enorme e Veloce (Stella Binaria) -> Tratta come orbita
                thresh_dist = STEP_ORBIT_SQ
            else:
                # Enorme e Lento (SOLE!) -> Dettaglio massimo per cuspidi
                thresh_dist = STEP_SUN_SQ
        else:
            if is_fast:
                # Piccolo e Veloce (Pianeta) -> Tratta come orbita (per avere storia)
                thresh_dist = STEP_ORBIT_SQ
            else:
                # Piccolo e Lento (Asteroide) -> Risparmio
                thresh_dist = STEP_DRIFT_SQ

    # 4. Confronto e Scrittura
    if force_write or dist_sq > thresh_dist:
        
        head = trail_heads[i]
        cap = trail_buf.shape[1]
        
        trail_buf[i, head, 0] = pos_x
        trail_buf[i, head, 1] = pos_y
        
        new_head = head + 1
        if new_head >= cap: new_head = 0
        trail_heads[i] = new_head
        
        trail_last_pos[i, 0] = pos_x
        trail_last_pos[i, 1] = pos_y


        

@njit(inline='always', fastmath=True, cache=True)
def solve_retarded_time(dx, dy, vx, vy, a_term):
    """
    Risolve l'equazione del tempo di volo per la propagazione causale.
    Ottimizzato per inlining JIT.
    """
    # 1. Prodotti scalari e quadrati
    dist_sq = dx*dx + dy*dy
    d_dot_v = dx*vx + dy*vy
    
    # 2. Coefficiente 'b' dimezzato (half_b)
    # Eq originale: a*T^2 + b*T + c = 0
    # b = -2*(D.v)  --> half_b = -(D.v)
 
    
    # 3. Delta Ridotto
    delta_reduced = d_dot_v*d_dot_v + a_term*dist_sq
    
    # Limite causale (cono di luce)
    if delta_reduced < 0.0: return -1.0

    # 4. Soluzione dell'equazione causale
    # Caso limite ultra-relativistico (a_term -> 0)
    if a_term < 1e-4:
        # Se l'oggetto si allontana, l'intersezione causale nel passato è impossibile
        if d_dot_v >= 0.0: return -1.0
        return dist_sq / (-2.0 * d_dot_v)

    # Caso standard (quadratica ridotta)
    # Si sceglie la radice positiva per il tempo passato
    return (d_dot_v + math.sqrt(delta_reduced)) / a_term


# ==============================================================================
# HELPER: CALCOLO FORZA RELATIVISTICA (Paczyński-Wiita + 2.5PN Radiation Reaction)
# ==============================================================================
@njit(inline='always', fastmath=True, cache=True)
def compute_relativistic_force(my_x, my_y, my_vx, my_vy, my_rad, src_x, src_y, src_vx, src_vy, src_ax, src_ay, src_mass, src_rad, src_px, src_py, mass_arr, inv_c, c_sq, g_const, rs_factor, m_chirp_mult, my_idx, tick_counter, dt):
    """Calcola la forza gravitazionale relativistica integrando il potenziale di Paczynski-Wiita e la reazione di radiazione 2.5PN."""
    # 1. Dati Iniziali (Geometria Passata)
    dx_old = src_x - my_x
    dy_old = src_y - my_y
    dist_sq_old = dx_old*dx_old + dy_old*dy_old + SOFTENING_SQ
    dist_visual = math.sqrt(dist_sq_old) 
    min_dist = my_rad + src_rad
    if dist_visual < min_dist:
        scale = min_dist / dist_visual
        dx_old *= scale
        dy_old *= scale
        dist_visual = min_dist
        dist_sq_old = dist_visual * dist_visual
    
    # ---- SOGLIE RELATIVISTICHE ----
    v_sq = src_vx*src_vx + src_vy*src_vy
    
    r_s = src_mass * rs_factor
    threshold_gw = 0.0025 * c_sq
    threshold_lw = 0.25 * c_sq
    
    # 2. Dead Reckoning Ibrido 
    time_of_flight = dist_visual * inv_c
    
    is_gw = (v_sq > threshold_gw) and (dist_visual < (r_s * 1000.0))
    
    if is_gw:
        # Regime GW: si utilizza la posizione attuale per prevenire errori di aberrazione
        eff_x = src_px
        eff_y = src_py
    else:
        eff_x = src_x + src_vx * time_of_flight + 0.5 * src_ax * time_of_flight * time_of_flight
        eff_y = src_y + src_vy * time_of_flight + 0.5 * src_ay * time_of_flight * time_of_flight
    
    dx = eff_x - my_x
    dy = eff_y - my_y

    if is_gw:
        # Distanza attuale per evitare eccentricità spuria causata da correzioni O((v/c)^2)
        dist = math.sqrt(dx * dx + dy * dy + SOFTENING_SQ)
    else:
        dot_v_r = dx_old * src_vx + dy_old * src_vy
        correction = dot_v_r * inv_c
        dist = dist_visual + correction

    if dist < 1.0: dist = 1.0

    # 3. Newton + Potenziale di Paczyński-Wiita
    r_s = src_mass * rs_factor
    dist_pw = dist - r_s
    
    # Sicurezza: Se cadiamo OLTRE l'Orizzonte degli Eventi, la forza esplode ma non va in NaN
    if dist_pw < 1.0: 
        dist_pw = 1.0

    # Vettore = (1 / r) * (1 / (r - rs)^2)
    inv_dist3 = 1.0 / (dist * dist_pw * dist_pw) 
    scalar = (g_const * src_mass) * inv_dist3
    
    # 4. Correzione Liénard-Wiechert (Check Relativistico)
    threshold_lw = 0.25 * c_sq
    
    if v_sq > threshold_lw:
        lw_denominator = dist 
        if lw_denominator < 1e-3: lw_denominator = 1e-3
        doppler_factor = dist_visual / lw_denominator
        scalar *= doppler_factor

    ax = dx * scalar
    ay = dy * scalar

    # 5. RADIATION REACTION (Esattore delle Tasse 2.5 PN)
    # Gatekeeper calibrato: > 5% della velocità della luce (15.000 km/s) e vicinanza estrema
    if is_gw:
        rel_vx = my_vx - src_vx
        rel_vy = my_vy - src_vy
        v_rel_sq = rel_vx*rel_vx + rel_vy*rel_vy
        
        # Stampa telemetria ogni 0.25 s di simulazione; nell'endgame passa a 1 ms
        # per non lasciare cieca la spazzolata finale. Soglia scale-aware: 120 km
        # copre le NS, 6*r_s i buchi neri (il loro contatto e' a centinaia di km).
        if my_idx == 0:
            telemetry_period = 0.001 if dist < max(120.0, r_s * 6.0) else 0.25
            if int(tick_counter / telemetry_period)!= int((tick_counter - dt) / telemetry_period):
                f_gw = math.sqrt(v_rel_sq) / (math.pi * dist)
                int_part = int(f_gw)
                frac_part = int(round((f_gw - int_part) * 100))
                if frac_part >= 100:
                    int_part += 1
                    frac_part -= 100
                if frac_part < 10:
                    f_gw_str = str(int_part) + ".0" + str(frac_part)
                else:
                    f_gw_str = str(int_part) + "." + str(frac_part)
                d_str = str(int(dist))
                v_str = str(int(math.sqrt(v_rel_sq)))
                # Timestamp di simulazione a 4 decimali (0.1 ms), formattato a mano
                # perche' Numba in nopython non supporta f-string/format.
                t_int_part = int(tick_counter)
                t_frac_part = int(round((tick_counter - t_int_part) * 10000.0))
                if t_frac_part >= 10000:
                    t_int_part += 1
                    t_frac_part -= 10000
                if t_frac_part < 10:
                    t_str = str(t_int_part) + ".000" + str(t_frac_part)
                elif t_frac_part < 100:
                    t_str = str(t_int_part) + ".00" + str(t_frac_part)
                elif t_frac_part < 1000:
                    t_str = str(t_int_part) + ".0" + str(t_frac_part)
                else:
                    t_str = str(t_int_part) + "." + str(t_frac_part)
                print("T: " + t_str + " s | D: " + d_str + " km | V_rel: " + v_str + " km/s | F_GW: " + f_gw_str + " Hz")
                
        inv_c5 = inv_c * inv_c * inv_c * inv_c * inv_c

        # --- Reazione di radiazione 2.5PN REALE (Formulazione Damour-Deruelle) ---
        my_mass = mass_arr[my_idx]
        M_pair = my_mass + src_mass
        mu_pair = my_mass * src_mass / M_pair

        sep_sq = dx * dx + dy * dy
        inv_sep = 1.0 / math.sqrt(sep_sq)
        nx = dx * inv_sep
        ny = dy * inv_sep
        rdot = nx * rel_vx + ny * rel_vy
        rdot_sq = rdot * rdot
        gm_over_r = g_const * M_pair * inv_sep

        # Calcolo del precursore di accoppiamento corretto (8/5)
        pref = (8.0 / 5.0) * (g_const * g_const) * M_pair * mu_pair * inv_c5 * (inv_sep / sep_sq)
        
        # Coefficienti di espansione 2.5PN per la reazione di radiazione di Damour-Deruelle
        coeff_n = rdot * (18.0 * v_rel_sq + (2.0 / 3.0) * gm_over_r - 25.0 * rdot_sq)
        coeff_v = 6.0 * v_rel_sq - 2.0 * gm_over_r - 15.0 * rdot_sq

        # Calcolo dell'accelerazione relativa coerente
        a_rel_x = pref * (coeff_n * nx - coeff_v * rel_vx)
        a_rel_y = pref * (coeff_n * ny - coeff_v * rel_vy)

        share = (src_mass / M_pair) * m_chirp_mult
        ax += share * a_rel_x
        ay += share * a_rel_y

    return ax, ay

# ==============================================================================
# HELPER: CALCOLO POTENZIALE (PHI) UNIFICATO
# ==============================================================================
@njit(inline='always', fastmath=True, cache=True)
def calculate_potential_contribution(
    # Coordinate Target
    target_x, target_y,
    # Dati Corpo Sorgente
    px, py, vx, vy,  mass, rad,  
    # Buffer Storici Corpo Sorgente
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    i, # Indice corpo
    # Costanti
    c_sq, c_threshold_sq, inv_c, inv_dt, void_val
):
    """
    Calcola il contributo al potenziale (GM/r) con supporto Deep Space Accelerato.
    """
    
    # 1. Check Relativistico & Delay
    dx_now = target_x - px
    dy_now = target_y - py
    v_sq = vx*vx + vy*vy
    relativistic = v_sq >= c_threshold_sq
    
    t_delay = 0.0
    if relativistic:
        a_term = c_sq - v_sq
        # Approssimazione del cono di luce basata sulla velocità attuale (non iterativa per prestazioni)
        t_delay = solve_retarded_time(dx_now, dy_now, vx, vy, a_term)
        if t_delay < 0.0: return 0.0
    else:
        dist_now = math.sqrt(dx_now*dx_now + dy_now*dy_now)
        t_delay = dist_now * inv_c

    ticks = int(t_delay * inv_dt)
    
    # 2. Retrieval Storico
    ret_x, ret_y, ret_vx, ret_vy = 0.0, 0.0, 0.0, 0.0
    ret_mass = mass
    valid = False
    
    # L0
    if ticks < len_L0:
        ptr = (heads_L0[i] - ticks) & mask_L0
        if h_L0[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L0[i, ptr, 0], h_L0[i, ptr, 1]
            ret_vx, ret_vy = h_L0[i, ptr, 2], h_L0[i, ptr, 3]
            ret_mass = h_L0[i, ptr, 4]
            valid = True
    # L1
    elif ticks < (len_L1 << 5):
        ptr = (heads_L1[i] - (ticks >> 5)) & mask_L1
        if h_L1[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L1[i, ptr, 0], h_L1[i, ptr, 1]
            ret_vx, ret_vy = h_L1[i, ptr, 2], h_L1[i, ptr, 3]
            ret_mass = h_L1[i, ptr, 4]
            valid = True
    # L2
    elif ticks < (len_L2 << 8):
        ptr = (heads_L2[i] - (ticks >> 8)) & mask_L2
        if h_L2[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L2[i, ptr, 0], h_L2[i, ptr, 1]
            ret_vx, ret_vy = h_L2[i, ptr, 2], h_L2[i, ptr, 3]
            ret_mass = h_L2[i, ptr, 4]
            valid = True
    
    # --- DEEP SPACE CON MOTORE ARTIFICIALE ---
    else:
        # CUTOFF RELATIVISTICO: Per velocità estreme (v >= 0.1c), ci affidiamo solo alla storia reale del buffer (L2)
        if relativistic:
            return 0.0
            
        # Verifica riempimento del buffer storico per l'estrapolazione lineare nel passato
        is_history_full = False

        if len_L2 > 0:
            ptr_tail = (heads_L2[i] + 1) & mask_L2
            if h_L2[i, ptr_tail, 0] > void_val: is_history_full = True
        elif len_L1 > 0:
            ptr_tail = (heads_L1[i] + 1) & mask_L1
            if h_L1[i, ptr_tail, 0] > void_val: is_history_full = True
        elif len_L0 > 0:
            ptr_tail = (heads_L0[i] + 1) & mask_L0
            if h_L0[i, ptr_tail, 0] > void_val: is_history_full = True


        if is_history_full:
            ret_x = px - vx * t_delay
            ret_y = py - vy * t_delay
            ret_vx = vx
            ret_vy = vy
            valid = True
            
    if not valid: return 0.0

    # 3. Fisica (Liénard-Wiechert)
    dx_ret = target_x - ret_x
    dy_ret = target_y - ret_y
    dist_geom = math.sqrt(dx_ret*dx_ret + dy_ret*dy_ret + rad*rad) 
    
    lw_denom = dist_geom
    if relativistic:
        dot_v_r = ret_vx * dx_ret + ret_vy * dy_ret
        lw_denom = dist_geom - (dot_v_r * inv_c)
    
    if lw_denom < 1.0: lw_denom = 1.0
    
    return ret_mass / lw_denom


# ==============================================================================
# HELPER: CALCOLO ONDE (DPHI/DT) - DEEP SPACE INERZIALE
# ==============================================================================
@njit(inline='always', fastmath=True, cache=True)
def calculate_dphi_contribution(
    target_x, target_y,
    px, py, mass, rad,
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    i, 
    inv_c, inv_dt, void_val
):
    """Calcola la variazione temporale del potenziale gravitazionale dPhi/dt indotta dal movimento del corpo."""
    # --- 1. PRIMA STIMA (basata sul presente) ---
    dx_now = target_x - px
    dy_now = target_y - py
    dist_sq_now = dx_now*dx_now + dy_now*dy_now
    
    if dist_sq_now < (rad*rad): return 0.0

    dist_now = math.sqrt(dist_sq_now)
    t_delay_est = dist_now * inv_c
    ticks_est = int(t_delay_est * inv_dt)
    
    ret_x, ret_y = 0.0, 0.0
    ret_mass = mass
    valid_est = False
    
    if ticks_est < len_L0:
        ptr = (heads_L0[i] - ticks_est) & mask_L0
        if h_L0[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L0[i, ptr, 0], h_L0[i, ptr, 1]
            ret_mass = h_L0[i, ptr, 4]
            valid_est = True
    elif ticks_est < (len_L1 << 5):
        ptr = (heads_L1[i] - (ticks_est >> 5)) & mask_L1
        if h_L1[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L1[i, ptr, 0], h_L1[i, ptr, 1]
            ret_mass = h_L1[i, ptr, 4]
            valid_est = True
    elif ticks_est < (len_L2 << 8):
        ptr = (heads_L2[i] - (ticks_est >> 8)) & mask_L2
        if h_L2[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L2[i, ptr, 0], h_L2[i, ptr, 1]
            ret_mass = h_L2[i, ptr, 4]
            valid_est = True

    # --- DEEP SPACE CON MOTORE ARTIFICIALE ---
    else:
        is_history_full = False
        if len_L2 > 0:
            ptr_tail = (heads_L2[i] + 1) & mask_L2
            if h_L2[i, ptr_tail, 0] > void_val: is_history_full = True
        elif len_L1 > 0:
            ptr_tail = (heads_L1[i] + 1) & mask_L1
            if h_L1[i, ptr_tail, 0] > void_val: is_history_full = True
        elif len_L0 > 0:
            ptr_tail = (heads_L0[i] + 1) & mask_L0
            if h_L0[i, ptr_tail, 0] > void_val: is_history_full = True

        if is_history_full:
            ret_x = px
            ret_y = py
            valid_est = True

    if not valid_est: return 0.0

    # --- 2. RICALCOLO CAUSALE (Il centro del compasso diventa il passato) ---
    dx_true = target_x - ret_x
    dy_true = target_y - ret_y
    dist_true = math.sqrt(dx_true*dx_true + dy_true*dy_true)
    
    # Ricalcoliamo i ticks usando la VERA distanza percorsa dall'onda
    true_ticks = int(dist_true * inv_c * inv_dt)
    
    ret_vx, ret_vy = 0.0, 0.0
    is_deep_space = False
    
    # ESTRAZIONE DEFINITIVA DEI DATI
    if true_ticks < len_L0:
        ptr = (heads_L0[i] - true_ticks) & mask_L0
        ret_vx, ret_vy = h_L0[i, ptr, 2], h_L0[i, ptr, 3]
        ret_x, ret_y = h_L0[i, ptr, 0], h_L0[i, ptr, 1]
        ret_mass = h_L0[i, ptr, 4]
    elif true_ticks < (len_L1 << 5):
        ptr = (heads_L1[i] - (true_ticks >> 5)) & mask_L1
        ret_vx, ret_vy = h_L1[i, ptr, 2], h_L1[i, ptr, 3]
        ret_x, ret_y = h_L1[i, ptr, 0], h_L1[i, ptr, 1]
        ret_mass = h_L1[i, ptr, 4]
    elif true_ticks < (len_L2 << 8):
        ptr = (heads_L2[i] - (true_ticks >> 8)) & mask_L2
        ret_vx, ret_vy = h_L2[i, ptr, 2], h_L2[i, ptr, 3]
        ret_x, ret_y = h_L2[i, ptr, 0], h_L2[i, ptr, 1]
        ret_mass = h_L2[i, ptr, 4]
    else:
        # Nel deep space prendiamo la velocità corrente dall'head di L0 se possibile
        ret_vx, ret_vy = 0.0, 0.0
        if len_L0 > 0:
            last_ptr = (heads_L0[i] - 1) & mask_L0
            ret_vx, ret_vy = h_L0[i, last_ptr, 2], h_L0[i, last_ptr, 3]
        
        # Taglio netto del deep space quando si superano i 15.000 km/s per evitare artefatti a spirale ("beyblade")
        if (ret_vx * ret_vx + ret_vy * ret_vy) > 2.25e8:  # 15000^2
            return 0.0
            
        is_deep_space = True
        
    dx_final = target_x - ret_x
    dy_final = target_y - ret_y
    
    dot_prod = dx_final * ret_vx + dy_final * ret_vy
    
    if is_deep_space:
        lw_denom = dist_true
    else:
        lw_denom = dist_true - (dot_prod * inv_c)
        if lw_denom < 1.0: lw_denom = 1.0
    
    return ret_mass * dot_prod / (lw_denom * lw_denom * lw_denom)



@njit(inline='always', fastmath=True, cache=True)
def update_ligo_probe_step(n_bodies, pos_arr, vel_arr, mass_arr, flags_arr, 
                           probe_active, probe_pos, probe_buf, probe_head, probe_mask):
    """
    Sonda LIGO a lettura istantanea basata sul Quadrupolo.
    Bypassa la causalità visiva per evitare l'aliasing della compressione L1/L2.
    Calcola la polarizzazione h_plus tramite il proxy cinematico (vx² - vy²) delle
    velocità relative al centro di massa del sistema (V_COM), che riproduce esattamente
    la frequenza doppia (2ω) dell'onda gravitazionale ed è galileianamente invariante.
    """
    if not probe_active[0]:
        return

    # 1. Calcolo del centro di massa (V_COM) per i corpi vivi
    vcom_x = 0.0
    vcom_y = 0.0
    m_tot = 0.0
    for j in range(n_bodies):
        if (flags_arr[j] & FLAG_ALIVE) == 0:
            continue
        m = mass_arr[j]
        m_tot += m
        vcom_x += vel_arr[j, 0] * m
        vcom_y += vel_arr[j, 1] * m
    
    if m_tot > 0.0:
        vcom_x /= m_tot
        vcom_y /= m_tot

    strain_totale = 0.0
    px = probe_pos[0]
    py = probe_pos[1]
    
    for j in range(n_bodies):
        if (flags_arr[j] & FLAG_ALIVE) == 0: 
            continue
        
        # Distanza geometrica vera attuale dalla sonda
        dx = pos_arr[j, 0] - px
        dy = pos_arr[j, 1] - py
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1.0: 
            dist = 1.0
        
        # Velocità relative al baricentro istantaneo (V_COM)
        vx = vel_arr[j, 0] - vcom_x
        vy = vel_arr[j, 1] - vcom_y
        
        # PROXY QUADRUPOLARE CINEMATICO (Oscillazione h_plus)
        # Per orbite kepleriane, vx²-vy² ∝ cos(2ωt) tramite identità trigonometrica.
        # Questa forma è equivalente alla metà cinetica della seconda derivata del
        # momento di quadrupolo di massa (Ï_xx - Ï_yy), ed è numericamente stabile
        # perché limitata superiormente da c² grazie al freno relativistico γ.
        h_plus_quadrupole = vx*vx - vy*vy
        
        # Decadimento d'ampiezza 1/R rispettato
        strain = (mass_arr[j] * h_plus_quadrupole) / dist
        strain_totale += strain
    
    # Scrittura nel Ring Buffer
    head = probe_head[0]
    probe_buf[head] = strain_totale
    probe_head[0] = (head + 1) & probe_mask


@njit(inline='always', fastmath=True, cache=True)
def calculate_gw_contribution(
    target_x, target_y,
    px, py, mass, rad,
    h_L0, heads_L0, mask_L0, len_L0,
    h_L1, heads_L1, mask_L1, len_L1,
    h_L2, heads_L2, mask_L2, len_L2,
    i, 
    inv_c, inv_dt, void_val,
    vcom_x, vcom_y
):
    """
    Calcola la deformazione causale proiettata (GW strain) indotta dal moto
    del corpo k nel frame inerziale della binaria (con V_COM sottratta).
    """
    # --- 1. PRIMA STIMA (basata sul presente) ---
    dx_now = target_x - px
    dy_now = target_y - py
    dist_sq_now = dx_now*dx_now + dy_now*dy_now
    
    if dist_sq_now < (rad*rad): 
        return 0.0

    dist_now = math.sqrt(dist_sq_now)
    t_delay_est = dist_now * inv_c
    ticks_est = int(t_delay_est * inv_dt)
    
    ret_x, ret_y = 0.0, 0.0
    ret_mass = mass
    valid_est = False
    
    if ticks_est < len_L0:
        ptr = (heads_L0[i] - ticks_est) & mask_L0
        if h_L0[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L0[i, ptr, 0], h_L0[i, ptr, 1]
            ret_mass = h_L0[i, ptr, 4]
            valid_est = True
    elif ticks_est < (len_L1 << 5):
        ptr = (heads_L1[i] - (ticks_est >> 5)) & mask_L1
        if h_L1[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L1[i, ptr, 0], h_L1[i, ptr, 1]
            ret_mass = h_L1[i, ptr, 4]
            valid_est = True
    elif ticks_est < (len_L2 << 8):
        ptr = (heads_L2[i] - (ticks_est >> 8)) & mask_L2
        if h_L2[i, ptr, 0] > void_val:
            ret_x, ret_y = h_L2[i, ptr, 0], h_L2[i, ptr, 1]
            ret_mass = h_L2[i, ptr, 4]
            valid_est = True
    else:
        is_history_full = False
        if len_L2 > 0:
            ptr_tail = (heads_L2[i] + 1) & mask_L2
            if h_L2[i, ptr_tail, 0] > void_val: is_history_full = True
        elif len_L1 > 0:
            ptr_tail = (heads_L1[i] + 1) & mask_L1
            if h_L1[i, ptr_tail, 0] > void_val: is_history_full = True
        elif len_L0 > 0:
            ptr_tail = (heads_L0[i] + 1) & mask_L0
            if h_L0[i, ptr_tail, 0] > void_val: is_history_full = True

        if is_history_full:
            ret_x = px
            ret_y = py
            valid_est = True

    if not valid_est: 
        return 0.0

    # --- 2. RICALCOLO CAUSALE (Il centro del compasso diventa il passato) ---
    dx_true = target_x - ret_x
    dy_true = target_y - ret_y
    dist_true = math.sqrt(dx_true*dx_true + dy_true*dy_true)
    if dist_true < rad:
        return 0.0
    
    true_ticks = int(dist_true * inv_c * inv_dt)
    
    ret_vx, ret_vy = 0.0, 0.0
    
    if true_ticks < len_L0:
        ptr = (heads_L0[i] - true_ticks) & mask_L0
        ret_vx, ret_vy = h_L0[i, ptr, 2], h_L0[i, ptr, 3]
        ret_x, ret_y = h_L0[i, ptr, 0], h_L0[i, ptr, 1]
        ret_mass = h_L0[i, ptr, 4]
    elif true_ticks < (len_L1 << 5):
        ptr = (heads_L1[i] - (true_ticks >> 5)) & mask_L1
        ret_vx, ret_vy = h_L1[i, ptr, 2], h_L1[i, ptr, 3]
        ret_x, ret_y = h_L1[i, ptr, 0], h_L1[i, ptr, 1]
        ret_mass = h_L1[i, ptr, 4]
    elif true_ticks < (len_L2 << 8):
        ptr = (heads_L2[i] - (true_ticks >> 8)) & mask_L2
        ret_vx, ret_vy = h_L2[i, ptr, 2], h_L2[i, ptr, 3]
        ret_x, ret_y = h_L2[i, ptr, 0], h_L2[i, ptr, 1]
        ret_mass = h_L2[i, ptr, 4]
    else:
        if len_L0 > 0:
            last_ptr = (heads_L0[i] - 1) & mask_L0
            ret_vx, ret_vy = h_L0[i, last_ptr, 2], h_L0[i, last_ptr, 3]

    dx_final = target_x - ret_x
    dy_final = target_y - ret_y
    r_geom = math.sqrt(dx_final*dx_final + dy_final*dy_final)
    if r_geom < rad:
        r_geom = rad
    if r_geom < 1.0:
        r_geom = 1.0

    # Sottrazione del moto di COM
    vx_rel = ret_vx - vcom_x
    vy_rel = ret_vy - vcom_y

    # Proiezione del quadrupolo
    nx = dx_final / r_geom
    ny = dy_final / r_geom
    h_plus_proj = (vx_rel*vx_rel - vy_rel*vy_rel) * (nx*nx - ny*ny) + 4.0 * (vx_rel * vy_rel) * (nx * ny)

    # Radiazione Far-Field (1/R)
    return (ret_mass * h_plus_proj) / r_geom
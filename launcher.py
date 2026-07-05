import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import subprocess
import core.presets as presets
import core.data as data
from core.data import AU_IN_KM

def format_unit(val):
    abs_v = abs(val)
    if abs_v >= AU_IN_KM * 0.1:
        return f"{val/AU_IN_KM:.4f} AU"
    elif abs_v >= 1000000:
        return f"{val/1000000.0:.2f}M km"
    else:
        return f"{val:.0f} km"

# ==============================================================================
# TOOLTIP CLASS
# ==============================================================================
class ToolTip(object):
    """Classe helper per mostrare tooltip esplicativi sui widget."""
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # millisecondi prima del popup
        self.wraplength = 180   # pixel prima di andare a capo
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

# ==============================================================================
# DATABASE PRESET & INFO
# ==============================================================================
PRESETS_DB = {
    "Sistema Solare Completo": {
        "desc": "Il nostro ecosistema planetario completo: Sole, 8 pianeti principali, Plutone e le lune più grandi. Le orbite sono inizializzate al pericentro con velocità kepleriana risolta numericamente sul potenziale di Paczyński-Wiita per garantire la massima stabilità fisica.\nConsigliato: Visualizzazione Phi Scalare per i pozzi gravitazionali o Roche per esplorare le sfere di Hill dei pianeti maggiori.",
        "dt": "150.0"
    },
    "Sistema Solare (Leggero)": {
        "desc": "La versione semplificata del Sistema Solare (solo il Sole e i 9 pianeti maggiori, senza satelliti naturali). Consente di osservare la stabilità kepleriana a lungo termine su qualsiasi hardware grazie a un DT incrementato (512 s/step).\nConsigliato: Heatmap Phi per analizzare la geometria statica e pulita dei campi gravitazionali.",
        "dt": "512.0"
    },
    "Sistema Solare: Orbita Galattica (Sgr A*)": {
        "desc": "Il Sistema Solare viaggia a 230 km/s in orbita galattica attorno a Sagittarius A* (il buco nero supermassiccio centrale da 4.1 milioni di M\u2609). Test per osservare il comportamento del campo gravitazionale e della stabilità orbitale sotto una traslazione globale ad alta velocità (boost di 230 km/s).\nConsigliato: Heatmap Phi per osservare come i campi locali rimangano stabili e non distorti nonostante la velocità globale di sistema.",
        "dt": "512.0"
    },
    "Ammasso Caotico (100 Corpi)": {
        "desc": "Stress-test N-Body estremo con 100 corpi massicci che orbitano in modo caotico attorno a un buco nero centrale da 1000 M\u2609.\nGUIDA PERFORMANCE: Data l'estrema richiesta computazionale, gioca con i tasti T (dimezza DT, aumenta precisione) e Y (raddoppia DT, riduce precisione) per gestire la velocità mantenendo buoni FPS. Evita velocità engine (tasti 1-5) troppo elevate. Premere H per spegnere completamente le heatmap grafiche disattivando il campo aumenta drasticamente le prestazioni.",
        "dt": "1.0"
    },
    "Terra - Luna - ISS - Hubble": {
        "desc": "Problema a più corpi reale in regime geocentrico. Include l'orbita ellittica reale della Luna, la Stazione Spaziale Internazionale (ISS) attiva e controllabile dal giocatore (tasti WASD) e il Telescopio Spaziale Hubble passivo in orbita circolare stabile.\nLAGRANGE HUNTER GUIDE: Per far emergere naturalmente i punti di Lagrange (L1-L5), seleziona la Luna premendo il tasto TAB a ripetizione (o facendo doppio click su di essa per bloccare la camera), quindi premi L per attivare il Roche Lagrange Hunter. Regola il fader della sensibilità sullo schermo e usa lo zoom per visualizzare i lobi gravitazionali e le valli stabili.",
        "dt": "1.0"
    },
    "Sole - Terra - Luna - Artemis II (Motors Off)": {
        "desc": "La navicella Artemis II (Orion + modulo di servizio, ~26 tonnellate) in crociera translunare passiva (\"motors off\"). Scenario eliocentrico reale con il Sole al centro cartesiano e Terra e Luna che gli orbitano attorno, ideale per mostrare la transizione degli spazi gravitazionali efficaci.\nConsigliato: Roche Lagrange Hunter per mappare l'interazione dei campi durante l'avvicinamento lunare.",
        "dt": "1.0"
    },
    "Sistema Gioviano Completo": {
        "desc": "Giove e le sue 13 lune principali, divise tra lune interne, galileiane in risonanza e lune irregolari esterne.\nTIDAL STRESS GUIDE: Premi H fino ad attivare la Tidal Map (Mappa delle Forze di Marea). Potrai osservare chiaramente l'intenso stress gravitazionale esercitato da Giove sulle lune più interne, in particolare su Io: questa continua azione mareale è la causa diretta del suo eccezionale vulcanismo (il corpo geologicamente più attivo del Sistema Solare).",
        "dt": "60.0"
    },
    "Approccio alla Velocità della Luce (ART) [0.999c -> c] - 20 gb RAM ver": {
        "desc": "Il Sole lanciato a 0.999c con Accelerazione Relativistica Artificiale (ART) che viola il freno fisico. Man mano che v->c, i campi si schiacchiano e la coda causale L0->L1->L2 collassa in una singolarità ottica. Richiede 20 GB di RAM di picco in fase di costruzione (10 GB operativi) a causa dell'enorme buffer di storici necessari a coprire 320 anni luce di storia causale. SOLO la heatmap Phi (potenziale scalare) possiede il ramo relativistico che gestisce la distorsione in questo contesto.\nConsigliato: Utilizzare molto i tasti da 1 a 5 per regolare la velocità di simulazione. Premi TAB o fai doppio click sul Sole per monitorare la velocità in tempo reale.",
        "dt": "0.16"
    },
    "Approccio alla Velocità della Luce (ART) [0.9c -> c] - LIGHT 10 gb RAM ver": {
        "desc": "Versione alleggerita dello scenario relativistico che parte da una velocità inferiore (0.9c) consentendo di osservare la progressiva distorsione del campo. Richiede 10 GB di RAM di picco in fase di costruzione (5 GB operativi) coprendo ben 1742 anni luce di storia causale con DT=1.6. SOLO la heatmap Phi possiede il ramo relativistico che gestisce la distorsione in questo contesto.\nConsigliato: Utilizzare molto i tasti da 1 a 5 per regolare la velocità di simulazione. Premi TAB o fai doppio click sul Sole per monitorare la velocità in tempo reale.",
        "dt": "1.6"
    },
    "Approccio alla Velocità della Luce (ART) [0.7c -> c] - ULTRA-LIGHT 5 gb RAM ver": {
        "desc": "Versione ultra-alleggerita dello scenario relativistico. Partendo da 0.7c, permette di apprezzare la transizione dinamica da un campo gravitazionale sferico al disco piatto di Liénard-Wiechert man mano che v si approssima a c. Richiede solo 5 GB di RAM di picco in fase di costruzione (2.5 GB operativi) coprendo ben 8710 anni luce di storia causale con DT=16.0. SOLO la heatmap Phi gestisce questo ramo relativistico.\nConsigliato: Utilizzare molto i tasti da 1 a 5 per regolare la velocità di simulazione. Premi TAB o fai doppio click sul Sole per monitorare la velocità in tempo reale.",
        "dt": "16.0"
    },
    "Stelle di Neutroni Binarie: Eccentricità Estrema": {
        "desc": "Due stelle di neutroni gemelle (~1.5 M\u2609) in orbite estremamente eccentriche attorno al comune baricentro. Il baricentro orbitale corrisponde esattamente alla metà della loro separazione al pericentro (200 km), con le orbite che si intrecciano velocemente.\nConsigliato: DPHI per osservare l'onda quadrupolare impulsiva al pericentro.",
        "dt": "0.000001"
    },
    "Stelle di Neutroni Binarie: Orbita Stabile": {
        "desc": "Due stelle di neutroni (~1.5 M\u2609) in orbita circolare stabile a 40.000 km. Stato di riferimento pre-inspiral. L'irraggiamento di onde gravitazionali a questa distanza produce un decadimento orbitale reale ma lento, con fusione prevista su scala di secoli.\nConsigliato: DPHI per l'onda quadrupolare pura del sistema binario.",
        "dt": "0.001"
    },
    "Stelle di Neutroni Binarie: Pre-Collisione": {
        "desc": "Late Inspiral di due stelle di neutroni separate da soli 375 km. Il collasso finale e la fusione avvengono in circa 60 secondi di tempo simulato.\nGUIDA OPERATIVA: La modalità DPHI (onde gravitazionali) è obbligatoria. Premi P per posizionare la sonda LIGO sullo schermo (non troppo vicina al centro per evitarne la distruzione prematura). Per salvare il dump NPY dei dati prima della collisione, premi nuovamente P (disattivando la sonda) o chiudi la simulazione tornando al launcher. Usa i tasti da 1 a 5 per accelerare la simulazione, ma NON PREMERE T o Y: la fisica relativistica 2.5PN è tarata sul DT iniziale (1e-6) e alterarlo rovinerebbe irrimediabilmente il chirp ondulatorio.",
        "dt": "0.000001"
    },
    "GW170817: Merger Stelle di Neutroni": {
        "desc": "Replica dell'evento GW170817 a f_GW = 50 Hz. Il collasso gravitazionale e la conseguente kilonova avvengono in circa 14 secondi di tempo simulato.\nGUIDA OPERATIVA: La visualizzazione DPHI è obbligatoria. Premi P per posizionare la sonda LIGO a debita distanza dal baricentro orbitale per catturarne lo strain. Salva il dump dei dati disattivando la sonda con P prima dell'impatto o chiudendo la simulazione tornando al launcher. Regola la velocità tramite i tasti 1-5, ma evita rigorosamente i tasti T e Y per non compromettere le correzioni relativistiche calibrate sul DT di partenza.",
        "dt": "0.000001"
    },
    "GW150914: Merger Buchi Neri": {
        "desc": "Il primo storico segnale di onde gravitazionali rilevato da LIGO. Due buchi neri da 36 e 29 M\u2609 (source frame) si fondono in circa 52 secondi di tempo simulato (52.034 s misurati, contro i ~55 attesi da Peters e dalla relativit\u00e0 numerica SXS; errore medio del chirp vs NR: 1.27%).\nGUIDA OPERATIVA: Usa la mappa DPHI (tasto H) per tracciare i fronti d'onda concentrici. Distribuisci la sonda LIGO premendo P a distanza adeguata (non troppo vicina). Salva premendo di nuovo P o chiudendo la simulazione tornando al launcher per eseguire l'analisi spettrale nel LIGO Analyzer. Regola i passi dell'engine con i tasti 1-5 ma NON alterare il DT con T o Y per preservare la calibrazione del chirp relativistico.",
        "dt": "0.000001"
    },
    "GW190814: Merger Asimmetrico (Mass Gap)": {
        "desc": "Il merger pi\u00f9 asimmetrico osservato all'epoca (q = 0.112): un buco nero da 23 M\u2609 ingoia un oggetto misterioso da 2.6 M\u2609 nel 'mass gap', la stella di neutroni pi\u00f9 pesante o il buco nero pi\u00f9 leggero mai rilevato, senza controparte elettromagnetica. La coalescenza avviene in circa 20 secondi di tempo simulato (inizializzazione Peters a T-20s, f_GW iniziale ~15 Hz, ISCO a ~162 Hz).\nGUIDA OPERATIVA: Usa DPHI (tasto H) o GW Strain (tasto L con corpo bloccato) per il chirp asimmetrico. Premi P per posizionare la sonda LIGO a debita distanza; salva il dump premendo di nuovo P prima dell'impatto o chiudendo la simulazione tornando al launcher. Regola la velocit\u00e0 con i tasti 1-5 ma NON usare T o Y: la fisica 2.5PN \u00e8 tarata sul DT iniziale (1e-6).",
        "dt": "0.000001"
    },
    "Alpha Centauri + Sistema Polyphemus (Avatar)": {
        "desc": "Sistema triplo reale (\u03b1 Cen A+B+Proxima) con il Sistema Polyphemus da Avatar (gigante gassoso + Pandora + 4 lune in phase-locking). Sfasamenti angolari forzati a multipli di 45\u00b0 per garantire la stabilità.\nConsigliato: Roche per le sfere di Hill stellari, Phi Scalare per i tre campi sovrapposti.",
        "dt": "2.0"
    },
    "Laboratorio Orbite Estreme": {
        "desc": "Laboratorio didattico con un buco nero centrale (1000 M\u2609) e 5 particelle test su corsie separate: Circolare (e=0), Ellittica (e=0.6), Alta Eccentricit\u00e0 (e=0.95), Iperbolica (fuga), Retrograda Circolare.\nConsigliato: Phi Scalare per osservare le deformazioni e la precessione delle isolinee di potenziale.",
        "dt": "0.2"
    },
    "EMRI: Plunge Relativistico": {
        "desc": "Extreme Mass Ratio Inspiral: un buco nero da 10 M\u2609 spiraleggia verso un BH da 1000 M\u2609 (rapporto 1:100). Il collasso e il plunge finale avvengono in esattamente 13 giorni e 10 ore di tempo simulato. Se al posto del buco nero minore vi fosse una stella comune, verrebbe fatta a pezzi dalle forze mareali estreme già alla prima rivoluzione (fenomeno osservabile attivando la Tidal Heatmap).\nConsigliato: Usa la modalità DPHI (tasto H) per seguire le onde concentriche ed accelera la simulazione con i tasti 4 e 5 per coprire l'intera durata del plunge.",
        "dt": "0.05"
    },
    "Scontro fra Galassie Nane": {
        "desc": "Due galassie nane (65.000 M\u2609 + 100 stelle ciascuna) in collisione quasi-frontale. Ciano vs Magenta per tracciare la rimescolazione stellare durante la fusione.\nGUIDA PERFORMANCE: A causa del grandissimo numero di interazioni (202 corpi), ottimizza i frame rate premendo H per spegnere le heatmap. Usa T (riduzione DT) e Y (aumento DT) con parsimonia per controllare la stabilità dell'engine, e usa i moltiplicatori di velocità 1-5 con attenzione per evitare scatti durante lo scontro.",
        "dt": "150.0"
    },
    "Scenario Vuoto (Blank)": {
        "desc": "Universo completamente vuoto con parametri di default. Nessun corpo pre-esistente. Ideale per costruire scenari personalizzati.\nGUIDA CREAZIONE: Premi il tasto N per attivare lo Spawner Orbitale. Usa i tasti 0 e 5 per sfogliare le categorie di corpi celesti e 1-4 per selezionare l'oggetto. Successivamente, scegli la modalità di orbita (Stazionaria, Circolare/Eccentrica attorno alla massa maggiore o al corpo più vicino, o seleziona la modalità Punti di Lagrange per inserire il corpo stabilmente co-rotante su L1-L5).",
        "dt": "1.0"
    }
}

# ==============================================================================
# MAIN LAUNCHER APP
# ==============================================================================
class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Astro Causal Sim - Pre-Flight Launcher")
        self.geometry("750x780")
        self.configure(bg="#1E1E1E")
        self.resizable(False, False)

        # Stile Moderno Tkinter (ttk)
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except:
            pass
        
        # Colori e configurazioni palette stile
        bg_col = "#1E1E1E"
        fg_col = "#D4D4D4"
        accent_col = "#007ACC"
        
        style.configure('TFrame', background=bg_col)
        style.configure('TLabel', background=bg_col, foreground=fg_col, font=('Segoe UI', 12))
        style.configure('Header.TLabel', font=('Segoe UI', 17, 'bold'), foreground="#FFFFFF")
        style.configure('TCombobox', fieldbackground="#FFFFFF", background="#FFFFFF", foreground="#000000")
        style.configure('TEntry', fieldbackground="#2D2D2D", foreground="#FFFFFF")
        style.configure('Launch.TButton', font=('Segoe UI', 15, 'bold'), background=accent_col, foreground=fg_col)
        style.configure('Ligo.TButton', font=('Segoe UI', 13, 'bold'), background="#5A2E8A", foreground=fg_col)
        style.map('Launch.TButton', background=[('active', '#005A9E')])
        style.map('Ligo.TButton', background=[('active', '#7A3EAA')])

        # Contenitore Principale
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- TITOLO ---
        title_label = ttk.Label(main_frame, text="Astro Causal Physics Engine", style='Header.TLabel')
        title_label.pack(pady=(0, 5))
        subtitle_label = ttk.Label(main_frame, text="Numba JIT | CPU-Driven | Float64 Precision", foreground="#888888", font=('Segoe UI', 10))
        subtitle_label.pack(pady=(0, 20))

        # --- SEZIONE 1: PRESET SELECTION ---
        preset_frame = tk.LabelFrame(main_frame, text=" Scelta Scenario Dinamico ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        preset_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(preset_frame, text="Scenario Replicato:").pack(anchor=tk.W, pady=(0, 5))
        
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, state='readonly', values=list(PRESETS_DB.keys()))
        self.preset_combo.pack(fill=tk.X, ipady=4)
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_change)

        # Area di testo per descrizione Preset
        # Area testuale più grande
        self.desc_text = tk.Text(preset_frame, height=8, bg="#2D2D2D", fg="#D4D4D4", font=('Segoe UI', 11), wrap=tk.WORD, borderwidth=1, relief="sunken")
        self.desc_text.pack(fill=tk.X, pady=(10, 5))
        self.desc_text.insert(tk.END, "Seleziona uno scenario per leggerne i dettagli.")
        self.desc_text.config(state=tk.DISABLED)

        # Informazioni READ-ONLY del Preset (Ricavate dinamicamente prima del boot)
        info_frame = ttk.Frame(preset_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.lbl_bodies = ttk.Label(info_frame, text="Corpi: N/A", font=('Segoe UI', 10, 'bold'), foreground="#A0C0FF")
        self.lbl_bodies.grid(row=0, column=0, sticky=tk.W, padx=(0, 15))
        ToolTip(self.lbl_bodies, "Totale reale dei corpi celesti pre-generati per questo preset al frame 0.")

        self.lbl_rad = ttk.Label(info_frame, text="Sim Radius: N/A", font=('Segoe UI', 10), foreground="#C0A0FF")
        self.lbl_rad.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        ToolTip(self.lbl_rad, "Il raggio massimo entro cui forze e campi mantengono la causalità (propagazione alla velocità della luce c, letta dai buffer storici). Oltre questo raggio l'interazione torna newtoniana istantanea.")

        self.lbl_step = ttk.Label(info_frame, text="Ideal Step: N/A", font=('Segoe UI', 10), foreground="#FFC0A0")
        self.lbl_step.grid(row=0, column=2, sticky=tk.W)
        ToolTip(self.lbl_step, "Il moltiplicatore della velocità (1x, 10x, ecc) raccomandato per far scorrere lo scenario ad occhio nudo fluidamente ma senza saltare dettagli critici.")

        # --- SEZIONE 2: PARAMETRI HARDWARE/CORE ---
        settings_frame = tk.LabelFrame(main_frame, text=" Core Settings ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        settings_frame.pack(fill=tk.X, pady=(0, 20))

        # Risoluzione
        res_frame = ttk.Frame(settings_frame)
        res_frame.pack(fill=tk.X, pady=(0, 10))
        
        res_lbl = ttk.Label(res_frame, text="Risoluzione Rendering:")
        res_lbl.pack(side=tk.LEFT)
        ToolTip(res_lbl, text="RACCOMANDATO: 1200x800. \nPer via del Memory Wall architetturale, risoluzioni sopra il 1200x800 causeranno cache miss aggressivi ritardando drasticamente i calcoli su CPU nel rendering DPHI. Usare il 1920x1080 o 2K SOLO se si ha moltissima cache L3/L2 sul chip.")
        
        self.res_var = tk.StringVar(value="1200x800 (Racc.)")
        res_opts = ["1200x800 (Racc.)", "900x600 (Fast)", "1440x900", "1920x1080 (Heavy)", "FULL SCREEN"]
        self.res_combo = ttk.Combobox(res_frame, textvariable=self.res_var, state='readonly', values=res_opts, width=20)
        self.res_combo.pack(side=tk.RIGHT)

        # Delta Time
        dt_frame = ttk.Frame(settings_frame)
        dt_frame.pack(fill=tk.X)

        dt_lbl = ttk.Label(dt_frame, text="Delta Time Integratore (DT):")
        dt_lbl.pack(side=tk.LEFT)
        ToolTip(dt_lbl, text="Il tempo simulato (in secondi) avanzato a ogni step di fisica.\nUn DT piccolo (es. 1e-6) aumenta la precisione ma richiede più slot nei buffer storici per coprire il raggio causale (più RAM) e fa scorrere il tempo simulato lentamente.\nUn DT grande alleggerisce RAM e accelera il tempo simulato, a scapito della precisione numerica delle orbite.\nÈ fortemente raccomandato il valore fornito dallo scenario stesso!")

        self.dt_var = tk.StringVar(value="1.0")
        self.dt_entry = tk.Entry(dt_frame, textvariable=self.dt_var, bg="#2D2D2D", fg="#FFFFFF", font=('Segoe UI', 10), justify='right')
        self.dt_entry.pack(side=tk.RIGHT, ipadx=5, ipady=3)

        # --- SEZIONE 3: INIZIO ---
        launch_btn = ttk.Button(main_frame, text="INIZIALIZZA MOTORE", style='Launch.TButton', command=self.launch_simulation)
        launch_btn.pack(fill=tk.X, ipady=15, pady=(10, 0))

        # --- SEZIONE 4: LIGO ANALYZER ---
        ligo_frame = ttk.Frame(main_frame)
        ligo_frame.pack(fill=tk.X, pady=(45, 10))
        
        ligo_btn = ttk.Button(ligo_frame, text="LAUNCH LIGO ANALYZER UI", style='Ligo.TButton', command=self.launch_ligo)
        ligo_btn.pack(fill=tk.X, ipady=8)

        # Setup Default (Sistema Solare Completo)
        self.preset_combo.current(0)
        self.on_preset_change()

    def launch_ligo(self):
        print(f"===========================================================")
        print(f"[LAUNCHER] Avvio LIGO Analyzer Kernel Interface...")
        print(f"===========================================================")
        self.withdraw()
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ligo_path = os.path.join(base_dir, "ligo_analyzer.py")
            cmd = [sys.executable, ligo_path]
            subprocess.run(cmd, check=True)
        except Exception as e:
            messagebox.showerror("Errore Kernel", f"LIGO Analyzer non riuscito o chiuso con errore:\n{e}")
        self.deiconify()

    def on_preset_change(self, event=None):
        selected = self.preset_var.get()
        if selected in PRESETS_DB:
            info = PRESETS_DB[selected]
            
            # Aggiorna la descrizione testuale
            self.desc_text.config(state=tk.NORMAL)
            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert(tk.END, info["desc"])
            self.desc_text.config(state=tk.DISABLED)
            
            # Autocompila la suggestione per DT e popola labels
            self.dt_var.set(info.get("dt", "1.0"))
            self.lbl_bodies.config(text=f"Corpi Totali: {info.get('num_bodies', 0)}")
            sim_rad_val = info.get('sim_rad', 0.0)
            if sim_rad_val >= AU_IN_KM * 0.1:
                rad_str = f"{sim_rad_val/AU_IN_KM:.1f} AU"
            else:
                rad_str = format_unit(sim_rad_val)
            self.lbl_rad.config(text=f"Sim Radius: {rad_str}")
            self.lbl_step.config(text=f"Ideal Step Speed: {info.get('ideal_step', 1)}x")

    def launch_simulation(self):
        preset = self.preset_var.get()
        res_str = self.res_var.get()
        dt_str = self.dt_var.get()
        
        # Parsing Risoluzione
        w, h = 1200, 800
        if "FULL SCREEN" in res_str:
            w, h = -1, -1
        else:
            try:
                clean_res = res_str.split()[0] # Rimuove eventuali '(Racc.)' o '(Heavy)'
                w, h = map(int, clean_res.split('x'))
            except:
                pass # Fallback safe a 1200x800
            
        # Parsing DT
        try:
            dt_val = abs(float(dt_str))
            self.dt_var.set(str(dt_val)) # Forza la visualizzazione del valore assoluto positivo sulla GUI
        except ValueError:
            messagebox.showerror("Errore di compilazione", "Il Delta Time (DT) deve essere un numero valido.")
            return

        print(f"===========================================================")
        print(f"[LAUNCHER] Risveglio Kernel Richiesto per:")
        print(f" -> Preset: {preset}")
        print(f" -> Resolution: {'FULL SCREEN' if w == -1 else f'{w}x{h}'}")
        print(f" -> Override DT: {dt_val}")
        print(f"===========================================================")
        
        self.withdraw()  # Nascondiamo il launcher temporaneamente
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        main_gui_path = os.path.join(base_dir, "main_gui.py")
        
        cmd = [
            sys.executable, 
            main_gui_path,
            "--preset", preset,
            "--width", str(w),
            "--height", str(h)
        ]
        
        if dt_val is not None:
            cmd.extend(["--dt", str(dt_val)])
            
        try:
            # subprocess.run bloccherà il launcher finché main_gui.py non termina
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            # Il processo è uscito con un codice di errore
            messagebox.showerror("Errore Kernel", f"Il simulatore è crashato (Exit code {e.returncode}). Controlla i log della console per dettagli.")
        except Exception as e:
            messagebox.showerror("Errore Kernel", f"Impossibile avviare il simulatore:\n{e}")
            
        self.deiconify() # Risvegliamo il launcher quando il simulatore si spegne.


if __name__ == "__main__":
    print("[LAUNCHER] Generazione e calcolo attributi dinamici dei preset in corso...")
    for pname in PRESETS_DB.keys():
        try:
            data.RADAR_WARNING_TRIGGERED = False
            bodies, ideal_dt, sim_rad, ideal_step = presets.get_preset(pname)
            
            PRESETS_DB[pname]["dt"] = str(ideal_dt) 
            PRESETS_DB[pname]["num_bodies"] = len(bodies)
            PRESETS_DB[pname]["sim_rad"] = sim_rad
            PRESETS_DB[pname]["ideal_step"] = ideal_step
            del bodies # Wipe heavy objects immediately
        except Exception as e:
            print(f"[LAUNCHER] Fallimento letale durante pre-load del preset '{pname}': {e}")
            
    print("[LAUNCHER] Setup completato. Avvio GUI Tkinter.")
    app = LauncherApp()
    app.mainloop()

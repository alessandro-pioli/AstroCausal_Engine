import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import subprocess
import core.presets as presets
import core.data as data
from core.data import AU_IN_KM


def format_unit(val, au_decimals=4):
    """Formatta una distanza in km scegliendo l'unità leggibile (AU, milioni di km, km)."""
    abs_v = abs(val)
    if abs_v >= AU_IN_KM * 0.1:
        return f"{val/AU_IN_KM:.{au_decimals}f} AU"
    elif abs_v >= 1000000:
        return f"{val/1000000.0:.2f}M km"
    else:
        return f"{val:.0f} km"


# TOOLTIP CLASS
class ToolTip(object):
    """Classe helper per mostrare tooltip esplicativi sui widget."""
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # millisecondi prima del popup
        self.wraplength = 320   # pixel prima di andare a capo
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


# --- CATALOGO SCENARI ---
# Nomi ed etichette arrivano da core.presets.PRESET_REGISTRY, che è la sola fonte
# di verità: qui si costruiscono soltanto le viste che servono alla GUI (ordine del
# menu, mappa etichetta -> ID). L'ID è ciò che viene passato a main_gui via --preset,
# così le etichette restano puro testo di presentazione.
PRESET_IDS = presets.get_preset_ids()
PRESET_LABELS = [presets.PRESET_REGISTRY[pid]["label"] for pid in PRESET_IDS]
LABEL_TO_ID = {presets.PRESET_REGISTRY[pid]["label"]: pid for pid in PRESET_IDS}

# Attributi calcolati a runtime costruendo davvero ogni scenario una volta all'avvio
# (vedi il blocco __main__ in fondo al file). Chiave: ID del preset.
PRESET_INFO = {pid: {} for pid in PRESET_IDS}


# MAIN LAUNCHER APP
class LauncherApp(tk.Tk):
    def __init__(self):
        """Costruisce l'interfaccia pre-simulazione: la root Tk creata qui vive per
        l'intera sessione, mai distrutta né ricreata (§12 di ARCHITECTURE_DEEP_DIVE.md,
        il rimedio all'interprete Tcl singleton per processo)."""
        super().__init__()
        self.title("AstroCausal Engine - Pre-Flight Launcher")
        self.geometry("750x780")
        self.configure(bg="#1E1E1E")
        self.resizable(False, False)

        # Stile Moderno Tkinter (ttk)
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass  # tema non disponibile su questa piattaforma: si resta sul default

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
        title_label = ttk.Label(main_frame, text="AstroCausal Engine", style='Header.TLabel')
        title_label.pack(pady=(0, 5))
        subtitle_label = ttk.Label(main_frame, text="Numba JIT | CPU-Driven | Float64 Precision", foreground="#888888", font=('Segoe UI', 10))
        subtitle_label.pack(pady=(0, 20))

        # --- SEZIONE 1: PRESET SELECTION ---
        preset_frame = tk.LabelFrame(main_frame, text=" Scenario Selection ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        preset_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(preset_frame, text="Scenario:").pack(anchor=tk.W, pady=(0, 5))

        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, state='readonly', values=PRESET_LABELS)
        self.preset_combo.pack(fill=tk.X, ipady=4)
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_change)

        # Area di testo per la descrizione dello scenario selezionato
        self.desc_text = tk.Text(preset_frame, height=8, bg="#2D2D2D", fg="#D4D4D4", font=('Segoe UI', 11), wrap=tk.WORD, borderwidth=1, relief="sunken")
        self.desc_text.pack(fill=tk.X, pady=(10, 5))
        self.desc_text.insert(tk.END, "Select a scenario to read its details.")
        self.desc_text.config(state=tk.DISABLED)

        # Informazioni READ-ONLY del Preset (Ricavate dinamicamente prima del boot)
        info_frame = ttk.Frame(preset_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        self.lbl_bodies = ttk.Label(info_frame, text="Total Bodies: N/A", font=('Segoe UI', 10, 'bold'), foreground="#A0C0FF")
        self.lbl_bodies.grid(row=0, column=0, sticky=tk.W, padx=(0, 15))
        ToolTip(self.lbl_bodies, "Actual number of celestial bodies pre-generated by this scenario at frame 0.")

        self.lbl_rad = ttk.Label(info_frame, text="Sim Radius: N/A", font=('Segoe UI', 10), foreground="#C0A0FF")
        self.lbl_rad.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        ToolTip(self.lbl_rad, "The maximum radius within which forces and fields stay causal: gravitational information propagates at the speed of light c, read back from the history buffers. Beyond this radius the interaction falls back to instantaneous Newtonian gravity.")

        self.lbl_step = ttk.Label(info_frame, text="Ideal Step Speed: N/A", font=('Segoe UI', 10), foreground="#FFC0A0")
        self.lbl_step.grid(row=0, column=2, sticky=tk.W)
        ToolTip(self.lbl_step, "The speed multiplier (1x, 10x, ...) recommended for this scenario: fast enough to watch it unfold smoothly, slow enough not to skip critical detail.")

        # --- SEZIONE 2: PARAMETRI HARDWARE/CORE ---
        settings_frame = tk.LabelFrame(main_frame, text=" Core Settings ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        settings_frame.pack(fill=tk.X, pady=(0, 20))

        # Risoluzione
        res_frame = ttk.Frame(settings_frame)
        res_frame.pack(fill=tk.X, pady=(0, 10))

        res_lbl = ttk.Label(res_frame, text="Rendering Resolution:")
        res_lbl.pack(side=tk.LEFT)
        ToolTip(res_lbl, text="RECOMMENDED: 1200x800.\nThe heatmaps are computed pixel by pixel on the CPU, so going above 1200x800 pushes the working set past the cache and slows the dPhi/dt rendering down sharply. Pick 1920x1080 or higher ONLY if your CPU has a lot of L2/L3 cache.")

        # Il parsing in launch_simulation prende solo il primo token (`split()[0]`),
        # quindi il suffisso descrittivo è libero; la width segue la voce più lunga.
        res_opts = ["1200x800 (Recommended)", "900x600 (Fast)", "1440x900", "1920x1080 (Heavy)", "FULL SCREEN"]
        self.res_var = tk.StringVar(value=res_opts[0])
        self.res_combo = ttk.Combobox(res_frame, textvariable=self.res_var, state='readonly', values=res_opts, width=24)
        self.res_combo.pack(side=tk.RIGHT)

        # Delta Time
        dt_frame = ttk.Frame(settings_frame)
        dt_frame.pack(fill=tk.X)

        dt_lbl = ttk.Label(dt_frame, text="Integrator Time Step (DT):")
        dt_lbl.pack(side=tk.LEFT)
        ToolTip(dt_lbl, text="How much simulated time (in seconds) advances at each physics step.\nA small DT (e.g. 1e-6) raises precision, but needs more slots in the history buffers to cover the causal radius (more RAM) and makes simulated time crawl.\nA large DT saves RAM and speeds simulated time up, at the cost of numerical accuracy of the orbits.\nUsing the value supplied by the scenario itself is strongly recommended.")

        self.dt_var = tk.StringVar(value="1.0")
        self.dt_entry = tk.Entry(dt_frame, textvariable=self.dt_var, bg="#2D2D2D", fg="#FFFFFF", font=('Segoe UI', 10), justify='right')
        self.dt_entry.pack(side=tk.RIGHT, ipadx=5, ipady=3)

        # --- SEZIONE 3: INIZIO ---
        launch_btn = ttk.Button(main_frame, text="INITIALIZE ENGINE", style='Launch.TButton', command=self.launch_simulation)
        launch_btn.pack(fill=tk.X, ipady=15, pady=(10, 0))

        # --- SEZIONE 4: LIGO ANALYZER ---
        ligo_frame = ttk.Frame(main_frame)
        ligo_frame.pack(fill=tk.X, pady=(45, 10))

        ligo_btn = ttk.Button(ligo_frame, text="LAUNCH LIGO ANALYZER UI", style='Ligo.TButton', command=self.launch_ligo)
        ligo_btn.pack(fill=tk.X, ipady=8)

        # Selezione iniziale sul preset di default, non sul primo indice per posizione
        default_label = presets.get_preset_label(presets.DEFAULT_PRESET_ID)
        if default_label in PRESET_LABELS:
            self.preset_combo.current(PRESET_LABELS.index(default_label))
        else:
            self.preset_combo.current(0)
        self.on_preset_change()

    @property
    def selected_preset_id(self):
        """ID del preset attualmente scelto nel menu (None se l'etichetta è sconosciuta)."""
        return LABEL_TO_ID.get(self.preset_var.get())

    def launch_ligo(self):
        """Nasconde il launcher e lancia `ligo_analyzer.py` come sottoprocesso
        completamente isolato (`subprocess.run`, bloccante), lo stesso schema di
        `launch_simulation`: evita di ricreare una root Tk nello stesso processo
        dopo averne già una attiva. La finestra riappare al ritorno del figlio,
        anche se questo termina con un errore."""
        print("===========================================================")
        print("[LAUNCHER] Starting LIGO Analyzer kernel interface...")
        print("===========================================================")
        self.withdraw()
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ligo_path = os.path.join(base_dir, "ligo_analyzer.py")
            cmd = [sys.executable, ligo_path]
            subprocess.run(cmd, check=True)
        except Exception as e:
            messagebox.showerror("Kernel Error", f"LIGO Analyzer failed or exited with an error:\n{e}")
        self.deiconify()

    def on_preset_change(self, event=None):
        """Ripopola il pannello info col preset selezionato. I numeri mostrati
        (corpi totali, raggio causale, DT ideale) non sono statici: derivano dalla
        costruzione reale del preset fatta una volta all'avvio del launcher
        (`__main__` in fondo al file), non da un ricalcolo qui."""
        preset_id = self.selected_preset_id
        if preset_id is None:
            return

        info = PRESET_INFO.get(preset_id, {})

        # Aggiorna la descrizione testuale
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert(tk.END, presets.PRESET_REGISTRY[preset_id]["desc"])
        self.desc_text.config(state=tk.DISABLED)

        # Autocompila la suggestione per DT e popola labels
        self.dt_var.set(info.get("dt", "1.0"))
        self.lbl_bodies.config(text=f"Total Bodies: {info.get('num_bodies', 0)}")
        self.lbl_rad.config(text=f"Sim Radius: {format_unit(info.get('sim_rad', 0.0), au_decimals=1)}")
        self.lbl_step.config(text=f"Ideal Step Speed: {info.get('ideal_step', 1)}x")

    def launch_simulation(self):
        """Costruisce il comando completo per `main_gui.py` (preset, risoluzione
        fino a schermo intero, DT opzionale), nasconde il launcher e lo lancia come
        sottoprocesso isolato, bloccante su `subprocess.run`. Un exit code diverso
        da zero (`check=True`) diventa un dialogo d'errore invece di un crash del
        launcher stesso, che resta pronto a rilanciare (§12).

        Sulla riga di comando viaggia l'ID del preset, non la sua etichetta: è ASCII
        puro e senza spazi, quindi immune a problemi di quoting e di encoding."""
        preset_id = self.selected_preset_id
        if preset_id is None:
            messagebox.showerror("Selection Error", "No valid scenario selected.")
            return

        res_str = self.res_var.get()
        dt_str = self.dt_var.get()

        # Parsing Risoluzione
        w, h = 1200, 800
        if "FULL SCREEN" in res_str:
            w, h = -1, -1
        else:
            try:
                clean_res = res_str.split()[0]  # Rimuove eventuali '(Rec.)' o '(Heavy)'
                w, h = map(int, clean_res.split('x'))
            except (ValueError, IndexError):
                pass  # Fallback safe a 1200x800

        # Parsing DT
        try:
            dt_val = abs(float(dt_str))
            self.dt_var.set(str(dt_val))  # Forza la visualizzazione del valore assoluto positivo sulla GUI
        except ValueError:
            messagebox.showerror("Invalid Input", "The time step (DT) must be a valid number.")
            return

        if dt_val == 0.0:
            messagebox.showerror("Invalid Input", "The time step (DT) must be greater than zero.")
            return

        print("===========================================================")
        print("[LAUNCHER] Kernel wake-up requested for:")
        print(f" -> Scenario: {presets.get_preset_label(preset_id)}  [id: {preset_id}]")
        print(f" -> Resolution: {'FULL SCREEN' if w == -1 else f'{w}x{h}'}")
        print(f" -> DT override: {dt_val}")
        print("===========================================================")

        self.withdraw()  # Nascondiamo il launcher temporaneamente

        base_dir = os.path.dirname(os.path.abspath(__file__))
        main_gui_path = os.path.join(base_dir, "main_gui.py")

        cmd = [
            sys.executable,
            main_gui_path,
            "--preset", preset_id,
            "--width", str(w),
            "--height", str(h),
            "--dt", str(dt_val),
        ]

        try:
            # subprocess.run bloccherà il launcher finché main_gui.py non termina
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            # Il processo è uscito con un codice di errore
            messagebox.showerror("Kernel Error", f"The simulator crashed (exit code {e.returncode}). Check the console log for details.")
        except Exception as e:
            messagebox.showerror("Kernel Error", f"Could not start the simulator:\n{e}")

        self.deiconify()  # Risvegliamo il launcher quando il simulatore si spegne.


if __name__ == "__main__":
    print("[LAUNCHER] Building scenarios to read back their dynamic attributes...")
    for pid in PRESET_IDS:
        try:
            data.RADAR_WARNING_TRIGGERED = False
            bodies, ideal_dt, sim_rad, ideal_step = presets.get_preset(pid)

            PRESET_INFO[pid]["dt"] = str(ideal_dt)
            PRESET_INFO[pid]["num_bodies"] = len(bodies)
            PRESET_INFO[pid]["sim_rad"] = sim_rad
            PRESET_INFO[pid]["ideal_step"] = ideal_step
            del bodies  # Wipe heavy objects immediately
        except Exception as e:
            print(f"[LAUNCHER] Fatal failure while pre-loading scenario '{pid}': {e}")

    print("[LAUNCHER] Setup complete. Starting the Tkinter GUI.")
    app = LauncherApp()
    app.mainloop()

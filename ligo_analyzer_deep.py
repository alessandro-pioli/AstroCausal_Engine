import os
import glob
import datetime
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.scrolledtext as st

# ==============================================================================
# PHYSICAL CONSTANTS (SI units)
# ==============================================================================
G_SI   = 6.674e-11   # Gravitational constant [m^3 kg^-1 s^-2]
C_SI   = 2.998e8     # Speed of light [m/s]
M_SUN  = 1.989e30    # Solar mass [kg]


# ==============================================================================
# SIGNAL PROCESSING & PHYSICAL MODELS
# ==============================================================================
def apply_high_pass_filter(data, fs, cutoff=5.0, order=4):
    """Applies a Butterworth high-pass filter to isolate the relativistic strain."""
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    if normal_cutoff >= 1.0 or normal_cutoff <= 0.0:
        return data
    sos = signal.butter(order, normal_cutoff, btype='high', analog=False, output='sos')
    return signal.sosfiltfilt(sos, data)


def peters_frequency(t_to_merger, m_chirp_kg):
    """
    Computes the theoretical instantaneous frequency of a gravitational wave 
    before the merger using Peters' formula:
    f(t) = (1/pi) * (5/256)^(3/8) * (c^3 / (G * M_chirp))^(5/8) * (t_merger - t)^(-3/8)
    """
    t_to_merger = np.asarray(t_to_merger, dtype=np.float64)
    t_to_merger = np.where(t_to_merger > 0, t_to_merger, np.nan)
    factor_const = (5.0 / 256.0) ** (3.0 / 8.0)
    factor_mass = (C_SI**3 / (G_SI * m_chirp_kg)) ** (5.0 / 8.0)
    return (1.0 / np.pi) * factor_const * factor_mass * (t_to_merger ** (-3.0 / 8.0))


def peters_chirp_mass_from_rate(f_hz, dfdt_hz_per_s):
    """
    Inversion of Peters' formula to estimate the chirp mass from the 
    measured frequency (f) and its rate of change (df/dt):
    M_chirp = (c^3/G) * (5/(96*pi^(8/3)) * df/dt / f^(11/3))^(3/5)
    """
    if f_hz <= 0 or dfdt_hz_per_s <= 0:
        return None
    ratio = (5.0 / (96.0 * np.pi**(8.0/3.0))) * dfdt_hz_per_s / (f_hz**(11.0/3.0))
    return (C_SI**3 / G_SI) * (ratio ** (3.0/5.0))


def peters_chirp_mass_from_freq(f_hz, tau_s):
    """
    Massa chirp dalla FORMA della curva di Peters f(tau) = A * tau^(-3/8),
    invertita punto per punto (non dalla pendenza df/dt). A e' fissato dalla
    legge di Peters, da cui:
        M_chirp = (c^3/G) / [ f * pi * tau^(3/8) / (5/256)^(3/8) ]^(8/5)
    Usando la forma della curva invece della derivata, e' insensibile al bias
    del fit lineare su una power-law e all'oscillazione residua: dove la traccia
    coincide con Peters, restituisce la massa esatta.
    """
    k = (5.0 / 256.0) ** (3.0 / 8.0)
    bracket = (f_hz * np.pi * (tau_s ** (3.0 / 8.0))) / k
    return (C_SI**3 / G_SI) / (bracket ** (8.0 / 5.0))


# ==============================================================================
# TELEMETRY POPUP WINDOW & SCONTRINO (RECEIPT)
# ==============================================================================
class LigoTelemetryReportWindow(tk.Toplevel):
    """Displays analysis results in a clean, terminal-like telemetry report window (scaled up for readability)."""
    def __init__(self, parent, results, raw_logs):
        super().__init__(parent)
        self.title("LIGO SIGNAL ANALYSIS — TELEMETRY REPORT (DEEP)")
        self.geometry("710x870")
        self.configure(bg="#0B0F19")
        self.resizable(True, True)
        
        # Center the window relative to the parent
        try:
            self.update_idletasks()
            w, h = 710, 870
            x = parent.winfo_x() + (parent.winfo_width() - w) // 2
            y = parent.winfo_y() + (parent.winfo_height() - h) // 2
            self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self.receipt_text = self.generate_receipt(results, raw_logs)
        self._build_ui(results)

    def _build_ui(self, results):
        # Helper to add rows to grids with scaled up fonts
        def add_row(parent, label, value, row, font=('Segoe UI', 11, 'bold'), fg="#9CA3AF", val_font=('Consolas', 11), val_fg="#E5E7EB"):
            tk.Label(parent, text=label, font=font, fg=fg, bg="#0B0F19").grid(row=row, column=0, sticky='w', padx=12, pady=5)
            tk.Label(parent, text=str(value), font=val_font, fg=val_fg, bg="#0B0F19").grid(row=row, column=1, sticky='w', padx=12, pady=5)

        # 1. Header Banner
        header = tk.Frame(self, bg="#111827", bd=1, relief=tk.RAISED)
        header.pack(fill=tk.X, padx=18, pady=(18, 12))
        tk.Label(header, text="LIGO SIGNAL ANALYSIS REPORT (DEEP)", font=('Segoe UI', 14, 'bold'), fg="#00F0FF", bg="#111827", anchor='w').pack(fill=tk.X, padx=18, pady=10)
        
        # 2. Metadata Frame
        meta = tk.LabelFrame(self, text=" INFO TELEMETRIA ", font=('Segoe UI', 11, 'bold'), bg="#0B0F19", fg="#00F0FF", bd=1, relief=tk.GROOVE)
        meta.pack(fill=tk.X, padx=18, pady=6)
        add_row(meta, "File Dump:", results['file_name'], 0)
        add_row(meta, "F-Campione:", f"{results['fs']:.3f} Hz", 1)
        add_row(meta, "Risoluzione DT:", f"{results['dt']:.3e} s", 2)
        
        mode_color = "#39FF14" if results['final_mode'] == 'SPECTRAL' else "#FF9900"
        add_row(meta, "Modalità Finale:", results['final_mode'], 3, val_font=('Segoe UI', 11, 'bold'), val_fg=mode_color)

        # 3. Gatekeeper classifier
        gk = tk.LabelFrame(self, text=" SIGNAL CLASSIFIER — GATEKEEPER ", font=('Segoe UI', 11, 'bold'), bg="#0B0F19", fg="#39FF14", bd=1, relief=tk.GROOVE)
        gk.pack(fill=tk.X, padx=18, pady=6)
        add_row(gk, "Decisione:", results['gatekeeper_decision'], 0, val_font=('Segoe UI', 11, 'bold'))
        reason = results['gatekeeper_reason'] or "Nessuna fluttuazione (scelta manuale/ottimale)"
        add_row(gk, "Motivazione:", reason, 1, val_font=('Segoe UI', 11, 'italic'), val_fg="#D1D5DB")

        # 4. Mode-specific results
        res_frame = tk.LabelFrame(self, text=" REPORT DELLE METRICHE DI SEGNALE ", font=('Segoe UI', 11, 'bold'), bg="#0B0F19", fg="#00F0FF", bd=1, relief=tk.GROOVE)
        res_frame.pack(fill=tk.X, padx=18, pady=6)
        
        if results['final_mode'] == 'SPECTRAL':
            m_frame = tk.Frame(res_frame, bg="#0B0F19")
            m_frame.pack(fill=tk.X, padx=12, pady=6)
            
            est = results['estimated_m_chirp_solar']
            est_str = f"{est:.4f} M_sol" if est is not None else "N/D (df/dt non valido)"
            add_row(m_frame, "Massa Chirp Stimata:", est_str, 0, val_font=('Segoe UI', 12, 'bold'), val_fg="#39FF14")
            
            exp = results['expected_m_chirp_solar']
            exp_str = f"{exp:.4f} M_sol" if exp is not None else "Non inserita"
            add_row(m_frame, "Massa Chirp Attesa:", exp_str, 1, val_fg="#D1D5DB")
            
            err = results['error_pct']
            err_str = f"{err:.2f}%" if err is not None else "Nessun confronto"
            err_color = "#39FF14" if err is not None and err < 5 else ("#FF9900" if err is not None else "#9CA3AF")
            add_row(m_frame, "Errore Relativo:", err_str, 2, val_font=('Segoe UI', 11, 'bold'), val_fg=err_color)

            tk.Label(res_frame, text="Punti di Controllo Frequenza (Hilbert Chirp Tracker):", font=('Segoe UI', 11, 'bold'), fg="#9CA3AF", bg="#0B0F19", anchor='w').pack(fill=tk.X, padx=12, pady=(6, 3))
            cp_frame = tk.Frame(res_frame, bg="#111827", bd=1, relief=tk.SUNKEN)
            cp_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
            
            cp_area = st.ScrolledText(cp_frame, height=5, font=('Consolas', 11), bg="#111827", fg="#D1D5DB", bd=0, highlightthickness=0)
            cp_area.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
            
            if results['checkpoints']:
                for t, f in results['checkpoints']:
                    cp_area.insert(tk.END, f"  T: {t:+.4f} s    ->    f_inst: {f:.1f} Hz\n")
            else:
                cp_area.insert(tk.END, "  Nessun punto di controllo rilevato in questa finestra.\n")
            cp_area.configure(state=tk.DISABLED)
            
        else:  # RADIOMETRIC
            tk.Label(res_frame, text="Soglie critiche dell'Integrazione Energetica Raggiunte:", font=('Segoe UI', 11, 'bold'), fg="#9CA3AF", bg="#0B0F19", anchor='w').pack(fill=tk.X, padx=12, pady=6)
            e_frame = tk.Frame(res_frame, bg="#111827", bd=1, relief=tk.SUNKEN)
            e_frame.pack(fill=tk.X, padx=12, pady=6)
            
            e_area = st.ScrolledText(e_frame, height=5, font=('Consolas', 11), bg="#111827", fg="#D1D5DB", bd=0, highlightthickness=0)
            e_area.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
            
            if results['slow_energies']:
                for label, t in results['slow_energies']:
                    e_area.insert(tk.END, f"  Threshold {label} reached at: {t:+.4f} s\n")
            else:
                e_area.insert(tk.END, "  Nessuna transizione registrata.\n")
            e_area.configure(state=tk.DISABLED)

        # 5. Raw Code / Receipt Log area
        tk.Label(self, text="TELEMETRY LOG — ASCII TRANSMISSION", font=('Segoe UI', 11, 'bold'), fg="#9CA3AF", bg="#0B0F19", anchor='w').pack(fill=tk.X, padx=18, pady=(12, 3))
        receipt_text_frame = tk.Frame(self, bg="#1E1E1E", bd=1, relief=tk.SUNKEN)
        receipt_text_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 12))
        
        receipt_area = st.ScrolledText(receipt_text_frame, font=('Consolas', 11), bg="#1E1E1E", fg="#39FF14", insertbackground="#39FF14", bd=0, highlightthickness=0)
        receipt_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        receipt_area.insert(tk.END, self.receipt_text)
        receipt_area.configure(state=tk.DISABLED)

        # 6. Bottom action buttons
        btn_panel = tk.Frame(self, bg="#111827", height=60)
        btn_panel.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(btn_panel, text="SALVA REGISTRO (.txt)", bg="#007ACC", fg="white", font=('Segoe UI', 11, 'bold'), bd=0, padx=18, pady=8, command=self.save_receipt_log).pack(side=tk.LEFT, padx=18, pady=12)
        tk.Button(btn_panel, text="CHIUDI", bg="#4B5563", fg="white", font=('Segoe UI', 11), bd=0, padx=18, pady=8, command=self.destroy).pack(side=tk.RIGHT, padx=18, pady=12)

    def generate_receipt(self, results, raw_logs):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\",
            "       LIGO POST-PROCESSING SUITE (DEEP)     ",
            "        --- TELEMETRY REPORT ---            ",
            "============================================",
            f"DATA/ORA : {now}",
            f"FILE     : {results['file_name']}",
            f"DT       : {results['dt']:.3e} s",
            f"F-CAMP   : {results['fs']:.3f} Hz",
            f"ANALISI  : {results['final_mode']}",
            "============================================"
        ]
        
        if results['gatekeeper_decision'] != "N/D":
            lines.extend([
                "CRITERIO GATEKEEPER:",
                f"  Decisione: {results['gatekeeper_decision']}"
            ])
            if results['gatekeeper_reason']:
                lines.append(f"  Dettaglio: {results['gatekeeper_reason']}")
            lines.append("--------------------------------------------")
            
        if results['final_mode'] == 'SPECTRAL':
            lines.extend([
                "  [CHIRP TRACKER V4 HILBERT ENVELOPE (DEEP)]",
                f"  {'T-MERGER (s)':<15} | {'FREQ STIMATA (Hz)':<15}",
                "  " + "-" * 35
            ])
            for t, f in results['checkpoints']:
                lines.append(f"  {t:+.4f} s{' ': <5} | {f:.2f} Hz")
            lines.extend([
                "--------------------------------------------",
                "ESTRAPOLAZIONE MASSA CHIRP:"
            ])
            est = results['estimated_m_chirp_solar']
            if est is not None:
                lines.append(f"  M_chirp Stimata : {est:.4f} M_sol")
                exp = results['expected_m_chirp_solar']
                if exp is not None:
                    lines.append(f"  M_chirp Attesa  : {exp:.4f} M_sol")
                    err = results.get('error_pct')
                    if err is not None:
                        lines.append(f"  Errore Relativo : {err:.2f} %")
                else:
                    lines.append("  M_chirp Attesa  : Non definita/confrontata")
            else:
                lines.append("  M_chirp Stimata : N/D (df/dt non affidabile)")
                
        elif results['final_mode'] == 'RADIOMETRIC':
            lines.extend([
                "  [RADIOMETRIC MODE — CUMULATIVE ENERGY MAPPING]",
                "  Registrazione fluttuazione temporale:",
                "  " + "-" * 35
            ])
            for label, t in results['slow_energies']:
                lines.append(f"  Soglia {label:<8}: raggiunta a {t:+.4f} s")
                
        lines.extend([
            "============================================",
            "             LOG DETAILS DUMP               ",
            "============================================"
        ])
        for line in raw_logs.split('\n'):
            if line.strip():
                lines.append(f"  {line}")
        lines.extend([
            "============================================",
            "        CAUSAL ASTRO-ENGINE COMPLETE        ",
            "\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/"
        ])
        return "\n".join(lines)

    def save_receipt_log(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                                                 title="Salva Scontrino Telemetria",
                                                 initialfile="ligo_telem_receipt_deep.txt")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.receipt_text)
                messagebox.showinfo("Successo", "Scontrino salvato con successo!")
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}")


# ==============================================================================
# MAIN ANALYSIS PIPELINE
# ==============================================================================
def analyze_ligo_dump(filename, system_type='AUTO', expected_m_chirp_solar=None):
    """
    Main signal analysis pipeline for LIGO.
    Detects/filters chirp signals, calculates spectrograms, tracks inst freq via Hilbert,
    and estimates physical parameters (chirp mass) with Peters' equations.
    """
    base_name = os.path.basename(filename)
    dt_str = base_name.split('DT_')[1].replace('.npy', '').split('_')[0]
    dt = float(dt_str)
    fs = 1.0 / dt

    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)

    log(f"\n[ANALISI INIZIATA (DEEP) - MODALITÀ: {system_type}]")
    log(f"File: {base_name} | DT: {dt} | FS: {fs} Hz")

    # Load data and strip early zeros
    data = np.load(filename)
    first_valid = np.argmax(data != 0.0)
    if first_valid > 0 or data[0] != 0.0:
        data = data[first_valid:]

    if len(data) < 1000:
        log("Errore: Dati insufficienti. Fai girare la simulazione un po' di più.")
        return

    # Detrend data
    data = data - np.mean(data)

    results = {
        "file_name": base_name,
        "dt": dt,
        "fs": fs,
        "requested_mode": system_type,
        "final_mode": None,
        "gatekeeper_decision": "Bypassato (Scelta Manuale)",
        "gatekeeper_reason": "",
        "checkpoints": [],
        "estimated_m_chirp_solar": None,
        "expected_m_chirp_solar": expected_m_chirp_solar,
        "error_pct": None,
        "slow_energies": []
    }

    # --- AUTOMATIC GATEKEEPER ---
    if system_type == 'AUTO':
        peak_amp = np.max(np.abs(data))
        merger_idx = np.argmax(np.abs(data))
        
        # Analyze local peak window
        w_size = 300
        start = max(0, merger_idx - w_size)
        end = min(len(data), merger_idx + 5)
        local_data = data[start:end]

        is_casual = False
        reason = ""
        if peak_amp < 1e-15:
            is_casual = True
            reason = "Potenza Insufficiente"
        elif len(local_data) > 10:
            local_peak = np.max(np.abs(local_data))
            safe_local = local_data / (local_peak + 1e-30)
            local_rms = np.sqrt(np.mean(safe_local**2))
            local_crest = 1.0 / (local_rms + 1e-30)
            if local_crest > 10.0:
                is_casual = True
                reason = f"Impatto Verticale (Crest: {local_crest:.1f})"
        else:
            is_casual = True
            reason = "Array troppo corto"
            
        if is_casual:
            log(f"\n[GATEKEEPER] Rilevato segnale impulsivo o fluttuazione: {reason}")
            log("[GATEKEEPER] -> Modalità RADIOMETRIC (Energia Irradiata Cumulativa) forzata automaticamente.")
            system_type = 'RADIOMETRIC'
            results["gatekeeper_decision"] = 'FORZAMENTO RADIOMETRIC (Energia)'
            results["gatekeeper_reason"] = f"Segnale impulsivo / transitorio di rumore: {reason}"
        else:
            log("\n[GATEKEEPER] Rilevato probabile Chirp/Merger.")
            log("[GATEKEEPER] -> Modalità SPECTRAL (Strain + Spettrogramma) forzata automaticamente.")
            system_type = 'SPECTRAL'
            results["gatekeeper_decision"] = 'FORZAMENTO SPECTRAL (Spettrogramma)'
            results["gatekeeper_reason"] = "Rivelato probabile chirp coerente"
    else:
        results["gatekeeper_reason"] = f"Analisi forzata direttamente in modalita {system_type}"

    results["final_mode"] = system_type

    # --- FILTERING & SMOOTHING WINDOWS ---
    if system_type == 'SPECTRAL':
        log("[PULIZIA] Applicazione Filtro Passa-Alto (Cutoff: 5 Hz)...")
        data = apply_high_pass_filter(data, fs, cutoff=5.0, order=4)
        window = signal.windows.tukey(len(data), alpha=0.05)
    else:
        log("[PULIZIA] Filtro disattivato. Lettura dati RAW.")
        window = signal.windows.tukey(len(data), alpha=0.01)

    # Il picco va individuato PRIMA di applicare la finestra: se il merger cade
    # nel taper finale della Tukey (registrazione chiusa subito dopo il botto),
    # l'argmax post-finestra slitta indietro di decine di ms e falsa l'asse dei
    # tempi di tutti i checkpoint.
    merger_idx = np.argmax(np.abs(data))
    data = data * window
    time_absolute = np.arange(len(data)) * dt

    if system_type == 'SPECTRAL':
        time_axis = (np.arange(len(data)) - merger_idx) * dt
        x_label = "Tempo Relativo al Merger [s]"
        merger_label = "Merger (picco)"
        vline_idx = 0
    else:
        time_axis = time_absolute
        x_label = "Tempo di Registrazione [s]"
        merger_label = "Picco Energetico"
        vline_idx = time_absolute[merger_idx]

    # --- PLOT LAYOUT CONFIGURATION ---
    fig_bg = '#050510'
    ax_bg = '#0a0a1a'
    if system_type == 'SPECTRAL':
        log("[VISUALIZZAZIONE] Generazione Strain + Spettrogramma (DEEP mode)...")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [1, 2]})
    else:
        log("[RENDER] Generating Strain + Radiated Energy map (RADIOMETRIC)...")
        fig, (ax1, ax_energy) = plt.subplots(2, 1, figsize=(14, 7), gridspec_kw={'height_ratios': [2, 1]})

    # Panel 1: Strain (Common to both modes)
    ax1.plot(time_axis, data, color='cyan', linewidth=0.8)
    title_suffix = "High-pass filtered > 5 Hz" if system_type == 'SPECTRAL' else "Unfiltered RAW"
    ax1.set_title(f"Strain Gravitazionale ($h_+$) — {title_suffix}", color='white')
    ax1.set_ylabel(r"Amplitude ($h_+$)", color='white')
    ax1.grid(True, alpha=0.2)
    ax1.set_facecolor(ax_bg)
    ax1.tick_params(colors='white')
    ax1.axvline(vline_idx, color='#ff003c', linestyle='--', linewidth=1.5, alpha=0.8, label=merger_label)
    ax1.legend(loc='upper right', facecolor=ax_bg, edgecolor='none', labelcolor='white')

    # ==========================================================
    # RADIOMETRIC MODE: CUMULATIVE ENERGY INTEGRATION
    # ==========================================================
    if system_type == 'RADIOMETRIC':
        power = data**2
        energy_cumulative = np.cumsum(power) * dt
        energy_cumulative /= (energy_cumulative[-1] + 1e-30)

        ax_energy.plot(time_axis, energy_cumulative, color='#ff9900', linewidth=1.2)
        ax_energy.set_title("Energia Irradiata Cumulativa (Fluttuazione Energetica)", color='white')
        ax_energy.set_ylabel("E_cum / E_tot", color='white')
        ax_energy.set_xlabel(x_label, color='white')
        ax_energy.set_facecolor(ax_bg)
        ax_energy.tick_params(colors='white')
        ax_energy.grid(True, alpha=0.2)
        ax_energy.axvline(vline_idx, color='#ff003c', linestyle='--', linewidth=1.2, alpha=0.8)

        # Map 50% and 90% cumulative energy times
        for frac, label in [(0.5, '50%'), (0.9, '90%')]:
            idx_frac = np.searchsorted(energy_cumulative, frac)
            if idx_frac < len(time_axis):
                t_frac = time_axis[idx_frac]
                ax_energy.axvline(t_frac, color='#aaaaff', linestyle=':', linewidth=1.0, alpha=0.7)
                ax_energy.text(t_frac, frac + 0.03, f'{label}\n{t_frac:.2f}s', color='#aaaaff', fontsize=8, ha='center')
                results["slow_energies"].append((label, t_frac))
                print(f"[ENERGIA] Raggiunta soglia {label} al tempo {t_frac:.4f} s")

        zoom_start, zoom_end = time_axis[0], time_axis[-1]
        ax1.set_xlim(zoom_start, zoom_end)
        ax_energy.set_xlim(zoom_start, zoom_end)
        ax1.set_xlabel(x_label, color='white')

    # ==========================================================
    # SPECTRAL MODE: SPECTROGRAM & HILBERT TRACKER (DEEP extraction every millisecond)
    # ==========================================================
    else:
        nperseg = int(fs / 20.0)
        nperseg = max(128, min(nperseg, len(data) // 8))
        noverlap = int(nperseg * 0.95)
        nfft = nperseg * 8

        frequencies, times_spec, Sxx = signal.spectrogram(
            data, fs=fs, window='hann', nperseg=nperseg, noverlap=noverlap, nfft=nfft
        )

        time_shift = merger_idx * dt
        times_spec_relative = times_spec - time_shift
        Sxx_dB = 10 * np.log10(Sxx + 1e-20)

        # Hilbert Instantaneous Frequency Tracking
        log("\n[CHIRP TRACKER V4 (DEEP)] Estrazione Frequenza Istantanea (Hilbert) degli ultimi 0.5 secondi:")
        hilb_t_start = max(time_axis[0], -20.0)
        mask = (time_axis >= hilb_t_start) & (time_axis <= 0.10)
        t_hilb = time_axis[mask]
        data_hilb = data[mask]

        est_m_kg = None
        if len(data_hilb) > 10:
            analytic_signal = signal.hilbert(data_hilb)
            inst_phase = np.unwrap(np.angle(analytic_signal))
            inst_freq = np.diff(inst_phase) / (2.0 * np.pi) * fs
            t_freq = t_hilb[:-1]
            window_len = max(5, int(fs * 0.002) | 1)
            inst_freq_clean = signal.savgol_filter(inst_freq, window_length=window_len, polyorder=3)

            # --- ESTRAZIONE AD ALTA RISOLUZIONE (DEEP) ---
            dt_tfreq = float(t_freq[1] - t_freq[0]) if len(t_freq) > 1 else dt
            step_size = max(0.001, dt_tfreq)
            checkpoints = np.arange(-0.500, 0.000, step_size)
            
            print(f"Risoluzione temporale nativa della simulazione: {dt_tfreq*1000:.4f} ms")
            if dt_tfreq > 0.001:
                print(f"[ATTENZIONE] Risoluzione simulazione inferiore a 1 ms. Adattamento safe a step di {dt_tfreq*1000:.4f} ms")
            else:
                print("Dati a risoluzione di 1 ms o superiore disponibili ed estratti con successo.")

            for t_target in checkpoints:
                tol = max(step_size * 0.5, 1.5 * dt_tfreq)
                idx_t = np.argmin(np.abs(t_freq - t_target))
                if abs(t_freq[idx_t] - t_target) < tol:
                    t_val = t_freq[idx_t]
                    f_val = inst_freq_clean[idx_t]
                    print(f"  -> Tempo: {t_val:.4f} s | Freq: {f_val:.2f} Hz")
                    results["checkpoints"].append((t_val, f_val))

            # Salva i dati tracciati per test_deep.py in formato JSON
            import json
            output_json_path = "C:/Users/Alessandro/Desktop/Nuova cartella/tracked_simulation_chirp.json"
            try:
                # results["checkpoints"] è una lista di coppie [t_val, f_val]
                with open(output_json_path, "w") as f_json:
                    json.dump(results["checkpoints"], f_json)
                print(f"\n[INTEGRAZIONE] Dati di tracciamento Hilbert salvati con successo in: {output_json_path}")
                
                # Avvio automatico di test_deep.py
                import subprocess
                import sys
                test_deep_path = "C:/Users/Alessandro/Desktop/Nuova cartella/test_deep.py"
                if os.path.exists(test_deep_path):
                    print(f"[PIPELINE] Avvio automatico di: {test_deep_path}")
                    subprocess.Popen([sys.executable, test_deep_path], cwd="C:/Users/Alessandro/Desktop/Nuova cartella")
                else:
                    print(f"[ATTENZIONE PIPELINE] Script di confronto {test_deep_path} non trovato.")
            except Exception as pipe_err:
                print(f"[ERRORE PIPELINE] Impossibile completare la fusione: {pipe_err}")

            # Stima massa chirp dal fit della FORMA di Peters (power-law), non da df/dt.
            # BNS: fit negli ultimi istanti (inspiral pulito). BBH: gli ultimi ~0.2 s
            # sono plunge post-ISCO (tracker Hilbert inaffidabile), si fitta prima.
            if expected_m_chirp_solar is not None and expected_m_chirp_solar > 10.0:
                fit_lo, fit_hi = -1.0, -0.25
            else:
                fit_lo, fit_hi = -0.10, -0.02
            mask_rate = (t_freq >= fit_lo) & (t_freq <= fit_hi)
            if np.sum(mask_rate) > 5:
                tau_w = -t_freq[mask_rate]                # tempo al merger (positivo)
                f_w = inst_freq_clean[mask_rate]
                ok = (tau_w > 0.0) & (f_w > 0.0)
                if np.sum(ok) > 5:
                    # Massa chirp dalla FORMA f(tau)=A*tau^(-3/8) (Peters), invertita per
                    # punto e mediata: usa la curva, non la pendenza df/dt, quindi e'
                    # robusta al bias del fit lineare su una power-law e all'oscillazione.
                    est_m_kg = float(np.median(peters_chirp_mass_from_freq(f_w[ok], tau_w[ok])))

            if est_m_kg is not None:
                m_chirp_solar = est_m_kg / M_SUN
                results["estimated_m_chirp_solar"] = m_chirp_solar
                print(f"\n[MASSA CHIRP STIMATA] {m_chirp_solar:.2f} M_sol  (da fit power-law f(tau) di Peters)")
                if expected_m_chirp_solar is not None:
                    err_pct = abs(m_chirp_solar - expected_m_chirp_solar) / expected_m_chirp_solar * 100
                    results["error_pct"] = err_pct
                    print(f"[CONFRONTO]  Attesa: {expected_m_chirp_solar:.2f} M_sol  |  Errore: {err_pct:.1f}%")
            else:
                print("[MASSA CHIRP] Impossibile stimare (df/dt non affidabile)")

        log("[CHIRP TRACKER V4 (DEEP)] Analisi completata.")
        log("-" * 50)

        # Autoscale spectrogram frequency axis based on signal peak
        vmax = np.max(Sxx_dB)
        vmin = vmax - 18
        col_start = np.argmin(np.abs(times_spec_relative - (-0.10)))
        col_end = np.argmin(np.abs(times_spec_relative - 0.05))
        
        if col_start < col_end:
            strong_pixels = np.where(Sxx_dB[:, col_start:col_end] > (vmax - 40))
            max_visible_freq = frequencies[np.max(strong_pixels[0])] if len(strong_pixels[0]) > 0 else 150.0
        else:
            max_visible_freq = 150.0

        plot_max_freq = max(50.0, max_visible_freq * 1.4)
        keep = frequencies <= plot_max_freq

        pcm = ax2.imshow(
            Sxx_dB[keep, :], aspect='auto', origin='lower',
            extent=[times_spec_relative.min(), times_spec_relative.max(), frequencies[keep].min(), frequencies[keep].max()],
            cmap='magma', vmin=vmin, vmax=vmax, interpolation='bilinear'
        )
        ax2.axvline(0, color='#ff003c', linestyle='--', linewidth=1.5, alpha=0.8)
        ax2.set_ylim(0, plot_max_freq)

        zoom_start, zoom_end = max(time_axis[0], -2.5), min(time_axis[-1], 0.2)
        ax1.set_xlim(zoom_start, zoom_end)
        ax2.set_xlim(zoom_start, zoom_end)

        # Theoretical Overlay (Peters curve)
        if expected_m_chirp_solar is not None:
            t_peters = np.linspace(zoom_start, -1e-4, 2000)
            f_peters = peters_frequency(-t_peters, expected_m_chirp_solar * M_SUN)
            valid = (f_peters >= 0) & (f_peters <= plot_max_freq) & np.isfinite(f_peters)
            
            ax2.plot(t_peters[valid], f_peters[valid], color='#00ff99', linewidth=1.8, linestyle='--', alpha=0.85,
                     label=f"Peters teorico ({expected_m_chirp_solar:.1f} M_sol)")
            ax2.legend(loc='upper left', fontsize=9, facecolor=ax_bg, edgecolor='#444444', labelcolor='white')

            if results["estimated_m_chirp_solar"] is not None:
                comparison_text = (
                    f"M_chirp Attesa: {expected_m_chirp_solar:.2f} M_sol\n"
                    f"M_chirp Stimata: {results['estimated_m_chirp_solar']:.2f} M_sol\n"
                    f"Errore: {results['error_pct']:.1f}%"
                )
                ax2.text(zoom_start + 0.05, plot_max_freq * 0.82, comparison_text, color='#00ff99', fontsize=9, fontweight='bold',
                         bbox=dict(facecolor=ax_bg, alpha=0.85, edgecolor='#444444'))

        title_suffix = " — Peters overlay attivo" if expected_m_chirp_solar is not None else ""
        ax2.set_title(f"Spettrogramma LIGO (Max: {plot_max_freq:.1f} Hz){title_suffix}", color='white')
        ax2.set_ylabel("Frequenza [Hz]", color='white')
        ax2.set_xlabel("Tempo Relativo al Merger [s]", color='white')
        ax2.tick_params(colors='white')

        cbar = fig.colorbar(pcm, ax=ax2)
        cbar.set_label("Potenza [dB]", color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

    fig.patch.set_facecolor(fig_bg)
    plt.tight_layout()

    # Save output plot
    output_dir = os.path.join("ligo_output", "plots")
    os.makedirs(output_dir, exist_ok=True)
    output_png = os.path.join(output_dir, base_name.replace('.npy', f'_HD_{system_type}_deep.png'))
    plt.savefig(output_png, facecolor=fig.get_facecolor(), edgecolor='none')
    log(f"[SUCCESSO] Analisi {system_type} salvata in {output_png}\n")
    
    # Spawn the telemetry receipt GUI window
    try:
        raw_logs_text = "\n".join(log_lines)
        if tk._default_root is not None:
            receipt_win = LigoTelemetryReportWindow(tk._default_root, results, raw_logs_text)
            receipt_win.deiconify()
            receipt_win.focus_force()
    except Exception as tk_err:
        print(f"[ATTENZIONE] Impossibile mostrare la telemetria Tkinter: {tk_err}")

    plt.show()


# ==============================================================================
# ENTRY POINT & LAUNCHER APPLICATION
# ==============================================================================
class LigoLauncherApp(tk.Tk):
    """Launcher app to select LIGO dump file, analysis mode and run the pipeline."""
    def __init__(self):
        super().__init__()
        self.title("LIGO Analyzer (DEEP) - Kernel Interface")
        self.geometry("500x550")
        self.configure(bg="#1E1E1E")
        self.resizable(False, False)

        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        
        bg_col = "#1E1E1E"
        fg_col = "#D4D4D4"
        accent_col = "#007ACC"
        
        style.configure('TFrame', background=bg_col)
        style.configure('TLabel', background=bg_col, foreground=fg_col, font=('Segoe UI', 11))
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'), foreground="#FFFFFF")
        style.configure('TCombobox', fieldbackground="#FFFFFF", background="#FFFFFF", foreground="#000000")
        style.configure('TEntry', fieldbackground="#2D2D2D", foreground="#FFFFFF")
        style.configure('Launch.TButton', font=('Segoe UI', 12, 'bold'), background="#5A2E8A", foreground=fg_col)
        style.map('Launch.TButton', background=[('active', '#7A3EAA')])

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title Header
        ttk.Label(main_frame, text="LIGO Post-Processing (DEEP)", style='Header.TLabel').pack(pady=(0, 5))
        
        # File selector
        file_frame = tk.LabelFrame(main_frame, text=" Selezione Sim-Dump (.npy) ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        file_frame.pack(fill=tk.X, pady=(10, 10))
        
        search_path = os.path.join("ligo_output", "data_npy", "*DT_*.npy")
        self.file_list = glob.glob(search_path)
        
        if self.file_list:
            self.file_list.sort(key=os.path.getmtime, reverse=True)
            file_names = [os.path.basename(f) for f in self.file_list]
            self.file_var = tk.StringVar(value=file_names[0])
        else:
            file_names = ["Nessun DUMP trovato"]
            self.file_var = tk.StringVar(value=file_names[0])
            
        self.file_combo = ttk.Combobox(file_frame, textvariable=self.file_var, state='readonly', values=file_names)
        self.file_combo.pack(fill=tk.X, ipady=4)
        
        # Mode selector
        mode_frame = tk.LabelFrame(main_frame, text=" Modalità di Analisi ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mode_var = tk.StringVar(value="1) AUTO  — Rilevamento automatico (Gatekeeper)")
        modes = [
            "1) AUTO  — Rilevamento automatico (Gatekeeper)",
            "2) FORZA SPECTRAL (Spettrogramma + Peters)",
            "3) FORZA RADIOMETRIC (Fluttuazione Energia)"
        ]
        self.mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, state='readonly', values=modes)
        self.mode_combo.pack(fill=tk.X, ipady=4)
        
        # Theoretical Overlay input
        overlay_frame = tk.LabelFrame(main_frame, text=" Overlay Teorico Peters (Opzionale) ", bg=bg_col, fg=accent_col, font=('Segoe UI', 11, 'bold'), padx=15, pady=15)
        overlay_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(overlay_frame, text="Massa Chirp attesa in M_sol:").pack(side=tk.LEFT)
        self.chirp_var = tk.StringVar(value="")
        self.chirp_entry = tk.Entry(overlay_frame, textvariable=self.chirp_var, bg="#2D2D2D", fg="#FFFFFF", font=('Segoe UI', 10), justify='right')
        self.chirp_entry.pack(side=tk.RIGHT, ipadx=5, ipady=3)
        
        # Run Button
        ttk.Button(main_frame, text="ESEGUI ANALISI LIGO DEEP", style='Launch.TButton', command=self.on_launch).pack(fill=tk.X, ipady=15)
        
    def on_launch(self):
        if not self.file_list:
            messagebox.showerror("Errore", "Nessun file LIGO presente in ligo_output/data_npy.")
            return
        
        sel_file = self.file_var.get()
        file_path = next((f for f in self.file_list if os.path.basename(f) == sel_file), None)
        
        sel_mode = self.mode_var.get()
        if "AUTO" in sel_mode:
            sys_type = 'AUTO'
        elif "SPECTRAL" in sel_mode:
            sys_type = 'SPECTRAL'
        else:
            sys_type = 'RADIOMETRIC'
        
        raw_chirp = self.chirp_var.get().strip()
        expected_m = None
        if raw_chirp:
            try:
                expected_m = float(raw_chirp)
            except ValueError:
                messagebox.showwarning("Attenzione", "Massa Chirp non valida. L'analisi procederà senza confronto teorico.")
                self.chirp_var.set("")
                
        print(f"Lancio DEEP: File={sel_file}, Mode={sys_type}, Chirp={expected_m}")
        
        self.withdraw()
        try:
            analyze_ligo_dump(file_path, system_type=sys_type, expected_m_chirp_solar=expected_m)
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Errore di Analisi", f"L'analisi è fallita con errore:\n{e}")
        finally:
            self.deiconify()


if __name__ == "__main__":
    app = LigoLauncherApp()
    app.mainloop()

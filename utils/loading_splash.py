"""
utils/loading_splash.py
=======================
Splash screen Tkinter di caricamento per il motore fisico.

Responsabilità:
  - Mostrare una finestra di progresso PRIMA di pygame.display.init().
  - Eseguire presets.get_preset() + rebuild_simulation() in un thread daemon.
  - Catturare solo i print del thread di loading (thread-safe: gli altri passano
    all'originale, Tkinter non viene disturbato).
  - Restituire (bodies, dt, sim_rad, step, print_buffer) al chiamante.
"""

import builtins
import queue
import threading
import traceback
import tkinter as tk


# ---------------------------------------------------------------------------
# Thread worker
# ---------------------------------------------------------------------------

def _loading_worker(preset_name, gstate, dt_val, progress_q, result_holder):
    """
    Gira in un thread daemon. Carica il preset e ricostruisce la simulazione,
    catturando i print in result_holder['print_buffer'].
    Invia tuple (kind, msg, pct) sulla progress_q per aggiornare la splash.
    """
    print_buffer     = []
    original_print   = builtins.print
    my_thread_id     = threading.current_thread().ident

    def _thread_local_print(*args, **kwargs):
        """
        Intercetta SOLO i print del thread di loading.
        I print degli altri thread (Tkinter incluso) passano all'originale.
        Thread-safe: nessuna race condition.
        """
        if threading.current_thread().ident != my_thread_id:
            # Non siamo nel thread di loading → comportamento originale
            original_print(*args, **kwargs)
            return

        sep = kwargs.get('sep', ' ')
        msg = sep.join(str(a) for a in args)
        print_buffer.append(msg.rstrip('\n'))

        # Aggiornamenti di progresso basati sul contenuto del messaggio
        if "L2 BUDGET" in msg or "DATA ALLOC" in msg:
            progress_q.put(("status", "Allocazione buffer storici...", 35))
        elif "SMART COPY" in msg or "INTERPOLAZIONE" in msg:
            progress_q.put(("status", "Ripristino storia causale...", 65))
        elif "MEM CHECK" in msg:
            progress_q.put(("status", "Verifica memoria...", 80))
        elif "Ricostruzione completata" in msg:
            progress_q.put(("status", "Avvio motore grafico...", 95))

    builtins.print = _thread_local_print
    try:
        # Import lazy (i moduli sono già in sys.modules grazie a main_gui.py,
        # quindi non c'è overhead di import effettivo)
        from core import presets
        from core.simulation_manager import rebuild_simulation

        progress_q.put(("status", "Caricamento preset...", 5))
        bodies_raw, new_dt_raw, new_sim_rad, step = presets.get_preset(preset_name)
        if dt_val is not None:
            new_dt_raw = dt_val

        progress_q.put(("status", "Calcolo architettura memoria...", 15))
        bodies_out, dt_out = rebuild_simulation(
            bodies_raw, gstate.show_info_causality, new_dt_raw, new_sim_rad
        )

        result_holder['bodies']       = bodies_out
        result_holder['dt']           = dt_out
        result_holder['sim_rad']      = new_sim_rad
        result_holder['step']         = step
        result_holder['print_buffer'] = print_buffer

        progress_q.put(("done", None, 100))

    except Exception:
        # Traceback completo → visibile nel terminale E nella game console
        tb = traceback.format_exc()
        result_holder['print_buffer'] = print_buffer
        result_holder['print_buffer'].append(tb)      # anche nel deferred log
        progress_q.put(("error", tb, 0))

    finally:
        builtins.print = original_print


# ---------------------------------------------------------------------------
# Finestra Tkinter
# ---------------------------------------------------------------------------

def show_splash_and_load(preset_name, gstate, dt_val):
    """
    Mostra una splash screen Tkinter di caricamento, esegue il preset e
    rebuild_simulation in un thread daemon, e ritorna quando il caricamento
    è completo.

    Returns
    -------
    bodies       : list[CelestialBody]
    dt           : float
    sim_rad      : float
    step         : int
    print_buffer : list[str]  — messaggi da rilasciare nella GameConsole
    """
    progress_q    = queue.Queue()
    result_holder = {}

    # --- Finestra ---
    root = tk.Tk()
    root.title("Astro Causal Physics Engine — Inizializzazione")
    root.geometry("520x240")
    root.configure(bg="#0D0D1A")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # Centramento
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"520x240+{(sw - 520) // 2}+{(sh - 240) // 2}")

    # --- Widgets ---
    tk.Label(root, text="CAUSAL PHYSICS ENGINE",
             bg="#0D0D1A", fg="#4FC3F7",
             font=("Segoe UI", 15, "bold")).pack(pady=(28, 4))
    tk.Label(root, text="Inizializzazione kernel causale...",
             bg="#0D0D1A", fg="#888888",
             font=("Segoe UI", 10)).pack(pady=(0, 18))

    status_var = tk.StringVar(value="Avvio...")
    tk.Label(root, textvariable=status_var,
             bg="#0D0D1A", fg="#CFD8DC",
             font=("Segoe UI", 10)).pack()

    # Barra di progresso custom (Canvas — evita i glitch di ttk.Progressbar col tema clam)
    bar_canvas = tk.Canvas(root, width=440, height=18, bg="#1A1A2E",
                           highlightthickness=1, highlightbackground="#4FC3F7")
    bar_canvas.pack(pady=(10, 0))
    bar_fill = bar_canvas.create_rectangle(0, 0, 0, 18, fill="#4FC3F7", outline="")

    pct_var = tk.StringVar(value="0%")
    tk.Label(root, textvariable=pct_var,
             bg="#0D0D1A", fg="#4FC3F7",
             font=("Segoe UI", 9)).pack(pady=(4, 0))

    error_holder = [None]

    def _update_bar(pct):
        bar_canvas.coords(bar_fill, 0, 0, int(440 * pct / 100), 18)
        pct_var.set(f"{pct}%")

    def _poll():
        try:
            while True:
                kind, msg, pct = progress_q.get_nowait()
                if kind == "status":
                    status_var.set(msg)
                    _update_bar(pct)
                elif kind == "done":
                    _update_bar(100)
                    status_var.set("Pronto.")
                    root.after(200, root.destroy)
                    return
                elif kind == "error":
                    error_holder[0] = msg
                    root.destroy()
                    return
        except queue.Empty:
            pass
        root.after(80, _poll)

    # --- Thread di caricamento ---
    t = threading.Thread(
        target=_loading_worker,
        args=(preset_name, gstate, dt_val, progress_q, result_holder),
        daemon=True,
    )
    t.start()
    root.after(80, _poll)
    root.mainloop()
    t.join()

    if error_holder[0]:
        # Stampa il traceback completo sul terminale per debug immediato
        builtins.print("\n[LOADING ERROR] Traceback completo:\n" + error_holder[0])
        raise RuntimeError(
            "Il thread di caricamento è fallito. "
            "Vedi il traceback completo sopra (o nella GameConsole dopo il boot)."
        )

    return (
        result_holder['bodies'],
        result_holder['dt'],
        result_holder['sim_rad'],
        result_holder['step'],
        result_holder.get('print_buffer', []),
    )


# ---------------------------------------------------------------------------
# Helper per il flush differito
# ---------------------------------------------------------------------------

def flush_deferred_prints(print_buffer):
    """
    Stampa i messaggi catturati durante il caricamento.
    Va chiamato DOPO aver reindirizzato sys.stdout alla GameConsole,
    così i log appaiono nella console in-game invece che sul terminale.
    """
    for line in print_buffer:
        print(line)

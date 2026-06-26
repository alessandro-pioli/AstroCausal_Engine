from core.data import AU_IN_KM

def format_time(sim_time):
    total_seconds = int(sim_time)
    ms = int((sim_time - total_seconds) * 1000)
    d = total_seconds // 86400
    rem = total_seconds % 86400
    h = rem // 3600
    rem %= 3600
    m = rem // 60
    s = rem % 60
    return f"TIME: {int(d)}g {int(h):02}h {int(m):02}m {int(s):02}s {ms:03}ms"

def format_rate(seconds):
    if seconds >= 86400: return f"{seconds/86400:.1f} giorni/s"
    if seconds >= 3600: return f"{seconds/3600:.1f} ore/s"
    if seconds >= 60: return f"{seconds/60:.1f} min/s"
    if seconds >= 1: return f"{seconds:.2f} sec/s"
    return f"{seconds*1000:.1f} ms/s"

def format_dt(seconds):
    """Formatta un intervallo di tempo in unità leggibili."""
    if seconds < 1e-3:   return f"{seconds*1e6:.3g} μs/slot"
    if seconds < 1.0:    return f"{seconds*1e3:.3g} ms/slot"
    if seconds < 3600:   return f"{seconds:.4g} s/slot"
    if seconds < 86400:  return f"{seconds/3600:.3g} h/slot"
    return f"{seconds/86400:.3g} d/slot"

def format_unit(val):
    abs_v = abs(val)
    if abs_v >= AU_IN_KM * 0.1:
        return f"{val/AU_IN_KM:.4f} AU"
    elif abs_v >= 1000000:
        return f"{val/1000000.0:.2f}M km"
    else:
        return f"{val:.0f} km"

def format_dist_pair(cc, ss):
    """CC e SS nella stessa unità (scelta da CC), mostrata una sola volta: compatto per l'HUD."""
    a = abs(cc)
    if a >= AU_IN_KM * 0.1:
        return f"CC {cc/AU_IN_KM:.3f} SS {ss/AU_IN_KM:.3f} AU"
    elif a >= 1000000:
        return f"CC {cc/1000000.0:.2f} SS {ss/1000000.0:.2f} M km"
    else:
        return f"CC {cc:.0f} SS {ss:.0f} km"

def format_acc(val):
    abs_v = abs(val)
    if abs_v >= 1000000.0:
        return f"{val/1000000.0:+.2f} M km/s²"
    elif abs_v >= 1000.0:
        return f"{val/1000.0:+.2f}k km/s²"
    elif abs_v >= 1.0:
        return f"{val:+.4f} km/s²"
    else:
        return f"{val*1000.0:+.4f} m/s²"

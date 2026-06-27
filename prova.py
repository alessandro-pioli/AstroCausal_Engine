#!/usr/bin/env python3
# fix_mix_videos.py
# Usa: python3 fix_mix_videos.py
import re, os, subprocess, sys

MD="PHYSICS_AND_SCENARIO_GUIDE.md"
REPO_RAW_BASE="https://github.com/Havock-prog/Astro-Causal-Sim/raw/main/"

# CONFIG: elenca qui i mp4 che vuoi trasformare in GIF (path relativi)
convert_to_gif = [
    "docs/vid/07_to_c_fast.mp4",
    "docs/vid/0999_to_c_slow.mp4",
    "docs/vid/earth_swap_jupiter.mp4",
    "docs/vid/artemis2flyby.mp4",
]

# I restanti mp4 saranno trattati come mp4 con thumbnail (se vuoi escluderne qualcuno aggiungilo qui)
leave_as_mp4 = [

  # aggiungi qui gli altri
]

# parametri per la gif
FPS="30"
WIDTH="-1"   # setta width target; usa -1 per mantenere aspect ratio (scale=640:-1)

def run(cmd):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd)

# assicurati che le directory esistano
os.makedirs("docs/gif", exist_ok=True)
os.makedirs("docs/vid", exist_ok=True)

# 1) genera GIF per i file in convert_to_gif
for mp4 in convert_to_gif:
    if not os.path.exists(mp4):
        print("Non trovato:", mp4); continue
    base = os.path.splitext(os.path.basename(mp4))[0]
    palette = f"docs/gif/{base}_palette.png"
    gif = f"docs/gif/{base}.gif"
    # palettegen
    run(["ffmpeg","-v","warning","-i", mp4, "-vf", f"fps={FPS},scale={WIDTH}:-1:flags=lanczos,palettegen", "-y", palette])
    run(["ffmpeg","-v","warning","-i", mp4, "-i", palette, "-filter_complex", f"fps={FPS},scale={WIDTH}:-1:flags=lanczos[x];[x][1:v]paletteuse", "-loop","0", "-y", gif])
    try:
        os.remove(palette)
    except: pass
    print("GIF generata:", gif)

# 2) genera thumbnails per leave_as_mp4
for mp4 in leave_as_mp4:
    if not os.path.exists(mp4):
        print("Non trovato:", mp4); continue
    base = os.path.splitext(os.path.basename(mp4))[0]
    thumb = os.path.join(os.path.dirname(mp4), base + "_thumb.jpg")
    if not os.path.exists(thumb):
        run(["ffmpeg","-y","-ss","00:00:01","-i", mp4, "-frames:v","1","-q:v","2", thumb])
        print("Thumb generata:", thumb)
    else:
        print("Thumb già esistente:", thumb)

# 3) sostituisce i <video ... src="..."> nel MD
with open(MD, "r", encoding="utf8") as f:
    text = f.read()

# pattern semplice: trova tag <video ... src="...mp4" ...>...</video> o <video .../>
video_pattern = re.compile(r'<video[^>]*src="([^"]+?\.mp4)"[^>]*>(?:</video>)?', re.IGNORECASE|re.DOTALL)

def replacement(match):
    src = match.group(1)
    # decide se è gif o mp4
    if src in convert_to_gif:
        gif_rel = "docs/gif/" + os.path.splitext(os.path.basename(src))[0] + ".gif"
        return f'![gif]({gif_rel})'
    else:
        base = os.path.splitext(os.path.basename(src))[0]
        thumb = os.path.join(os.path.dirname(src), base + "_thumb.jpg")
        raw = REPO_RAW_BASE + src
        return f'[![Anteprima video]({thumb})]({raw})'

new_text = video_pattern.sub(replacement, text)

if new_text == text:
    print("Nessuna sostituzione effettuata.")
else:
    bak = MD + ".bak"
    os.rename(MD, bak)
    with open(MD, "w", encoding="utf8") as f:
        f.write(new_text)
    print("File aggiornato:", MD, "Originale salvato come", bak)
    print("Controlla il file, poi git add/commit/push.")
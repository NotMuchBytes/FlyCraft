"""A temporary, dismissible DVD-style message; changes no Windows settings."""
import ctypes
import json
import os
from pathlib import Path
import time
import tkinter as tk

CAMPAIGN = Path("C:/Users/anass/Documents/Codex/FlyCraft-curriculum/experiments/phase9/fc9_stage25")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass

root = tk.Tk()
root.title("FlyCraft - DO NOT TOUCH screensaver")
root.configure(bg="black")
root.attributes("-fullscreen", True)
root.attributes("-topmost", True)
root.config(cursor="none")
canvas = tk.Canvas(root, bg="black", highlightthickness=0, cursor="none")
canvas.pack(fill="both", expand=True)
palette = ["#47E6FF", "#FF5CA8", "#B692FF", "#FFE066", "#69F0AE", "#FF9364"]
font_size = max(22, min(64, root.winfo_screenwidth() // 25))
main = canvas.create_text(140, 140, text="DO NOT TOUCH", font=("Segoe UI", font_size, "bold"),
                          anchor="center", fill=palette[0], tags="logo")
sub = canvas.create_text(140, 140 + font_size, text="FlyCraft  ·  background work",
                         font=("Segoe UI", max(13, font_size // 3)), anchor="center",
                         fill=palette[0], tags="logo")
clock = canvas.create_text(140, 140 + font_size * 1.65, text=time.strftime("%I:%M:%S %p"),
                           font=("Segoe UI", max(18, font_size // 2)), anchor="center",
                           fill=palette[0], tags="logo")
width, height = root.winfo_screenwidth(), root.winfo_screenheight()
progress_label = canvas.create_text(width / 2, height - 112, text="Reading actual campaign progress…",
    font=("Segoe UI", 18), fill="#D5E5FF")
track = canvas.create_rectangle(width * .15, height - 80, width * .85, height - 60,
    fill="#182634", outline="#3B526B")
bar = canvas.create_rectangle(width * .15, height - 80, width * .15, height - 60,
    fill="#69F0AE", outline="")
detail_label = canvas.create_text(width / 2, height - 35, text="Esc to close · Shutdown after verified campaign completion",
    font=("Segoe UI", 12), fill="#91A5BE")
canvas.update_idletasks()
box = canvas.bbox("logo")
canvas.move("logo", 90 - box[0], 90 - box[1])
velocity = [3.2, 2.5]
color = [0]
started = time.monotonic()
state = Path(__file__).with_name("flycraft_screensaver_status.json")
state.write_text(json.dumps({"pid": os.getpid(), "started_unix": time.time(),
    "message": "DO NOT TOUCH", "clock": "live local time with seconds", "progress": "actual completed world slots / 10000",
    "dismiss": "Escape key", "changes_system_settings": False}), encoding="utf-8")

def animate():
    box = canvas.bbox("logo")
    width, height = canvas.winfo_width(), canvas.winfo_height() - 155
    bounced = False
    if box[0] + velocity[0] < 18 or box[2] + velocity[0] > width - 18:
        velocity[0] = -velocity[0]
        bounced = True
    if box[1] + velocity[1] < 18 or box[3] + velocity[1] > height - 18:
        velocity[1] = -velocity[1]
        bounced = True
    if bounced:
        color[0] = (color[0] + 1) % len(palette)
        canvas.itemconfigure("logo", fill=palette[color[0]])
    canvas.move("logo", *velocity)
    root.after(33, animate)

def update_clock():
    canvas.itemconfigure(clock, text=time.strftime("%I:%M:%S %p"))
    root.after(1000, update_clock)

def update_progress():
    try:
        report = json.loads((CAMPAIGN / "summary.json").read_text(encoding="utf-8"))
        finished = report["official_training_worlds"]
        total = report["world_limit"]
        percent = min(100, finished * 100 / total)
        canvas.itemconfigure(progress_label, text=f"Training worlds: {finished:,} / {total:,}  ·  {percent:.2f}%  ·  {report['training_episodes']:,} new scored")
        canvas.coords(bar, width * .15, root.winfo_screenheight() - 80,
                      width * (.15 + .70 * percent / 100), root.winfo_screenheight() - 60)
        status = "Running in background"
        if (CAMPAIGN / "fix_request.json").exists():
            status = "Paused for evidence review · no shutdown on error"
        elif (CAMPAIGN / "STOP").exists():
            status = "Safely stopped · progress preserved"
        elif report.get("curriculum_status") in ("stage_gate_failed", "awaiting_next_skill_implementation"):
            status = "Curriculum needs further development · checkpoint preserved"
        elif finished >= total:
            status = "World budget complete · verifying recordings before shutdown"
        estimate = report.get("estimated_remaining_seconds")
        eta = f" · rough ETA {estimate / 86400:.1f} days" if estimate and finished >= 10 else " · broader curriculum ETA unmeasured"
        canvas.itemconfigure(detail_label, text=status + eta + " · Esc to close")
    except (OSError, ValueError, KeyError, TypeError):
        pass  # A temporary read failure retains the last real value.
    root.after(2000, update_progress)

root.bind("<Escape>", lambda event: root.destroy())
root.after(150, animate)
root.after(1000, update_clock)
root.after(200, update_progress)
root.mainloop()

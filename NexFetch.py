"""NexFetch v2.8 launcher — no CMD window, crash-safe"""
import sys, os, multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()

import subprocess, threading, zipfile, shutil, urllib.request
from pathlib import Path

# Suppress all child process console windows on Windows
if sys.platform == "win32":
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

SETUP_FLAG = APP_DIR / ".setup_complete"
FFMPEG_DIR = APP_DIR / "ffmpeg_bin"
FFMPEG_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)
REQUIREMENTS = [
    "yt-dlp", "spotdl", "instaloader", "requests",
    "Pillow", "beautifulsoup4", "lxml", "mutagen",
]


def show_error(title, message):
    try:
        import tkinter as tk
        r = tk.Tk(); r.title(title)
        r.geometry("640x320"); r.configure(bg="#080c14"); r.resizable(False, False)
        tk.Label(r, text="⚠  " + title,
                 font=("Segoe UI", 14, "bold"), fg="#ef4444", bg="#080c14").pack(pady=(20, 8))
        frm = tk.Frame(r, bg="#0d1117"); frm.pack(fill="both", expand=True, padx=20)
        txt = tk.Text(frm, font=("Consolas", 9), bg="#0d1117", fg="#fca5a5",
                      relief="flat", bd=0, wrap="word")
        txt.insert("1.0", message); txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Label(r, text="Run START_DEBUG.bat for full details.",
                 font=("Segoe UI", 9), fg="#64748b", bg="#080c14").pack(pady=(0, 4))
        tk.Button(r, text="  OK  ", command=r.destroy,
                  font=("Segoe UI", 10, "bold"), bg="#b3100f", fg="white",
                  relief="flat", cursor="hand2", pady=6).pack(pady=(0, 16))
        r.mainloop()
    except Exception:
        try:
            (APP_DIR / "nexfetch_error.txt").write_text(f"{title}\n\n{message}", "utf-8")
        except Exception:
            pass


def inst(pkg, cb=None):
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg, "--quiet", "--upgrade"],
        capture_output=True, text=True, creationflags=CREATE_NO_WINDOW
    )
    if cb: cb(f"{'✔' if r.returncode == 0 else '✘'} {pkg}")


def has_ff():
    if (FFMPEG_DIR / "ffmpeg.exe").exists(): return True
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True,
                       timeout=5, creationflags=CREATE_NO_WINDOW)
        return True
    except Exception:
        return False


def dl_ff(cb=None):
    if cb: cb("⏳ Downloading ffmpeg (~50MB)...")
    zp = APP_DIR / "ffmpeg_tmp.zip"; FFMPEG_DIR.mkdir(exist_ok=True)
    try:
        def h(c, b, t):
            if t > 0 and c % 60 == 0 and cb:
                cb(f"   {min(int(c*b*100/t), 100)}%")
        urllib.request.urlretrieve(FFMPEG_URL, zp, h)
        with zipfile.ZipFile(zp, "r") as z:
            for m in z.namelist():
                fn = Path(m).name
                if fn in ("ffmpeg.exe", "ffprobe.exe"):
                    with z.open(m) as s, open(FFMPEG_DIR / fn, "wb") as d:
                        shutil.copyfileobj(s, d)
                    if cb: cb(f"✔ {fn}")
        zp.unlink(missing_ok=True)
        if (FFMPEG_DIR / "ffmpeg.exe").exists():
            if cb: cb("✅ ffmpeg ready!")
            os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")
            return True
    except Exception as e:
        if cb: cb(f"❌ ffmpeg: {e}")
        try: zp.unlink(missing_ok=True)
        except: pass
    return False


def inj():
    if (FFMPEG_DIR / "ffmpeg.exe").exists():
        os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")


def run_setup():
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("NexFetch — Setting Up")
    root.geometry("520x400"); root.resizable(False, False)
    root.configure(bg="#080c14")
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    title_var = tk.StringVar(value="⚡ NexFetch")
    tk.Label(root, textvariable=title_var,
             font=("Segoe UI", 22, "bold"), fg="#b3100f", bg="#080c14").pack(pady=(32, 4))
    tk.Label(root, text="First time setup — runs only once.",
             font=("Segoe UI", 10), fg="#64748b", bg="#080c14").pack()

    bar_frame = tk.Frame(root, bg="#080c14")
    bar_frame.pack(fill="x", padx=50, pady=(24, 8))
    try:
        s = ttk.Style()
        try: s.theme_use("clam")
        except: pass
        try:
            s.configure("TProgressbar",
                        troughcolor="#1a2332", background="#b3100f",
                        thickness=18, relief="flat")
        except: pass
    except: pass
    bar = ttk.Progressbar(bar_frame, length=420, mode="determinate",
                          maximum=len(REQUIREMENTS) + 3)
    bar.pack()

    step_var = tk.StringVar(value="Initializing...")
    tk.Label(root, textvariable=step_var,
             font=("Segoe UI", 10, "bold"), fg="#b3100f", bg="#080c14").pack(pady=(4, 0))

    log_frame = tk.Frame(root, bg="#0d1117", bd=0)
    log_frame.pack(fill="both", expand=True, padx=40, pady=(12, 20))
    log_text = tk.Text(log_frame, font=("Consolas", 8), bg="#0d1117", fg="#64748b",
                       relief="flat", bd=0, state="disabled", height=8)
    log_text.pack(fill="both", expand=True, padx=8, pady=6)

    _dc = [0]
    def dots():
        title_var.set("⚡ NexFetch" + "." * (_dc[0] % 4))
        _dc[0] += 1; root.after(400, dots)
    dots()

    def add_log(msg):
        log_text.configure(state="normal")
        log_text.insert("end", f"  {msg}\n"); log_text.see("end")
        log_text.configure(state="disabled"); root.update_idletasks()

    def do():
        try:
            subprocess.run([sys.executable, "-m", "pip", "install",
                           "--upgrade", "pip", "--quiet"],
                          capture_output=True, creationflags=CREATE_NO_WINDOW)
            step_var.set("pip ready"); bar["value"] = 1; root.update_idletasks()
            for i, pkg in enumerate(REQUIREMENTS, 2):
                step_var.set(f"Installing {pkg}...")
                inst(pkg, add_log); bar["value"] = i; root.update_idletasks()
            step_var.set("Checking ffmpeg...")
            if not has_ff(): dl_ff(add_log)
            else: add_log("✔ ffmpeg already present")
            bar["value"] = len(REQUIREMENTS) + 2
            SETUP_FLAG.write_text("ok")
            step_var.set("✅ Done! Launching NexFetch...")
            title_var.set("⚡ NexFetch")
            add_log("Setup complete — launching...")
            import time; time.sleep(1)
            root.after(0, lambda: launch(root))
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            root.after(0, lambda: (
                step_var.set("❌ Setup error"),
                add_log(f"ERROR: {err}")
            ))

    def launch(r):
        r.destroy(); inj(); _start_app()

    threading.Thread(target=do, daemon=True).start()
    root.mainloop()


def _start_app():
    try:
        from core.app import LoginWindow, NexFetchApp
        u = LoginWindow(APP_DIR).run()
        if u: NexFetchApp(u, APP_DIR).run()
    except ImportError as e:
        import traceback
        show_error("Import Error",
                   f"Missing module: {e}\n\nRun RESET_SETUP.bat then START_NEXFETCH.bat\n\n{traceback.format_exc()}")
    except Exception as e:
        import traceback
        show_error("NexFetch Error", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


if __name__ == "__main__":
    try:
        if not SETUP_FLAG.exists(): run_setup()
        else: inj(); _start_app()
    except Exception as e:
        import traceback
        show_error("Fatal Error", f"NexFetch failed to start:\n\n{traceback.format_exc()}")

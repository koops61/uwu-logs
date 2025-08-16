#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UwU Logs – Dashboard GUI (minimal)
- Services systemd : server_5000 / server_5010 / server_5020
- Stats live : CPU / RAM / Disk
- Logs (tail + capture temps réel des scripts)
- Lancer script : logs_auto.py (avec sortie live)
- Cron : afficher + s’assurer que la ligne logs_auto.py existe
"""

import os, sys, time, shlex, queue, getpass, threading, subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---------- CONFIG ----------

BASE_DIR = Path("/var/www/html")
VENV_PY  = BASE_DIR / "venv" / "bin" / "python"
LOG_DIR  = BASE_DIR / "_loggers"

# Services systemd
SERVICES = [
    ("server_5000", 5000),
    ("server_5010", 5010),
    ("server_5020", 5020),
]

# Fichiers de logs (présélections — peuvent ne pas exister)
LOG_CANDIDATES = [
    LOG_DIR / "server_main.log",
    LOG_DIR / "server_top.log",
    LOG_DIR / "uploads.log",
    LOG_DIR / "reports.log",
]

# Script utile
SCRIPT_LOGS_AUTO = BASE_DIR / "logs_auto.py"

# Cron (UNE SEULE ligne)
CRON_LINE = (
    r'*/2 * * * * cd /var/www/html && /var/www/html/venv/bin/python '
    r'/var/www/html/logs_auto.py >> /home/{USER}/logs/logs_auto.log 2>&1'
)

# ---------- Helpers ----------

def which(cmd):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        x = Path(p) / cmd
        if x.exists() and os.access(x, os.X_OK):
            return str(x)
    return None

SYSTEMCTL = which("systemctl") or "/bin/systemctl"
CRONTAB   = which("crontab")   or "/usr/bin/crontab"
PY        = str(VENV_PY if VENV_PY.exists() else sys.executable)

def run_cmd(cmd, check=False, text=True, input_data=None):
    try:
        res = subprocess.run(
            cmd, check=check, text=text,
            input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def human_bytes(n):
    try:
        n = float(n)
    except:
        return str(n)
    units = ["B","KB","MB","GB","TB"]
    i = 0
    while n >= 1024 and i < len(units)-1:
        n /= 1024.0; i += 1
    return f"{n:.1f} {units[i]}"

# ---------- Stats fallback (si pas psutil) ----------

def get_cpu_percent_fallback(interval=0.5):
    def read():
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("cpu "):
                    vals = list(map(int, line.split()[1:]))
                    idle = vals[3] + vals[4]
                    total = sum(vals)
                    return idle, total
        return None, None
    i1, t1 = read(); time.sleep(interval); i2, t2 = read()
    if None in (i1, t1, i2, t2): return 0.0
    idle, total = i2 - i1, t2 - t1
    return round(100*(1 - idle/total), 1) if total > 0 else 0.0

def get_meminfo_fallback():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            info[k] = v.strip()
    tot = int(info.get("MemTotal", "0").split()[0])
    ava = int(info.get("MemAvailable", "0").split()[0])
    used = tot - ava; pct = (used/tot*100) if tot else 0
    return used*1024, tot*1024, pct

def get_disk_usage(path="/"):
    st = os.statvfs(path)
    total = st.f_frsize * st.f_blocks
    free  = st.f_frsize * st.f_bavail
    used  = total - free
    pct   = (used/total*100) if total else 0
    return used, total, pct

# ---------- Systemd helper ----------

def service_cmd(service, action, use_sudo=False):
    cmd = [SYSTEMCTL, action, service]
    if use_sudo: cmd = ["sudo"] + cmd
    return run_cmd(cmd)

# ---------- Cron helpers ----------

def get_user_crontab():
    code, out, err = run_cmd([CRONTAB, "-l"])
    # pas de crontab -> code != 0 => on considère "(vide)"
    return out if code == 0 else ""

def set_user_crontab(content):
    return run_cmd([CRONTAB, "-"], input_data=content)

def ensure_cron_line(username):
    current = get_user_crontab()
    line_final = CRON_LINE.replace("{USER}", username)
    # matching simple (évite doublons exacts)
    if line_final not in current.splitlines():
        new = (current + "\n" if current else "") + line_final + "\n"
        code, out, err = set_user_crontab(new)
        return code == 0, line_final, (err or out)
    return None, line_final, ""

# ---------- GUI logger ----------

class TextLogger(ttk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.text = tk.Text(self, height=14, wrap="word",
                            bg="#0f1117", fg="#d1e7ff", insertbackground="#d1e7ff")
        self.text.config(state="disabled")
        self.text.pack(fill="both", expand=True)
        self.queue = queue.Queue()
        self.after(200, self._poll)

    def log(self, s):
        ts = datetime.now().strftime("%H:%M:%S")
        self.queue.put(f"[{ts}] {s}\n")

    def _poll(self):
        try:
            while True:
                s = self.queue.get_nowait()
                self.text.config(state="normal")
                self.text.insert("end", s)
                self.text.see("end")
                self.text.config(state="disabled")
        except queue.Empty:
            pass
        self.after(200, self._poll)

# ---------- Script runner ----------

class ScriptRunner:
    def __init__(self, logger: TextLogger):
        self.logger = logger
        self.proc = None
        self.q = queue.Queue()
        self._polling = False

    def run(self, cmd, workdir="/var/www/html"):
        if self.proc:
            messagebox.showwarning("Déjà en cours", "Un script tourne déjà.")
            return
        self.logger.log(f"Exec {shlex.join(cmd)}")

        def _reader():
            try:
                self.proc = subprocess.Popen(
                    cmd, cwd=workdir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                assert self.proc.stdout is not None
                for line in self.proc.stdout:
                    self.q.put(line)
            except Exception as e:
                self.q.put(f"[ERROR] {e}\n")
            finally:
                code = self.proc.wait() if self.proc else -1
                self.q.put(("__EXIT__", code))

        threading.Thread(target=_reader, daemon=True).start()
        if not self._polling:
            self._polling = True
            self._drain()

    def _drain(self):
        try:
            while True:
                it = self.q.get_nowait()
                if isinstance(it, tuple) and it[0] == "__EXIT__":
                    self.logger.log(f"[done] rc={it[1]}")
                    self.proc = None
                    self._polling = False
                    return
                else:
                    self.logger.log(it)
        except queue.Empty:
            pass
        if self.proc:
            self.logger.after(80, self._drain)
        else:
            self._polling = False

# ---------- GUI ----------

class UwUGui(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self.pack(fill="both", expand=True)

        existing_logs = [str(p) for p in LOG_CANDIDATES if p.exists()]
        default_log = existing_logs[0] if existing_logs else ""
        self.selected_log = tk.StringVar(value=default_log)

        self.runner = None
        self._build_layout()
        self._start_stats()

    def _frame_card(self, parent, title):
        return ttk.LabelFrame(parent, text=title, padding=8)

    def _build_layout(self):
        # Stats
        stats = self._frame_card(self, "Stats système")
        stats.pack(fill="x", pady=4)
        self.lbl_cpu  = ttk.Label(stats, text="CPU: …");  self.lbl_cpu.pack(anchor="w")
        self.lbl_ram  = ttk.Label(stats, text="RAM: …");  self.lbl_ram.pack(anchor="w")
        self.lbl_disk = ttk.Label(stats, text="Disk: …"); self.lbl_disk.pack(anchor="w")

        # Services
        svc = self._frame_card(self, "Services systemd")
        svc.pack(fill="x", pady=4)
        for name, port in SERVICES:
            row = ttk.Frame(svc); row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{name} (:{port})").pack(side="left")
            for act in ["start", "stop", "restart", "status"]:
                ttk.Button(row, text=act.capitalize(),
                           command=lambda n=name, a=act: self.do_service(n, a)).pack(side="left", padx=2)

        # Script
        scr = self._frame_card(self, "Script logs_auto.py")
        scr.pack(fill="x", pady=4)
        ttk.Button(scr, text="Lancer logs_auto.py", command=self.run_logs_auto).pack(side="left", padx=4)

        # Cron
        cron = self._frame_card(self, "Cron")
        cron.pack(fill="x", pady=4)
        ttk.Button(cron, text="Afficher", command=self.show_crontab).pack(side="left", padx=4)
        ttk.Button(cron, text="Assurer ligne logs_auto.py", command=self.ensure_cron).pack(side="left", padx=4)
        self.lbl_cron = ttk.Label(cron, text=""); self.lbl_cron.pack(side="left")

        # Logs
        logf = self._frame_card(self, "Logs")
        logf.pack(fill="both", expand=True, pady=4)
        top = ttk.Frame(logf); top.pack(fill="x")
        self.cmb_log = ttk.Combobox(top, textvariable=self.selected_log,
                                    values=[str(p) for p in LOG_CANDIDATES if p.exists()],
                                    width=60)
        self.cmb_log.pack(side="left", padx=4)
        ttk.Button(top, text="Parcourir…", command=self.pick_log).pack(side="left", padx=4)
        ttk.Button(top, text="Tail 200", command=self.tail_log).pack(side="left", padx=4)

        self.log_view = TextLogger(logf)
        self.log_view.pack(fill="both", expand=True)
        self.runner = ScriptRunner(self.log_view)

    # Actions
    def do_service(self, name, action):
        rc, out, err = service_cmd(name, action)
        if rc == 0:
            self.log_view.log(f"{name} {action}: OK")
            if out: self.log_view.log(out)
        else:
            msg = err or out or "(aucune sortie)"
            self.log_view.log(f"{name} {action}: ERR — {msg}")

    def run_logs_auto(self):
        if not SCRIPT_LOGS_AUTO.exists():
            messagebox.showerror("logs_auto.py", f"Introuvable: {SCRIPT_LOGS_AUTO}")
            return
        self.runner.run([PY, str(SCRIPT_LOGS_AUTO)])

    def show_crontab(self):
        c = get_user_crontab() or "(vide)"
        self._popup("Crontab", c)

    def ensure_cron(self):
        user = getpass.getuser()
        changed, line, err = ensure_cron_line(user)
        if changed:
            self.lbl_cron.config(text="Ajouté ✓")
            self.log_view.log(f"Cron ajouté: {line}")
        elif changed is None:
            self.lbl_cron.config(text="Déjà présent ✓")
            self.log_view.log("Cron: déjà présent")
        else:
            self.lbl_cron.config(text="Erreur")
            messagebox.showerror("Cron", err or "échec crontab")

    def pick_log(self):
        p = filedialog.askopenfilename(initialdir=str(LOG_DIR), title="Choisir un fichier log")
        if p:
            self.selected_log.set(p)

    def tail_log(self):
        p = Path(self.selected_log.get())
        if not p.exists():
            return messagebox.showerror("Log", f"Introuvable: {p}")
        rc, out, err = run_cmd(["tail", "-n", "200", str(p)])
        if rc == 0:
            self.log_view.log(f"--- tail {p} ---\n{out}")
        else:
            self.log_view.log(f"[tail ERR] {err or out}")

    def _popup(self, title, content):
        win = tk.Toplevel(self); win.title(title)
        txt = tk.Text(win, width=100, height=30)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", content)
        txt.config(state="disabled")

    # Stats loop
    def _start_stats(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            import psutil
        except Exception:
            psutil = None
        while True:
            try:
                cpu = psutil.cpu_percent(0.6) if psutil else get_cpu_percent_fallback(0.6)
                if psutil:
                    vm = psutil.virtual_memory(); ru, rt, rp = vm.used, vm.total, vm.percent
                else:
                    ru, rt, rp = get_meminfo_fallback()
                if psutil:
                    du = psutil.disk_usage("/"); u, t, p = du.used, du.total, du.percent
                else:
                    u, t, p = get_disk_usage("/")
                self.after(0, lambda: self._update(cpu, ru, rt, rp, u, t, p))
            except Exception:
                pass
            time.sleep(1)

    def _update(self, cpu, ru, rt, rp, du, dt, dp):
        self.lbl_cpu.config(text=f"CPU: {cpu:.1f}%")
        self.lbl_ram.config(text=f"RAM: {human_bytes(ru)} / {human_bytes(rt)} ({rp:.1f}%)")
        self.lbl_disk.config(text=f"Disk: {human_bytes(du)} / {human_bytes(dt)} ({dp:.1f}%)")

def main():
    root = tk.Tk()
    root.title("UwU Logs – Dashboard")
    root.geometry("1000x700")
    UwUGui(root)
    root.mainloop()

if __name__ == "__main__":
    main()


#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UwU Logs – Dashboard GUI (multi-langue, tooltips, fix permissions, tail -F, sorties live)
"""

import os, sys, time, shlex, queue, getpass, threading, subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ===================== CONFIG =====================

BASE_DIR = Path("/var/www/html")
VENV_PY  = BASE_DIR / "venv" / "bin" / "python"
PY        = str(VENV_PY if VENV_PY.exists() else sys.executable)

LOG_DIR  = BASE_DIR / "_loggers"
LOG_CANDIDATES = [
    LOG_DIR / "server_main.log",
    LOG_DIR / "server_top.log",
    LOG_DIR / "uploads.log",
    LOG_DIR / "reports.log",
]

SERVICES = [
    ("server_5000", 5000),
    ("server_5010", 5010),
    ("server_5020", 5020),
]

SCRIPT_LOGS_AUTO  = BASE_DIR / "logs_auto.py"
SCRIPT_FIX_PERMS  = BASE_DIR / "tools" / "fix_uwu_permissions.sh"
SCRIPT_FETCH_ICONS = BASE_DIR / "tools" / "fetch_items_icons.py"
SCRIPT_REPARSE_ALL = BASE_DIR / "tools" / "reparse_all.py"

CRON_LINE = (
    r'*/2 * * * * cd /var/www/html && /var/www/html/venv/bin/python '
    r'/var/www/html/logs_auto.py >> /home/{USER}/logs/logs_auto.log 2>&1'
)

# ===================== TRADUCTIONS =====================

TR = {
    "fr": {
        # Titres cadres
        "sudo_options": "Options sudo ⚙️",
        "stats": "Stats système 🖥️",
        "services": "Services systemd 🚀",
        "script": "Script Outils  📜",
        "cron": "Cron ⏰",
        "permissions": "Permissions 🔐",
        "autre": "Future ",
        "logs": "Logs 📑",

        # Boutons / labels
        "use_sudo": "Utiliser sudo",
        "sudo_non_interactive": "sudo -n (non interactif)",
        "run_logs_auto": "▶️ Lancer Logs_auto",
        "run_reparse_all": "▶️ Correction No gear snapshots",
        "show_cron": "Afficher",
        "ensure_cron": "Assurer ligne logs_auto.py",
        "fix_permissions": "Corriger les permissions",
        "download_icons": "📦 Télécharger icônes",
        "browse": "Parcourir…",
        "tail200": "Tail 200",
        "follow": "Suivre (tail -f)",
        "stop_follow": "Stop suivi",

        # Tooltips
        "tt_lang": "Changer de langue (FR/EN)",
        "tt_use_sudo": "Exécuter les commandes avec sudo.",
        "tt_sudo_n": "Utiliser sudo -n (n'interrompt pas pour un mot de passe).",
        "tt_cpu": "Charge CPU moyenne instantanée.",
        "tt_ram": "Mémoire utilisée / totale.",
        "tt_disk": "Espace disque utilisé / total.",
        "tt_service_start": "Démarrer le service systemd.",
        "tt_service_stop": "Arrêter le service systemd.",
        "tt_service_restart": "Redémarrer le service systemd.",
        "tt_service_status": "Afficher l'état du service systemd.",
        "tt_logs_auto": "Lancer le script logs_auto.py et voir la sortie en direct.",
        "tt_cron_show": "Afficher votre crontab utilisateur actuelle.",
        "tt_cron_ensure": "Ajouter la ligne logs_auto.py s'il manque dans votre crontab.",
        "tt_fix_perms": "Réparer les permissions de tous les dossiers UwU Logs.",
        "tt_fetch_icons": "Télécharger toutes les icônes (items/gemmes/enchant) nécessaires.",
        "tt_browse": "Choisir un fichier de log à afficher.",
        "tt_tail200": "Afficher les 200 dernières lignes du fichier sélectionné.",
        "tt_follow": "Suivre en direct (tail -f) le fichier sélectionné.",
        "tt_stop_follow": "Arrêter le suivi en direct.",
        "tt_reparse_all": "Correction No gear snapshots",
        "tt_reparse_all": "Lancer le script reparse_all.py pour régénérer les équipements.",
    },
    "en": {
        "sudo_options": "Sudo options ⚙️",
        "stats": "System stats 🖥️",
        "services": "Systemd services 🚀",
        "script": "script tools  📜",
        "cron": "Cron ⏰",
        "permissions": "Permissions 🔐",
        "Autre": "Future ",
        "logs": "Logs 📑",

        "use_sudo": "Use sudo",
        "sudo_non_interactive": "sudo -n (non interactive)",
        "run_logs_auto": "▶️ Run logs_auto",
        "run_reparse_all": "▶️ Fix No gear snapshots",
        "show_cron": "Show",
        "ensure_cron": "Ensure logs_auto.py line",
        "fix_permissions": "Fix permissions",
        "download_icons": "📦 Download icons",
        "browse": "Browse…",
        "tail200": "Tail 200",
        "follow": "Follow (tail -f)",
        "stop_follow": "Stop follow",

        "tt_lang": "Switch language (FR/EN).",
        "tt_use_sudo": "Run commands with sudo.",
        "tt_sudo_n": "Use sudo -n (won't prompt for password).",
        "tt_cpu": "Instant average CPU load.",
        "tt_ram": "Memory used / total.",
        "tt_disk": "Disk space used / total.",
        "tt_service_start": "Start the systemd service.",
        "tt_service_stop": "Stop the systemd service.",
        "tt_service_restart": "Restart the systemd service.",
        "tt_service_status": "Show the systemd service status.",
        "tt_logs_auto": "Run logs_auto.py and watch live output.",
        "tt_cron_show": "Show your current user crontab.",
        "tt_cron_ensure": "Add logs_auto.py line if missing in your crontab.",
        "tt_fix_perms": "Fix permissions for all UwU Logs folders.",
        "tt_fetch_icons": "Download all required icons (items/gems/enchant).",
        "tt_browse": "Choose a log file to display.",
        "tt_tail200": "Show last 200 lines of selected file.",
        "tt_follow": "Follow selected file in real time (tail -f).",
        "tt_stop_follow": "Stop following in real time.",
        "tt_reparse_all": "Fix No gear snapshots",
        "tt_reparse_all": "Run reparse_all.py script to regenerate gear snapshots.",

    }
}

# ===================== Tooltips =====================

class CreateToolTip:
    def __init__(self, widget, text_getter):
        self.widget = widget
        self.text_getter = text_getter  # function returning localized text
        self.tipwindow = None
        self.id = None
        widget.bind("<Enter>", self._enter)
        widget.bind("<Leave>", self._leave)

    def _enter(self, _=None):
        self._schedule()

    def _leave(self, _=None):
        self._unschedule()
        self._hide()

    def _schedule(self):
        self._unschedule()
        self.id = self.widget.after(450, self._show)

    def _unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def _show(self):
        if self.tipwindow: return
        text = self.text_getter()
        if not text: return
        x, y, cx, cy = self.widget.bbox("insert") if self.widget.bbox("insert") else (0,0,0,0)
        x = self.widget.winfo_rootx() + 30
        y = self.widget.winfo_rooty() + cy + 30
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=text, justify="left",
                         background="#ffffe0", relief="solid",
                         borderwidth=1, font=("tahoma", "9"))
        label.pack(ipadx=1, ipady=1)
        self.tipwindow = tw

    def _hide(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

# ===================== Helpers =====================

def which(cmd):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        x = Path(p) / cmd
        if x.exists() and os.access(x, os.X_OK):
            return str(x)
    return None

SYSTEMCTL = which("systemctl") or "/bin/systemctl"
CRONTAB   = which("crontab")   or "/usr/bin/crontab"

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

# ===================== Logger widget =====================

class TextLogger(ttk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.text = tk.Text(self, height=14, wrap="word",
                            bg="#0f1117", fg="#d1e7ff", insertbackground="#d1e7ff")
        self.text.config(state="disabled")
        self.text.pack(fill="both", expand=True)
        self.queue = queue.Queue()
        self.after(120, self._poll)

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
        self.after(120, self._poll)

# ===================== ScriptRunner (stdout live) =====================

class ScriptRunner:
    def __init__(self, logger: TextLogger, tk_root):
        self.logger = logger
        self.proc = None
        self.q = queue.Queue()
        self._polling = False
        self.tk_root = tk_root   # racine Tkinter (root) pour after()

    def run(self, cmd, workdir="/var/www/html"):
        if self.proc:
            messagebox.showwarning("Déjà en cours", "Un script tourne déjà.")
            return

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self.logger.log(f"[RUN] cwd={workdir}")
        self.logger.log(f"[RUN] cmd={' '.join(cmd)}")

        def _reader(pipe, prefix=""):
            try:
                for line in iter(pipe.readline, ""):
                    if line:
                        self.q.put(prefix + line.rstrip("\n"))
            finally:
                pipe.close()

        def _runner():
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=workdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env
                )
                threading.Thread(target=_reader, args=(self.proc.stdout, ""), daemon=True).start()
                threading.Thread(target=_reader, args=(self.proc.stderr, "[ERR] "), daemon=True).start()
                code = self.proc.wait()
                self.q.put(("__EXIT__", code))
            except Exception as e:
                self.q.put(f"[ERROR] {e}")

        threading.Thread(target=_runner, daemon=True).start()
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
            self.tk_root.after(80, self._drain)  # correction importante
        else:
            self._polling = False


# ===================== GUI =====================

class UwUGui(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self.grid(sticky="nsew")  # grid au lieu de pack, pour le rendre extensible

        # --- Make self expand properly ---
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Langue
        self.lang = "fr"

        # Sudo
        self.use_sudo = tk.BooleanVar(value=True)
        self.sudo_non_interactive = tk.BooleanVar(value=True)

        # Log files
        existing_logs = [str(p) for p in LOG_CANDIDATES if p.exists()]
        default_log = existing_logs[0] if existing_logs else ""
        self.selected_log = tk.StringVar(value=default_log)

        # Tail
        self.tail_proc = None
        self.tail_thread = None
        self.tail_stop = threading.Event()

        self._text_bindings = []      # [(widget, key), ...]
        self._tooltip_bindings = []   # [(tooltip, key), ...]

        # Layout
        self._build_layout()
        self._start_stats()

        self.winfo_toplevel().protocol("WM_DELETE_WINDOW", self._on_close)


    # ---------- Localisation helpers ----------
    def T(self, key):  # text
        return TR[self.lang].get(key, key)

    def TT(self, key):  # tooltip
        return TR[self.lang].get(key, "")

    def bind_text(self, widget, key):
        self._text_bindings.append((widget, key))

    def bind_tip(self, widget, key):
        tip = CreateToolTip(widget, lambda k=key: self.TT(k))
        self._tooltip_bindings.append((tip, key))

    def switch_lang(self):
        self.lang = "en" if self.lang == "fr" else "fr"
        # refresh texts
        for w, k in self._text_bindings:
            try: w.config(text=self.T(k))
            except: pass
        # tooltips use lambdas bound to self.TT so nothing to update here

    # ---------- Layout ----------
    def _frame_card(self, parent, title_key):
        f = ttk.LabelFrame(parent, text=self.T(title_key), padding=8)
        self.bind_text(f, title_key)
        return f

    def _build_layout(self):
        # Paned horizontal
        pw = ttk.Panedwindow(self, orient="horizontal")
        left  = ttk.Frame(pw, width=550)   # largeur fixe de départ
        right = ttk.Frame(pw)

        pw.add(left, weight=0)   # minsize protège la colonne gauche
        pw.add(right, weight=3)               # colonne droite s’étire mieux
        pw.pack(fill="both", expand=True)

        # --- Langue ---
        topbar = ttk.Frame(left); topbar.pack(fill="x", pady=4)
        btn_lang = ttk.Button(topbar, text="🇫🇷/🇺🇸", command=self.switch_lang)
        btn_lang.pack(side="left")
        self.bind_tip(btn_lang, "tt_lang")

        # --- Stats ---
        stats = self._frame_card(left, "stats"); stats.pack(fill="x", pady=4)
        self.lbl_cpu  = ttk.Label(stats, text="CPU: …");  self.lbl_cpu.pack(anchor="w")
        self.lbl_ram  = ttk.Label(stats, text="RAM: …");  self.lbl_ram.pack(anchor="w")
        self.lbl_disk = ttk.Label(stats, text="Disk: …"); self.lbl_disk.pack(anchor="w")
        self.bind_tip(self.lbl_cpu,  "tt_cpu")
        self.bind_tip(self.lbl_ram,  "tt_ram")
        self.bind_tip(self.lbl_disk, "tt_disk")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)


        # --- Services ---
        svc = self._frame_card(left, "services"); svc.pack(fill="x", pady=4)
        for name, port in SERVICES:
            row = ttk.Frame(svc); row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{name} (:{port})").pack(side="left")
            for act, ttip in [
                ("start",   "tt_service_start"),
                ("stop",    "tt_service_stop"),
                ("restart", "tt_service_restart"),
                ("status",  "tt_service_status"),
            ]:
                b = ttk.Button(row, text=act.capitalize(),
                               command=lambda n=name, a=act: self.do_service(n, a))
                b.pack(side="left", padx=2)
                self.bind_tip(b, ttip)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)

        # --- Script Logs_auto & Reparse_all ---
        scr = self._frame_card(left, "script"); scr.pack(fill="x", expand=True, pady=4)
        bt_run = ttk.Button(scr, text=self.T("run_logs_auto"), command=self.run_logs_auto)
        bt_run.pack(side="left", padx=4)
        self.bind_text(bt_run, "run_logs_auto")
        self.bind_tip(bt_run, "tt_logs_auto")
        
        bt_reparse = ttk.Button(scr, text=self.T("run_reparse_all"), command=self.run_reparse_all)
        bt_reparse.pack(side="left", padx=4)
        self.bind_text(bt_reparse, "run_reparse_all")
        self.bind_tip(bt_reparse, "tt_reparse_all")
        
        bt_icons = ttk.Button(scr, text=self.T("download_icons"), command=self.fetch_icons)
        bt_icons.pack(side="left", padx=4)
        self.bind_text(bt_icons, "download_icons")
        self.bind_tip(bt_icons, "tt_fetch_icons")

        
        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)

        # --- Cron ---
        cron = self._frame_card(left, "cron"); cron.pack(fill="x", pady=4)
        bt_show = ttk.Button(cron, text=self.T("show_cron"), command=self.show_crontab)
        bt_show.pack(side="left", padx=4)
        self.bind_text(bt_show, "show_cron")
        self.bind_tip(bt_show, "tt_cron_show")

        bt_ensure = ttk.Button(cron, text=self.T("ensure_cron"), command=self.ensure_cron)
        bt_ensure.pack(side="left", padx=4)
        self.bind_text(bt_ensure, "ensure_cron")
        self.bind_tip(bt_ensure, "tt_cron_ensure")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)
        
        # --- Permissions ---
        perm = self._frame_card(left, "permissions"); perm.pack(fill="x", pady=4)
        bt_fix = ttk.Button(perm, text=self.T("fix_permissions"), command=self.fix_permissions)
        bt_fix.pack(side="left", padx=4)
        self.bind_text(bt_fix, "fix_permissions")
        self.bind_tip(bt_fix, "tt_fix_perms")

        # ============ Colonne droite ============
        
        # --- Sudo options ---
        sudo_f = self._frame_card(right, "sudo_options"); sudo_f.pack(fill="x", pady=4)
        cb_sudo = ttk.Checkbutton(sudo_f, text=self.T("use_sudo"), variable=self.use_sudo)
        cb_sudo.pack(side="left", padx=4)
        self.bind_text(cb_sudo, "use_sudo")
        self.bind_tip(cb_sudo, "tt_use_sudo")

        cb_sudon = ttk.Checkbutton(sudo_f, text=self.T("sudo_non_interactive"), variable=self.sudo_non_interactive)
        cb_sudon.pack(side="left", padx=4)
        self.bind_text(cb_sudon, "sudo_non_interactive")
        self.bind_tip(cb_sudon, "tt_sudo_n")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)
        
        right_paned = ttk.Panedwindow(right, orient="vertical")
        right_paned.pack(fill="both", expand=True)
        

        # --- Logs (bas) ---
        logs_card = ttk.Frame(right_paned)
        right_paned.add(logs_card, weight=1)
        logf = self._frame_card(logs_card, "logs")
        logf.pack(fill="both", expand=True, pady=4)

        top = ttk.Frame(logf); top.pack(fill="x")
        self.cmb_log = ttk.Combobox(top, textvariable=self.selected_log,
                                    values=[str(p) for p in LOG_CANDIDATES if p.exists()],
                                    width=60)
        self.cmb_log.pack(side="left", padx=4)

        bt_browse = ttk.Button(top, text=self.T("browse"), command=self.pick_log)
        bt_browse.pack(side="left", padx=4)
        self.bind_text(bt_browse, "browse")
        self.bind_tip(bt_browse, "tt_browse")

        bt_tail = ttk.Button(top, text=self.T("tail200"), command=self.tail_log)
        bt_tail.pack(side="left", padx=4)
        self.bind_text(bt_tail, "tail200")
        self.bind_tip(bt_tail, "tt_tail200")

        bt_follow = ttk.Button(top, text=self.T("follow"), command=self.start_tail_follow)
        bt_follow.pack(side="left", padx=4)
        self.bind_text(bt_follow, "follow")
        self.bind_tip(bt_follow, "tt_follow")

        bt_stop = ttk.Button(top, text=self.T("stop_follow"), command=self.stop_tail_follow)
        bt_stop.pack(side="left", padx=4)
        self.bind_text(bt_stop, "stop_follow")
        self.bind_tip(bt_stop, "tt_stop_follow")

        self.log_view = TextLogger(logf)
        self.log_view.pack(fill="both", expand=True)
        self.runner = ScriptRunner(self.log_view, self.winfo_toplevel())
        

    # ---------- Actions ----------


    def fix_permissions(self):
        if not SCRIPT_FIX_PERMS.exists():
            return messagebox.showerror("Permissions", f"Script introuvable: {SCRIPT_FIX_PERMS}")
        self.runner.run(["bash", str(SCRIPT_FIX_PERMS)], workdir=str(BASE_DIR))

    def do_service(self, name, action):
        cmd = [SYSTEMCTL, action, name]
        if self.use_sudo.get():
            cmd = ["sudo"] + (["-n"] if self.sudo_non_interactive.get() else []) + cmd
        rc, out, err = run_cmd(cmd)
        if rc == 0:
            self.log_view.log(f"{name} {action}: OK")
            if out: self.log_view.log(out)
        else:
            self.log_view.log(f"{name} {action}: ERR — {err or out or '(aucune sortie)'}")

    def run_logs_auto(self):
        if not SCRIPT_LOGS_AUTO.exists():
            return messagebox.showerror("logs_auto.py", f"Introuvable: {SCRIPT_LOGS_AUTO}")
        self.runner.run([PY, "-u", str(SCRIPT_LOGS_AUTO)], workdir=str(BASE_DIR))

    def show_crontab(self):
        rc, out, err = run_cmd([CRONTAB, "-l"])
        txt = out if rc == 0 else (err or "(vide)")
        self._popup("Crontab", txt)
        
    def ensure_cron(self):
        user = getpass.getuser()
        line_final = CRON_LINE.replace("{USER}", user)
        rc, out, err = run_cmd([CRONTAB, "-l"])
        cur = out if rc == 0 else ""
        if line_final not in cur.splitlines():
            new = (cur + "\n" if cur else "") + line_final + "\n"
            rc2, out2, err2 = run_cmd([CRONTAB, "-"], input_data=new)
            if rc2 == 0:
                self.log_view.log(f"Cron ajouté: {line_final}")
                messagebox.showinfo("Cron", "Ligne ajoutée ✅")
            else:
                messagebox.showerror("Cron", err2 or out2 or "échec crontab")
        else:
            self.log_view.log("Cron: déjà présent")
            messagebox.showinfo("Cron", "Déjà présent ✓")

    def fetch_icons(self):
        if not SCRIPT_FETCH_ICONS.exists():
            return messagebox.showerror("Icônes", f"Script introuvable: {SCRIPT_FETCH_ICONS}")
        self.runner.run([PY, "-u", str(SCRIPT_FETCH_ICONS)], workdir=str(BASE_DIR))

    def run_reparse_all(self):
        if not SCRIPT_REPARSE_ALL.exists():
            return messagebox.showerror("Reparse", f"Script introuvable: {SCRIPT_REPARSE_ALL}")
        self.runner.run([PY, "-u", str(SCRIPT_REPARSE_ALL)], workdir=str(BASE_DIR))


    # ---------- Logs ----------
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

    def start_tail_follow(self):
        path = Path(self.selected_log.get())
        if not path.exists():
            return messagebox.showerror("Tail -f", f"Introuvable : {path}")
        if self.tail_proc:
            return messagebox.showinfo("Tail -f", "Déjà en cours. Clique sur ‘Stop suivi’ pour arrêter.")
        self.log_view.log(f"[tail -F] {path}")
        self.tail_stop.clear()

        def _tail():
            try:
                self.tail_proc = subprocess.Popen(
                    ["tail", "-n", "0", "-F", str(path)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                assert self.tail_proc.stdout is not None
                for line in self.tail_proc.stdout:
                    if self.tail_stop.is_set():
                        break
                    self.log_view.log(line.rstrip("\n"))
            except Exception as e:
                self.log_view.log(f"[tail ERR] {e}")
            finally:
                if self.tail_proc and self.tail_proc.poll() is None:
                    try: self.tail_proc.terminate()
                    except Exception: pass
                self.tail_proc = None

        self.tail_thread = threading.Thread(target=_tail, daemon=True)
        self.tail_thread.start()

    def stop_tail_follow(self):
        if not self.tail_proc:
            return
        self.tail_stop.set()
        try:
            if hasattr(self.tail_proc, "terminate"):
                self.tail_proc.terminate()
        except Exception:
            pass
        self.log_view.log("[tail] arrêt demandé")

    def _popup(self, title, content):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("640x480")

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        txt = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set)
        txt.insert("1.0", content)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True)

        scrollbar.config(command=txt.yview)


    # ---------- Stats ----------
    def _start_stats(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            import psutil
        except Exception:
            psutil = None
        while True:
            try:
                cpu = psutil.cpu_percent(0.6) if psutil else self._cpu_percent_fallback(0.6)
                if psutil:
                    vm = psutil.virtual_memory(); ru, rt, rp = vm.used, vm.total, vm.percent
                    du = psutil.disk_usage("/"); u, t, dp = du.used, du.total, du.percent
                else:
                    ru, rt, rp = self._meminfo_fallback()
                    u, t, dp   = self._disk_usage("/")
                self.after(0, lambda: self._update(cpu, ru, rt, rp, u, t, dp))
            except Exception:
                pass
            time.sleep(1)

    def _cpu_percent_fallback(self, interval=0.5):
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

    def _meminfo_fallback(self):
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = v.strip()
        tot = int(info.get("MemTotal", "0").split()[0])
        ava = int(info.get("MemAvailable", "0").split()[0])
        used = tot - ava; pct = (used/tot*100) if tot else 0
        return used*1024, tot*1024, pct

    def _disk_usage(self, path="/"):
        st = os.statvfs(path)
        total = st.f_frsize * st.f_blocks
        free  = st.f_frsize * st.f_bavail
        used  = total - free
        pct   = (used/total*100) if total else 0
        return used, total, pct

    def _update(self, cpu, ru, rt, rp, du, dt, dp):
        self.lbl_cpu.config(text=f"CPU: {cpu:.1f}%")
        self.lbl_ram.config(text=f"RAM: {human_bytes(ru)} / {human_bytes(rt)} ({rp:.1f}%)")
        self.lbl_disk.config(text=f"Disk: {human_bytes(du)} / {human_bytes(dt)} ({dp:.1f}%)")

    # ---------- Close ----------
    def _on_close(self):
        try: self.stop_tail_follow()
        except: pass
        self.winfo_toplevel().destroy()

# ===================== MAIN =====================

def apply_theme(root: tk.Tk, dark: bool = True):
    """Applique un thème adaptatif. Si le thème système ignore les bg ttk,
    on force un jeu de couleurs cohérent pour TLabel, TButton, TCombobox, etc.
    Passe dark=False pour un thème clair."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    if dark:
        # Couleurs sombres
        BG = "#1e1e2f"
        FG = "#f0f0f0"
        WBG = "#0f1117"   # widgets comme Text
        WFG = "#d1e7ff"
        SEL = "#2a2a40"

        root.configure(bg=BG)

        # Label/Frame/Button de base
        style.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TLabelFrame", background=BG, foreground=FG)
        style.configure("TButton", padding=6)
        style.map("TButton", foreground=[("active", FG)])

        # Checkbutton / Radiobutton
        style.configure("TCheckbutton", background=BG, foreground=FG)
        style.configure("TRadiobutton", background=BG, foreground=FG)

        # Combobox (important: field/foreground/list)
        style.configure("TCombobox",
                        fieldbackground=WBG,
                        foreground=WFG,
                        background=BG)
        # Pour certains thèmes, il faut aussi :
        try:
            style.element_create("Plain.TCombobox.field", "from", "clam")
            style.layout("TCombobox",
                [('Combobox.downarrow', {'side': 'right', 'sticky': 'ns'}),
                 ('Combobox.padding', {'expand': '1', 'sticky': 'nswe',
                   'children': [('Plain.TCombobox.field', {'sticky': 'nswe'})]})])
        except Exception:
            pass

        # Tooltips (les nôtres sont en tk.Label à fond jaune pâle, OK)
        # Zone de texte custom (tk.Text) → configure dans le code du widget:
        # self.text = tk.Text(..., bg=WBG, fg=WFG, insertbackground=WFG)

    else:
        # Thème clair “sécurisé” si le dark ne passe pas bien
        BG = "#ffffff"
        FG = "#000000"
        WBG = "#ffffff"
        WFG = "#000000"
        SEL = "#e6e6e6"

        root.configure(bg=BG)
        style.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TLabelFrame", background=BG, foreground=FG)
        style.configure("TButton", padding=6)
        style.configure("TCheckbutton", background=BG, foreground=FG)
        style.configure("TRadiobutton", background=BG, foreground=FG)
        style.configure("TCombobox",
                        fieldbackground=WBG,
                        foreground=WFG,
                        background=BG)


def main():
    root = tk.Tk()
    root.title("UwU Logs – Dashboard 😺")
    root.geometry("1350x720")

    # Responsive
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # >>> Thème adaptatif (dark=False = thème clair)
    apply_theme(root, dark=False)

    gui = UwUGui(root)
    gui.grid(sticky="nsew")  # on utilise grid pour le rendre responsive

    root.mainloop()



if __name__ == "__main__":
    main()


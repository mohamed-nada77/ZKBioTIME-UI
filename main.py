# File: main.py
import os, sys, json, hashlib, base64
import tkinter as tk
from tkinter import ttk, messagebox

from auth import login as remote_login
from ui.main_menu import launch_menu
from utils.state import get_token, get_auth_headers

TITLE = "ATTENDANCE"
ADMIN_USERS = {"IT"}  # only these can manage users

def asset_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, "assets", *parts)

# ---------- Local credential store ----------
def _appdata_dir():
    root = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(root, "ALPAGO")
    os.makedirs(path, exist_ok=True)
    return path

CREDS_PATH = os.path.join(_appdata_dir(), "creds.json")
SETTINGS_PATH = os.path.join(_appdata_dir(), "settings.json")

def _hash_pw(password: str, salt: bytes) -> str:
    h = hashlib.sha256(salt + password.encode("utf-8")).digest()
    return base64.b64encode(salt + h).decode("ascii")  # store salt+hash together

def _verify_pw(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored.encode("ascii"))
    salt, real = raw[:16], raw[16:]
    test = hashlib.sha256(salt + password.encode("utf-8")).digest()
    return test == real

def _load_creds():
    if os.path.exists(CREDS_PATH):
        try:
            with open(CREDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_creds(creds):
    with open(CREDS_PATH, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)

def _ensure_seed_users():
    creds = _load_creds()
    changed = False
    def seed_user(username, plain):
        nonlocal changed
        if username not in creds:
            salt = os.urandom(16)
            creds[username] = _hash_pw(plain, salt)
            changed = True
    seed_user("IT", "IT@team")
    if changed:
        _save_creds(creds)

def _load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_settings(data):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------- Admin prompts ----------
def _prompt_admin_auth(parent, creds):
    """Small modal asking for admin username+password; returns True if admin verified."""
    BG="black"; FG="white"
    dlg = tk.Toplevel(parent); dlg.title("Admin Authentication"); dlg.configure(bg=BG)
    dlg.transient(parent); dlg.grab_set()
    tk.Label(dlg, text="Admin Username", fg=FG, bg=BG).grid(row=0, column=0, padx=10, pady=(10,4), sticky="w")
    u = tk.Entry(dlg, width=24, bg="#111", fg="white", insertbackground="white", relief="flat")
    u.grid(row=0, column=1, padx=10, pady=(10,4))
    tk.Label(dlg, text="Admin Password", fg=FG, bg=BG).grid(row=1, column=0, padx=10, pady=4, sticky="w")
    p = tk.Entry(dlg, show="*", width=24, bg="#111", fg="white", insertbackground="white", relief="flat")
    p.grid(row=1, column=1, padx=10, pady=4)

    ok = {"v": False}
    def check():
        name, pwd = (u.get() or "").strip(), p.get()
        if name not in ADMIN_USERS or name not in creds or not _verify_pw(pwd, creds[name]):
            messagebox.showerror("Admin", "Invalid admin credentials.", parent=dlg); return
        ok["v"] = True; dlg.destroy()
    tk.Button(dlg, text="OK", command=check, bg="#222", fg="white", relief="flat", padx=12, pady=6)\
        .grid(row=2, column=0, padx=10, pady=10)
    tk.Button(dlg, text="Cancel", command=dlg.destroy, bg="#222", fg="white", relief="flat", padx=12, pady=6)\
        .grid(row=2, column=1, padx=10, pady=10)

    u.focus(); dlg.wait_window()
    return ok["v"]

def _show_manage_users_dialog(parent, creds):
    BG="black"; FG="white"
    dlg = tk.Toplevel(parent); dlg.title("Manage Users"); dlg.configure(bg=BG)
    dlg.transient(parent); dlg.grab_set(); dlg.geometry("360x220")
    tk.Label(dlg, text="Add New User", fg=FG, bg=BG, font=("Segoe UI", 11, "bold")).pack(pady=(10, 4))
    form = tk.Frame(dlg, bg=BG); form.pack(padx=12, pady=6, fill="x")
    tk.Label(form, text="Username", fg=FG, bg=BG).grid(row=0, column=0, sticky="w", pady=4)
    user_e = tk.Entry(form, width=24, bg="#111", fg="white", insertbackground="white", relief="flat"); user_e.grid(row=0, column=1, sticky="w")
    tk.Label(form, text="Password", fg=FG, bg=BG).grid(row=1, column=0, sticky="w", pady=4)
    pass_e = tk.Entry(form, show="*", width=24, bg="#111", fg="white", insertbackground="white", relief="flat"); pass_e.grid(row=1, column=1, sticky="w")

    def do_add():
        nu = (user_e.get() or "").strip()
        npw = pass_e.get()
        if not nu or not npw:
            messagebox.showwarning("Add User", "Enter username and password.", parent=dlg); return
        if nu in creds:
            messagebox.showerror("Add User", "User already exists.", parent=dlg); return
        salt = os.urandom(16)
        creds[nu] = _hash_pw(npw, salt)
        _save_creds(creds)
        messagebox.showinfo("Add User", f"User '{nu}' added.", parent=dlg)
        user_e.delete(0, tk.END); pass_e.delete(0, tk.END)

    btns = tk.Frame(dlg, bg=BG); btns.pack(pady=10, anchor="e", padx=12)
    tk.Button(btns, text="Save", command=do_add, bg="#222", fg="white", relief="flat", padx=14, pady=8).pack(side="left", padx=6)
    tk.Button(btns, text="Close", command=dlg.destroy, bg="#222", fg="white", relief="flat", padx=14, pady=8).pack(side="left", padx=6)

    user_e.focus(); dlg.wait_window()

# ---------- Local login dialog ----------
def local_gate_login():
    _ensure_seed_users()
    creds = _load_creds()
    settings = _load_settings()

    root = tk.Tk()
    root.title("ALPAGO – Local Login")
    root.configure(bg="black"); root.geometry("380x260")
    try:
        lp = asset_path("newg.png")
        if os.path.exists(lp):
            icon_img = tk.PhotoImage(file=lp)
            root.iconphoto(True, icon_img)
    except Exception:
        pass

    BG, FG = "black", "white"
    tk.Label(root, text="Sign in to ALPAGO", fg=FG, bg=BG, font=("Segoe UI", 12, "bold")).pack(pady=(12, 2))

    frm = tk.Frame(root, bg=BG); frm.pack(padx=12, pady=8, fill="x")
    tk.Label(frm, text="Username", fg=FG, bg=BG).grid(row=0, column=0, sticky="w", pady=4)
    user_var = tk.StringVar(value=settings.get("last_user", ""))
    user_entry = ttk.Combobox(frm, textvariable=user_var, width=24, values=sorted(creds.keys()))
    user_entry.grid(row=0, column=1, sticky="w")

    tk.Label(frm, text="Password", fg=FG, bg=BG).grid(row=1, column=0, sticky="w", pady=4)
    pass_var = tk.StringVar(value=base64.b64decode(settings["saved_password"]).decode("utf-8") if settings.get("remember_password") and settings.get("saved_password") else "")
    pass_entry = tk.Entry(frm, textvariable=pass_var, show="*", width=26, bg="#111", fg="white", insertbackground="white", relief="flat")
    pass_entry.grid(row=1, column=1, sticky="w")

    # Remember options
    opts = tk.Frame(root, bg=BG); opts.pack(fill="x", padx=12)
    remember_user = tk.BooleanVar(value=bool(settings.get("remember_user")))
    remember_pass = tk.BooleanVar(value=bool(settings.get("remember_password")))
    tk.Checkbutton(opts, text="Remember username", variable=remember_user, fg=FG, bg=BG, activeforeground=FG, activebackground=BG, selectcolor=BG).pack(anchor="w")
    tk.Checkbutton(opts, text="Remember password (not secure)", variable=remember_pass, fg=FG, bg=BG, activeforeground=FG, activebackground=BG, selectcolor=BG).pack(anchor="w")

    # Buttons row
    btns = tk.Frame(root, bg=BG); btns.pack(pady=10, fill="x", padx=12)

    result = {"ok": False, "user": None}

    def do_login(event=None):
        u, p = user_var.get().strip(), pass_var.get()
        if not u or not p:
            messagebox.showwarning("Login", "Enter username and password."); return
        if u not in creds:
            messagebox.showerror("Login", "Unknown user."); return
        if not _verify_pw(p, creds[u]):
            messagebox.showerror("Login", "Invalid password."); return

        # Save settings
        settings["remember_user"] = bool(remember_user.get())
        settings["remember_password"] = bool(remember_pass.get())
        if settings["remember_user"]:
            settings["last_user"] = u
        else:
            settings.pop("last_user", None)
        if settings["remember_password"]:
            settings["saved_password"] = base64.b64encode(p.encode("utf-8")).decode("ascii")
        else:
            settings.pop("saved_password", None)
        _save_settings(settings)

        result["ok"] = True
        result["user"] = u
        root.destroy()

    def do_manage_users():
        # Admin-only via prompt
        if not _prompt_admin_auth(root, creds):
            return
        _show_manage_users_dialog(root, creds)
        # refresh usernames list after changes
        user_entry["values"] = sorted(_load_creds().keys())

    # Left: Login/Exit ; Right: Manage Users
    left = tk.Frame(btns, bg=BG); left.pack(side="left")
    right = tk.Frame(btns, bg=BG); right.pack(side="right", anchor="e")
    tk.Button(left, text="Login", command=do_login, bg="#222", fg="white", relief="flat", padx=14, pady=8).pack(side="left", padx=6)
    tk.Button(left, text="Exit",  command=root.destroy,  bg="#222", fg="white", relief="flat", padx=14, pady=8).pack(side="left", padx=6)
    tk.Button(right, text="Manage Users", command=do_manage_users, bg="#222", fg="white", relief="flat", padx=14, pady=8).pack()

    root.bind("<Return>", do_login)
    user_entry.focus()
    root.mainloop()
    return result["ok"], result["user"]

# ---------- Main flow ----------
def main():
    ok, username = local_gate_login()
    if not ok:
        print("[ERROR] Local login failed or cancelled.")
        return

    # Continue with your remote/API login
    if remote_login():
        print("[DEBUG] Final token after login:", get_token())
        print("[DEBUG] Headers being passed:", get_auth_headers())

        menu_kwargs = {
            "title": TITLE,
            "theme": "black",
            "logo_path": asset_path("newg.png"),
            "icon_path": None,
            "modules": [
                {"label": "➕ Add Employee",      "module": "add_employee",         "entry_points": ["open_add_employee", "main", "run"]},
                {"label": "🔎 Check Employee",    "module": "check_employee",       "entry_points": ["open_check_employee", "main", "run"]},
                {"label": "🕒 Employee Attendance","module": "employee_attendance", "entry_points": ["open_department_attendance", "main", "run"]},
            ],
        }
        try:
            launch_menu(**menu_kwargs)
        except TypeError:
            launch_menu()
    else:
        print("[ERROR] Server login failed.")

if __name__ == "__main__":
    main()

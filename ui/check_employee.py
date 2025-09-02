# File: ui/check_employee.py
import os, sys
import tkinter as tk
from tkinter import messagebox
import requests
from config import BASE_URL
from utils.state import get_auth_headers

# ===== THEME =====
BG = "black"
FG = "white"
BTN_BG = "#222"
BTN_H  = "#333"
INPUT_BG = "#111"

def _asset_path(*parts):
    # Works in dev and frozen EXE
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", *parts)

def _app_dir():
    # Where to place log.txt (next to EXE when frozen)
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

def _add_header(win, text=""):
    header = tk.Frame(win, bg=BG)
    header.pack(fill="x", pady=(3, 5))
    logo = tk.Label(header, bg=BG)
    lp = _asset_path("newg.png")
    if os.path.exists(lp):
        try:
            from PIL import Image, ImageTk
            img = Image.open(lp); img.thumbnail((60, 60))
            ph = ImageTk.PhotoImage(img)
            logo.image = ph; logo.config(image=ph)
        except Exception:
            try:
                ph = tk.PhotoImage(file=lp)
                logo.image = ph; logo.config(image=ph)
            except Exception:
                logo.config(text="[LOGO]", fg=FG)
    else:
        logo.config(text="[LOGO]", fg=FG)
    logo.pack(side="left", padx=(5, 8))
    if text:
        tk.Label(header, text=text, font=("Segoe UI", 9, "bold"), fg=FG, bg=BG)\
          .pack(side="left", pady=(15, 0))

def open_check_employee(parent=None):
    win = tk.Toplevel(parent) if parent else tk.Toplevel()
    win.title("Check Employee Biometric")
    win.configure(bg=BG)
    win.geometry("520x420")

    _add_header(win, "")  # logo only

    # --- Input area ---
    frm = tk.Frame(win, bg=BG)
    frm.pack(fill="x", padx=10, pady=(6, 4))

    tk.Label(frm, text="Enter Employee Code:", fg=FG, bg=BG).grid(row=0, column=0, sticky="w", pady=4)
    code_var = tk.StringVar()
    code_entry = tk.Entry(frm, textvariable=code_var, bg=INPUT_BG, fg=FG, insertbackground=FG, width=24, relief="flat")
    code_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))

    # --- Buttons ---
    btns = tk.Frame(win, bg=BG)
    btns.pack(fill="x", padx=10, pady=6)

    def mkbtn(text, cmd):
        b = tk.Button(btns, text=text, command=cmd, bg=BTN_BG, fg="white",
                      activebackground=BTN_H, activeforeground="white",
                      padx=14, pady=8, relief="flat", cursor="hand2")
        b.pack(side="left", padx=(0,8))
        return b

    # --- Result box ---
    result_box = tk.Text(win, width=62, height=14, state='disabled',
                         font=('Consolas', 10), bg="#0e0e0e", fg="white")
    result_box.pack(padx=10, pady=(6,10), fill="both", expand=True)

    # ---- helpers (same idea, just safer) ----
    def _log_missing(code):
        try:
            path = os.path.join(_app_dir(), "log.txt")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[NOT FOUND] Employee code: {code}\n")
        except Exception as e:
            print("[WARN] Could not write log.txt:", e)

    def _has_any_biometric(emp):
        # same fields you used
        for field in ['fingerprint', 'face', 'palm', 'vl_face']:
            val = emp.get(field)
            if isinstance(val, str):
                v = val.strip().lower()
                if v and v != "-":
                    return True
            elif val:  # truthy non-string
                return True
        return False

    def _set_text(s):
        result_box.config(state='normal')
        result_box.delete(1.0, tk.END)
        result_box.insert(tk.END, s)
        result_box.config(state='disabled')

    def check(event=None):
        emp_code = code_var.get().strip()
        if not emp_code:
            messagebox.showwarning("Input Error", "Please enter an employee code.")
            return

        url = f"{BASE_URL}/personnel/api/employees/"
        headers = get_auth_headers()
        params = {"emp_code": emp_code}
        print("[DEBUG] Checking employee with code:", emp_code)

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            print("[DEBUG] Response:", resp.status_code)
            if resp.status_code != 200:
                try:
                    txt = resp.text
                except Exception:
                    txt = ""
                messagebox.showerror("Server Error", f"HTTP {resp.status_code}\n{txt}")
                return

            payload = resp.json() if resp.content else {}
            data = payload.get("data", []) if isinstance(payload, dict) else []
            if not data:
                messagebox.showinfo("Not Found", "No employee found with this code.")
                _log_missing(emp_code)
                return

            emp = data[0]  # keep same behavior
            biometric_result = "✅" if _has_any_biometric(emp) else "❌"

            dept_name = "N/A"
            dept = emp.get('department')
            if isinstance(dept, dict):
                dept_name = dept.get('dept_name', 'N/A')
            elif isinstance(dept, str):
                dept_name = dept

            pos_val = emp.get('position')
            if isinstance(pos_val, dict):
                pos_name = pos_val.get('position_name')
            else:
                pos_name = pos_val

            areas = emp.get('area') or []
            try:
                area_text = ", ".join([a.get('area_name','') for a in areas if isinstance(a, dict)]) or "N/A"
            except Exception:
                area_text = "N/A"

            info = (
                f"ID: {emp.get('id','')}\n"
                f"Code: {emp.get('emp_code','')}\n"
                f"Name: {(emp.get('first_name','') or '')} {(emp.get('last_name','') or '')}\n"
                f"Department: {dept_name}\n"
                f"Position: {pos_name or 'N/A'}\n"
                f"Area(s): {area_text}\n\n"
                f"BioMetrics: {biometric_result}\n"
            )

            _set_text(info)

        except Exception as e:
            print("[EXCEPTION] Failed to check employee:", e)
            messagebox.showerror("Error", str(e))

    mkbtn("Check", check)
    mkbtn("Close", win.destroy)

    # Enter to submit
    win.bind("<Return>", check)
    code_entry.focus()

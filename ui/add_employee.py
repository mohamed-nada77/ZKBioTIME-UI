# File: ui/add_employee.py
import os, sys, time
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from config import BASE_URL
from utils.state import get_auth_headers

# ===== THEME =====
BG = "black"
FG = "white"
BTN_BG = "#222"
BTN_H  = "#333"
INPUT_BG = "#111"
ENTRY_W = 26

def _asset_path(*parts):
    # Works in dev and frozen EXE
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", *parts)

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
        except Exception:
            try:
                ph = tk.PhotoImage(file=lp)
            except Exception:
                ph = None
        if ph:
            logo.image = ph
            logo.config(image=ph)
        else:
            logo.config(text="[LOGO]", fg=FG)
    else:
        logo.config(text="[LOGO]", fg=FG)
    logo.pack(side="left", padx=(5, 8))
    if text:
        tk.Label(header, text=text, font=("Segoe UI", 9, "bold"), fg=FG, bg=BG)\
          .pack(side="left", pady=(15, 0))

def _install_alpha_jump(combo: ttk.Combobox):
    """
    Letter-wise jump like native listboxes:
    - Press a letter to jump to the next item starting with that letter.
    - Re-press within a short window cycles through matches.
    - Works whether the combobox is readonly or editable.
    """
    state = {"last_char": "", "last_time": 0.0, "last_index": -1}

    def on_key(e):
        text = e.char or ""
        if len(text) != 1:
            return  # ignore non-printables here; arrow keys still work
        key = text.lower()
        if not key.isalnum():  # jump only on letters/digits
            return

        values = list(combo.cget("values"))
        if not values:
            return

        now = time.time()
        cycle = (key == state["last_char"] and (now - state["last_time"]) < 1.0)
        state["last_char"] = key
        state["last_time"] = now

        start_idx = (state["last_index"] + 1) if cycle else 0

        # Find next match starting with that key
        sel = None
        n = len(values)
        for i in range(n):
            idx = (start_idx + i) % n
            v = str(values[idx]).lower()
            if v.startswith(key):
                sel = idx
                break

        if sel is not None:
            state["last_index"] = sel
            combo.current(sel)  # moves selection & text
            # if dropdown is open, move the highlight too
            combo.event_generate("<<ComboboxSelected>>")

    combo.bind("<KeyPress>", on_key, add="+")  # keep default handling too

def open_add_employee(parent=None):
    win = tk.Toplevel(parent) if parent else tk.Toplevel()
    win.title("Add New Employee")
    win.configure(bg=BG)
    win.geometry("620x460")

    _add_header(win, "")  # logo only

    frm = tk.Frame(win, bg=BG)
    frm.pack(fill="x", padx=12, pady=8)

    def L(r, c, text):
        tk.Label(frm, text=text, fg=FG, bg=BG).grid(row=r, column=c, sticky="w", pady=6, padx=(0,8))

    # Employee ID (code)
    L(0,0,"Employee ID")
    emp_id_entry = tk.Entry(frm, width=ENTRY_W, bg=INPUT_BG, fg=FG, insertbackground=FG, relief="flat")
    emp_id_entry.grid(row=0, column=1, sticky="w")

    # First name
    L(1,0,"First Name")
    fname_entry = tk.Entry(frm, width=ENTRY_W, bg=INPUT_BG, fg=FG, insertbackground=FG, relief="flat")
    fname_entry.grid(row=1, column=1, sticky="w")

    # --- Departments (readonly; sorted; letter-jump) ---
    L(2,0,"Department")
    dept_var = tk.StringVar()
    dept_dropdown = ttk.Combobox(frm, textvariable=dept_var, state="readonly", width=ENTRY_W-2)
    dept_dropdown.grid(row=2, column=1, sticky="w")

    dept_map = {}
    try:
        page = 1
        while True:
            resp = requests.get(
                f"{BASE_URL}/personnel/api/departments/?page={page}",
                headers=get_auth_headers(), timeout=20
            )
            if resp.status_code != 200:
                break
            payload = resp.json() or {}
            data = payload.get("data", [])
            for dept in data:
                name = dept.get("dept_name")
                did  = dept.get("id")
                if name and did is not None:
                    dept_map[name] = did
            if not payload.get("next"):
                break
            page += 1
    except Exception as e:
        print("[ERROR] Fetching departments:", e)

    dept_values = sorted(dept_map.keys(), key=lambda s: s.lower())
    dept_dropdown["values"] = dept_values
    if dept_values:
        dept_dropdown.current(0)
    _install_alpha_jump(dept_dropdown)

    # --- Positions (editable; sorted; letter-jump still works on the list) ---
    L(3,0,"Position")
    pos_var = tk.StringVar()
    pos_dropdown = ttk.Combobox(frm, textvariable=pos_var, width=ENTRY_W-2)  # editable so user can add new
    pos_dropdown.grid(row=3, column=1, sticky="w")

    pos_map = {}
    try:
        page = 1
        while True:
            resp = requests.get(
                f"{BASE_URL}/personnel/api/positions/?page={page}",
                headers=get_auth_headers(), timeout=20
            )
            if resp.status_code != 200:
                break
            payload = resp.json() or {}
            data = payload.get("data", [])
            for pos in data:
                pname = pos.get("position_name")
                pid   = pos.get("id")
                if pname and pid is not None:
                    pos_map[pname] = pid
            if not payload.get("next"):
                break
            page += 1
    except Exception as e:
        print("[ERROR] Fetching positions:", e)

    pos_values = sorted(pos_map.keys(), key=lambda s: s.lower())
    pos_dropdown["values"] = pos_values
    if pos_values:
        pos_dropdown.current(0)
    _install_alpha_jump(pos_dropdown)

    # --- Area (fixed) ---
    L(4,0,"Area")
    tk.Label(frm, text="ALPAGO (Fixed)", fg=FG, bg=BG).grid(row=4, column=1, sticky="w")

    # Buttons
    btns = tk.Frame(win, bg=BG); btns.pack(fill="x", padx=12, pady=10)

    def submit(event=None):
        emp_code = emp_id_entry.get().strip()
        fname    = fname_entry.get().strip()
        dept_id  = dept_map.get(dept_var.get())
        pos_name = (pos_var.get() or "").strip()

        if not emp_code:
            messagebox.showwarning("Input", "Employee ID is required."); return
        if not fname:
            messagebox.showwarning("Input", "First Name is required."); return
        if not dept_id:
            messagebox.showwarning("Input", "Please select a Department."); return
        if not pos_name:
            messagebox.showwarning("Input", "Please enter or select a Position."); return

        # Ensure position exists (create if typed new)
        pos_id = pos_map.get(pos_name)
        if not pos_id:
            try:
                new_pos = requests.post(
                    f"{BASE_URL}/personnel/api/positions/",
                    headers=get_auth_headers(), timeout=20,
                    json={
                        "position_code": pos_name[:10] or "POS",
                        "position_name": pos_name,
                        "parent_position": None
                    }
                )
                if new_pos.status_code in (200, 201):
                    pos_id = (new_pos.json() or {}).get("id")
                    if pos_id:
                        pos_map[pos_name] = pos_id
                        # re-sort values and keep selection on the new one
                        new_vals = sorted(pos_map.keys(), key=lambda s: s.lower())
                        pos_dropdown["values"] = new_vals
                        pos_dropdown.set(pos_name)
                else:
                    messagebox.showerror("Position", f"Failed to create position.\n{new_pos.text}")
                    return
            except Exception as e:
                messagebox.showerror("Position", f"Error creating position:\n{e}")
                return

        payload = {
            "emp_code": emp_code,
            "first_name": fname,
            "department": dept_id,
            "position": pos_id,
            "area": [2]  # Always ALPAGO
        }

        try:
            res = requests.post(
                f"{BASE_URL}/personnel/api/employees/",
                headers=get_auth_headers(), json=payload, timeout=25
            )
            if res.status_code in (200, 201):
                messagebox.showinfo("Success", "Employee Added Successfully!")
                win.destroy()
            else:
                messagebox.showerror("Error", f"Failed to add employee.\nHTTP {res.status_code}\n{res.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Request failed:\n{e}")

    def cancel():
        win.destroy()

    def mkbtn(text, cmd):
        b = tk.Button(btns, text=text, command=cmd, bg=BTN_BG, fg="white",
                      activebackground=BTN_H, activeforeground="white",
                      padx=14, pady=8, relief="flat", cursor="hand2")
        b.pack(side="left", padx=(0,8))
        return b

    mkbtn("Submit", submit)
    mkbtn("Cancel", cancel)

    # Shortcuts
    win.bind("<Return>", submit)
    win.bind("<Escape>", lambda e: cancel())
    emp_id_entry.focus()

# Backwards-compat entry points
def main(): return open_add_employee()
def run():  return open_add_employee()

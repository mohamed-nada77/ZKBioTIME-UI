import os, sys, csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import requests

from config import BASE_URL
from utils.state import get_auth_headers

# Optional Excel support (openpyxl)
try:
    from openpyxl import Workbook
    HAVE_XLSX = True
except Exception:
    HAVE_XLSX = False

# ===== THEME =====
BG, FG = "black", "white"
BTN_BG, BTN_H = "#222", "#333"

def _asset_path(*parts):
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

# ==== Helpers ====
def _to_date(s):
    if not s: return None
    s = str(s)[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    return None

def _to_hhmm(ts):
    if not ts: return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try: return datetime.strptime(ts, fmt).strftime("%H:%M")
        except: pass
    # last resort: slice
    try: return str(ts)[11:16]
    except: return None

def _paginate(url, params=None):
    """Follow ?next pagination and collect transactions."""
    headers = get_auth_headers()
    items, next_url = [], url
    try:
        while next_url:
            r = requests.get(next_url, headers=headers,
                             params=(params if ('?' not in next_url) else None),
                             timeout=25)
            if r.status_code != 200:
                break
            payload = r.json() or {}
            chunk = payload.get("data") or payload.get("results")
            if isinstance(chunk, list):
                items.extend(chunk)
            elif isinstance(payload, list):
                items.extend(payload)
                break
            next_url = payload.get("next")
    except Exception as e:
        print("[ERROR] pagination:", e)
    return items

# ==== CORE: fetch + normalize for your endpoint ====
def fetch_employee_transactions(emp_code, start_date, end_date):
    """
    Pull from /iclock/api/transactions/ and filter by emp_code and date range.
    We try common filter params first; if backend ignores them, we paginate and filter client-side.
    """
    base = f"{BASE_URL}/iclock/api/transactions/"
    # Try server-side filters (edit if your backend uses different names)
    param_attempts = [
        {"emp_code": emp_code, "start": start_date, "end": end_date},
        {"emp_code": emp_code, "from": start_date, "to": end_date},
        {"emp_code": emp_code, "date__gte": start_date, "date__lte": end_date},
        {"emp": emp_code, "start": start_date, "end": end_date},  # if it expects numeric emp id
    ]

    # 1) try with params
    for params in param_attempts:
        try:
            data = _paginate(base, params=params)
            if data:
                return _filter_and_group(data, emp_code, start_date, end_date)
        except Exception as e:
            print("[WARN] fetch with params failed:", e)

    # 2) fallback: crawl pages and filter client-side (can be heavy if dataset is huge)
    print("[INFO] Falling back to client-side filtering over pagination…")
    data = _paginate(base)  # will rely on "next" chain the server returns
    return _filter_and_group(data, emp_code, start_date, end_date)

def _filter_and_group(records, emp_code, start_date, end_date):
    """Filter by emp_code and date window; then compute first/last punch per day."""
    s, e = _to_date(start_date), _to_date(end_date)
    out = {}
    for r in records:
        code = str(r.get("emp_code", "")).strip()
        if code != str(emp_code).strip():
            continue

        # pick the best timestamp field
        stamp = r.get("punch_time") or r.get("upload_time")
        if not stamp:
            continue

        day = str(stamp)[:10]
        d = _to_date(day)
        if not d or (s and d < s) or (e and d > e):
            continue

        hhmm = _to_hhmm(stamp)
        if not hhmm:
            continue

        slot = out.setdefault(day, {"first": None, "last": None, "punches": 0})
        if slot["first"] is None or hhmm < slot["first"]:
            slot["first"] = hhmm
        if slot["last"] is None or hhmm > slot["last"]:
            slot["last"] = hhmm
        slot["punches"] += 1

    return out

# ==== UI ====
def open_employee_attendance(parent=None):
    win = tk.Toplevel(parent) if parent else tk.Toplevel()
    win.title("Employee Attendance")
    win.configure(bg=BG)
    win.geometry("860x640")

    _add_header(win, "")  # logo only

    form = tk.Frame(win, bg=BG); form.pack(fill="x", padx=10, pady=6)
    tk.Label(form, text="Employee Code:", fg=FG, bg=BG).grid(row=0, column=0, sticky="w", pady=2)
    emp_var = tk.StringVar()
    tk.Entry(form, textvariable=emp_var, bg="#111", fg=FG, insertbackground=FG, width=22)\
        .grid(row=0, column=1, sticky="w", padx=(6, 18))

    tk.Label(form, text="From:", fg=FG, bg=BG).grid(row=1, column=0, sticky="w", pady=2)
    from_entry = DateEntry(form, date_pattern='yyyy-mm-dd'); from_entry.grid(row=1, column=1, sticky="w", padx=(6, 18))
    tk.Label(form, text="To (optional):", fg=FG, bg=BG).grid(row=1, column=2, sticky="w", pady=2)
    to_entry = DateEntry(form, date_pattern='yyyy-mm-dd'); to_entry.grid(row=1, column=3, sticky="w", padx=(6, 0))

    btns = tk.Frame(win, bg=BG); btns.pack(fill="x", padx=10, pady=6)

    result_box = tk.Text(win, width=110, height=24, state='disabled',
                         font=('Consolas', 10), bg="#0e0e0e", fg="white")
    result_box.pack(padx=10, pady=(6,10), fill="both", expand=True)

    store = {"rows": []}  # for export

    def render(rows):
        result_box.config(state="normal"); result_box.delete(1.0, tk.END)
        lines = []
        lines.append(f"{'Date':10}  {'First':8}  {'Last':8}  {'Punches':7}")
        lines.append(f"{'-'*10}  {'-'*8}  {'-'*8}  {'-'*7}")
        for d, first, last, n in rows:
            lines.append(f"{d:10}  {first:8}  {last:8}  {str(n):7}")
        result_box.insert(tk.END, "\n".join(lines))
        result_box.config(state="disabled")

    def do_search():
        emp = emp_var.get().strip()
        if not emp:
            messagebox.showwarning("Input Required", "Please enter Employee Code.")
            return
        s = from_entry.get_date().strftime("%Y-%m-%d")
        e = to_entry.get_date().strftime("%Y-%m-%d")
        if _to_date(e) < _to_date(s):
            messagebox.showwarning("Date Range", "End date must be on or after the start date.")
            return

        data = fetch_employee_transactions(emp, s, e)
        # turn dict->sorted rows; fill all days in range (so missing days appear)
        rows = []
        d = _to_date(s)
        endd = _to_date(e)
        while d <= endd:
            key = d.strftime("%Y-%m-%d")
            slot = data.get(key)
            if slot:
                first = slot["first"] or "--:--"
                last  = slot["last"]  or first or "--:--"
                n     = slot["punches"]
            else:
                first = last = "--:--"; n = 0
            rows.append((key, first, last, n))
            d += timedelta(days=1)

        store["rows"] = rows
        render(rows)

    def do_export():
        if not store["rows"]:
            messagebox.showinfo("Nothing to Export", "Run a search first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx" if HAVE_XLSX else ".csv",
            filetypes=[("Excel Workbook", "*.xlsx"), ("CSV", "*.csv"), ("All Files", "*.*")],
            title="Save Attendance"
        )
        if not path: return
        try:
            header = ["Date", "First", "Last", "Punches"]
            if path.lower().endswith(".xlsx") and HAVE_XLSX:
                wb = Workbook(); ws = wb.active; ws.title = "Attendance"
                ws.append(header)
                for r in store["rows"]: ws.append(list(r))
                wb.save(path)
            else:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f); w.writerow(header); w.writerows(store["rows"])
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save file.\n\n{e}")

    def mkbtn(t, cmd):
        b = tk.Button(btns, text=t, command=cmd, bg=BTN_BG, fg="white",
                      activebackground=BTN_H, activeforeground="white",
                      padx=14, pady=8, relief="flat", cursor="hand2")
        b.pack(side="left", padx=(0,8))

    mkbtn("Search", do_search)
    mkbtn("Export to Excel", do_export)
    mkbtn("Close", win.destroy)

# Backwards-compat if your router still calls this name:
def open_department_attendance(parent=None):
    return open_employee_attendance(parent)
def main(): return open_employee_attendance()
def run():  return open_employee_attendance()

# File: ui/main_menu.py
import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

BG = "black"
FG = "white"
BTN_BG = "#222"
BTN_BG_HOVER = "#333"
BTN_FG = "white"

def _hover_color(widget, enter=True):
    try:
        widget.configure(bg=BTN_BG_HOVER if enter else BTN_BG)
    except Exception:
        pass

def _resolve_asset(path_or_none):
    """Return a path that exists, trying sys._MEIPASS/assets if frozen."""
    if not path_or_none:
        return None
    # 1) If already exists (dev run), use it
    if os.path.exists(path_or_none):
        return path_or_none
    # 2) If frozen, try MEIPASS/assets/<basename>
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidate = os.path.join(base, "assets", os.path.basename(path_or_none))
        if os.path.exists(candidate):
            return candidate
    return None

def _safe_open(module_name, candidate_funcs, parent=None):
    """Import ui.<module_name> and call an entry function, showing errors in a dialog."""
    try:
        mod = __import__(f"ui.{module_name}", fromlist=["*"])
    except Exception as e:
        tb = traceback.format_exc()
        messagebox.showerror("Load Error", f"Could not import ui.{module_name}\n\n{e}\n\n{tb}")
        print(f"[ERROR] import ui.{module_name}:\n{tb}")
        return

    # Try common entry names in order
    candidates = list(dict.fromkeys(candidate_funcs + [
        "open_window", "open_ui", "show", "start", "launch", f"open_{module_name}"
    ]))

    import inspect
    for fname in candidates:
        fn = getattr(mod, fname, None)
        if callable(fn):
            try:
                sig = inspect.signature(fn)
                if len(sig.parameters) >= 1:
                    return fn(parent)  # pass parent if accepted
                else:
                    return fn()        # call without args
            except Exception as e:
                tb = traceback.format_exc()
                messagebox.showerror("Runtime Error", f"{module_name}.{fname}() failed:\n\n{e}\n\n{tb}")
                print(f"[ERROR] {module_name}.{fname}():\n{tb}")
                return

    messagebox.showerror("Entry Not Found",
                         f"No usable entry function found in ui.{module_name}.\nTried: {', '.join(candidates)}")
    print(f"[WARN] No entry point in ui.{module_name}: {candidates}")

def _header(parent, logo_path, header_text):
    header = tk.Frame(parent, bg=BG)
    header.pack(fill="x", pady=(5, 8))

    logo_label = tk.Label(header, bg=BG)

    # Resolve asset path for frozen builds
    resolved_logo = _resolve_asset(logo_path)
    if resolved_logo:
        try:
            from PIL import Image, ImageTk
            img = Image.open(resolved_logo)
            img.thumbnail((80, 80))
            photo = ImageTk.PhotoImage(img)
            logo_label.image = photo
            logo_label.configure(image=photo)
        except Exception:
            try:
                photo = tk.PhotoImage(file=resolved_logo)
                logo_label.image = photo
                logo_label.configure(image=photo)
            except Exception:
                logo_label.configure(text="[LOGO]", fg=FG, bg=BG)
    else:
        logo_label.configure(text="[LOGO]", fg=FG, bg=BG)

    logo_label.pack(side="left", padx=(8, 10))

    # Optional title text (you can pass "" from main.py to hide it)
    if header_text:
        title = tk.Label(
            header, text=header_text, font=("Segoe UI", 12, "bold"), fg=FG, bg=BG
        )
        title.pack(side="left", pady=(20, 0))

def _add_buttons(parent, modules):
    btns = tk.Frame(parent, bg=BG)
    btns.pack(anchor="w", fill="x")

    def add_btn(text, command):
        b = tk.Button(
            btns, text=text, command=command,
            bg=BTN_BG, fg=BTN_FG,
            activebackground=BTN_BG_HOVER, activeforeground=BTN_FG,
            font=("Segoe UI", 10), relief="flat", padx=14, pady=8, cursor="hand2"
        )
        b.pack(anchor="w", pady=4, fill="x")
        b.bind("<Enter>", lambda e: _hover_color(b, True))
        b.bind("<Leave>", lambda e: _hover_color(b, False))

    top = parent.winfo_toplevel()

    for m in modules:
        add_btn(
            m.get("label", "Open"),
            lambda mod=m["module"], eps=m["entry_points"]: _safe_open(mod, eps, top)
        )

    add_btn("⏻ Exit", top.destroy)

def launch_menu(title, theme, logo_path, icon_path, modules, header_text="ALPAGO ATTENDANCE"):
    root = tk.Tk()
    root.configure(bg=BG)
    root.title(title or "ATTENDANCE")

    # Resolve icon/ logo for frozen builds
    icon_resolved = _resolve_asset(icon_path)
    logo_resolved = _resolve_asset(logo_path)

    if icon_resolved:
        try:
            root.iconbitmap(icon_resolved)
        except Exception:
            pass
    elif logo_resolved:
        try:
            icon_img = tk.PhotoImage(file=logo_resolved)
            root.iconphoto(True, icon_img)
        except Exception:
            pass

    container = tk.Frame(root, bg=BG, padx=10, pady=10)
    container.pack(fill="both", expand=True)

    _header(container, logo_resolved or logo_path, header_text)

    tk.Label(
        container, text="Choose a module:", fg=FG, bg=BG, font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 8))

    _add_buttons(container, modules or [])

    root.minsize(900, 600)
    root.mainloop()

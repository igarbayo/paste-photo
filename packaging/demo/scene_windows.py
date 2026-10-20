# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Ventanas de la escena de la demo: `app` (factura con un fallo) o `backdrop` (fondo liso).

Uso: python scene_windows.py app|backdrop   (los lanza demo.py)
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

ctypes.windll.shcore.SetProcessDpiAwareness(2)

INK, MUTED, RED = "#1f1d1a", "#6b645d", "#c0392b"


def app() -> None:
    root = tk.Tk()
    root.title("Invoices")
    root.configure(bg="#ffffff")
    root.geometry("820x560+60+180")
    root.resizable(False, False)
    font = ("Segoe UI", 15)

    def label(text, x, y, **kw):
        tk.Label(root, text=text, bg=kw.pop("bg", "#ffffff"), **kw).place(x=x, y=y)

    label("Invoice #2026-104", 40, 30, font=("Segoe UI Semibold", 22), fg=INK)
    label("Client: Acme Studio", 42, 82, font=("Segoe UI", 13), fg=MUTED)
    for i, (name, price) in enumerate((("Design", "1,200.00 €"), ("Hosting", "240.00 €"),
                                       ("Support", "—"))):
        y = 150 + i * 62
        tk.Frame(root, bg="#ece7e1", height=2, width=740).place(x=40, y=y - 10)
        label(name, 40, y + 6, font=font, fg=INK)
        tk.Label(root, text=price, font=font, bg="#ffffff", fg=INK).place(x=780, y=y + 6,
                                                                          anchor="ne")
    tk.Frame(root, bg=INK, height=2, width=740).place(x=40, y=345)
    label("Total", 40, 365, font=("Segoe UI Semibold", 18), fg=INK)
    tk.Label(root, text="NaN €", font=("Segoe UI Semibold", 18), bg="#ffffff",
             fg=RED).place(x=780, y=365, anchor="ne")
    label("⚠  Could not compute the total", 40, 440, font=("Segoe UI", 13), bg="#fdecea",
          fg="#a93226", padx=14, pady=8)
    root.mainloop()


def backdrop() -> None:
    root = tk.Tk()
    root.title("PastePhoto backdrop")
    root.overrideredirect(True)
    root.configure(bg="#e9e3da")
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{width}x{height}+0+0")
    root.mainloop()


if __name__ == "__main__":
    {"app": app, "backdrop": backdrop}[sys.argv[1]]()

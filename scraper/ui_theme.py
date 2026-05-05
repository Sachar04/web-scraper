"""
Glassmorphism theme engine for Tkinter.
Provides modern, translucent card-style widgets with blur-inspired aesthetics.
"""

import tkinter as tk
from tkinter import ttk, font as tkfont


# ── Color Palette ──────────────────────────────────────────────
COLORS = {
    "bg_dark":        "#0B0D1A",
    "bg_mid":         "#121429",
    "bg_card":        "#1A1D36",
    "bg_card_hover":  "#222545",
    "bg_input":       "#14162B",
    "border":         "#2E3158",
    "border_light":   "#3D4170",
    "accent":         "#7C6AEF",
    "accent_hover":   "#9580FF",
    "accent_dim":     "#5B4CB8",
    "success":        "#3DDC84",
    "warning":        "#FFB347",
    "error":          "#FF6B6B",
    "text":           "#E8E6F0",
    "text_dim":       "#8B89A0",
    "text_muted":     "#5C5A72",
    "highlight":      "#A78BFA",
    "tag_bg":         "#2A2650",
    "scrollbar":      "#3A3D5C",
    "scrollbar_active": "#5B5E80",
}

# ── Font Definitions ──────────────────────────────────────────
FONTS = {
    "title":     ("Segoe UI", 20, "bold"),
    "heading":   ("Segoe UI", 14, "bold"),
    "subhead":   ("Segoe UI", 12, "bold"),
    "body":      ("Segoe UI", 11),
    "body_sm":   ("Segoe UI", 10),
    "mono":      ("Cascadia Code", 10),
    "mono_sm":   ("Cascadia Code", 9),
    "button":    ("Segoe UI", 11, "bold"),
    "tag":       ("Segoe UI", 9),
}


def apply_theme(root):
    """Apply the glassmorphism dark theme globally."""
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=COLORS["bg_dark"])
    root.option_add("*Font", FONTS["body"])
    root.option_add("*Background", COLORS["bg_dark"])
    root.option_add("*Foreground", COLORS["text"])

    # ── TFrame ─────────────────────────────────────────────
    style.configure("TFrame", background=COLORS["bg_dark"])
    style.configure("Card.TFrame", background=COLORS["bg_card"])
    style.configure("Dark.TFrame", background=COLORS["bg_mid"])

    # ── TLabel ─────────────────────────────────────────────
    style.configure("TLabel",
                    background=COLORS["bg_dark"],
                    foreground=COLORS["text"],
                    font=FONTS["body"])
    style.configure("Card.TLabel",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text"])
    style.configure("Title.TLabel",
                    background=COLORS["bg_dark"],
                    foreground=COLORS["text"],
                    font=FONTS["title"])
    style.configure("Heading.TLabel",
                    background=COLORS["bg_card"],
                    foreground=COLORS["highlight"],
                    font=FONTS["heading"])
    style.configure("Dim.TLabel",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text_dim"],
                    font=FONTS["body_sm"])
    style.configure("Status.TLabel",
                    background=COLORS["bg_dark"],
                    foreground=COLORS["text_dim"],
                    font=FONTS["body_sm"])

    # ── TButton ────────────────────────────────────────────
    style.configure("Accent.TButton",
                    background=COLORS["accent"],
                    foreground="#FFFFFF",
                    font=FONTS["button"],
                    borderwidth=0,
                    focuscolor="none",
                    padding=(16, 8))
    style.map("Accent.TButton",
              background=[("active", COLORS["accent_hover"]),
                          ("disabled", COLORS["bg_card"])],
              foreground=[("disabled", COLORS["text_muted"])])

    style.configure("Secondary.TButton",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text"],
                    font=FONTS["button"],
                    borderwidth=1,
                    focuscolor="none",
                    padding=(16, 8))
    style.map("Secondary.TButton",
              background=[("active", COLORS["bg_card_hover"])],
              foreground=[("active", COLORS["text"])])

    style.configure("Small.TButton",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text_dim"],
                    font=FONTS["body_sm"],
                    borderwidth=0,
                    focuscolor="none",
                    padding=(8, 4))
    style.map("Small.TButton",
              background=[("active", COLORS["bg_card_hover"])],
              foreground=[("active", COLORS["text"])])

    # ── TEntry ─────────────────────────────────────────────
    style.configure("TEntry",
                    fieldbackground=COLORS["bg_input"],
                    foreground=COLORS["text"],
                    insertcolor=COLORS["text"],
                    borderwidth=1,
                    relief="flat",
                    padding=(10, 8))
    style.map("TEntry",
              fieldbackground=[("focus", COLORS["bg_card"])],
              bordercolor=[("focus", COLORS["accent"])])

    # ── TCheckbutton ───────────────────────────────────────
    style.configure("TCheckbutton",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text"],
                    font=FONTS["body"],
                    focuscolor="none",
                    indicatorcolor=COLORS["bg_input"],
                    indicatorrelief="flat")
    style.map("TCheckbutton",
              background=[("active", COLORS["bg_card_hover"])],
              indicatorcolor=[("selected", COLORS["accent"])])

    # ── TCombobox ──────────────────────────────────────────
    style.configure("TCombobox",
                    fieldbackground=COLORS["bg_input"],
                    background=COLORS["bg_card"],
                    foreground=COLORS["text"],
                    arrowcolor=COLORS["text_dim"],
                    borderwidth=1,
                    padding=(8, 6))
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["bg_input"])],
              foreground=[("readonly", COLORS["text"])])
    root.option_add("*TCombobox*Listbox.background", COLORS["bg_card"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent"])

    # ── TNotebook ──────────────────────────────────────────
    style.configure("TNotebook",
                    background=COLORS["bg_dark"],
                    borderwidth=0,
                    tabmargins=(4, 4, 4, 0))
    style.configure("TNotebook.Tab",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text_dim"],
                    font=FONTS["subhead"],
                    padding=(20, 10),
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_mid"]),
                          ("active", COLORS["bg_card_hover"])],
              foreground=[("selected", COLORS["accent"]),
                          ("active", COLORS["text"])])

    # ── Treeview ───────────────────────────────────────────
    style.configure("Treeview",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text"],
                    fieldbackground=COLORS["bg_card"],
                    borderwidth=0,
                    font=FONTS["body_sm"],
                    rowheight=28)
    style.configure("Treeview.Heading",
                    background=COLORS["bg_mid"],
                    foreground=COLORS["highlight"],
                    font=FONTS["subhead"],
                    borderwidth=0,
                    relief="flat")
    style.map("Treeview",
              background=[("selected", COLORS["accent_dim"])],
              foreground=[("selected", "#FFFFFF")])
    style.map("Treeview.Heading",
              background=[("active", COLORS["bg_card_hover"])])

    # ── TProgressbar ───────────────────────────────────────
    style.configure("Horizontal.TProgressbar",
                    background=COLORS["accent"],
                    troughcolor=COLORS["bg_card"],
                    borderwidth=0,
                    thickness=6)

    # ── Scrollbar ──────────────────────────────────────────
    style.configure("Vertical.TScrollbar",
                    background=COLORS["scrollbar"],
                    troughcolor=COLORS["bg_card"],
                    borderwidth=0,
                    arrowsize=0,
                    width=8)
    style.map("Vertical.TScrollbar",
              background=[("active", COLORS["scrollbar_active"])])

    # ── TSeparator ─────────────────────────────────────────
    style.configure("TSeparator", background=COLORS["border"])

    # ── TLabelframe ────────────────────────────────────────
    style.configure("TLabelframe",
                    background=COLORS["bg_card"],
                    foreground=COLORS["text"],
                    bordercolor=COLORS["border"],
                    borderwidth=1,
                    relief="flat")
    style.configure("TLabelframe.Label",
                    background=COLORS["bg_card"],
                    foreground=COLORS["highlight"],
                    font=FONTS["subhead"])


def create_glass_card(parent, **kwargs):
    """Create a frame that looks like a glassmorphism card."""
    card = tk.Frame(
        parent,
        bg=COLORS["bg_card"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
        bd=0,
        **kwargs,
    )
    return card


def create_styled_text(parent, height=10, width=60, **kwargs):
    """Create a styled Text widget matching the theme."""
    text = tk.Text(
        parent,
        bg=COLORS["bg_input"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        selectbackground=COLORS["accent"],
        selectforeground="#FFFFFF",
        font=FONTS["mono"],
        relief="flat",
        borderwidth=0,
        padx=12,
        pady=8,
        height=height,
        width=width,
        wrap="word",
        **kwargs,
    )
    return text


def create_styled_entry(parent, **kwargs):
    """Create a styled Entry matching the theme."""
    entry = tk.Entry(
        parent,
        bg=COLORS["bg_input"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        selectbackground=COLORS["accent"],
        selectforeground="#FFFFFF",
        font=FONTS["body"],
        relief="flat",
        borderwidth=0,
        **kwargs,
    )
    return entry


def create_accent_button(parent, text, command, **kwargs):
    """Create a styled accent button using tk.Button for rounded feel."""
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=COLORS["accent"],
        fg="#FFFFFF",
        activebackground=COLORS["accent_hover"],
        activeforeground="#FFFFFF",
        font=FONTS["button"],
        relief="flat",
        borderwidth=0,
        cursor="hand2",
        padx=18,
        pady=8,
        **kwargs,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=COLORS["accent_hover"]))
    btn.bind("<Leave>", lambda e: btn.configure(bg=COLORS["accent"]))
    return btn


def create_secondary_button(parent, text, command, **kwargs):
    """Create a styled secondary button."""
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=COLORS["bg_card"],
        fg=COLORS["text"],
        activebackground=COLORS["bg_card_hover"],
        activeforeground=COLORS["text"],
        font=FONTS["button"],
        relief="flat",
        borderwidth=1,
        highlightbackground=COLORS["border"],
        cursor="hand2",
        padx=14,
        pady=6,
        **kwargs,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=COLORS["bg_card_hover"]))
    btn.bind("<Leave>", lambda e: btn.configure(bg=COLORS["bg_card"]))
    return btn

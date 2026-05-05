"""
Main application window - Glassmorphism Tkinter UI for the Web Scraper Tool.
Features:
  - URL input with page overview / constructor
  - Selectable data categories (checkboxes per section)
  - CSS selector custom extraction
  - API scraping tab (generic REST + Twitter)
  - Export format selection (TXT, HTML, JSON, BIN)
  - Live status bar & progress
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import os
import webbrowser

from scraper.engine import ScraperEngine, PageAnalyzer, DataExtractor
from scraper.exporters import ExportManager
from scraper.api_scraper import GenericAPIScraper, TwitterScraper, MastodonScraper, APIScrapeManager
from scraper.ui_theme import (
    COLORS, FONTS, apply_theme,
    create_glass_card, create_styled_text, create_styled_entry,
    create_accent_button, create_secondary_button,
)


class WebScraperApp:
    """Main application class."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Web Scraper Tool")
        self.root.geometry("1280x860")
        self.root.minsize(1000, 700)
        self.root.configure(bg=COLORS["bg_dark"])

        # Try to remove title bar decorations for a cleaner look on Windows
        try:
            self.root.attributes("-alpha", 0.97)
        except Exception:
            pass

        apply_theme(self.root)

        # State
        self.engine = ScraperEngine()
        self.export_manager = ExportManager()
        self.api_manager = APIScrapeManager()
        self.current_overview = None
        self.current_soup = None
        self.current_url = None
        self.category_vars = {}
        self.is_loading = False

        self._build_ui()

    # ────────────────────────────────────────────────────────
    # UI Construction
    # ────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        self._build_header()

        # Main notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Tab 1: Web Scraper
        self.tab_web = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_web, text="  Web Scraper  ")

        # Tab 2: API Scraper
        self.tab_api = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_api, text="  API Scraper  ")

        # Tab 3: History / Results
        self.tab_results = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_results, text="  Results  ")

        self._build_web_tab()
        self._build_api_tab()
        self._build_results_tab()

        # Status bar
        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLORS["bg_dark"], height=60)
        header.pack(fill="x", padx=16, pady=(12, 8))
        header.pack_propagate(False)

        title_label = tk.Label(
            header, text="Web Scraper", font=FONTS["title"],
            bg=COLORS["bg_dark"], fg=COLORS["accent"],
        )
        title_label.pack(side="left", padx=(4, 0))

        subtitle = tk.Label(
            header, text="Modular  ·  Configurable  ·  Powerful",
            font=FONTS["body_sm"], bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
        )
        subtitle.pack(side="left", padx=(12, 0), pady=(6, 0))

        # Output dir button
        btn_output = create_secondary_button(
            header, "📂 Output Folder", self._open_output_folder
        )
        btn_output.pack(side="right", padx=(8, 0))

    # ── Web Scraper Tab ────────────────────────────────────

    def _build_web_tab(self):
        # Top bar: URL input + fetch button
        url_frame = create_glass_card(self.tab_web)
        url_frame.pack(fill="x", padx=12, pady=(12, 6))

        inner = tk.Frame(url_frame, bg=COLORS["bg_card"])
        inner.pack(fill="x", padx=16, pady=12)

        lbl = tk.Label(inner, text="Target URL", font=FONTS["subhead"],
                       bg=COLORS["bg_card"], fg=COLORS["highlight"])
        lbl.pack(anchor="w")

        entry_row = tk.Frame(inner, bg=COLORS["bg_card"])
        entry_row.pack(fill="x", pady=(6, 0))

        self.url_entry = create_styled_entry(entry_row)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.url_entry.insert(0, "https://")
        self.url_entry.bind("<Return>", lambda e: self._fetch_overview())

        self.fetch_btn = create_accent_button(entry_row, "Analyze Page", self._fetch_overview)
        self.fetch_btn.pack(side="left", padx=(10, 0))

        # Paned window: overview (left) + config (right)
        pane = tk.PanedWindow(
            self.tab_web, orient="horizontal",
            bg=COLORS["bg_dark"], sashwidth=6,
            sashrelief="flat", bd=0,
        )
        pane.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        # Left: overview / constructor
        self.overview_frame = create_glass_card(pane)
        pane.add(self.overview_frame, minsize=450, stretch="always")

        overview_header = tk.Frame(self.overview_frame, bg=COLORS["bg_card"])
        overview_header.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(overview_header, text="Page Overview", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["highlight"]).pack(side="left")

        self.overview_status = tk.Label(
            overview_header, text="Enter a URL and click Analyze",
            font=FONTS["body_sm"], bg=COLORS["bg_card"], fg=COLORS["text_dim"],
        )
        self.overview_status.pack(side="right")

        # Scrollable overview content
        overview_container = tk.Frame(self.overview_frame, bg=COLORS["bg_card"])
        overview_container.pack(fill="both", expand=True, padx=4, pady=4)

        self.overview_canvas = tk.Canvas(
            overview_container, bg=COLORS["bg_card"],
            highlightthickness=0, bd=0,
        )
        overview_scroll = ttk.Scrollbar(
            overview_container, orient="vertical",
            command=self.overview_canvas.yview,
        )
        self.overview_inner = tk.Frame(self.overview_canvas, bg=COLORS["bg_card"])

        self.overview_inner.bind(
            "<Configure>",
            lambda e: self.overview_canvas.configure(
                scrollregion=self.overview_canvas.bbox("all")
            ),
        )
        self.overview_canvas.create_window((0, 0), window=self.overview_inner, anchor="nw")
        self.overview_canvas.configure(yscrollcommand=overview_scroll.set)

        self.overview_canvas.pack(side="left", fill="both", expand=True)
        overview_scroll.pack(side="right", fill="y")

        # Bind mouse wheel
        self.overview_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(self.overview_canvas))
        self.overview_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        # Placeholder content
        placeholder = tk.Label(
            self.overview_inner,
            text="No page loaded yet.\n\nEnter a URL above and click 'Analyze Page'\nto see the full page structure here.",
            font=FONTS["body"], bg=COLORS["bg_card"], fg=COLORS["text_muted"],
            justify="center",
        )
        placeholder.pack(pady=80)

        # Right: config panel
        self.config_frame = create_glass_card(pane)
        pane.add(self.config_frame, minsize=320, stretch="never")

        self._build_config_panel()

    def _build_config_panel(self):
        """Build the right-side configuration panel."""
        header = tk.Frame(self.config_frame, bg=COLORS["bg_card"])
        header.pack(fill="x", padx=16, pady=(12, 8))
        tk.Label(header, text="Scrape Configuration", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["highlight"]).pack(anchor="w")

        # CSS Selector input
        sel_card = tk.Frame(self.config_frame, bg=COLORS["bg_card"])
        sel_card.pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(sel_card, text="CSS Selector (optional)", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w")
        self.css_entry = create_styled_entry(sel_card)
        self.css_entry.pack(fill="x", pady=(4, 0), ipady=4)
        self.css_entry.insert(0, "")

        # Separator
        ttk.Separator(self.config_frame).pack(fill="x", padx=16, pady=8)

        # Category checkboxes (populated after fetch)
        cat_header = tk.Frame(self.config_frame, bg=COLORS["bg_card"])
        cat_header.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(cat_header, text="Select Data to Scrape", font=FONTS["subhead"],
                 bg=COLORS["bg_card"], fg=COLORS["text"]).pack(side="left")

        self.select_all_var = tk.BooleanVar(value=False)
        self.select_all_cb = tk.Checkbutton(
            cat_header, text="All", variable=self.select_all_var,
            bg=COLORS["bg_card"], fg=COLORS["text_dim"],
            selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"], font=FONTS["body_sm"],
            command=self._toggle_select_all,
        )
        self.select_all_cb.pack(side="right")

        self.categories_frame = tk.Frame(self.config_frame, bg=COLORS["bg_card"])
        self.categories_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._populate_default_categories()

        # Separator
        ttk.Separator(self.config_frame).pack(fill="x", padx=16, pady=4)

        # Export format
        exp_frame = tk.Frame(self.config_frame, bg=COLORS["bg_card"])
        exp_frame.pack(fill="x", padx=16, pady=(4, 8))
        tk.Label(exp_frame, text="Export Format", font=FONTS["subhead"],
                 bg=COLORS["bg_card"], fg=COLORS["text"]).pack(anchor="w")

        fmt_row = tk.Frame(exp_frame, bg=COLORS["bg_card"])
        fmt_row.pack(fill="x", pady=(6, 0))

        self.format_var = tk.StringVar(value="json")
        for fmt, label in [("json", "JSON"), ("txt", "TXT"), ("html", "HTML"), ("bin", "BIN")]:
            rb = tk.Radiobutton(
                fmt_row, text=label, variable=self.format_var, value=fmt,
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                activeforeground=COLORS["text"], font=FONTS["body_sm"],
                indicatoron=True,
            )
            rb.pack(side="left", padx=(0, 16))

        # Scrape button
        btn_frame = tk.Frame(self.config_frame, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x", padx=16, pady=(8, 16))

        self.scrape_btn = create_accent_button(btn_frame, "Scrape & Export", self._run_scrape)
        self.scrape_btn.pack(fill="x", ipady=4)

    def _populate_default_categories(self):
        """Set up the default category checkboxes."""
        categories = [
            ("title",      "Page Title"),
            ("meta",       "Meta Tags"),
            ("headings",   "Headings (H1-H6)"),
            ("links",      "Links"),
            ("images",     "Images"),
            ("tables",     "Tables"),
            ("forms",      "Forms"),
            ("paragraphs", "Paragraphs"),
            ("lists",      "Lists"),
            ("scripts",    "Scripts"),
            ("styles",     "Stylesheets"),
            ("raw_text",   "Raw Text Content"),
        ]
        self._create_category_checkboxes(categories)

    def _create_category_checkboxes(self, categories):
        """Clear and recreate category checkboxes."""
        for w in self.categories_frame.winfo_children():
            w.destroy()
        self.category_vars.clear()

        for key, label in categories:
            var = tk.BooleanVar(value=False)
            self.category_vars[key] = var

            cb = tk.Checkbutton(
                self.categories_frame, text=label, variable=var,
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_input"],
                activebackground=COLORS["bg_card"],
                activeforeground=COLORS["text"],
                font=FONTS["body_sm"],
                anchor="w",
                padx=4, pady=2,
            )
            cb.pack(fill="x", anchor="w")

    def _toggle_select_all(self):
        val = self.select_all_var.get()
        for var in self.category_vars.values():
            var.set(val)

    # ── API Scraper Tab ────────────────────────────────────

    def _build_api_tab(self):
        # Inner notebook for API types
        api_notebook = ttk.Notebook(self.tab_api)
        api_notebook.pack(fill="both", expand=True, padx=12, pady=12)

        # Generic REST tab
        rest_tab = ttk.Frame(api_notebook)
        api_notebook.add(rest_tab, text="  REST API  ")
        self._build_rest_panel(rest_tab)

        # Mastodon tab
        mastodon_tab = ttk.Frame(api_notebook)
        api_notebook.add(mastodon_tab, text="  Mastodon  ")
        self._build_mastodon_panel(mastodon_tab)

        # Twitter tab
        twitter_tab = ttk.Frame(api_notebook)
        api_notebook.add(twitter_tab, text="  Twitter / X  ")
        self._build_twitter_panel(twitter_tab)

    def _build_rest_panel(self, parent):
        card = create_glass_card(parent)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        inner = tk.Frame(card, bg=COLORS["bg_card"])
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(inner, text="REST API Endpoint", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["highlight"]).pack(anchor="w")

        # URL
        tk.Label(inner, text="Base URL", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", pady=(12, 0))
        self.api_url_entry = create_styled_entry(inner)
        self.api_url_entry.pack(fill="x", ipady=5)
        self.api_url_entry.insert(0, "https://api.example.com/v1/data")

        # Method
        method_row = tk.Frame(inner, bg=COLORS["bg_card"])
        method_row.pack(fill="x", pady=(10, 0))
        tk.Label(method_row, text="Method", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.api_method_var = tk.StringVar(value="GET")
        method_combo = ttk.Combobox(
            method_row, textvariable=self.api_method_var,
            values=["GET", "POST", "PUT", "DELETE"],
            state="readonly", width=10,
        )
        method_combo.pack(side="left", padx=(10, 0))

        # Auth token
        tk.Label(inner, text="Authorization Token (optional)", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", pady=(10, 0))
        self.api_token_entry = create_styled_entry(inner, show="•")
        self.api_token_entry.pack(fill="x", ipady=5)

        # Headers
        tk.Label(inner, text="Custom Headers (JSON, optional)", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", pady=(10, 0))
        self.api_headers_text = create_styled_text(inner, height=3)
        self.api_headers_text.pack(fill="x")
        self.api_headers_text.insert("1.0", '{}')

        # Params / Body
        tk.Label(inner, text="Parameters / Body (JSON, optional)", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", pady=(10, 0))
        self.api_params_text = create_styled_text(inner, height=4)
        self.api_params_text.pack(fill="x")
        self.api_params_text.insert("1.0", '{}')

        # Export format for API
        exp_row = tk.Frame(inner, bg=COLORS["bg_card"])
        exp_row.pack(fill="x", pady=(12, 0))
        tk.Label(exp_row, text="Export As:", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.api_format_var = tk.StringVar(value="json")
        for fmt in ["json", "txt", "html", "bin"]:
            rb = tk.Radiobutton(
                exp_row, text=fmt.upper(), variable=self.api_format_var, value=fmt,
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                font=FONTS["body_sm"],
            )
            rb.pack(side="left", padx=(12, 0))

        # Fetch button
        btn_row = tk.Frame(inner, bg=COLORS["bg_card"])
        btn_row.pack(fill="x", pady=(16, 0))
        create_accent_button(btn_row, "Fetch API Data", self._fetch_api).pack(fill="x", ipady=4)

    def _build_mastodon_panel(self, parent):
        card = create_glass_card(parent)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        # Scrollable inner area for all the fields
        canvas = tk.Canvas(card, bg=COLORS["bg_card"], highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(card, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["bg_card"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        scroll.pack(side="right", fill="y", pady=8)
        canvas.bind("<Enter>", lambda e: self._bind_mousewheel(canvas))
        canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        tk.Label(inner, text="Mastodon Public API", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["highlight"]).pack(anchor="w", padx=8)
        tk.Label(inner, text="No auth required — uses public API endpoints only. Respects rate limits.",
                 font=FONTS["body_sm"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dim"]).pack(anchor="w", padx=8, pady=(2, 0))

        # Instance URL
        tk.Label(inner, text="Instance URL", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", padx=8, pady=(12, 0))
        self.masto_instance_entry = create_styled_entry(inner)
        self.masto_instance_entry.pack(fill="x", padx=8, ipady=5)
        self.masto_instance_entry.insert(0, "https://mastodon.social")

        # Action selector
        action_row = tk.Frame(inner, bg=COLORS["bg_card"])
        action_row.pack(fill="x", padx=8, pady=(12, 0))
        tk.Label(action_row, text="Action", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.masto_action_var = tk.StringVar(value="public_timeline")
        masto_actions = [
            "public_timeline", "local_timeline", "hashtag_timeline",
            "lookup_account", "account_statuses",
            "get_status", "status_context",
            "instance_info",
            "trends_statuses", "trends_tags", "trends_links",
            "custom_emojis", "directory",
        ]
        masto_combo = ttk.Combobox(
            action_row, textvariable=self.masto_action_var,
            values=masto_actions, state="readonly", width=24,
        )
        masto_combo.pack(side="left", padx=(10, 0))

        # Query / ID field (multi-purpose)
        tk.Label(inner, text="Query / Hashtag / Username / Status ID (depends on action)",
                 font=FONTS["body_sm"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dim"]).pack(anchor="w", padx=8, pady=(12, 0))
        self.masto_query_entry = create_styled_entry(inner)
        self.masto_query_entry.pack(fill="x", padx=8, ipady=5)

        # Limit
        limit_row = tk.Frame(inner, bg=COLORS["bg_card"])
        limit_row.pack(fill="x", padx=8, pady=(10, 0))
        tk.Label(limit_row, text="Limit", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.masto_limit_var = tk.StringVar(value="20")
        create_styled_entry(limit_row, textvariable=self.masto_limit_var, width=8).pack(
            side="left", padx=(10, 0), ipady=3
        )

        # Download media checkbox
        self.masto_download_media_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            inner, text="Also download media attachments (images/video/audio) as binary files",
            variable=self.masto_download_media_var,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"], font=FONTS["body_sm"],
        ).pack(anchor="w", padx=8, pady=(12, 0))

        # Export format
        exp_row = tk.Frame(inner, bg=COLORS["bg_card"])
        exp_row.pack(fill="x", padx=8, pady=(12, 0))
        tk.Label(exp_row, text="Export As:", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.masto_format_var = tk.StringVar(value="json")
        for fmt in ["json", "txt", "html", "bin"]:
            rb = tk.Radiobutton(
                exp_row, text=fmt.upper(), variable=self.masto_format_var, value=fmt,
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                font=FONTS["body_sm"],
            )
            rb.pack(side="left", padx=(12, 0))

        # Fetch button
        btn_row = tk.Frame(inner, bg=COLORS["bg_card"])
        btn_row.pack(fill="x", padx=8, pady=(16, 12))
        create_accent_button(btn_row, "Fetch from Mastodon", self._fetch_mastodon).pack(
            fill="x", ipady=4
        )

        # Action help text
        help_card = tk.Frame(inner, bg=COLORS["bg_mid"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
        help_card.pack(fill="x", padx=8, pady=(0, 12))
        help_lines = [
            "Action Guide:",
            "  public_timeline / local_timeline — leave query empty, uses limit",
            "  hashtag_timeline — enter hashtag (e.g. 'cats')",
            "  lookup_account — enter username (e.g. 'Gargron')",
            "  account_statuses — enter account ID (numeric, from lookup first)",
            "  get_status / status_context — enter status ID",
            "  instance_info — no query needed",
            "  trends_statuses / trends_tags / trends_links — no query, uses limit",
            "  custom_emojis / directory — no query needed",
            "",
            "Media: statuses include media_attachments with downloadable URLs.",
            "Check 'download media' to also save images/video/audio as files.",
        ]
        tk.Label(help_card, text="\n".join(help_lines), font=FONTS["mono_sm"],
                 bg=COLORS["bg_mid"], fg=COLORS["text_dim"], justify="left",
                 anchor="w", padx=12, pady=10).pack(fill="x")

    def _build_twitter_panel(self, parent):
        card = create_glass_card(parent)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        inner = tk.Frame(card, bg=COLORS["bg_card"])
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(inner, text="Twitter / X API", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["highlight"]).pack(anchor="w")
        tk.Label(inner, text="Requires a Twitter API Bearer Token",
                 font=FONTS["body_sm"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dim"]).pack(anchor="w", pady=(2, 0))

        # Bearer token
        tk.Label(inner, text="Bearer Token", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", pady=(12, 0))
        self.tw_token_entry = create_styled_entry(inner, show="•")
        self.tw_token_entry.pack(fill="x", ipady=5)

        # Action
        action_row = tk.Frame(inner, bg=COLORS["bg_card"])
        action_row.pack(fill="x", pady=(12, 0))
        tk.Label(action_row, text="Action", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.tw_action_var = tk.StringVar(value="search")
        ttk.Combobox(
            action_row, textvariable=self.tw_action_var,
            values=["search", "user_tweets", "user_info"],
            state="readonly", width=16,
        ).pack(side="left", padx=(10, 0))

        # Query / Username
        tk.Label(inner, text="Query or Username", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(anchor="w", pady=(12, 0))
        self.tw_query_entry = create_styled_entry(inner)
        self.tw_query_entry.pack(fill="x", ipady=5)

        # Max results
        max_row = tk.Frame(inner, bg=COLORS["bg_card"])
        max_row.pack(fill="x", pady=(10, 0))
        tk.Label(max_row, text="Max Results", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.tw_max_var = tk.StringVar(value="10")
        create_styled_entry(max_row, textvariable=self.tw_max_var, width=8).pack(
            side="left", padx=(10, 0), ipady=3
        )

        # Export format
        exp_row = tk.Frame(inner, bg=COLORS["bg_card"])
        exp_row.pack(fill="x", pady=(12, 0))
        tk.Label(exp_row, text="Export As:", font=FONTS["body_sm"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left")
        self.tw_format_var = tk.StringVar(value="json")
        for fmt in ["json", "txt", "html", "bin"]:
            rb = tk.Radiobutton(
                exp_row, text=fmt.upper(), variable=self.tw_format_var, value=fmt,
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                font=FONTS["body_sm"],
            )
            rb.pack(side="left", padx=(12, 0))

        btn_row = tk.Frame(inner, bg=COLORS["bg_card"])
        btn_row.pack(fill="x", pady=(16, 0))
        create_accent_button(btn_row, "Fetch Tweets", self._fetch_twitter).pack(fill="x", ipady=4)

    # ── Results Tab ────────────────────────────────────────

    def _build_results_tab(self):
        card = create_glass_card(self.tab_results)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        header = tk.Frame(card, bg=COLORS["bg_card"])
        header.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(header, text="Scrape Results", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["highlight"]).pack(side="left")

        btn_row = tk.Frame(header, bg=COLORS["bg_card"])
        btn_row.pack(side="right")
        create_secondary_button(btn_row, "Copy", self._copy_results).pack(side="left", padx=4)
        create_secondary_button(btn_row, "Clear", self._clear_results).pack(side="left", padx=4)

        text_frame = tk.Frame(card, bg=COLORS["bg_card"])
        text_frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.results_text = create_styled_text(text_frame, height=30)
        results_scroll = ttk.Scrollbar(text_frame, orient="vertical",
                                       command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        self.results_text.pack(side="left", fill="both", expand=True)
        results_scroll.pack(side="right", fill="y")

        self.results_text.configure(state="disabled")

    # ── Status Bar ─────────────────────────────────────────

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=COLORS["bg_mid"], height=32)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_label = tk.Label(
            bar, text="Ready", font=FONTS["body_sm"],
            bg=COLORS["bg_mid"], fg=COLORS["text_dim"],
        )
        self.status_label.pack(side="left", padx=16)

        self.progress = ttk.Progressbar(
            bar, orient="horizontal", mode="indeterminate", length=140,
        )
        self.progress.pack(side="right", padx=16, pady=6)

    # ────────────────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────────────────

    def _set_status(self, text, color=None):
        self.status_label.configure(
            text=text, fg=color or COLORS["text_dim"]
        )

    def _start_loading(self):
        self.is_loading = True
        self.progress.start(12)
        self.fetch_btn.configure(state="disabled")
        self.scrape_btn.configure(state="disabled")

    def _stop_loading(self):
        self.is_loading = False
        self.progress.stop()
        self.fetch_btn.configure(state="normal")
        self.scrape_btn.configure(state="normal")

    def _fetch_overview(self):
        """Fetch and display the page overview / constructor."""
        url = self.url_entry.get().strip()
        if not url or url == "https://":
            messagebox.showwarning("Input Required", "Please enter a valid URL.")
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)

        self._set_status(f"Fetching {url}...", COLORS["warning"])
        self._start_loading()

        def worker():
            try:
                soup, resp = self.engine.fetch_page(url)
                analyzer = PageAnalyzer(soup, url)
                overview = analyzer.get_overview()
                self.current_overview = overview
                self.current_soup = soup
                self.current_url = url

                self.root.after(0, lambda: self._display_overview(overview, resp))
                self.root.after(0, lambda: self._set_status(
                    f"Loaded: {url}  ·  Status {resp.status_code}  ·  "
                    f"{len(resp.content)} bytes", COLORS["success"]
                ))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self._set_status(f"Error: {err_msg}", COLORS["error"]))
                self.root.after(0, lambda: messagebox.showerror("Fetch Error", err_msg))
            finally:
                self.root.after(0, self._stop_loading)

        threading.Thread(target=worker, daemon=True).start()

    def _display_overview(self, overview, resp):
        """Populate the overview panel with the page structure."""
        # Clear existing content
        for w in self.overview_inner.winfo_children():
            w.destroy()

        self.overview_status.configure(text=f"{resp.status_code} OK  ·  {len(resp.content):,} bytes")

        # Summary header
        summary = tk.Frame(self.overview_inner, bg=COLORS["bg_mid"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        summary.pack(fill="x", padx=12, pady=(12, 6))

        title_text = overview.get("title", "No title")
        tk.Label(summary, text=title_text, font=FONTS["subhead"],
                 bg=COLORS["bg_mid"], fg=COLORS["text"], wraplength=500).pack(
            anchor="w", padx=12, pady=(10, 2)
        )

        # Stats row
        stats = (
            f"Links: {len(overview.get('links', []))}  ·  "
            f"Images: {len(overview.get('images', []))}  ·  "
            f"Tables: {len(overview.get('tables', []))}  ·  "
            f"Forms: {len(overview.get('forms', []))}  ·  "
            f"Headings: {len(overview.get('headings', []))}  ·  "
            f"Paragraphs: {len(overview.get('paragraphs', []))}"
        )
        tk.Label(summary, text=stats, font=FONTS["body_sm"],
                 bg=COLORS["bg_mid"], fg=COLORS["text_dim"], wraplength=500).pack(
            anchor="w", padx=12, pady=(0, 10)
        )

        # Render each category
        category_display = [
            ("meta",       "Meta Tags",        self._render_meta),
            ("headings",   "Headings",          self._render_simple_list),
            ("links",      "Links",             self._render_links),
            ("images",     "Images",            self._render_images),
            ("tables",     "Tables",            self._render_tables),
            ("forms",      "Forms",             self._render_forms),
            ("paragraphs", "Paragraphs",        self._render_paragraphs),
            ("lists",      "Lists",             self._render_lists),
            ("scripts",    "Scripts",           self._render_simple_list),
            ("styles",     "Stylesheets",       self._render_simple_list),
        ]

        for key, label, renderer in category_display:
            data = overview.get(key, [])
            if not data:
                continue
            self._render_overview_section(key, label, data, renderer)

        # Update categories with counts
        categories = []
        for key, label, _ in category_display:
            data = overview.get(key, [])
            count = len(data) if isinstance(data, list) else (1 if data else 0)
            if count > 0:
                categories.append((key, f"{label} ({count})"))
        categories.insert(0, ("title", f"Page Title"))
        categories.append(("raw_text", "Raw Text Content"))
        self._create_category_checkboxes(categories)

    def _render_overview_section(self, key, label, data, renderer):
        """Render a collapsible overview section."""
        section = tk.Frame(self.overview_inner, bg=COLORS["bg_card"])
        section.pack(fill="x", padx=12, pady=4)

        # Section header (clickable to expand/collapse)
        header_frame = tk.Frame(section, bg=COLORS["bg_mid"],
                                highlightbackground=COLORS["border"],
                                highlightthickness=1, cursor="hand2")
        header_frame.pack(fill="x")

        count = len(data) if isinstance(data, list) else 1
        arrow_var = tk.StringVar(value="▸")
        arrow_label = tk.Label(header_frame, textvariable=arrow_var, font=FONTS["body"],
                               bg=COLORS["bg_mid"], fg=COLORS["accent"], width=2)
        arrow_label.pack(side="left", padx=(8, 0))

        tk.Label(header_frame, text=f"{label}", font=FONTS["subhead"],
                 bg=COLORS["bg_mid"], fg=COLORS["text"]).pack(side="left", padx=(0, 8))

        tk.Label(header_frame, text=f"{count} items", font=FONTS["tag"],
                 bg=COLORS["tag_bg"], fg=COLORS["highlight"],
                 padx=8, pady=2).pack(side="right", padx=8, pady=6)

        # Content frame (initially hidden)
        content_frame = tk.Frame(section, bg=COLORS["bg_card"])
        content_visible = [False]

        def toggle(event=None):
            if content_visible[0]:
                content_frame.pack_forget()
                arrow_var.set("▸")
                content_visible[0] = False
            else:
                content_frame.pack(fill="x", padx=4, pady=(0, 4))
                renderer(content_frame, data)
                arrow_var.set("▾")
                content_visible[0] = True

        for widget in [header_frame, arrow_label]:
            widget.bind("<Button-1>", toggle)
        # Also bind child labels
        for child in header_frame.winfo_children():
            child.bind("<Button-1>", toggle)

    def _render_meta(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for item in data[:30]:
            row = tk.Frame(parent, bg=COLORS["bg_card"])
            row.pack(fill="x", padx=8, pady=1)
            name = item.get("name") or item.get("property") or item.get("charset", "")
            content = item.get("content", item.get("charset", ""))
            tk.Label(row, text=f"{name}:", font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["highlight"], width=22,
                     anchor="w").pack(side="left")
            tk.Label(row, text=content[:80], font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["text"], anchor="w").pack(
                side="left", fill="x", expand=True
            )

    def _render_simple_list(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for item in data[:50]:
            row = tk.Frame(parent, bg=COLORS["bg_card"])
            row.pack(fill="x", padx=8, pady=1)
            if isinstance(item, dict):
                text = " · ".join(f"{k}: {str(v)[:60]}" for k, v in item.items() if v)
            else:
                text = str(item)[:120]
            tk.Label(row, text=text, font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["text"],
                     anchor="w", wraplength=500).pack(anchor="w")

    def _render_links(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for item in data[:50]:
            row = tk.Frame(parent, bg=COLORS["bg_card"])
            row.pack(fill="x", padx=8, pady=1)
            text = item.get("text", "")[:40] or "(no text)"
            href = item.get("href", "")[:80]
            tk.Label(row, text=text, font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["accent"], width=25,
                     anchor="w").pack(side="left")
            lbl = tk.Label(row, text=href, font=FONTS["mono_sm"],
                           bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                           anchor="w", cursor="hand2")
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, u=item.get("href", ""): webbrowser.open(u))

    def _render_images(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for item in data[:30]:
            row = tk.Frame(parent, bg=COLORS["bg_card"])
            row.pack(fill="x", padx=8, pady=1)
            alt = item.get("alt", "")[:30] or "(no alt)"
            src = item.get("src", "")[:80]
            tk.Label(row, text=alt, font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["text"], width=20,
                     anchor="w").pack(side="left")
            tk.Label(row, text=src, font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                     anchor="w").pack(side="left", fill="x", expand=True)

    def _render_tables(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for table in data[:10]:
            frame = tk.Frame(parent, bg=COLORS["bg_mid"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
            frame.pack(fill="x", padx=8, pady=4)
            info = (f"Table #{table['index']}  ·  "
                    f"{table['row_count']} rows  ·  "
                    f"id=\"{table.get('id', '')}\"  ·  "
                    f"class=\"{table.get('class', '')}\"")
            tk.Label(frame, text=info, font=FONTS["mono_sm"],
                     bg=COLORS["bg_mid"], fg=COLORS["text"]).pack(
                anchor="w", padx=8, pady=6
            )
            # Show first 3 rows as preview
            for row_data in table.get("rows", [])[:3]:
                row_text = " | ".join(cell.get("text", "")[:20] for cell in row_data)
                tk.Label(frame, text=row_text, font=FONTS["mono_sm"],
                         bg=COLORS["bg_mid"], fg=COLORS["text_dim"]).pack(
                    anchor="w", padx=16, pady=1
                )

    def _render_forms(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for form in data[:10]:
            frame = tk.Frame(parent, bg=COLORS["bg_mid"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
            frame.pack(fill="x", padx=8, pady=4)
            info = f"Form  ·  method={form.get('method', '?')}  ·  action=\"{form.get('action', '')}\""
            tk.Label(frame, text=info, font=FONTS["mono_sm"],
                     bg=COLORS["bg_mid"], fg=COLORS["text"]).pack(
                anchor="w", padx=8, pady=(6, 2)
            )
            for field in form.get("fields", [])[:8]:
                field_text = (f"  <{field.get('tag', '?')}> "
                              f"type={field.get('type', '')} "
                              f"name=\"{field.get('name', '')}\"")
                tk.Label(frame, text=field_text, font=FONTS["mono_sm"],
                         bg=COLORS["bg_mid"], fg=COLORS["text_dim"]).pack(
                    anchor="w", padx=16, pady=1
                )

    def _render_paragraphs(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for item in data[:30]:
            row = tk.Frame(parent, bg=COLORS["bg_card"])
            row.pack(fill="x", padx=8, pady=1)
            text = item.get("text", "")[:120]
            if len(item.get("text", "")) > 120:
                text += "…"
            tk.Label(row, text=text, font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=COLORS["text"],
                     anchor="w", wraplength=500).pack(anchor="w")

    def _render_lists(self, parent, data):
        for w in parent.winfo_children():
            w.destroy()
        for lst in data[:15]:
            frame = tk.Frame(parent, bg=COLORS["bg_mid"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
            frame.pack(fill="x", padx=8, pady=4)
            info = f"<{lst['type']}>  ·  {len(lst.get('items', []))} items"
            tk.Label(frame, text=info, font=FONTS["mono_sm"],
                     bg=COLORS["bg_mid"], fg=COLORS["text"]).pack(
                anchor="w", padx=8, pady=(6, 2)
            )
            for li_text in lst.get("items", [])[:5]:
                tk.Label(frame, text=f"  • {li_text[:80]}", font=FONTS["mono_sm"],
                         bg=COLORS["bg_mid"], fg=COLORS["text_dim"]).pack(
                    anchor="w", padx=16, pady=1
                )

    # ── Scrape Action ──────────────────────────────────────

    def _run_scrape(self):
        """Execute the scrape based on current configuration."""
        if not self.current_soup or not self.current_url:
            messagebox.showwarning("No Page", "Analyze a page first before scraping.")
            return

        # Build selections
        selections = {}
        any_selected = False
        for key, var in self.category_vars.items():
            if var.get():
                selections[key] = True
                any_selected = True

        css_selector = self.css_entry.get().strip()

        if not any_selected and not css_selector:
            messagebox.showwarning("No Selection",
                                   "Select at least one data category or enter a CSS selector.")
            return

        self._set_status("Scraping data...", COLORS["warning"])
        self._start_loading()

        def worker():
            try:
                extractor = DataExtractor(self.current_soup, self.current_url)
                result = {}

                if any_selected:
                    result.update(extractor.extract(selections))

                if css_selector:
                    result["css_selector_results"] = extractor.extract_css_selector(css_selector)

                # Add metadata
                result["_metadata"] = {
                    "source_url": self.current_url,
                    "scrape_categories": [k for k, v in selections.items() if v],
                    "css_selector": css_selector or None,
                }

                # Export
                fmt = self.format_var.get()
                filepath = self.export_manager.export(result, fmt)

                # Display in results tab
                display_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                self.root.after(0, lambda: self._show_results(display_text))
                self.root.after(0, lambda: self._set_status(
                    f"Exported to {filepath}", COLORS["success"]
                ))
                self.root.after(0, lambda: self.notebook.select(self.tab_results))

            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self._set_status(f"Scrape error: {err_msg}", COLORS["error"]))
                self.root.after(0, lambda: messagebox.showerror("Scrape Error", err_msg))
            finally:
                self.root.after(0, self._stop_loading)

        threading.Thread(target=worker, daemon=True).start()

    # ── API Actions ────────────────────────────────────────

    def _fetch_api(self):
        """Fetch data from a REST API."""
        url = self.api_url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Enter an API URL.")
            return

        method = self.api_method_var.get()
        token = self.api_token_entry.get().strip() or None

        try:
            headers = json.loads(self.api_headers_text.get("1.0", "end").strip() or "{}")
        except json.JSONDecodeError:
            messagebox.showerror("Invalid JSON", "Custom headers must be valid JSON.")
            return

        try:
            params_or_body = json.loads(self.api_params_text.get("1.0", "end").strip() or "{}")
        except json.JSONDecodeError:
            messagebox.showerror("Invalid JSON", "Parameters/body must be valid JSON.")
            return

        self._set_status(f"Calling API: {method} {url}...", COLORS["warning"])
        self._start_loading()

        def worker():
            try:
                scraper = GenericAPIScraper()
                scraper.configure(url, headers=headers, auth_token=token)

                if method == "GET":
                    result = scraper.get(params=params_or_body or None)
                else:
                    result = scraper.post(json_data=params_or_body or None)

                # Export
                fmt = self.api_format_var.get()
                filepath = self.export_manager.export(result, fmt)

                display_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                self.root.after(0, lambda: self._show_results(display_text))
                self.root.after(0, lambda: self._set_status(
                    f"API data exported to {filepath}", COLORS["success"]
                ))
                self.root.after(0, lambda: self.notebook.select(self.tab_results))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self._set_status(f"API error: {err_msg}", COLORS["error"]))
                self.root.after(0, lambda: messagebox.showerror("API Error", err_msg))
            finally:
                self.root.after(0, self._stop_loading)

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_twitter(self):
        """Fetch data from Twitter/X API."""
        token = self.tw_token_entry.get().strip()
        if not token:
            messagebox.showwarning("Token Required",
                                   "Enter your Twitter API Bearer Token.")
            return

        action = self.tw_action_var.get()
        query = self.tw_query_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Required", "Enter a search query or username.")
            return

        try:
            max_results = int(self.tw_max_var.get())
        except ValueError:
            max_results = 10

        self._set_status(f"Fetching from Twitter: {action}...", COLORS["warning"])
        self._start_loading()

        def worker():
            try:
                self.api_manager.twitter.configure(bearer_token=token)

                if action == "search":
                    result = self.api_manager.scrape_twitter("search",
                                                            query=query,
                                                            max_results=max_results)
                elif action == "user_tweets":
                    result = self.api_manager.scrape_twitter("user_tweets",
                                                            username=query,
                                                            max_results=max_results)
                elif action == "user_info":
                    result = self.api_manager.scrape_twitter("user_info",
                                                            username=query)
                else:
                    result = {"error": f"Unknown action: {action}"}

                fmt = self.tw_format_var.get()
                filepath = self.export_manager.export(result, fmt)

                display_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                self.root.after(0, lambda: self._show_results(display_text))
                self.root.after(0, lambda: self._set_status(
                    f"Twitter data exported to {filepath}", COLORS["success"]
                ))
                self.root.after(0, lambda: self.notebook.select(self.tab_results))
            except ImportError as e:
                err_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror(
                    "Missing Dependency",
                    "Tweepy is required for Twitter scraping.\n"
                    "Install with: pip install tweepy"
                ))
                self.root.after(0, lambda: self._set_status(err_msg, COLORS["error"]))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self._set_status(f"Twitter error: {err_msg}", COLORS["error"]))
                self.root.after(0, lambda: messagebox.showerror("Twitter Error", err_msg))
            finally:
                self.root.after(0, self._stop_loading)

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_mastodon(self):
        """Fetch data from Mastodon public API."""
        instance_url = self.masto_instance_entry.get().strip()
        if not instance_url:
            messagebox.showwarning("Input Required", "Enter a Mastodon instance URL.")
            return

        if not instance_url.startswith(("http://", "https://")):
            instance_url = "https://" + instance_url
            self.masto_instance_entry.delete(0, "end")
            self.masto_instance_entry.insert(0, instance_url)

        action = self.masto_action_var.get()
        query = self.masto_query_entry.get().strip()
        download_media = self.masto_download_media_var.get()

        try:
            limit = int(self.masto_limit_var.get())
        except ValueError:
            limit = 20

        # Validate required query for certain actions
        needs_query = {
            "hashtag_timeline", "lookup_account", "account_statuses",
            "get_status", "status_context",
        }
        if action in needs_query and not query:
            messagebox.showwarning(
                "Input Required",
                f"The '{action}' action requires a query/ID.\n"
                "Enter a hashtag, username, or ID in the query field."
            )
            return

        self._set_status(f"Fetching from Mastodon: {action}...", COLORS["warning"])
        self._start_loading()

        def worker():
            try:
                self.api_manager.mastodon.configure(instance_url)

                # Build kwargs based on action
                kwargs = {}
                if action in ("public_timeline", "local_timeline"):
                    kwargs["limit"] = limit
                elif action == "hashtag_timeline":
                    kwargs["hashtag"] = query
                    kwargs["limit"] = limit
                elif action == "lookup_account":
                    kwargs["acct"] = query
                elif action == "account_statuses":
                    kwargs["account_id"] = query
                    kwargs["limit"] = limit
                elif action == "get_status":
                    kwargs["status_id"] = query
                elif action == "status_context":
                    kwargs["status_id"] = query
                elif action in ("trends_statuses", "trends_tags", "trends_links"):
                    kwargs["limit"] = limit
                elif action == "directory":
                    kwargs["limit"] = limit
                # instance_info, custom_emojis need no kwargs

                result = self.api_manager.scrape_mastodon(action, **kwargs)

                # Optionally download media attachments
                downloaded_media = []
                if download_media and isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict):
                            for att in item.get("media_attachments", []):
                                media_url = att.get("url", "")
                                if media_url:
                                    try:
                                        dl = self.api_manager.mastodon.download_media(media_url)
                                        downloaded_media.append(dl)
                                    except Exception:
                                        pass

                # Wrap result with metadata
                export_data = {
                    "mastodon_instance": instance_url,
                    "action": action,
                    "query": query or None,
                    "result_count": len(result) if isinstance(result, list) else 1,
                    "data": result,
                }
                if downloaded_media:
                    export_data["downloaded_media"] = downloaded_media

                fmt = self.masto_format_var.get()
                filepath = self.export_manager.export(export_data, fmt)

                display_text = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
                self.root.after(0, lambda: self._show_results(display_text))

                media_note = f"  ·  {len(downloaded_media)} media files saved" if downloaded_media else ""
                self.root.after(0, lambda: self._set_status(
                    f"Mastodon data exported to {filepath}{media_note}", COLORS["success"]
                ))
                self.root.after(0, lambda: self.notebook.select(self.tab_results))

            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self._set_status(f"Mastodon error: {err_msg}", COLORS["error"]))
                self.root.after(0, lambda: messagebox.showerror("Mastodon Error", err_msg))
            finally:
                self.root.after(0, self._stop_loading)

        threading.Thread(target=worker, daemon=True).start()

    # ── Helpers ────────────────────────────────────────────

    def _show_results(self, text):
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", text)
        self.results_text.configure(state="disabled")

    def _copy_results(self):
        self.root.clipboard_clear()
        content = self.results_text.get("1.0", "end").strip()
        if content:
            self.root.clipboard_append(content)
            self._set_status("Copied to clipboard", COLORS["success"])

    def _clear_results(self):
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
        self._set_status("Results cleared", COLORS["text_dim"])

    def _open_output_folder(self):
        output_dir = os.path.abspath("output")
        os.makedirs(output_dir, exist_ok=True)
        webbrowser.open(output_dir)

    def _bind_mousewheel(self, canvas):
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

    def _unbind_mousewheel(self):
        self.root.unbind_all("<MouseWheel>")

    # ── Run ────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()

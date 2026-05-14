import tkinter as tk
from tkinter import ttk

import database as db
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from stats import plot_combined_heatmaps


class HeatmapTab:
    def __init__(self, parent, app):
        self.app = app
        self.parent = parent
        self.heatmap_canvas = None
        self.empty_label = None
        self.selected_season_id = tk.IntVar()
        self.season_map = {}

        self.heatmap_tab = ttk.Frame(parent)
        parent.add(self.heatmap_tab, text="Heatmaps")

        control_frame = ttk.Frame(self.heatmap_tab)
        control_frame.pack(fill='x', pady=5, padx=5)

        ttk.Label(control_frame, text="Select Season:").pack(side=tk.LEFT, padx=(5, 5))
        self.season_selector_cb = ttk.Combobox(control_frame, state="readonly")
        self.season_selector_cb.pack(side=tk.LEFT, padx=5)
        self.season_selector_cb.bind("<<ComboboxSelected>>", self.on_season_selected)

        self.heatmap_frame = ttk.Frame(self.heatmap_tab)
        self.heatmap_frame.pack(fill='both', expand=True)

        parent.bind("<<NotebookTabChanged>>", self.on_tab_selected, add="+")

    def refresh_season_selector(self):
        seasons = db.get_seasons()
        if not seasons:
            return

        current_selection = self.season_selector_cb.get()
        self.season_map = {season['name']: season['id'] for season in seasons}
        season_names = list(self.season_map.keys())
        self.season_selector_cb['values'] = season_names

        selected_name = current_selection if current_selection in self.season_map else season_names[0]
        self.season_selector_cb.set(selected_name)
        self.selected_season_id.set(self.season_map[selected_name])
        if self.is_selected():
            self.render_heatmaps()

    def on_season_selected(self, event=None):
        selected_name = self.season_selector_cb.get()
        if selected_name in self.season_map:
            self.selected_season_id.set(self.season_map[selected_name])
            self.render_heatmaps()

    def on_tab_selected(self, event=None):
        if self.is_selected():
            self.render_heatmaps()

    def render_heatmaps(self):
        season_id = self.selected_season_id.get()
        if not season_id:
            return

        self.clear_heatmaps()

        fig = Figure(figsize=(12, 5), dpi=100)
        ax_left, ax_right = fig.subplots(1, 2)
        if not plot_combined_heatmaps(ax_left, ax_right, season_id=season_id):
            self.show_empty_message("No games recorded for this season yet.")
            return

        fig.tight_layout()
        self.heatmap_canvas = FigureCanvasTkAgg(fig, master=self.heatmap_frame)
        self.heatmap_canvas.draw()
        self.heatmap_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def clear_heatmaps(self):
        if self.heatmap_canvas:
            self.heatmap_canvas.get_tk_widget().destroy()
            self.heatmap_canvas = None
        if self.empty_label:
            self.empty_label.destroy()
            self.empty_label = None

    def show_empty_message(self, message):
        self.empty_label = ttk.Label(self.heatmap_frame, text=message)
        self.empty_label.pack(pady=20)

    def is_selected(self):
        return self.parent.select() == str(self.heatmap_tab)

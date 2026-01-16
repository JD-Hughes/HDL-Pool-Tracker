import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database as db
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from stats import show_combined_heatmaps

SMOOTHING_WINDOW = 5  # Number of games for moving average smoothing

class GraphTab:
    def __init__(self, parent, app):
        self.graph_canvas = None
        self.smoothing_enabled = tk.BooleanVar(value=True)
        self.selected_season_id = tk.IntVar()

        self.app = app
        self.graph_tab = ttk.Frame(parent)
        parent.add(self.graph_tab, text="Elo Graphs")
        
        control_frame = ttk.Frame(self.graph_tab)
        control_frame.pack(fill='x', pady=5, padx=5)

        ttk.Label(control_frame, text="Select Season:").pack(side=tk.LEFT, padx=(5,5))
        self.season_selector_cb = ttk.Combobox(control_frame, state="readonly")
        self.season_selector_cb.pack(side=tk.LEFT, padx=5)
        self.season_selector_cb.bind("<<ComboboxSelected>>", self.on_season_selected)

        ttk.Checkbutton(
            control_frame, 
            text=f"Smooth Elo ({SMOOTHING_WINDOW} games)", 
            variable=self.smoothing_enabled,
            command=self.plot_elo_graph
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            control_frame, 
            text="Show Heatmap",
            command=lambda: show_combined_heatmaps(season_id=self.selected_season_id.get())
        ).pack(side=tk.RIGHT, padx=5)

    def refresh_season_selector(self):
        seasons = db.get_seasons()
        if not seasons:
            return
            
        self.season_map = {s['name']: s['id'] for s in seasons}
        season_names = list(self.season_map.keys())
        self.season_selector_cb['values'] = season_names
        
        # Select the most recent season by default
        current_season_name = season_names[0]
        self.season_selector_cb.set(current_season_name)
        self.on_season_selected() # Trigger event handler manually

    def on_season_selected(self, event=None):
        """Handler for when a season is chosen in the dropdown."""
        selected_name = self.season_selector_cb.get()
        if selected_name in self.season_map:
            self.selected_season_id.set(self.season_map[selected_name])
            # Refresh views that depend on the selected season
            self.plot_elo_graph()

    def plot_elo_graph(self):
        if self.graph_canvas:
            self.graph_canvas.get_tk_widget().destroy()

        season_id = self.selected_season_id.get()
        matches = db.get_matches_for_season(season_id)

        if not matches:
            return

        # Get all unique players in this season's matches (including doubles)
        players_in_season = set()
        for match in matches:
            players_in_season.add(match['player1_name'])
            players_in_season.add(match['player2_name'])
            if match.get('doubles_match', 0):
                if match.get('player1b_name'):
                    players_in_season.add(match['player1b_name'])
                if match.get('player2b_name'):
                    players_in_season.add(match['player2b_name'])

        # Build elo history timeline from matches (using new schema)
        elo_data = {p: [db.INITIAL_ELO] for p in players_in_season}
        for match in matches:
            temp_elos = {p: elo_data[p][-1] if elo_data[p] else db.INITIAL_ELO for p in players_in_season}
            if match.get('doubles_match', 0):
                # Doubles match: update all four players
                temp_elos[match['player1_name']] = match['player1_elo_after']
                temp_elos[match['player2_name']] = match['player2_elo_after']
                if match.get('player1b_name') and match.get('player1b_elo_after') is not None:
                    temp_elos[match['player1b_name']] = match['player1b_elo_after']
                if match.get('player2b_name') and match.get('player2b_elo_after') is not None:
                    temp_elos[match['player2b_name']] = match['player2b_elo_after']
            else:
                # Singles match
                if match.get('winner', -1) == 1:
                    temp_elos[match['player1_name']] = match['player1_elo_after']
                    temp_elos[match['player2_name']] = match['player2_elo_after']
                elif match.get('winner', -1) == 2:
                    temp_elos[match['player2_name']] = match['player2_elo_after']
                    temp_elos[match['player1_name']] = match['player1_elo_after']
            for p in players_in_season:
                elo_data[p].append(temp_elos[p])

        # Conditional Smoothing
        elo_to_plot = elo_data
        title_suffix = ""
        if self.smoothing_enabled.get():
            elo_df = pd.DataFrame(elo_data)
            smoothed_elo_df = elo_df.rolling(window=SMOOTHING_WINDOW, min_periods=1).mean()
            elo_to_plot = {player: smoothed_elo_df[player].tolist() for player in players_in_season}
            title_suffix = f" (Smoothed over {SMOOTHING_WINDOW} games)"

        # --- Matplotlib Plotting ---
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)

        for player, elos in elo_to_plot.items():
            ax.plot(range(len(elos)), elos, label=player)

        ax.set_title(f"Elo Ratings Over Time{title_suffix}")
        ax.set_xlabel("Games Played in Season")
        ax.set_ylabel("Elo Rating")
        ax.grid(True)
        ax.legend()
        fig.tight_layout()

        self.graph_canvas = FigureCanvasTkAgg(fig, master=self.graph_tab)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

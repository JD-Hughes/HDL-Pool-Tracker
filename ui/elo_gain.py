import tkinter as tk
from tkinter import ttk

import database as db
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from stats import annotate_heatmap_with_counts, heatmap

K_FACTOR = 32
RECENT_MATCH_LIMIT = 5


class EloGainTab:
    def __init__(self, parent, app):
        self.app = app
        self.parent = parent
        self.chart_canvas = None
        self.empty_label = None
        self.selected_season_id = tk.IntVar()
        self.season_map = {}

        self.elo_gain_tab = ttk.Frame(parent)
        parent.add(self.elo_gain_tab, text="Elo Gain")

        control_frame = ttk.Frame(self.elo_gain_tab)
        control_frame.pack(fill='x', pady=5, padx=5)

        ttk.Label(control_frame, text="Select Season:").pack(side=tk.LEFT, padx=(5, 5))
        self.season_selector_cb = ttk.Combobox(control_frame, state="readonly")
        self.season_selector_cb.pack(side=tk.LEFT, padx=5)
        self.season_selector_cb.bind("<<ComboboxSelected>>", self.on_season_selected)

        self.chart_frame = ttk.Frame(self.elo_gain_tab)
        self.chart_frame.pack(fill='both', expand=True)

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
            self.plot_elo_gain()

    def on_season_selected(self, event=None):
        selected_name = self.season_selector_cb.get()
        if selected_name in self.season_map:
            self.selected_season_id.set(self.season_map[selected_name])
            self.plot_elo_gain()

    def on_tab_selected(self, event=None):
        if self.is_selected():
            self.plot_elo_gain()

    def plot_elo_gain(self):
        self.clear_chart()

        matches = db.get_matches_for_season(self.selected_season_id.get())
        if not matches:
            self.show_empty_message("No games recorded for this season yet.")
            return

        players = self.get_players(matches)
        if not players:
            self.show_empty_message("No player Elo changes found for this season.")
            return

        player_index = {player: index for index, player in enumerate(players)}
        elo_gain_data = np.zeros((len(players), len(players)), dtype=float)
        expected_value_data = np.zeros((len(players), len(players)), dtype=float)
        games_played = np.zeros((len(players), len(players)), dtype=int)
        recent_games_used = np.zeros((len(players), len(players)), dtype=int)
        recent_results = {
            player: {opponent: [] for opponent in players}
            for player in players
        }
        latest_elos = {player: db.INITIAL_ELO for player in players}

        for match in matches:
            team_a = self.get_team_players(match, "player1")
            team_b = self.get_team_players(match, "player2")
            winner = match.get('winner')

            for player, elo_change in team_a.items():
                latest_elos[player] = self.get_player_elo_after(match, player)
                for opponent in team_b:
                    row = player_index[player]
                    col = player_index[opponent]
                    elo_gain_data[row][col] += elo_change
                    games_played[row][col] += 1
                    recent_results[player][opponent].append(1 if winner == 1 else 0)

            for player, elo_change in team_b.items():
                latest_elos[player] = self.get_player_elo_after(match, player)
                for opponent in team_a:
                    row = player_index[player]
                    col = player_index[opponent]
                    elo_gain_data[row][col] += elo_change
                    games_played[row][col] += 1
                    recent_results[player][opponent].append(1 if winner == 2 else 0)

        for player in players:
            for opponent in players:
                if player == opponent:
                    continue

                recent_games = recent_results[player][opponent][-RECENT_MATCH_LIMIT:]
                if not recent_games:
                    continue

                win_rate = sum(recent_games) / len(recent_games)
                win_gain = self.calculate_win_gain(latest_elos[player], latest_elos[opponent])
                loss_cost = self.calculate_loss_cost(latest_elos[player], latest_elos[opponent])
                row = player_index[player]
                col = player_index[opponent]
                recent_games_used[row][col] = len(recent_games)
                expected_value_data[row][col] = (win_rate * win_gain) - ((1 - win_rate) * loss_cost)

        masked_gain_data = np.ma.array(elo_gain_data, copy=True)
        masked_expected_value_data = np.ma.array(expected_value_data, copy=True)
        for index in range(len(players)):
            masked_gain_data[index, index] = np.ma.masked
            masked_expected_value_data[index, index] = np.ma.masked

        plotted_values = masked_gain_data.compressed()
        if len(plotted_values) == 0:
            self.show_empty_message("No opponent Elo changes found for this season.")
            return

        fig = Figure(figsize=(14, 5), dpi=100)
        ax_gain, ax_expected_value = fig.subplots(1, 2)
        self.draw_heatmap(
            ax_gain,
            masked_gain_data,
            games_played,
            players,
            "Net Elo Gain/Loss",
            "Net Elo Gain"
        )
        self.draw_heatmap(
            ax_expected_value,
            masked_expected_value_data,
            recent_games_used,
            players,
            f"Expected Value Next Match\nLast {RECENT_MATCH_LIMIT} head-to-head games",
            "Expected Elo"
        )

        fig.tight_layout()
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def clear_chart(self):
        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = None
        if self.empty_label:
            self.empty_label.destroy()
            self.empty_label = None

    def show_empty_message(self, message):
        self.empty_label = ttk.Label(self.chart_frame, text=message)
        self.empty_label.pack(pady=20)

    def is_selected(self):
        return self.parent.select() == str(self.elo_gain_tab)

    @staticmethod
    def draw_heatmap(ax, data, counts, players, title, colorbar_label):
        plotted_values = data.compressed()
        max_abs_value = max(max(abs(value) for value in plotted_values), 1)
        norm = TwoSlopeNorm(vmin=-max_abs_value, vcenter=0, vmax=max_abs_value)
        im, cbar = heatmap(
            data,
            players,
            players,
            ax=ax,
            cmap="RdBu",
            norm=norm,
            cbarlabel=colorbar_label,
            title=title
        )
        annotate_heatmap_with_counts(im, counts, valfmt="{x:+.1f}")

    @staticmethod
    def get_players(matches):
        return sorted({
            player
            for match in matches
            for player in (
                match.get('player1_name'),
                match.get('player1b_name'),
                match.get('player2_name'),
                match.get('player2b_name'),
            )
            if player
        })

    @staticmethod
    def get_team_players(match, side):
        if side == "player1":
            players = {
                match.get('player1_name'): match.get('player1_elo_after') - match.get('player1_elo_before')
            }
            if (
                match.get('player1b_name')
                and match.get('player1b_elo_before') is not None
                and match.get('player1b_elo_after') is not None
            ):
                players[match.get('player1b_name')] = match.get('player1b_elo_after') - match.get('player1b_elo_before')
            return players

        players = {
            match.get('player2_name'): match.get('player2_elo_after') - match.get('player2_elo_before')
        }
        if (
            match.get('player2b_name')
            and match.get('player2b_elo_before') is not None
            and match.get('player2b_elo_after') is not None
        ):
            players[match.get('player2b_name')] = match.get('player2b_elo_after') - match.get('player2b_elo_before')
        return players

    @staticmethod
    def expected_score(player_elo, opponent_elo):
        return 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))

    @classmethod
    def calculate_win_gain(cls, player_elo, opponent_elo):
        return round(K_FACTOR * (1 - cls.expected_score(player_elo, opponent_elo)))

    @classmethod
    def calculate_loss_cost(cls, player_elo, opponent_elo):
        return abs(round(K_FACTOR * (0 - cls.expected_score(player_elo, opponent_elo))))

    @staticmethod
    def get_player_elo_after(match, player):
        if player == match.get('player1_name'):
            return match.get('player1_elo_after')
        if player == match.get('player1b_name'):
            return match.get('player1b_elo_after')
        if player == match.get('player2_name'):
            return match.get('player2_elo_after')
        if player == match.get('player2b_name'):
            return match.get('player2b_elo_after')
        return db.INITIAL_ELO

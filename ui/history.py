import tkinter as tk
from tkinter import ttk
import database as db
from datetime import datetime

class HistoryTab:
    def __init__(self, parent, app):
        self.app = app
        self.history_tab = ttk.Frame(parent)
        parent.add(self.history_tab, text="Match History")

        self.history_text = tk.Text(self.history_tab, wrap="word", height=20, font=("Courier", 9))
        self.history_text.pack(fill='both', expand=True)
        
    def refresh_history(self):
        self.history_text.delete(1.0, tk.END)
        season_id = db.get_current_season()['id'] if db.get_current_season() else None # Use current season if available
        if not season_id:
            self.history_text.insert(tk.END, "Select a season to view history.")
            return

        matches = db.get_matches_for_season(season_id)
        if not matches:
            self.history_text.insert(tk.END, "No games recorded for this season yet.")
            return

        for row in reversed(matches): # Show most recent first
            dt = datetime.fromisoformat(row["date"]).strftime("%Y-%m-%d %H:%M")
            # Determine winner/loser using new schema
            if row.get("winner", -1) == 1:
                winner = row["player1_name"]
                loser = row["player2_name"]
                win_elo_before = row["player1_elo_before"]
                win_elo_after = row["player1_elo_after"]
                lose_elo_before = row["player2_elo_before"]
                lose_elo_after = row["player2_elo_after"]
            elif row.get("winner", -1) == 2:
                winner = row["player2_name"]
                loser = row["player1_name"]
                win_elo_before = row["player2_elo_before"]
                win_elo_after = row["player2_elo_after"]
                lose_elo_before = row["player1_elo_before"]
                lose_elo_after = row["player1_elo_after"]
            else:
                winner = "?"
                loser = "?"
                win_elo_before = win_elo_after = lose_elo_before = lose_elo_after = 0
            win_elo_diff = win_elo_after - win_elo_before
            lose_elo_diff = lose_elo_after - lose_elo_before
            line = f"{dt} | {winner:<15} def. {loser:<15} | {win_elo_after:>4} (+{win_elo_diff:<2}) / {lose_elo_after:>4} ({lose_elo_diff:<3})\n"
            self.history_text.insert(tk.END, line)

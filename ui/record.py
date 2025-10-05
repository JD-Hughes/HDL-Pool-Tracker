import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database as db

# --- Constants ---
K_FACTOR = 32
K_NEW_PLAYER = 40
GAMES_NEW_PLAYER = 10

# --- Core Elo Logic ---
def expected_score(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))

def update_elo(winner_elo, loser_elo, k):
    expected_win = expected_score(winner_elo, loser_elo)
    winner_elo_new = winner_elo + k * (1 - expected_win)
    loser_elo_new = loser_elo + k * (0 - expected_score(loser_elo, winner_elo))
    return round(winner_elo_new), round(loser_elo_new)

class RecordTab:
    def __init__(self, parent, app):
        self.app = app
        self.record_tab = ttk.Frame(parent)
        parent.add(self.record_tab, text="Record Match")
    
        ttk.Label(self.record_tab, text="Player 1:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.p1_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.p1_cb.grid(row=0, column=1, padx=5, pady=5)
    
        ttk.Label(self.record_tab, text="Player 2:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.p2_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.p2_cb.grid(row=1, column=1, padx=5, pady=5)
    
        ttk.Label(self.record_tab, text="Winner:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.winner_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.winner_cb.grid(row=2, column=1, padx=5, pady=5)
    
        def update_winner_options(_=None):
            p1, p2 = self.p1_cb.get(), self.p2_cb.get()
            self.winner_cb['values'] = [p1, p2] if p1 and p2 and p1 != p2 else []
    
        self.p1_cb.bind("<<ComboboxSelected>>", update_winner_options)
        self.p2_cb.bind("<<ComboboxSelected>>", update_winner_options)
    
        ttk.Button(self.record_tab, text="Record Match", command=self.record_match).grid(row=3, column=0, columnspan=2, pady=10)

    def record_match(self):
        p1_name = self.p1_cb.get()
        p2_name = self.p2_cb.get()
        winner_name = self.winner_cb.get()

        if not all([p1_name, p2_name, winner_name]) or p1_name == p2_name or winner_name not in [p1_name, p2_name]:
            messagebox.showerror("Invalid Input", "Select two different players and a valid winner.")
            return

        current_season = db.get_current_season()
        if not current_season:
            messagebox.showerror("Error", "No active season found. Please start a new season from the Admin tab.")
            return

        p1 = db.get_player_by_name(p1_name)
        p2 = db.get_player_by_name(p2_name)

        # Determine winner integer for new schema
        if winner_name == p1_name:
            winner_int = 1
            winner = p1
            loser = p2
            loser_name = p2_name
        else:
            winner_int = 2
            winner = p2
            loser = p1
            loser_name = p1_name

        k_winner = K_NEW_PLAYER if winner['total_lifetime_games'] < GAMES_NEW_PLAYER else K_FACTOR
        k_loser = K_NEW_PLAYER if loser['total_lifetime_games'] < GAMES_NEW_PLAYER else K_FACTOR
        k = max(k_winner, k_loser)
        
        # Calculate new Elo
        winner_elo_new, loser_elo_new = update_elo(winner['current_elo'], loser['current_elo'], k)

        # Prepare data bundle for database
        elo_changes = {
            winner_name: {
                'elo_before': winner['current_elo'], 'elo_after': winner_elo_new,
                'wins_after': winner['current_wins'] + 1,
                'lifetime_games_after': winner['total_lifetime_games'] + 1
            },
            loser_name: {
                'elo_before': loser['current_elo'], 'elo_after': loser_elo_new,
                'losses_after': loser['current_losses'] + 1,
                'lifetime_games_after': loser['total_lifetime_games'] + 1
            }
        }

        # Record match in database (update to pass winner_int for new schema)
        # If you add doubles support, update this call accordingly
        db.record_match(current_season['id'], p1_name, p2_name, winner_int, elo_changes)

        # Show summary
        winner_elo_diff = winner_elo_new - winner['current_elo']
        loser_elo_diff = loser_elo_new - loser['current_elo']
        loser_name = p2_name if winner_name == p1_name else p1_name
        summary = (
            f"{winner_name} def. {loser_name}\n"
            f"{winner_name}: {winner_elo_new} (+{winner_elo_diff})\n"
            f"{loser_name}: {loser_elo_new} ({loser_elo_diff})\n"
            f"(K-factor used: {k})"
        )
        messagebox.showinfo("Match Recorded", summary)
        
        # Reset form and refresh UI
        self.app.refresh_all_views()

    def refresh_player_selectors(self):
        player_names = db.get_all_player_names()
        self.p1_cb['values'] = player_names
        self.p2_cb['values'] = player_names
        self.p1_cb.set('')
        self.p2_cb.set('')
        self.winner_cb.set('')
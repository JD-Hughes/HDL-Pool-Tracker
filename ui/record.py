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
        # Checkbox to toggle doubles mode
        self.doubles_var = tk.BooleanVar(value=False)
        self.doubles_check = ttk.Checkbutton(self.record_tab, text="Doubles Match", variable=self.doubles_var, command=self.toggle_doubles)
        self.doubles_check.grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)

        # Player selectors (horizontal layout)
        ttk.Label(self.record_tab, text="Player 1:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.p1_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.p1_cb.grid(row=1, column=1, padx=5, pady=5)

        self.p1b_l = ttk.Label(self.record_tab, text="Player 1b:")
        self.p1b_l.grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.p1b_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.p1b_cb.grid(row=1, column=3, padx=5, pady=5)
        self.p1b_l.grid_remove()
        self.p1b_cb.grid_remove()

        ttk.Label(self.record_tab, text="Player 2:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.p2_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.p2_cb.grid(row=2, column=1, padx=5, pady=5)

        self.p2b_l = ttk.Label(self.record_tab, text="Player 2b:")
        self.p2b_l.grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.p2b_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.p2b_cb.grid(row=2, column=3, padx=5, pady=5)
        self.p2b_l.grid_remove()
        self.p2b_cb.grid_remove()

        ttk.Label(self.record_tab, text="Winner:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.winner_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.winner_cb.grid(row=3, column=1, padx=5, pady=5)


        def update_winner_options(*args):
            if self.doubles_var.get():
                p1, p1b = self.p1_cb.get(), self.p1b_cb.get()
                p2, p2b = self.p2_cb.get(), self.p2b_cb.get()
                # Only show teams if all four are selected and teams are valid
                if all([p1, p1b, p2, p2b]) and len({p1, p1b, p2, p2b}) == 4:
                    team1 = f"{p1} & {p1b}"
                    team2 = f"{p2} & {p2b}"
                    self.winner_cb['values'] = [team1, team2]
                else:
                    self.winner_cb['values'] = []
            else:
                p1, p2 = self.p1_cb.get(), self.p2_cb.get()
                self.winner_cb['values'] = [p1, p2] if p1 and p2 and p1 != p2 else []

        self.p1_cb.bind("<<ComboboxSelected>>", update_winner_options)
        self.p2_cb.bind("<<ComboboxSelected>>", update_winner_options)
        self.p1b_cb.bind("<<ComboboxSelected>>", update_winner_options)
        self.p2b_cb.bind("<<ComboboxSelected>>", update_winner_options)
        self.doubles_var.trace_add('write', update_winner_options)

        ttk.Button(self.record_tab, text="Record Match", command=self.record_match).grid(row=4, column=0, columnspan=4, pady=10)

    def toggle_doubles(self):
        if self.doubles_var.get():
            self.p1b_cb.grid()
            self.p1b_l.grid()
            self.p2b_cb.grid()
            self.p2b_l.grid()
        else:
            self.p1b_cb.grid_remove()
            self.p1b_l.grid_remove()
            self.p2b_cb.grid_remove()
            self.p2b_l.grid_remove()
            # Clear doubles player selections
            self.p1b_cb.set('')
            self.p2b_cb.set('')
            self.winner_cb.set('')

    def record_match(self):
        doubles = self.doubles_var.get()
        p1_name = self.p1_cb.get()
        p2_name = self.p2_cb.get()
        winner_name = self.winner_cb.get()

        if doubles:
            p1b_name = self.p1b_cb.get()
            p2b_name = self.p2b_cb.get()
            if not all([p1_name, p1b_name, p2_name, p2b_name, winner_name]):
                messagebox.showerror("Invalid Input", "Select all four players and a valid winner.")
                return
            if len({p1_name, p1b_name, p2_name, p2b_name}) < 4:
                messagebox.showerror("Invalid Input", "Players must be unique.")
                return
            team1 = f"{p1_name} & {p1b_name}"
            team2 = f"{p2_name} & {p2b_name}"
            if winner_name not in [team1, team2]:
                messagebox.showerror("Invalid Input", "Winner must be a valid team.")
                return
        else:
            p1b_name = p2b_name = None
            if not all([p1_name, p2_name, winner_name]) or p1_name == p2_name or winner_name not in [p1_name, p2_name]:
                messagebox.showerror("Invalid Input", "Select two different players and a valid winner.")
                return

        current_season = db.get_current_season()
        if not current_season:
            messagebox.showerror("Error", "No active season found. Please start a new season from the Admin tab.")
            return

        p1 = db.get_player_by_name(p1_name)
        p2 = db.get_player_by_name(p2_name)
        p1b = db.get_player_by_name(p1b_name) if p1b_name else None
        p2b = db.get_player_by_name(p2b_name) if p2b_name else None

        if doubles:
            # Determine winner team
            if winner_name == f"{p1_name} & {p1b_name}":
                winner_int = 1
                winner_team = [p1, p1b]
                loser_team = [p2, p2b]
            else:
                winner_int = 2
                winner_team = [p2, p2b]
                loser_team = [p1, p1b]

            # Average team Elo
            winner_avg_elo = sum([m['current_elo'] for m in winner_team]) / 2
            loser_avg_elo = sum([m['current_elo'] for m in loser_team]) / 2

            # Use max K-factor among all team members
            k_winner = max([K_NEW_PLAYER if m['total_lifetime_games'] < GAMES_NEW_PLAYER else K_FACTOR for m in winner_team])
            k_loser = max([K_NEW_PLAYER if m['total_lifetime_games'] < GAMES_NEW_PLAYER else K_FACTOR for m in loser_team])
            k = max(k_winner, k_loser)

            # Calculate new Elo for teams
            winner_elo_new, loser_elo_new = update_elo(winner_avg_elo, loser_avg_elo, k)
            winner_elo_diff = round(winner_elo_new - winner_avg_elo)
            loser_elo_diff = round(loser_elo_new - loser_avg_elo)

            # Apply Elo change to all team members
            elo_changes = {}
            for member in winner_team:
                elo_changes[member['name']] = {
                    'elo_before': member['current_elo'],
                    'elo_after': member['current_elo'] + winner_elo_diff,
                    'wins_after': member['current_wins'] + 1,
                    'lifetime_games_after': member['total_lifetime_games'] + 1
                }
            for member in loser_team:
                elo_changes[member['name']] = {
                    'elo_before': member['current_elo'],
                    'elo_after': member['current_elo'] + loser_elo_diff,
                    'losses_after': member['current_losses'] + 1,
                    'lifetime_games_after': member['total_lifetime_games'] + 1
                }

            # Record match in database
            db.record_match(
                current_season['id'],
                p1_name, p2_name, winner_int, elo_changes,
                doubles_match=True,
                p1b_name=p1b_name, p2b_name=p2b_name,
                p1b_elo_before=p1b['current_elo'] if p1b else None,
                p1b_elo_after=elo_changes[p1b_name]['elo_after'] if p1b else None,
                p2b_elo_before=p2b['current_elo'] if p2b else None,
                p2b_elo_after=elo_changes[p2b_name]['elo_after'] if p2b else None
            )

            # Show summary
            summary = (
                f"{winner_name} def. {team2 if winner_int == 1 else team1}\n"
                f"{winner_team[0]['name']}: {elo_changes[winner_team[0]['name']]['elo_after']} (+{winner_elo_diff})\n"
                f"{winner_team[1]['name']}: {elo_changes[winner_team[1]['name']]['elo_after']} (+{winner_elo_diff})\n"
                f"{loser_team[0]['name']}: {elo_changes[loser_team[0]['name']]['elo_after']} ({loser_elo_diff})\n"
                f"{loser_team[1]['name']}: {elo_changes[loser_team[1]['name']]['elo_after']} ({loser_elo_diff})\n"
                f"(K-factor used: {k})"
            )
            messagebox.showinfo("Match Recorded", summary)
        else:
            # Singles logic (unchanged)
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
                winner['name']: {
                    'elo_before': winner['current_elo'], 'elo_after': winner_elo_new,
                    'wins_after': winner['current_wins'] + 1,
                    'lifetime_games_after': winner['total_lifetime_games'] + 1
                },
                loser['name']: {
                    'elo_before': loser['current_elo'], 'elo_after': loser_elo_new,
                    'losses_after': loser['current_losses'] + 1,
                    'lifetime_games_after': loser['total_lifetime_games'] + 1
                }
            }

            # Record match in database
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
        self.p1b_cb['values'] = player_names
        self.p2b_cb['values'] = player_names
        self.p1_cb.set('')
        self.p2_cb.set('')
        self.winner_cb.set('')
        self.p1b_cb.set('')
        self.p2b_cb.set('')
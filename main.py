import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# Import the new database module
import database as db

# --- Constants ---
K_FACTOR = 32
K_NEW_PLAYER = 40
GAMES_NEW_PLAYER = 10
SMOOTHING_WINDOW = 5

# --- Core Elo Logic (unchanged) ---
def expected_score(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))

def update_elo(winner_elo, loser_elo, k):
    expected_win = expected_score(winner_elo, loser_elo)
    winner_elo_new = winner_elo + k * (1 - expected_win)
    loser_elo_new = loser_elo + k * (0 - expected_score(loser_elo, winner_elo))
    return round(winner_elo_new), round(loser_elo_new)

# --- Main Application Class ---
class EloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pool Elo Tracker")

        # --- UI State Variables ---
        self.graph_canvas = None
        self.smoothing_enabled = tk.BooleanVar(value=True)
        self.selected_season_id = tk.IntVar()
        self.season_map = {} # Maps season name to season ID

        # --- Main UI Setup ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.create_leaderboard_tab()
        self.create_record_tab()
        self.create_history_tab()
        self.create_graph_tab()
        self.create_admin_tab()
        self.create_add_player_tab()

        # --- Initial Data Load ---
        self.refresh_all_views()

    def refresh_all_views(self):
        """Master function to refresh all data-driven UI components."""
        print("Refreshing all views...")
        player_names = db.get_all_player_names()
        
        # Refresh UI components that depend on player list
        self.p1_cb['values'] = player_names
        self.p2_cb['values'] = player_names
        self.p1_cb.set('')
        self.p2_cb.set('')
        self.winner_cb.set('')
        
        self.refresh_leaderboard()
        self.refresh_season_selector() # This will trigger graph/history refresh

    # --- Tab Creation Methods ---

    def create_leaderboard_tab(self):
        self.leaderboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.leaderboard_tab, text="Leaderboard")
    
        columns = ("Name", "Played", "Elo", "Wins", "Losses")
        self.leaderboard_tree = ttk.Treeview(self.leaderboard_tab, columns=columns, show="headings")
    
        for col in columns:
            self.leaderboard_tree.heading(col, text=col)
            self.leaderboard_tree.column(col, anchor='center', width=100)
    
        self.leaderboard_tree.pack(fill='both', expand=True)

    def create_record_tab(self):
        self.record_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.record_tab, text="Record Match")
    
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
    
        self.win_reasons = {
            "Opponent potted 8-ball early": tk.BooleanVar(),
            "Opponent fouled on 8-ball": tk.BooleanVar(),
            "Opponent Conceded": tk.BooleanVar()
        }
    
        ttk.Label(self.record_tab, text="Win Reason (optional):").grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(10,0))
        row_idx = 4
        for label, var in self.win_reasons.items():
            ttk.Checkbutton(self.record_tab, text=label, variable=var).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=20)
            row_idx += 1
    
        ttk.Button(self.record_tab, text="Record Match", command=self.record_match).grid(row=row_idx, column=0, columnspan=2, pady=10)

    def create_add_player_tab(self):
        self.add_player_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.add_player_tab, text="Add Player")

        ttk.Label(self.add_player_tab, text="New Player Name:").pack(pady=10)
        self.new_player_entry = ttk.Entry(self.add_player_tab, width=30)
        self.new_player_entry.pack(pady=5)
        ttk.Button(self.add_player_tab, text="Add Player", command=self.add_new_player).pack(pady=10)
        
    def create_history_tab(self):
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="Match History")

        self.history_text = tk.Text(self.history_tab, wrap="word", height=20, font=("Courier", 9))
        self.history_text.pack(fill='both', expand=True)

    def create_graph_tab(self):
        self.graph_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.graph_tab, text="Elo Graphs")
        
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
        
    def create_admin_tab(self):
        self.admin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.admin_tab, text="Admin")
        ttk.Button(self.admin_tab, text="Start New Season", command=self.start_new_season).pack(pady=10)
        ttk.Button(self.admin_tab, text="Delete Player", command=self.delete_player).pack(pady=10)

    # --- Data Handling and UI Refresh Methods ---

    def refresh_leaderboard(self):
        for row in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(row)
        
        players = db.get_leaderboard_players()
        for p in players:
            played = p["current_wins"] + p["current_losses"]
            self.leaderboard_tree.insert('', 'end', values=(p["name"], played, p["current_elo"], p["current_wins"], p["current_losses"]))

    def refresh_history(self):
        self.history_text.delete(1.0, tk.END)
        #season_id = self.selected_season_id.get() # Uncomment if you want the history to depend on selected season (Elo graph screen)
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
            winner = row["winner_name"]
            loser = row["player2_name"] if winner == row["player1_name"] else row["player1_name"]
            win_elo_diff = row["winner_elo_after"] - row["winner_elo_before"]
            lose_elo_diff = row["loser_elo_after"] - row["loser_elo_before"]
            
            line = f"{dt} | {winner:<15} def. {loser:<15} | {row['winner_elo_after']:>4} (+{win_elo_diff:<2}) / {row['loser_elo_after']:>4} ({lose_elo_diff:<3})\n"
            self.history_text.insert(tk.END, line)

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
            self.refresh_history()

    # --- Core Functionality Methods ---

    def add_new_player(self):
        name = self.new_player_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Player name cannot be empty.")
            return
        
        if db.get_player_by_name(name):
            messagebox.showinfo("Exists", f"Player '{name}' already exists.")
            return
            
        db.add_player(name)
        messagebox.showinfo("Added", f"Player '{name}' has been added.")
        self.new_player_entry.delete(0, tk.END)
        self.refresh_all_views()

    def record_match(self):
        p1_name = self.p1_cb.get()
        p2_name = self.p2_cb.get()
        winner_name = self.winner_cb.get()

        if not all([p1_name, p2_name, winner_name]) or p1_name == p2_name or winner_name not in [p1_name, p2_name]:
            messagebox.showerror("Invalid Input", "Select two different players and a valid winner.")
            return
        
        #self.maybe_create_backup() #TODO: Uncomment when backup logic is implemented

        current_season = db.get_current_season()
        if not current_season:
            messagebox.showerror("Error", "No active season found. Please start a new season from the Admin tab.")
            return

        p1 = db.get_player_by_name(p1_name)
        p2 = db.get_player_by_name(p2_name)
        loser_name = p2_name if winner_name == p1_name else p1_name

        winner = p1 if winner_name == p1_name else p2
        loser = p2 if winner_name == p1_name else p1
        
        # Determine K-factor based on TOTAL lifetime games
        k_winner = K_NEW_PLAYER if winner['total_lifetime_games'] < GAMES_NEW_PLAYER else K_FACTOR
        k_loser = K_NEW_PLAYER if loser['total_lifetime_games'] < GAMES_NEW_PLAYER else K_FACTOR
        k = max(k_winner, k_loser)
        
        # Calculate new Elo
        winner_elo_new, loser_elo_new = update_elo(winner['current_elo'], loser['current_elo'], k)

        win_reason = "; ".join(reason for reason, var in self.win_reasons.items() if var.get()) or "Won normally"

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

        # Record match in database
        db.record_match(current_season['id'], p1_name, p2_name, winner_name, elo_changes, win_reason)

        # Show summary
        winner_elo_diff = winner_elo_new - winner['current_elo']
        loser_elo_diff = loser_elo_new - loser['current_elo']
        summary = (
            f"{winner_name} def. {loser_name}\n"
            f"{winner_name}: {winner_elo_new} (+{winner_elo_diff})\n"
            f"{loser_name}: {loser_elo_new} ({loser_elo_diff})\n"
            f"(K-factor used: {k})"
        )
        messagebox.showinfo("Match Recorded", summary)
        
        # Reset form and refresh UI
        for var in self.win_reasons.values(): var.set(False)
        self.refresh_all_views()

    def plot_elo_graph(self):
        if self.graph_canvas:
            self.graph_canvas.get_tk_widget().destroy()

        season_id = self.selected_season_id.get()
        matches = db.get_matches_for_season(season_id)

        if not matches:
            return

        # Get all unique players in this season's matches
        players_in_season = set()
        for match in matches:
            players_in_season.add(match['player1_name'])
            players_in_season.add(match['player2_name'])
        
        # Build elo history timeline from matches
        elo_data = {p: [] for p in players_in_season}
        for match in matches:
            temp_elos = {p: elo_data[p][-1] if elo_data[p] else db.INITIAL_ELO for p in players_in_season}
            
            winner, loser = match['winner_name'], match['player1_name'] if match['winner_name'] == match['player2_name'] else match['player2_name']
            
            temp_elos[winner] = match['winner_elo_after']
            temp_elos[loser] = match['loser_elo_after']

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

    # --- Admin Methods ---

    def start_new_season(self):
        season_name = simpledialog.askstring("New Season", "Enter the name for the new season (e.g., 'Winter 2025'):")
        if season_name:
            if messagebox.askyesno("Confirm", f"Are you sure you want to start season '{season_name}'?\nThis will reset all current Elo scores and stats."):
                db.start_new_season(season_name)
                messagebox.showinfo("Success", f"New season '{season_name}' has started!")
                self.refresh_all_views()

    def delete_player(self):
        name = simpledialog.askstring("Delete Player", "Enter the exact player name to delete:")
        if not name:
            return

        player = db.get_player_by_name(name)
        if player:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{name}'?\nAll their matches across all seasons will be erased. This cannot be undone."):
                db.delete_player(name)
                messagebox.showinfo("Deleted", f"Player '{name}' and all their matches have been deleted.")
                self.refresh_all_views()
        else:
            messagebox.showerror("Not Found", f"Player '{name}' not found.")


    #TODO: Implement automatic backup logic here
    # def maybe_create_backup(self):
    #     #last_match_time = datetime.fromisoformat(self.history.iloc[-1]["Date"])
    #     last_match_time = db.get_matches_for_season(self.selected_season_id.get())[-1]["date"]
    #     now = datetime.now()
    #     if (now - last_match_time).days >= 1:
    #         timestamp = now.strftime("%Y-%m-%d_%H-%M")
    #         db.backup_database(f"Backup Data/database_{timestamp}.db")
    #         print(f"Backup created: {timestamp}")


if __name__ == "__main__":
    # Initialize the database first if it doesn't exist
    db.init_db()
    
    # Run the Tkinter application
    root = tk.Tk()
    #root.iconbitmap("assets/8-ball-icon.ico") #TODO: Fix this (No icon showing in MacOS and PyInstaller build issues)
    root.geometry("800x600")
    app = EloApp(root)
    root.mainloop()

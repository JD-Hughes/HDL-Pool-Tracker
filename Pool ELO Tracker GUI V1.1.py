import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd
from datetime import datetime
import os
import shutil
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

PLAYER_FILE = "players.csv"
HISTORY_FILE = "history.csv"
INITIAL_ELO = 1200
K_FACTOR = 32
K_NEW_PLAYER = 40
GAMES_NEW_PLAYER = 10

def load_players():
    if os.path.exists(PLAYER_FILE):
        return pd.read_csv(PLAYER_FILE)
    else:
        return pd.DataFrame(columns=["Name", "Elo", "Wins", "Losses"])

def load_history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if "Win_Reason" not in df.columns:
            df["Win_Reason"] = "Won normally"
        return df
    else:
        return pd.DataFrame(columns=[
            "Date", "Player1", "Player2", "Winner",
            "Winner_Elo_Before", "Winner_Elo_After",
            "Loser_Elo_Before", "Loser_Elo_After",
            "Win_Reason"
        ])

def save_players(df):
    df.to_csv(PLAYER_FILE, index=False)

def save_history(df):
    columns = [
        "Date", "Player1", "Player2", "Winner",
        "Winner_Elo_Before", "Winner_Elo_After",
        "Loser_Elo_Before", "Loser_Elo_After",
        "Win_Reason"
    ]
    df = df[columns]  # enforce column order
    df.to_csv(HISTORY_FILE, index=False)


def expected_score(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))

def update_elo(winner_elo, loser_elo, k):
    expected_win = expected_score(winner_elo, loser_elo)
    winner_elo += k * (1 - expected_win)
    loser_elo += k * (0 - expected_score(loser_elo, winner_elo))
    return round(winner_elo), round(loser_elo)


def ensure_player(players, name):
    if name not in players["Name"].values:
        new_row = pd.DataFrame([[name, INITIAL_ELO, 0, 0]], columns=["Name", "Elo", "Wins", "Losses"])
        players = pd.concat([players, new_row], ignore_index=True)
    return players

class EloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pool Elo Tracker")
        self.players = load_players()
        self.history = load_history()
        self.graph_canvas = None

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        self.create_leaderboard_tab()
        self.create_record_tab()
        self.create_history_tab()
        self.create_graph_tab()
        self.create_admin_tab()
        self.create_add_player_tab()
        
        self.win_reasons = {
            "Opponent potted 8-ball early": tk.BooleanVar(),
            "Opponent fouled on 8-ball": tk.BooleanVar(),
            "Opponent Conceded": tk.BooleanVar()
        }

    def create_leaderboard_tab(self):
        self.leaderboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.leaderboard_tab, text="Leaderboard")
    
        columns = ("Name", "Played", "Elo", "Wins", "Losses")
        self.leaderboard_tree = ttk.Treeview(
            self.leaderboard_tab,
            columns=columns,
            show="headings",
            height=20
        )
    
        for col in columns:
            self.leaderboard_tree.heading(col, text=col, anchor='center')
            self.leaderboard_tree.column(col, anchor='center', stretch=True)
    
        self.leaderboard_tree.pack(fill='both', expand=True)
        self.refresh_leaderboard()


    def refresh_leaderboard(self):
        for row in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(row)
        self.players["Played"] = self.players["Wins"] + self.players["Losses"]
        sorted_players = self.players.sort_values(by="Elo", ascending=False)
        for _, row in sorted_players.iterrows():
            self.leaderboard_tree.insert('', 'end', values=(row["Name"], row["Played"], row["Elo"], row["Wins"], row["Losses"]))

    def create_record_tab(self):
        self.record_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.record_tab, text="Record Match")
    
        ttk.Label(self.record_tab, text="Player 1:").grid(row=0, column=0, padx=5, pady=5)
        self.p1_cb = ttk.Combobox(self.record_tab, values=self.players["Name"].tolist(), state="readonly")
        self.p1_cb.grid(row=0, column=1, padx=5, pady=5)
    
        ttk.Label(self.record_tab, text="Player 2:").grid(row=1, column=0, padx=5, pady=5)
        self.p2_cb = ttk.Combobox(self.record_tab, values=self.players["Name"].tolist(), state="readonly")
        self.p2_cb.grid(row=1, column=1, padx=5, pady=5)
    
        ttk.Label(self.record_tab, text="Winner:").grid(row=2, column=0, padx=5, pady=5)
        self.winner_cb = ttk.Combobox(self.record_tab, state="readonly")
        self.winner_cb.grid(row=2, column=1, padx=5, pady=5)
    
        def update_winner_options(_=None):
            p1, p2 = self.p1_cb.get(), self.p2_cb.get()
            self.winner_cb['values'] = [p1, p2] if p1 and p2 and p1 != p2 else []
    
        self.p1_cb.bind("<<ComboboxSelected>>", update_winner_options)
        self.p2_cb.bind("<<ComboboxSelected>>", update_winner_options)
    
        # Win reason checkboxes
        self.win_reasons = {
            "Opponent potted 8-ball early": tk.BooleanVar(),
            "Opponent fouled on 8-ball": tk.BooleanVar(),
            "Opponent gave up / disconnected": tk.BooleanVar()
        }
    
        ttk.Label(self.record_tab, text="Win Reason (optional):").grid(row=3, column=0, columnspan=2, sticky="w", padx=5)
        row_idx = 4
        for label, var in self.win_reasons.items():
            ttk.Checkbutton(self.record_tab, text=label, variable=var).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=20)
            row_idx += 1
    
        ttk.Button(self.record_tab, text="Record Match", command=self.record_match).grid(row=row_idx, column=0, columnspan=2, pady=10)


    def record_match(self):
        p1 = self.p1_cb.get().strip()
        p2 = self.p2_cb.get().strip()
        winner = self.winner_cb.get().strip()
    
        if not all([p1, p2, winner]) or p1 == p2 or winner not in [p1, p2]:
            messagebox.showerror("Invalid Input", "Select two different players and a valid winner.")
            return
    
        self.maybe_create_backup()
    
        self.players = ensure_player(self.players, p1)
        self.players = ensure_player(self.players, p2)
        save_players(self.players)
    
        elo1 = self.players.loc[self.players["Name"] == p1, "Elo"].values[0]
        elo2 = self.players.loc[self.players["Name"] == p2, "Elo"].values[0]
    
        if winner == p1:
            loser = p2
            winner_elo_current = elo1
            loser_elo_current = elo2
        else:
            loser = p1
            winner_elo_current = elo2
            loser_elo_current = elo1
    
        # Dynamic K-factor
        winner_games = self.players.loc[self.players["Name"] == winner, ["Wins", "Losses"]].sum(axis=1).values[0]
        loser_games = self.players.loc[self.players["Name"] == loser, ["Wins", "Losses"]].sum(axis=1).values[0]
        winner_k = K_NEW_PLAYER if winner_games < GAMES_NEW_PLAYER else K_FACTOR
        loser_k = K_NEW_PLAYER if loser_games < GAMES_NEW_PLAYER else K_FACTOR
        k = max(winner_k, loser_k)
    
        winner_elo, loser_elo = update_elo(winner_elo_current, loser_elo_current, k)
    
        self.players.loc[self.players["Name"] == winner, "Elo"] = winner_elo
        self.players.loc[self.players["Name"] == loser, "Elo"] = loser_elo
        self.players.loc[self.players["Name"] == winner, "Wins"] += 1
        self.players.loc[self.players["Name"] == loser, "Losses"] += 1
    
        # Reason for win
        win_reason = "; ".join(reason for reason, var in self.win_reasons.items() if var.get())
        if not win_reason:
            win_reason = "Won normally"
    
        match = pd.DataFrame([[
            datetime.now().isoformat(), p1, p2, winner,
            winner_elo_current, winner_elo,
            loser_elo_current, loser_elo,
            win_reason
        ]], columns=[
            "Date", "Player1", "Player2", "Winner",
            "Winner_Elo_Before", "Winner_Elo_After",
            "Loser_Elo_Before", "Loser_Elo_After",
            "Win_Reason"
        ])
        self.history = pd.concat([self.history, match], ignore_index=True)
    
        save_players(self.players)
        save_history(self.history)
    
        self.refresh_leaderboard()
        self.refresh_history()
        self.plot_elo_graph()
    
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        winner_elo_diff = winner_elo - winner_elo_current
        loser_elo_diff = loser_elo - loser_elo_current
    
        summary = (
            f"{now_str} | {winner} def. {loser} | "
            f"+{winner_elo_diff} → {winner_elo} / {loser_elo_diff} → {loser_elo}\n"
            f"(K-factor used: {k})"
        )
        messagebox.showinfo("Match Recorded", summary)
    
        # Reset checkboxes
        for var in self.win_reasons.values():
            var.set(False)




    def create_add_player_tab(self):
        self.add_player_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.add_player_tab, text="Add Player")

        ttk.Label(self.add_player_tab, text="Player Name:").pack(pady=10)
        self.new_player_entry = ttk.Entry(self.add_player_tab)
        self.new_player_entry.pack(pady=5)

        def add_new_player():
            name = self.new_player_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Player name cannot be empty.")
                return
            if name in self.players["Name"].values:
                messagebox.showinfo("Exists", "Player already exists.")
                return
            self.players = ensure_player(self.players, name)
            save_players(self.players)
            self.refresh_leaderboard()
            self.p1_cb['values'] = self.players["Name"].tolist()
            self.p2_cb['values'] = self.players["Name"].tolist()
            messagebox.showinfo("Added", f"Player '{name}' added.")
            self.new_player_entry.delete(0, tk.END)

        ttk.Button(self.add_player_tab, text="Add Player", command=add_new_player).pack(pady=10)

    def create_history_tab(self):
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="Match History")

        self.history_text = tk.Text(self.history_tab, wrap="word", height=20)
        self.history_text.pack(fill='both', expand=True)
        self.refresh_history()

    def refresh_history(self):
        self.history_text.delete(1.0, tk.END)
        if self.history.empty:
            self.history_text.insert(tk.END, "No games recorded yet.")
        else:
            for _, row in self.history.iterrows():
                dt = datetime.fromisoformat(row["Date"]).strftime("%Y-%m-%d %H:%M")
                winner = row["Winner"]
                p1, p2 = row["Player1"], row["Player2"]
                loser = p2 if winner == p1 else p1
                win_elo_diff = row["Winner_Elo_After"] - row["Winner_Elo_Before"]
                lose_elo_diff = row["Loser_Elo_After"] - row["Loser_Elo_Before"]
                self.history_text.insert(tk.END, f"{dt} | {winner} def. {loser} | +{win_elo_diff} → {row['Winner_Elo_After']} / {lose_elo_diff} → {row['Loser_Elo_After']}\n")

    def create_graph_tab(self):
        self.graph_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.graph_tab, text="Elo Graphs")
        ttk.Button(self.graph_tab, text="Refresh Elo Graph", command=self.plot_elo_graph).pack(pady=10)

    def plot_elo_graph(self):
        if self.graph_canvas:
            self.graph_canvas.get_tk_widget().destroy()
            self.graph_canvas = None

        if self.history.empty:
            return

        history = self.history.copy()
        players = set(history["Player1"]) | set(history["Player2"])
        timestamps = []
        elo_data = {p: [] for p in players}

        for _, row in history.iterrows():
            timestamps.append(datetime.fromisoformat(row["Date"]).strftime("%Y-%m-%d %H:%M"))
            for p in players:
                if p == row["Player1"]:
                    elo_data[p].append(row["Winner_Elo_After"] if p == row["Winner"] else row["Loser_Elo_After"])
                elif p == row["Player2"]:
                    elo_data[p].append(row["Winner_Elo_After"] if p == row["Winner"] else row["Loser_Elo_After"])
                else:
                    elo_data[p].append(elo_data[p][-1] if elo_data[p] else INITIAL_ELO)

        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        for player, elos in elo_data.items():
            ax.plot(timestamps, elos, label=player)
        ax.set_title("Elo Ratings Over Time")
        ax.set_xlabel("Date & Time")
        ax.set_ylabel("Elo")
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True)
        ax.legend()
        fig.subplots_adjust(bottom=0.25)

        self.graph_canvas = FigureCanvasTkAgg(fig, master=self.graph_tab)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_admin_tab(self):
        self.admin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.admin_tab, text="Admin")
        ttk.Button(self.admin_tab, text="Delete Player", command=self.delete_player).pack(pady=10)
        ttk.Button(self.admin_tab, text="Delete Last Match", command=self.delete_last_match).pack(pady=10)

    def delete_player(self):
        name = simpledialog.askstring("Delete Player", "Enter player name to delete:")
        if name and name in self.players["Name"].values:
            self.players = self.players[self.players["Name"] != name].reset_index(drop=True)
            self.history = self.history[~((self.history["Player1"] == name) | (self.history["Player2"] == name))].reset_index(drop=True)
    
            save_history(self.history)
            save_players(self.players)
    
            self.p1_cb['values'] = self.players["Name"].tolist()
            self.p2_cb['values'] = self.players["Name"].tolist()
            self.winner_cb.set('')
            self.p1_cb.set('')
            self.p2_cb.set('')
    
            self.recalculate_all_ratings()
            self.refresh_leaderboard()
            self.refresh_history()
            self.plot_elo_graph()
    
            messagebox.showinfo("Deleted", f"Deleted player '{name}' and related matches.")
        else:
            messagebox.showerror("Not Found", "Player not found.")


    def delete_last_match(self):
        if not self.history.empty:
            self.history = self.history[:-1]
            save_history(self.history)
            self.recalculate_all_ratings()
            messagebox.showinfo("Match Deleted", "Last match deleted and Elo recalculated.")
        else:
            messagebox.showerror("No History", "No match to delete.")

    def recalculate_all_ratings(self):
        self.players["Elo"] = INITIAL_ELO
        self.players["Wins"] = 0
        self.players["Losses"] = 0
        for _, row in self.history.iterrows():
            p1, p2, winner = row["Player1"], row["Player2"], row["Winner"]
            loser = p2 if winner == p1 else p1
            elo1 = self.players.loc[self.players["Name"] == p1, "Elo"].values[0]
            elo2 = self.players.loc[self.players["Name"] == p2, "Elo"].values[0]
            winner_games = self.players.loc[self.players["Name"] == winner, ["Wins", "Losses"]].sum(axis=1).values[0]
            loser_games = self.players.loc[self.players["Name"] == loser, ["Wins", "Losses"]].sum(axis=1).values[0]
            winner_k = K_NEW_PLAYER if winner_games < GAMES_NEW_PLAYER else K_FACTOR
            loser_k = K_NEW_PLAYER if loser_games < GAMES_NEW_PLAYER else K_FACTOR
            k = max(winner_k, loser_k)
            
            if winner == p1:
                new_winner_elo, new_loser_elo = update_elo(elo1, elo2, k)
            else:
                new_winner_elo, new_loser_elo = update_elo(elo2, elo1, k)
            self.players.loc[self.players["Name"] == winner, "Elo"] = new_winner_elo
            self.players.loc[self.players["Name"] == loser, "Elo"] = new_loser_elo
            self.players.loc[self.players["Name"] == winner, "Wins"] += 1
            self.players.loc[self.players["Name"] == loser, "Losses"] += 1
        save_players(self.players)
        self.refresh_leaderboard()
        self.refresh_history()
        self.plot_elo_graph()

    def maybe_create_backup(self):
        if self.history.empty:
            return
        last_match_time = datetime.fromisoformat(self.history.iloc[-1]["Date"])
        now = datetime.now()
        if (now - last_match_time).days >= 1:
            os.makedirs("Backup Data", exist_ok=True)
            timestamp = now.strftime("%Y-%m-%d_%H-%M")
            shutil.copyfile(PLAYER_FILE, f"Backup Data/players_{timestamp}.csv")
            shutil.copyfile(HISTORY_FILE, f"Backup Data/history_{timestamp}.csv")
            print(f"Backup created: {timestamp}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EloApp(root)
    root.mainloop()

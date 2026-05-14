from tkinter import ttk
import database as db

class LeaderboardTab:
    def __init__(self, parent, app):
        self.app = app
        self.leaderboard_tab = ttk.Frame(parent)
        parent.add(self.leaderboard_tab, text="Leaderboard")
    
        columns = ("Name", "Played", "Elo", "Wins", "Losses")
        ttk.Label(self.leaderboard_tab, text="Active Players").pack(anchor='w', padx=5, pady=(5, 0))
        self.leaderboard_tree = ttk.Treeview(self.leaderboard_tab, columns=columns, show="headings", height=12)
    
        for col in columns:
            self.leaderboard_tree.heading(col, text=col)
            self.leaderboard_tree.column(col, anchor='center', width=100)
    
        self.leaderboard_tree.pack(fill='x', expand=False, padx=5, pady=(0, 10))

        ttk.Label(self.leaderboard_tab, text="No Games Played").pack(anchor='w', padx=5)
        self.inactive_tree = ttk.Treeview(self.leaderboard_tab, columns=columns, show="headings", height=5)

        for col in columns:
            self.inactive_tree.heading(col, text=col)
            self.inactive_tree.column(col, anchor='center', width=100)

        self.inactive_tree.pack(fill='both', expand=True, padx=5, pady=(0, 5))

        # Handle larger font sizes and stop them from cutting off text.
        style = ttk.Style()
        style.configure("Treeview", rowheight=30)

    def refresh_leaderboard(self):
        for row in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(row)
        for row in self.inactive_tree.get_children():
            self.inactive_tree.delete(row)
        
        players = db.get_leaderboard_players()
        for p in players:
            played = p["current_wins"] + p["current_losses"]
            target_tree = self.leaderboard_tree if played > 0 else self.inactive_tree
            target_tree.insert('', 'end', values=(p["name"], played, p["current_elo"], p["current_wins"], p["current_losses"]))

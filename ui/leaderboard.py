from tkinter import ttk
import database as db

class LeaderboardTab:
    def __init__(self, parent, app):
        self.app = app
        self.leaderboard_tab = ttk.Frame(parent)
        parent.add(self.leaderboard_tab, text="Leaderboard")
    
        columns = ("Name", "Played", "Elo", "Wins", "Losses")
        self.leaderboard_tree = ttk.Treeview(self.leaderboard_tab, columns=columns, show="headings")
    
        for col in columns:
            self.leaderboard_tree.heading(col, text=col)
            self.leaderboard_tree.column(col, anchor='center', width=100)
    
        self.leaderboard_tree.pack(fill='both', expand=True)

        # Handle larger font sizes and stop them from cutting off text.
        style = ttk.Style()
        style.configure("Treeview", rowheight=30)

    def refresh_leaderboard(self):
        for row in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(row)
        
        players = db.get_leaderboard_players()
        for p in players:
            played = p["current_wins"] + p["current_losses"]
            self.leaderboard_tree.insert('', 'end', values=(p["name"], played, p["current_elo"], p["current_wins"], p["current_losses"]))

# --- Imports ---
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# Import local modules
import database as db
from ui import graph
from ui import admin
from ui import leaderboard
from ui import history
from ui import record

# --- Main Application Class ---
class EloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pool Elo Tracker")

        # --- Main UI Setup ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.leaderboardTab = leaderboard.LeaderboardTab(self.notebook, self) # Create leaderboard tab instance
        self.recordTab = record.RecordTab(self.notebook, self) # Create record tab instance
        self.historyTab = history.HistoryTab(self.notebook, self) # Create history tab instance
        self.graphTab = graph.GraphTab(self.notebook, self) # Create graph tab instance
        self.adminTab = admin.AdminTab(self.notebook, self) # Create admin tab instance

        # --- Initial Data Load ---
        self.refresh_all_views()

    def refresh_all_views(self):
        """Master function to refresh all data-driven UI components."""
        print("Refreshing all views...")
        
        self.recordTab.refresh_player_selectors()
        self.leaderboardTab.refresh_leaderboard()
        self.graphTab.refresh_season_selector() # This will trigger graph/history refresh
        self.historyTab.refresh_history()

    # --- Core Functionality Methods ---

    

if __name__ == "__main__":
    # Initialize the database first if it doesn't exist
    db.init_db()

    # Auto-backup if last backup is older than 24 hours
    try:
        last_backup = db.get_last_backup_time('backups')
        now = datetime.now()
        if (not last_backup) or ((now - last_backup).total_seconds() > 86400):
            db.backup_database()
    except Exception as e:
        print(f"Auto-backup check failed: {e}")
        messagebox.showinfo("Backup Failed", f"Auto-backup check failed: {e}")

    # Run the Tkinter application
    root = tk.Tk()
    icon = tk.PhotoImage(file="assets/8-ball.png")
    root.iconphoto(True, icon)
    root.geometry("800x600")
    app = EloApp(root)
    root.mainloop()

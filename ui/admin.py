import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database as db

class AdminTab:
    def __init__(self, parent, app):
        self.app = app
        self.admin_tab = ttk.Frame(parent)
        parent.add(self.admin_tab, text="Admin")
        ttk.Button(self.admin_tab, text="Start New Season", command=self.start_new_season).pack(pady=10)
        ttk.Button(self.admin_tab, text="Delete Player", command=self.delete_player).pack(pady=10)
        ttk.Button(self.admin_tab, text="Archive Player", command=self.archive_player).pack(pady=10)
        ttk.Button(self.admin_tab, text="Backup Database", command=self.backup_database_ui).pack(pady=10)
        ttk.Button(self.admin_tab, text="Delete Last Match", command=self.delete_last_match).pack(pady=10)

        # Add Player UI
        ttk.Label(self.admin_tab, text="Add New Player:").pack(pady=(20, 5))
        self.new_player_entry = ttk.Entry(self.admin_tab, width=30)
        self.new_player_entry.pack(pady=5)
        ttk.Button(self.admin_tab, text="Add Player", command=self.add_new_player).pack(pady=5)

    def backup_database_ui(self):
        prefix = simpledialog.askstring("Backup Database", "Enter a prefix for the backup file (optional):")
        backup_name = db.backup_database(prefix=prefix if prefix else None)
        if backup_name:
            messagebox.showinfo("Backup Successful", f"Database backed up as: backups/{backup_name}")
        else:
            messagebox.showerror("Backup Failed", "Database backup failed. See console for details.")

    def start_new_season(self):
        season_name = simpledialog.askstring("New Season", "Enter the name for the new season (e.g., 'Winter 2025'):")
        if season_name:
            if messagebox.askyesno("Confirm", f"Are you sure you want to start season '{season_name}'?\nThis will reset all current Elo scores and stats."):
                db.start_new_season(season_name)
                messagebox.showinfo("Success", f"New season '{season_name}' has started!")
                self.app.refresh_all_views()

    def archive_player(self):
        name = simpledialog.askstring("Archive Player", "Enter the exact player name to archive:")
        if not name:
            return

        player = db.get_player_by_name(name)
        if player:
            if messagebox.askyesno("Confirm Archive", f"Are you sure you want to archive '{name}'?\nThey will be removed from active player lists but their match history will be retained."):
                db.archive_player(name)
                messagebox.showinfo("Archived", f"Player '{name}' has been archived.")
                self.app.refresh_all_views()
        else:
            messagebox.showerror("Not Found", f"Player '{name}' not found.")

    def delete_player(self):
        name = simpledialog.askstring("Delete Player", "Enter the exact player name to delete:")
        if not name:
            return

        player = db.get_player_by_name(name)
        if player:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{name}'?\nAll their matches across all seasons will be erased. This cannot be undone."):
                db.delete_player(name)
                messagebox.showinfo("Deleted", f"Player '{name}' and all their matches have been deleted.")
                self.app.refresh_all_views()
        else:
            messagebox.showerror("Not Found", f"Player '{name}' not found.")

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
        self.app.refresh_all_views()

    def delete_last_match(self):
        season = db.get_current_season()
        if not season:
            messagebox.showerror("Error", "No active season found.")
            return
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the last recorded match? This action cannot be undone."):
            db.delete_last_match(season['id'])
            self.app.refresh_all_views()
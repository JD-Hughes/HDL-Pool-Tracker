import sqlite3
from datetime import datetime
import os

DB_FILE = "elo_tracker.db"
INITIAL_ELO = 1200

# --- Database Initialization ---

def init_db():
    """
    Initializes the database and creates tables if they don't exist.
    Creates a default season if no seasons are present.
    """
    if os.path.exists(DB_FILE):
        return # Assume it's already initialized

    print("First run: Creating new database...")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Seasons Table: Stores the name of each season
        cursor.execute("""
            CREATE TABLE seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)

        # Players Table: Stores permanent player info and current season stats
        cursor.execute("""
            CREATE TABLE players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                current_elo INTEGER NOT NULL,
                current_wins INTEGER NOT NULL,
                current_losses INTEGER NOT NULL,
                total_lifetime_games INTEGER NOT NULL
            )
        """)

        # Matches Table: A history of all games played across all seasons
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                player1_name TEXT NOT NULL,
                player2_name TEXT NOT NULL,
                winner_name TEXT NOT NULL,
                winner_elo_before INTEGER NOT NULL,
                winner_elo_after INTEGER NOT NULL,
                loser_elo_before INTEGER NOT NULL,
                loser_elo_after INTEGER NOT NULL,
                win_reason TEXT,
                FOREIGN KEY (season_id) REFERENCES seasons (id)
            )
        """)
        
        conn.commit()
        print("Database tables created.")

        # Create a default first season
        start_new_season(f"Season started {datetime.now().strftime('%Y-%m-%d')}")
        print("Default season created.")

    finally:
        conn.close()


def get_db_connection():
    """Returns a database connection object."""
    conn = sqlite3.connect(DB_FILE)
    # Allows accessing columns by name (e.g., row['name'])
    conn.row_factory = sqlite3.Row
    return conn

# --- Season Management ---

def start_new_season(name):
    """
    Creates a new season and resets all player stats for the new season.
    Lifetime games are preserved.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 1. Add the new season to the seasons table
        cursor.execute(
            "INSERT INTO seasons (name, created_at) VALUES (?, ?)",
            (name, datetime.now().isoformat())
        )
        print(f"Started new season: '{name}'")
        
        # 2. Reset stats for all existing players
        cursor.execute("""
            UPDATE players
            SET current_elo = ?,
                current_wins = 0,
                current_losses = 0
        """, (INITIAL_ELO,))
        
        conn.commit()
    finally:
        conn.close()

def get_seasons():
    """Returns a list of all seasons, most recent first."""
    conn = get_db_connection()
    try:
        seasons = conn.execute("SELECT * FROM seasons ORDER BY id DESC").fetchall()
        return [dict(s) for s in seasons]
    finally:
        conn.close()

def get_current_season():
    """Returns the most recent season record."""
    conn = get_db_connection()
    try:
        # The season with the highest ID is the current one
        season = conn.execute("SELECT * FROM seasons ORDER BY id DESC LIMIT 1").fetchone()
        return dict(season) if season else None
    finally:
        conn.close()

# --- Player Management ---

def get_leaderboard_players():
    """Returns a list of all players with their current season stats, sorted by Elo."""
    conn = get_db_connection()
    try:
        players = conn.execute("""
            SELECT name, current_elo, current_wins, current_losses 
            FROM players 
            ORDER BY current_elo DESC
        """).fetchall()
        return [dict(p) for p in players]
    finally:
        conn.close()

def get_all_player_names():
    """Returns a simple list of all player names."""
    conn = get_db_connection()
    try:
        names = conn.execute("SELECT name FROM players ORDER BY name").fetchall()
        return [row['name'] for row in names]
    finally:
        conn.close()

def get_player_by_name(name):
    """Fetches a single player's full record by name."""
    conn = get_db_connection()
    try:
        player = conn.execute("SELECT * FROM players WHERE name = ?", (name,)).fetchone()
        return dict(player) if player else None
    finally:
        conn.close()

def add_player(name):
    """Adds a new player to the database with initial stats."""
    if get_player_by_name(name):
        return # Player already exists

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO players (name, current_elo, current_wins, current_losses, total_lifetime_games)
            VALUES (?, ?, 0, 0, 0)
        """, (name, INITIAL_ELO))
        conn.commit()
    finally:
        conn.close()

def delete_player(name):
    """Deletes a player and all their associated matches from the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Delete matches involving the player
        cursor.execute("DELETE FROM matches WHERE player1_name = ? OR player2_name = ?", (name, name))
        # Delete the player record
        cursor.execute("DELETE FROM players WHERE name = ?", (name,))
        conn.commit()
    finally:
        conn.close()

# --- Match Management ---

def record_match(season_id, p1_name, p2_name, winner_name, elo_changes, win_reason):
    """
    Records a match and updates player stats in a single transaction.
    `elo_changes` is a dict with new Elo, wins, losses, and lifetime games for both players.
    """
    loser_name = p2_name if winner_name == p1_name else p1_name
    winner_data = elo_changes[winner_name]
    loser_data = elo_changes[loser_name]

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Use a transaction to ensure data integrity
        cursor.execute("BEGIN TRANSACTION")

        # 1. Insert the match record
        cursor.execute("""
            INSERT INTO matches (
                season_id, date, player1_name, player2_name, winner_name,
                winner_elo_before, winner_elo_after, loser_elo_before, loser_elo_after, win_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            season_id, datetime.now().isoformat(), p1_name, p2_name, winner_name,
            winner_data['elo_before'], winner_data['elo_after'],
            loser_data['elo_before'], loser_data['elo_after'],
            win_reason
        ))
        
        # 2. Update winner's stats
        cursor.execute("""
            UPDATE players SET current_elo = ?, current_wins = ?, total_lifetime_games = ?
            WHERE name = ?
        """, (
            winner_data['elo_after'], winner_data['wins_after'],
            winner_data['lifetime_games_after'], winner_name
        ))

        # 3. Update loser's stats
        cursor.execute("""
            UPDATE players SET current_elo = ?, current_losses = ?, total_lifetime_games = ?
            WHERE name = ?
        """, (
            loser_data['elo_after'], loser_data['losses_after'],
            loser_data['lifetime_games_after'], loser_name
        ))
        
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_matches_for_season(season_id):
    """Returns all match records for a specific season, oldest first."""
    conn = get_db_connection()
    try:
        matches = conn.execute(
            "SELECT * FROM matches WHERE season_id = ? ORDER BY date ASC",
            (season_id,)
        ).fetchall()
        return [dict(m) for m in matches]
    finally:
        conn.close()

def backup_database(backup_file):
    """Creates a backup copy of the current database."""
    # Check if backup directory exists
    backup_dir = os.path.dirname(backup_file)
    if backup_dir and not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    if os.path.exists(DB_FILE):
        import shutil
        shutil.copyfile(DB_FILE, backup_file)
        print(f"Database backed up to '{backup_file}'")
    else:
        print("No database file found to back up.")
    
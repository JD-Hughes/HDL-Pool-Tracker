import sqlite3
from datetime import datetime
import os
import shutil

DB_FILE = "elo_tracker.db"
INITIAL_ELO = 1200
DB_VERSION = 2

# --- Database Initialization ---

def init_db():
    """
    Initializes the database and creates tables if they don't exist.
    Creates a default season if no seasons are present.
    """
    if os.path.exists(DB_FILE):
        # Check database schema version
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM dbinfo WHERE key = 'version'")
            row = cursor.fetchone()
            if row:
                current_version = int(row['value'])
            else:
                current_version = 0
        except:
            current_version = 0 # dbinfo table doesn't exist
        finally:
            conn.close()
        if current_version != DB_VERSION:
            migrate_db(DB_FILE)
        return # Assume it's already initialized and up-to-date
    
    create_new_db()
    conn = get_db_connection()
    try:
        # Create a default first season
        start_new_season(f"Season started {datetime.now().strftime('%Y-%m-%d')}")
        print("Default season created.")

    finally:
        conn.close()

def create_new_db():
    print("First run: Creating new database...")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE dbinfo (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        cursor.execute("INSERT INTO dbinfo (key, value) VALUES (?, ?)", ("version", str(DB_VERSION)))
        
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
                total_lifetime_games INTEGER NOT NULL,
                archive BOOLEAN NOT NULL DEFAULT 0
            )
        """)

        # Matches Table: A history of all games played across all seasons
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                doubles_match BOOLEAN NOT NULL DEFAULT 0,
                player1_name TEXT NOT NULL,
                player1b_name TEXT,
                player2_name TEXT NOT NULL,
                player2b_name TEXT,
                player1_elo_before INTEGER NOT NULL,
                player1_elo_after INTEGER NOT NULL,
                player1b_elo_before INTEGER,
                player1b_elo_after INTEGER,
                player2_elo_before INTEGER NOT NULL,
                player2_elo_after INTEGER NOT NULL,
                player2b_elo_before INTEGER,
                player2b_elo_after INTEGER,
                winner INTEGER NOT NULL,
                FOREIGN KEY (season_id) REFERENCES seasons (id)
            )
        """)
        
        conn.commit()
        print("Database tables created.")
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
            WHERE archive = 0 
            ORDER BY current_elo DESC
        """).fetchall()
        return [dict(p) for p in players]
    finally:
        conn.close()

def get_all_player_names():
    """Returns a simple list of all player names."""
    conn = get_db_connection()
    try:
        names = conn.execute("SELECT name FROM players WHERE archive = 0 ORDER BY name").fetchall()
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

def archive_player(name):
    """Archives a player, preventing them from appearing in active lists."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Set the archive flag to true
        cursor.execute("UPDATE players SET archive = 1 WHERE name = ?", (name,))
        conn.commit()
    finally:
        conn.close()

# --- Match Management ---

def record_match(season_id, p1_name, p2_name, winner_int, elo_changes,
                 doubles_match=False, p1b_name=None, p2b_name=None,
                 p1b_elo_before=None, p1b_elo_after=None,
                 p2b_elo_before=None, p2b_elo_after=None):
    """
    Records a match and updates player stats in a single transaction.
    Supports new schema: winner_int (1 or 2), new ELO columns, doubles fields.
    """
    loser_name = p2_name if winner_int == 1 else p1_name
    winner_name = p1_name if winner_int == 1 else p2_name
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
                season_id, date, doubles_match,
                player1_name, player1b_name, player2_name, player2b_name,
                player1_elo_before, player1_elo_after, player1b_elo_before, player1b_elo_after,
                player2_elo_before, player2_elo_after, player2b_elo_before, player2b_elo_after,
                winner
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            season_id, datetime.now().isoformat(), int(doubles_match),
            p1_name, p1b_name, p2_name, p2b_name,
            winner_data['elo_before'] if winner_int == 1 else loser_data['elo_before'],
            winner_data['elo_after'] if winner_int == 1 else loser_data['elo_after'],
            p1b_elo_before, p1b_elo_after,
            loser_data['elo_before'] if winner_int == 1 else winner_data['elo_before'],
            loser_data['elo_after'] if winner_int == 1 else winner_data['elo_after'],
            p2b_elo_before, p2b_elo_after,
            winner_int
        ))

        # Update winner's stats
        cursor.execute("""
            UPDATE players SET current_elo = ?, current_wins = ?, total_lifetime_games = ?
            WHERE name = ?
        """, (
            winner_data['elo_after'], winner_data.get('wins_after', 0),
            winner_data.get('lifetime_games_after', 0), winner_name
        ))

        # Update loser's stats
        cursor.execute("""
            UPDATE players SET current_elo = ?, current_losses = ?, total_lifetime_games = ?
            WHERE name = ?
        """, (
            loser_data['elo_after'], loser_data.get('losses_after', 0),
            loser_data.get('lifetime_games_after', 0), loser_name
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


def backup_database(db_path=DB_FILE, backup_dir='backups', prefix=None):
    """
    Creates a backup of the database file.
    Args:
        db_path (str): Path to the database file.
        backup_dir (str): Directory to store backups. Defaults to 'backups'.
        prefix (str, optional): Prefix for backup filename. If None, uses 'backup-YYYYMMDD-HHMMSS'.
    Returns:
        str: The name of the backup file created, or None if failed.
    """
    try:
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        if prefix:
            backup_name = f"{prefix}-{timestamp}.db"
        else:
            backup_name = f"backup-{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_name)
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")
        return backup_name
    except Exception as e:
        print(f"Failed to backup database: {e}")
        return None

def get_last_backup_time(backup_dir='backups'):
    """
    Returns the datetime of the most recent backup file in the backup_dir, or None if none exist.
    """
    if not os.path.exists(backup_dir):
        return None
    files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
    if not files:
        return None
    # Extract timestamp from filename (assumes format: prefix-YYYYMMDD-HHMMSS.db or backup-YYYYMMDD-HHMMSS.db)
    times = []
    for fname in files:
        try:
            parts = fname.split('-')
            if len(parts) >= 3:
                # e.g. backup-20251005-153000.db or customprefix-20251005-153000.db
                date_str = parts[-2] + '-' + parts[-1].split('.')[0] # YYYYMMDD-HHMMSS
                dt = datetime.strptime(date_str, '%Y%m%d-%H%M%S')
                times.append(dt)
        except Exception:
            continue
    return max(times) if times else None


# --- Database Migration Manager ---
# This function handles migrating the database schema and data from an old version to the current version.
# It creates a backup before attempting migration, and rolls back if anything goes wrong.
# Starting from the old version it finds in the dbinfo table, it applies each migration function in sequence until reaching the current version.

def migrate_db(db_path):
    # Make a copy of the existing database before migration
    rollback_db = backup_database(db_path, backup_dir='backups', prefix='migration')
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Determine current version and handle non-existent dbinfo table
            try:
                cursor.execute("SELECT value FROM dbinfo WHERE key = 'version'") # This will fail if dbinfo doesn't exist
                row = cursor.fetchone()
                current_version = int(row['value'])
            except:
                current_version = 0 # dbinfo table doesn't exist, so version is 0  
            print(f"Current DB version: {current_version}, Target version: {DB_VERSION}")
            if current_version >= DB_VERSION:
                print("Database is already up-to-date.")
                return
            # Import migration functions
            import helper_scripts.db_migration_rules as migration_rules
            # Apply migrations in sequence
            for version in range(current_version, DB_VERSION):
                next_version = version + 1
                migrate_func_name = f"migrate_v{version}_to_v{next_version}"
                migrate_func = getattr(migration_rules, migrate_func_name, None)
                if migrate_func:
                    print(f"Migrating from v{version} to v{next_version}...")
                    migrate_func(conn)
                    # Update the version in dbinfo table
                    cursor.execute("INSERT OR REPLACE INTO dbinfo (key, value) VALUES ('version', ?)", (str(next_version),))
                    conn.commit()
                    print(f"Migration to v{next_version} completed.")
                else:
                    raise Exception(f"No migration function found for v{version} to v{next_version}")
            print("Database migration completed.")
        except Exception as e:
            raise e
        finally:
            conn.close()
    except Exception as e:
        print(f"Database migration failed: {e}")
        # If migration fails, restore from backup (rollback_db)
        os.remove(db_path)
        if rollback_db:
            shutil.copy2(os.path.join('backups', rollback_db), db_path)
            print("Database restored from backup.")
        else:
            print("No backup available to restore automatically. Check backup directory.")
        raise

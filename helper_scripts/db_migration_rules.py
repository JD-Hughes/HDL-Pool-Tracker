# Each function in this file handles migration from one specific version to the next.
# They should be called in sequence to upgrade from an old version to the latest.
# Each function receives a database connection object and performs the necessary schema changes and data transformations.

def migrate_v0_to_v1(dbconn):
    #Updates:
    # - Create dbinfo table to track schema version
    # - Set initial version to 1
    cursor = dbconn.cursor()
    # Create dbinfo table to track schema version
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dbinfo (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    # Set initial version to 1
    cursor.execute("INSERT OR REPLACE INTO dbinfo (key, value) VALUES ('db_version', '1');")
    dbconn.commit()

def migrate_v1_to_v2(dbconn):
    # Updates:
    # - Add columns to matches table for doubles matches and ELO tracking
    # - Update existing records to set doubles_match to 0 (false)
    # - Transfer existing ELO data to new columns if applicable
    # - Remove old ELO columns and win_reason column
    # - Replaced winner_name with winner column which represents the team (player1 or player2)
    # - Update db_version to 2

    cursor = dbconn.cursor()

    # Add doubles_match column to matches table
    cursor.execute("ALTER TABLE matches ADD COLUMN doubles_match BOOLEAN NOT NULL DEFAULT 0;")
    # Update existing records to set doubles_match to 0 (false)
    cursor.execute("UPDATE matches SET doubles_match = 0 WHERE doubles_match IS NULL;")
    # Add B PLayer Names
    cursor.execute("ALTER TABLE matches ADD COLUMN player1b_name TEXT;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player2b_name TEXT;")
    # Add ELO tracking columns for each player, with defaults for singles players that will be updated below
    cursor.execute("ALTER TABLE matches ADD COLUMN player1_elo_before INTEGER NOT NULL DEFAULT -1;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player1_elo_after INTEGER NOT NULL DEFAULT -1;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player1b_elo_before INTEGER;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player1b_elo_after INTEGER;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player2_elo_before INTEGER NOT NULL DEFAULT -1;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player2_elo_after INTEGER NOT NULL DEFAULT -1;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player2b_elo_before INTEGER;")
    cursor.execute("ALTER TABLE matches ADD COLUMN player2b_elo_after INTEGER;")

    # Add winner column to represent the winning team (player1 or player2)
    cursor.execute("ALTER TABLE matches ADD COLUMN winner INTEGER NOT NULL DEFAULT -1;")

    # Transfer existing ELO data to new columns and replace those -1 defaults
    cursor.execute("SELECT id, player1_name, player2_name, winner_name, winner_elo_before, winner_elo_after, loser_elo_before, loser_elo_after FROM matches;")
    matches = cursor.fetchall()
    for match in matches:
        match_id, p1_name, p2_name, winner_name, winner_elo_before, winner_elo_after, loser_elo_before, loser_elo_after = match
        if p1_name == winner_name:
            p1_elo_before = winner_elo_before
            p1_elo_after = winner_elo_after
            p2_elo_before = loser_elo_before
            p2_elo_after = loser_elo_after
            winner = 1
        else:
            p1_elo_before = loser_elo_before
            p1_elo_after = loser_elo_after
            p2_elo_before = winner_elo_before
            p2_elo_after = winner_elo_after
            winner = 2
        cursor.execute("""
            UPDATE matches SET 
                player1_elo_before = ?, player1_elo_after = ?,
                player2_elo_before = ?, player2_elo_after = ?, winner = ?
            WHERE id = ?;
        """, (p1_elo_before, p1_elo_after, p2_elo_before, p2_elo_after, winner, match_id))

    dbconn.commit()

    # Remove old ELO columns, win_reason and winner_name column
    cursor.execute("PRAGMA foreign_keys=off;")
    cursor.execute("BEGIN TRANSACTION;")
    cursor.execute("""
        CREATE TABLE matches_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            doubles_match BOOLEAN NOT NULL DEFAULT 0,
            player1_name TEXT NOT NULL,
            player1_elo_before INTEGER NOT NULL,
            player1_elo_after INTEGER NOT NULL,
            player1b_name TEXT,
            player1b_elo_before INTEGER,
            player1b_elo_after INTEGER,
            player2_name TEXT NOT NULL,
            player2_elo_before INTEGER NOT NULL,
            player2_elo_after INTEGER NOT NULL,
            player2b_name TEXT,
            player2b_elo_before INTEGER,
            player2b_elo_after INTEGER,
            winner INTEGER NOT NULL,
            FOREIGN KEY (season_id) REFERENCES seasons (id)
        );
    """)
    cursor.execute("""
        INSERT INTO matches_new (
            id, season_id, date, player1_name, player1_elo_before, player1_elo_after,
            player1b_name, player1b_elo_before, player1b_elo_after,
            player2_name, player2_elo_before, player2_elo_after,
            player2b_name, player2b_elo_before, player2b_elo_after,
            doubles_match, winner
        )
        SELECT
            id, season_id, date, player1_name, player1_elo_before, player1_elo_after,
            player1b_name, player1b_elo_before, player1b_elo_after,
            player2_name, player2_elo_before, player2_elo_after,
            player2b_name, player2b_elo_before, player2b_elo_after,
            doubles_match, winner
        FROM matches;
    """)
    cursor.execute("DROP TABLE matches;")
    cursor.execute("ALTER TABLE matches_new RENAME TO matches;")
    cursor.execute("COMMIT;")
    cursor.execute("PRAGMA foreign_keys=on;")

    # Update db_version to 2
    cursor.execute("UPDATE dbinfo SET value = '2' WHERE key = 'db_version';")
    dbconn.commit()
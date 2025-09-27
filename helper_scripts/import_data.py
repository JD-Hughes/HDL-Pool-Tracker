import pandas as pd
import sqlite3
import os

# --- Configuration ---
CSV_FILE = 'history.csv'  # Replace with your actual CSV file name
DB_NAME = 'elo_tracker.db'
TABLE_NAME = 'matches'
DEFAULT_SEASON_ID = 1
DEFAULT_WIN_REASON = ''

# --- Database Schema and Setup ---

def setup_database(db_name, table_name):
    """
    Sets up the SQLite database and creates the 'matches' table
    if it doesn't already exist.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # NOTE: The 'seasons' table is assumed to exist for the FOREIGN KEY to be strictly valid.
    # For this script's purpose, we'll only create the 'matches' table.
    # If the 'seasons' table doesn't exist, the FOREIGN KEY will be ignored 
    # unless PRAGMA foreign_keys = ON is set.
    
    # Create the 'matches' table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
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
    conn.close()
    print(f"Database '{db_name}' and table '{table_name}' ensured.")

# --- Data Import Function ---

def import_csv_to_sqlite(csv_file, db_name, table_name, season_id, win_reason):
    """
    Reads data from the CSV, transforms it, and imports it into the SQLite table.
    """
    if not os.path.exists(csv_file):
        print(f"ERROR: CSV file not found at '{csv_file}'")
        return

    try:
        # 1. Read the CSV file into a pandas DataFrame
        df = pd.read_csv(csv_file)
        print(f"Successfully read {len(df)} rows from '{csv_file}'.")

        # 2. Rename columns to match the database schema if needed (based on the provided headings)
        # Note: The CSV headings provided are a close match, but we'll map them explicitly
        # to ensure the DataFrame columns match the final DB columns needed.
        df = df.rename(columns={
            'Date': 'date',
            'Player1': 'player1_name',
            'Player2': 'player2_name',
            'Winner': 'winner_name',
            'Winner_Elo_Before': 'winner_elo_before',
            'Winner_Elo_After': 'winner_elo_after',
            'Loser_Elo_Before': 'loser_elo_before',
            'Loser_Elo_After': 'loser_elo_after'
        })
        
        # 3. Add the required constant columns
        df['season_id'] = season_id
        df['win_reason'] = win_reason

        # 4. Select and reorder columns to exactly match the target table structure 
        # (excluding the auto-increment 'id' column)
        db_columns = [
            'season_id', 'date', 'player1_name', 'player2_name', 'winner_name',
            'winner_elo_before', 'winner_elo_after', 'loser_elo_before', 
            'loser_elo_after', 'win_reason'
        ]
        df_final = df[db_columns]

        # 5. Connect to the database and import the data
        conn = sqlite3.connect(db_name)
        
        # Write the data to the SQLite table
        # 'if_exists='append'' adds new rows; 'index=False' prevents writing DataFrame index as a column
        df_final.to_sql(table_name, conn, if_exists='append', index=False)
        
        conn.close()
        
        print(f"\n✅ Data import successful! {len(df_final)} records inserted into table '{table_name}'.")

    except Exception as e:
        print(f"\n❌ An error occurred during import: {e}")

# --- Main Execution Block ---

if __name__ == "__main__":
    
    # ⚠️ BEFORE RUNNING:
    # 1. Make sure you have pandas installed: pip install pandas
    # 2. Save your CSV data into a file named 'data.csv' in the same directory.
    
    print("--- Starting CSV to SQLite Import ---")
    setup_database(DB_NAME, TABLE_NAME)
    import_csv_to_sqlite(CSV_FILE, DB_NAME, TABLE_NAME, DEFAULT_SEASON_ID, DEFAULT_WIN_REASON)
    print("--- Script Finished ---")
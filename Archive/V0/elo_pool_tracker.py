import pandas as pd
import os
import matplotlib.pyplot as plt

from datetime import datetime

PLAYER_FILE = "players.csv"
HISTORY_FILE = "history.csv"
INITIAL_ELO = 1200
K_FACTOR = 32

def load_players():
    if os.path.exists(PLAYER_FILE):
        return pd.read_csv(PLAYER_FILE)
    else:
        return pd.DataFrame(columns=["Name", "Elo", "Wins", "Losses"])

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    else:
        return pd.DataFrame(columns=[
            "Date", "Player1", "Player2", "Winner",
            "Winner_Elo_Before", "Winner_Elo_After",
            "Loser_Elo_Before", "Loser_Elo_After"
        ])

def save_players(df):
    df.to_csv(PLAYER_FILE, index=False)

def save_history(df):
    df.to_csv(HISTORY_FILE, index=False)

def expected_score(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))

def update_elo(winner_elo, loser_elo):
    expected_win = expected_score(winner_elo, loser_elo)
    expected_lose = expected_score(loser_elo, winner_elo)
    winner_elo += K_FACTOR * (1 - expected_win)
    loser_elo += K_FACTOR * (0 - expected_lose)
    return round(winner_elo), round(loser_elo)

def ensure_player(players, name):
    if name not in players["Name"].values:
        new_row = pd.DataFrame([[name, INITIAL_ELO, 0, 0]], columns=["Name", "Elo", "Wins", "Losses"])
        players = pd.concat([players, new_row], ignore_index=True)
    return players

def select_player(players, prompt, exclude_idx=None):
    while True:
        print(f"\n{prompt}")
        for i, name in enumerate(players["Name"]):
            if i != exclude_idx:
                print(f"{i + 1}. {name}")
        print("0. Add a new player")
        print("C. Cancel and return to main menu")

        choice = input("Enter number: ").strip().lower()

        if choice == "c":
            return players, None
        elif choice == "0":
            new_name = input("Enter new player name: ").strip()
            if new_name:
                players = ensure_player(players, new_name)
                save_players(players)
                return players, players[players["Name"] == new_name].index[0]
            else:
                print("Name cannot be empty.")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(players) and idx != exclude_idx:
                    return players, idx
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number or 'C' to cancel.")

def record_match(players, history):
    if len(players) < 2:
        print("\nNot enough players. Let's add some.")
        while len(players) < 2:
            new_name = input("Enter a player name to add (or leave empty to stop): ").strip()
            if new_name:
                players = ensure_player(players, new_name)
                save_players(players)
            else:
                print("You need at least 2 players.")
        print()

    players, idx1 = select_player(players, "Select Player 1")
    if idx1 is None:
        print("Cancelled. Returning to main menu.")
        return players, history

    players, idx2 = select_player(players, "Select Player 2", exclude_idx=idx1)
    if idx2 is None:
        print("Cancelled. Returning to main menu.")
        return players, history

    player1 = players.at[idx1, "Name"]
    player2 = players.at[idx2, "Name"]

    while True:
        print(f"\nWho won?")
        print(f"1. {player1}")
        print(f"2. {player2}")
        print("C. Cancel and return to main menu")
        win_choice = input("Enter number: ").strip().lower()
        if win_choice == "1":
            winner, loser = player1, player2
            break
        elif win_choice == "2":
            winner, loser = player2, player1
            break
        elif win_choice == "c":
            print("Cancelled. Returning to main menu.")
            return players, history
        else:
            print("Invalid choice. Enter 1, 2, or 'C' to cancel.")

    winner_elo = players.loc[players["Name"] == winner, "Elo"].values[0]
    loser_elo = players.loc[players["Name"] == loser, "Elo"].values[0]
    new_winner_elo, new_loser_elo = update_elo(winner_elo, loser_elo)

    winner_gain = new_winner_elo - winner_elo
    loser_loss = new_loser_elo - loser_elo

    # Update Elo and stats
    players.loc[players["Name"] == winner, "Elo"] = new_winner_elo
    players.loc[players["Name"] == loser, "Elo"] = new_loser_elo
    players.loc[players["Name"] == winner, "Wins"] += 1
    players.loc[players["Name"] == loser, "Losses"] += 1

    match = pd.DataFrame([[
        datetime.now().isoformat(), player1, player2, winner,
        winner_elo, new_winner_elo, loser_elo, new_loser_elo
    ]], columns=[
        "Date", "Player1", "Player2", "Winner",
        "Winner_Elo_Before", "Winner_Elo_After",
        "Loser_Elo_Before", "Loser_Elo_After"
    ])

    history = pd.concat([history, match], ignore_index=True)

    save_players(players)
    save_history(history)

    print(f"\nMatch recorded. {winner} won!")
    print(f"{winner}: +{winner_gain} → {new_winner_elo}")
    print(f"{loser}: {loser_loss} → {new_loser_elo}")

    return players, history

def show_leaderboard(players):
    if players.empty:
        print("No players yet.")
    else:
        print("\nLeaderboard:")
        print(players.sort_values(by="Elo", ascending=False).to_string(index=False))

def show_history(history):
    if history.empty:
        print("No games recorded yet.")
        return

    print("\nMatch History:")
    for _, row in history.iterrows():
        dt = datetime.fromisoformat(row["Date"])
        timestamp = dt.strftime("%Y-%m-%d %H:%M")

        p1 = row["Player1"]
        p2 = row["Player2"]
        winner = row["Winner"]
        loser = p2 if winner == p1 else p1

        winner_change = row["Winner_Elo_After"] - row["Winner_Elo_Before"]
        loser_change = row["Loser_Elo_After"] - row["Loser_Elo_Before"]

        winner_str = f"+{winner_change} → {row['Winner_Elo_After']}"
        loser_str = f"{loser_change} → {row['Loser_Elo_After']}"

        print(f"{timestamp} | {winner} def. {loser} | {winner_str} / {loser_str}")


def plot_elo_graph(history):
    if history.empty:
        print("No matches to plot.")
        return

    history = history.copy()
    all_players = set(history["Player1"]) | set(history["Player2"])
    elo_data = {name: [] for name in all_players}

    timestamps = []

    for _, row in history.iterrows():
        timestamps.append(row["Date"])
        for player in all_players:
            if player == row["Player1"]:
                elo_data[player].append(row["Winner_Elo_After"] if player == row["Winner"] else row["Loser_Elo_After"])
            elif player == row["Player2"]:
                elo_data[player].append(row["Winner_Elo_After"] if player == row["Winner"] else row["Loser_Elo_After"])
            else:
                # Repeat last Elo or assume initial
                if elo_data[player]:
                    elo_data[player].append(elo_data[player][-1])
                else:
                    elo_data[player].append(INITIAL_ELO)

    timestamps = [datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M") for ts in timestamps]

    plt.figure(figsize=(10, 6))
    for player, elos in elo_data.items():
        plt.plot(timestamps, elos, label=player)
    plt.title("Elo Ratings Over Time")
    plt.xlabel("Date & Time")
    plt.ylabel("Elo Rating")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    players = load_players()
    history = load_history()

    while True:
        print("\n=== Pool Elo Tracker ===")
        print("1. Record a Match")
        print("2. View Leaderboard")
        print("3. View Match History")
        print("4. View Elo Graphs")
        print("5. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            players, history = record_match(players, history)
        elif choice == "2":
            show_leaderboard(players)
        elif choice == "3":
            show_history(history)
        elif choice == "4":
            plot_elo_graph(history)
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()

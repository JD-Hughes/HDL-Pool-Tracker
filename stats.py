import database as db
import matplotlib.pyplot as plt
import numpy as np
import matplotlib

def show_heatmap(season_id=None):
    # Get current season ID
    if season_id is None:
        season_id = db.get_current_season()['id']
    # Fetch players
    players = db.get_all_player_names(season_id)
    # Create a grid with player names along the top and left using matplotlib
    # Calculate win rates between players
    heatmap_data = np.zeros((len(players), len(players)))
    for i, player_a in enumerate(players):
        for j, player_b in enumerate(players):
            if i == j:
                heatmap_data[i][j] = 0
                continue
            wins_a = db.get_head_to_head_wins(player_a, player_b, season_id)
            wins_b = db.get_head_to_head_wins(player_b, player_a, season_id)
            total_matches = wins_a + wins_b
            if total_matches > 0:
                win_rate = wins_a / total_matches
            else:
                win_rate = 0
            heatmap_data[i][j] = win_rate * 100  # Convert to percentage

    fig, ax = plt.subplots()

    im, cbar = heatmap(heatmap_data, players, players, ax=ax,
                    cmap="YlGn", cbarlabel="Win Percentage", title="Player Win Rate Percentage (Left player vs Top Player)")
    texts = annotate_heatmap(im, valfmt="{x:.1f}%")

    fig.tight_layout()
    plt.show()

def show_matchup_heatmap(season_id=None):
    if season_id is None:
        current_season = db.get_current_season()
        if not current_season:
            return
        season_id = current_season['id']

    matches = db.get_matches_for_season(season_id)
    if not matches:
        return

    players = sorted({
        name
        for match in matches
        for name in (
            match.get('player1_name'),
            match.get('player1b_name'),
            match.get('player2_name'),
            match.get('player2b_name'),
        )
        if name
    })
    if not players:
        return

    player_index = {name: i for i, name in enumerate(players)}
    matchup_counts = np.zeros((len(players), len(players)), dtype=float)

    for match in matches:
        team_a = [match['player1_name']]
        if match.get('player1b_name'):
            team_a.append(match['player1b_name'])
        team_b = [match['player2_name']]
        if match.get('player2b_name'):
            team_b.append(match['player2b_name'])

        for player_a in team_a:
            for player_b in team_b:
                index_a = player_index[player_a]
                index_b = player_index[player_b]
                matchup_counts[index_a][index_b] += 1
                matchup_counts[index_b][index_a] += 1

    row_totals = matchup_counts.sum(axis=1)
    normalized = np.zeros_like(matchup_counts)
    for i, total in enumerate(row_totals):
        if total > 0:
            normalized[i, :] = matchup_counts[i, :] / total

    fig, ax = plt.subplots()
    im, cbar = heatmap(
        normalized * 100,
        players,
        players,
        ax=ax,
        cmap="YlOrRd",
        cbarlabel="Share of Games",
        title="Opponent Matchup Share (Row player vs Column player)"
    )
    texts = annotate_heatmap_with_counts(im, matchup_counts.astype(int), valfmt="{x:.1f}%")

    fig.tight_layout()
    plt.show()

def show_combined_heatmaps(season_id=None):
    if season_id is None:
        current_season = db.get_current_season()
        if not current_season:
            return
        season_id = current_season['id']

    matches = db.get_matches_for_season(season_id)
    if not matches:
        return

    players = sorted({
        name
        for match in matches
        for name in (
            match.get('player1_name'),
            match.get('player1b_name'),
            match.get('player2_name'),
            match.get('player2b_name'),
        )
        if name
    })
    if not players:
        return

    player_index = {name: i for i, name in enumerate(players)}

    matchup_counts = np.zeros((len(players), len(players)), dtype=float)
    for match in matches:
        team_a = [match['player1_name']]
        if match.get('player1b_name'):
            team_a.append(match['player1b_name'])
        team_b = [match['player2_name']]
        if match.get('player2b_name'):
            team_b.append(match['player2b_name'])

        for player_a in team_a:
            for player_b in team_b:
                index_a = player_index[player_a]
                index_b = player_index[player_b]
                matchup_counts[index_a][index_b] += 1
                matchup_counts[index_b][index_a] += 1

    row_totals = matchup_counts.sum(axis=1)
    matchup_share = np.zeros_like(matchup_counts)
    for i, total in enumerate(row_totals):
        if total > 0:
            matchup_share[i, :] = matchup_counts[i, :] / total

    win_rates = np.zeros((len(players), len(players)), dtype=float)
    win_counts = np.zeros((len(players), len(players)), dtype=int)
    for i, player_a in enumerate(players):
        for j, player_b in enumerate(players):
            if i == j:
                continue
            wins_a = db.get_head_to_head_wins(player_a, player_b, season_id)
            wins_b = db.get_head_to_head_wins(player_b, player_a, season_id)
            total_matches = wins_a + wins_b
            win_counts[i][j] = total_matches
            if total_matches > 0:
                win_rates[i][j] = (wins_a / total_matches) * 100

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(12, 5))

    im_left, cbar_left = heatmap(
        matchup_share * 100,
        players,
        players,
        ax=ax_left,
        cmap="YlOrRd",
        cbarlabel="Share of Games",
        title="Opponent Matchup Share (Row vs Column)"
    )
    annotate_heatmap_with_counts(im_left, matchup_counts.astype(int), valfmt="{x:.1f}%")

    im_right, cbar_right = heatmap(
        win_rates,
        players,
        players,
        ax=ax_right,
        cmap="YlGn",
        cbarlabel="Win Percentage",
        title="Player Win % (Row vs Column)"
    )
    annotate_heatmap_with_counts(im_right, win_counts, valfmt="{x:.1f}%")

    fig.tight_layout()
    plt.show()

# The following is taken from the Matplotlib documentation with minor modifications
# https://matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html

def heatmap(data, row_labels, col_labels, ax=None,
            cbar_kw=None, cbarlabel="", title="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (M, N).
    row_labels
        A list or array of length M with the labels for the rows.
    col_labels
        A list or array of length N with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current Axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if ax is None:
        ax = plt.gca()

    if cbar_kw is None:
        cbar_kw = {}

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # Show all ticks and label them with the respective list entries.
    ax.set_xticks(range(data.shape[1]), labels=col_labels,
                  rotation=-30, ha="right", rotation_mode="anchor")
    ax.set_yticks(range(data.shape[0]), labels=row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False)

    # Show the title
    ax.set_title(title)

    # Turn spines off and create white grid.
    ax.spines[:].set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar

def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
                     textcolors=("black", "white"),
                     threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        `matplotlib.ticker.Formatter`.  Optional.
    textcolors
        A pair of colors.  The first is used for values below a threshold,
        the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to `text` used to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a `Text` for each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts

def annotate_heatmap_with_counts(im, counts, data=None, valfmt="{x:.2f}",
                                 textcolors=("black", "white"),
                                 threshold=None, **textkw):
    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            count = counts[i][j] if counts is not None else 0
            label = f"{valfmt(data[i, j], None)}\n({count})"
            text = im.axes.text(j, i, label, **kw)
            texts.append(text)

    return texts

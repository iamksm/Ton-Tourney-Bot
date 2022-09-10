import json


def pull_results():
    # Pull data from JSON
    with open("results.json", "r") as results:
        new_results = json.load(results)

    # Populate leaderboard
    with open("leaderboard.json", "r+") as leaderboard:
        old_results = json.load(leaderboard)
        for match in new_results:
            results_ = match["player_results"]
            for player in results_:
                player_name = player["playerName"]
                try:
                    old_results[player_name] += player["kills"]
                except KeyError:
                    old_results[player_name] = player["kills"]

    with open("final_file.json", "w") as final_results:
        final_results.seek(0)
        json.dump(old_results, final_results, indent=4)


pull_results()

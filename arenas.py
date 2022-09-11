import json
import os

import requests

from utils import add_token, clear_tokens, show_tokens


class Arenas:

    def __init__(self, token=None) -> None:
        self.apex_endpoint = f"https://r5-crossplay.r5prod.stryder.respawn.com/privatematch/?token={token}"
        self.tokens_file = "arenas_tokens.txt"

        if not os.path.isfile("results.json"):
            open("results.json", "w").close()

        if not os.path.isfile("arenas_roster.json"):
            open("arenas_roster.json", "w").close()

        if not os.path.isfile(self.tokens_file):
            open(self.tokens_file, "w").close()

        if not os.path.isfile("arenas_leaderboard.json"):
            open("arenas_leaderboard.json", "w").close()

        if not os.path.isfile("arenas_raw_results.json"):
            open("arenas_raw_results.json", "w")

        with open("results.json", "r+") as file:
            self.results = json.load(file)

        with open("arenas_roster.json", "r") as roster:
            try:
                self.teams = json.load(roster)
            except json.decoder.JSONDecodeError:
                self.teams = {}

        with open(self.tokens_file, "r+") as file:
            self.tokens = set(file.readlines())
            file.seek(0)
            file.truncate()
            file.writelines(self.tokens)

    def leaderboard(self):
        try:
            with open("arenas_leaderboard.json", "r+") as file:
                standings = json.load(file)
                standings = dict(
                    sorted(standings.items(), key=lambda x: x[1], reverse=True)
                )
                return standings
        except json.decoder.JSONDecodeError:
            return "The leaderboard is currently empty"

    def populate_leader_board(self):
        leaders = {}
        results_fetched = self.populate_results_json()

        if not results_fetched:
            return

        with open("arenas_raw_results.json", "r") as file:
            matches = json.load(file)

        for match in matches:
            for player in match["player_results"]:
                team_name = player["teamName"]
                kills = player["kills"]

                if leaders.get(team_name):
                    leaders[team_name] += kills
                    continue

                leaders[team_name] = kills

        with open("arenas_leaderboard.json", "r+") as file:
            try:
                results = json.load(file)
                results.update(leaders)
                results = dict(
                    sorted(results.items(), key=lambda x: x[1], reverse=True)
                )
                file.seek(0)
                json.dump(results, file, indent=4)
            except json.decoder.JSONDecodeError:
                file.seek(0)
                leaders = dict(
                    sorted(leaders.items(), key=lambda x: x[1], reverse=True)
                )
                json.dump(leaders, file, indent=4)

    def list_tokens(self):
        with open(self.tokens_file, "r") as file:
            arenas_tokens = set(file.readlines())

        return show_tokens(arenas_tokens)

    def add_token(self, token):
        with open(self.tokens_file) as f:
            self.tokens = set(f.readlines())

        return add_token(token, self.tokens, self.tokens_file)

    def register_team(self, leader, team_name):
        if team_name in self.teams.values() and leader not in self.teams.keys():
            return "Sorry, that team name has already been used"

        operation = "r+" if self.teams.keys() else "w"
        self.teams[leader] = team_name

        with open("arenas_roster.json", operation) as file:
            if operation == "w":
                json.dump(self.teams, file, indent=4)
            roster = json.load(file)
            roster.update(self.teams)
            file.seek(0)
            json.dump(roster, file, indent=4)

    def remove_team(self, leader=None, team_name=None):
        if leader and leader in self.teams.keys():
            team = {leader: self.teams[leader]}
            del self.teams[leader]
            return f"Successfully deleted team {team[leader]}"

        if team_name and team_name in self.teams.keys():
            for player, team in self.teams.items():
                if team == team_name:
                    del self.teams[player]
                    return f"Successfully removed team {team}"

        if not (team_name and player):
            return "Please input a team name or player name to remove from roster"

        return "The team or player you entered does not exist in our database"

    def add_team(self, leader, team_name):
        self.register_team(leader, team_name)

    def list_teams(self):
        return " ".join(self.teams.values())

    def populate_results_json(self):
        with open("arenas_tokens.txt", "r") as file:
            self.tokens = file.readlines()

        results = []
        for token in self.tokens:
            endpoint = self.apex_endpoint.format(token.strip())
            response = requests.get(endpoint)

            if response.status_code != requests.codes.ok:
                continue

            results = results + list(response.json().get("matches"))

        if len(results) == 0:
            return False

        with open("arenas_raw_results.json", "w") as file:
            file.seek(0)
            file.truncate()
            json.dump(results, file, indent=4)
            return True

    def clear_tokens(self):
        return clear_tokens(self.tokens_file.format("Arenas"))

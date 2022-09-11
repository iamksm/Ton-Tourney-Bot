import json
from datetime import datetime

import pandas

from utils import clear_tokens, local_datetime, add_token, show_tokens


class KillsRace:

    def __init__(self) -> None:
        with open("kills_race_leaderboard.json", "r") as file:
            try:
                self.leadeboard = json.load(file)
            except json.decoder.JSONDecodeError:
                self.leadeboard = {}

        self.tokens_file = "kills_race_tokens.txt"
        with open(self.tokens_file, "r") as file:
            self.kills_race_tokens = set(file.readlines())
            

    def prepare_player_match_kill_details(match):
        player_results = match["player_results"]
        time_started = datetime.fromtimestamp(match["match_start"])
        time_started = local_datetime(time_started)
        positions = []
        player_names = []
        player_kills = []
        player_assists = []
        player_damage = []
        for player in player_results:
            positions.append(player["teamPlacement"])
            player_names.append(player["playerName"])
            player_kills.append(player["kills"])
            player_assists.append(player["assists"])
            player_damage.append(player["damageDealt"])

        df = pandas.DataFrame.from_dict(
            {
                "Team Position": positions,
                "Player Name": player_names,
                "Player Kills": player_kills,
                "Player Assists": player_assists,
                "Player Damage": player_damage,
            }
        )
        return df, time_started

    def populate_kills_leaderboard(self, match):
        player_results = match["player_results"]

        for player in player_results:
            player_name = player["playerName"]
            try:
                self.leaderboard[player_name] += player["kills"]
            except KeyError:
                self.leaderboard[player_name] = player["kills"]

        return self.leaderboard

    def eleaderboard(self):
        """To be used by casters to generate excel"""
        with open("leaderboard.json", "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
                df = pandas.DataFrame.from_dict(
                    {"Names": data.keys(), "Kills": data.values()}
                )
            except Exception as e:
                return False, e

        today = local_datetime(datetime.today())
        today = today.strftime("%d-%m-%Y %H:%M:%S")
        file_name = f"/tmp/leaderboard-{today}.xlsx"
        writer = pandas.ExcelWriter(file_name)

        df.sort_values("Kills", ascending=False, inplace=True)
        print(df)
        df.to_excel(writer, index=False, sheet_name="Sheet1")

        # Auto resize columns
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets["Sheet1"].set_column(col_idx, col_idx, column_length)
        writer.save()

        return True, file_name

    def add_token(self, token):
        with open(self.tokens_file) as f:
            self.kills_race_tokens = set(f.readlines())

        return add_token(token, self.kills_race_tokens, self.tokens_file)

    def list_tokens(self):
        with open(self.tokens_file) as f:
            self.kills_race_tokens = set(f.readlines())

        return show_tokens(self.kills_race_tokens)

    def clear_tokens(self):
        return clear_tokens(self.tokens_file.format("Kills race"))
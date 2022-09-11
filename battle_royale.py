import json
import os
import requests
from datetime import datetime

import pandas

from utils import clear_tokens, local_datetime, add_token, show_tokens



class BattleRoyale:

    def __init__(self) -> None:
        self.APEX_ENDPOINT = "https://r5-crossplay.r5prod.stryder.respawn.com/privatematch/?token={}"
        self.tokens_file = "battle_royale_tokens.txt"
        with open("battle_royale_leaderboard.json", "r") as file:
            try:
                self.leadeboard = json.load(file)
            except json.decoder.JSONDecodeError:
                self.leadeboard = {}

        with open(self.tokens_file, "r") as file:
            self.battle_royale_tokens = set(file.readlines())

    def prepare_match_details(match):
        player_results = match["player_results"]
        time_started = datetime.fromtimestamp(match["match_start"])
        time_started = local_datetime(time_started)
        positions = []
        team_names = []
        player_names = []
        player_kills = []
        player_assists = []
        player_damage = []
        for player in player_results:
            positions.append(player["teamPlacement"])
            team_names.append(player["teamName"])
            player_names.append(player["playerName"])
            player_kills.append(player["kills"])
            player_assists.append(player["assists"])
            player_damage.append(player["damageDealt"])
        df = pandas.DataFrame.from_dict(
            {
                "Team Position": positions,
                "Team Name": team_names,
                "Player Name": player_names,
                "Player Kills": player_kills,
                "Player Assists": player_assists,
                "Player Damage": player_damage,
            }
        )
        return df, time_started

    def results(self, ctx, token, match_no):        
        # only admins can run this
        if not token:
            return
        response = requests.get(self.APEX_ENDPOINT.format(token))
        if response.status_code != requests.codes.ok:
            return
        matches = response.json().get("matches")
        if not matches:
            return
        matches.reverse()
        match_count = 0
        for match in matches:
            match_data, time_started = self.prepare_match_details(match)
            file_name = f"/tmp/Match-{match_count +  1}-{time_started.date()}.xlsx"
            match_data.sort_values("Team Position", ascending=True, inplace=True)
            match_data.to_excel(file_name, index=False)
            if not match_no:
                yield file_name
                os.remove(file_name)
                match_count += 1
                continue

            if match_no and int(match_no) - 1 == match_count:
                yield file_name
                os.remove(file_name)
                break
            match_count += 1

    def add_token(self, token):
        with open(self.tokens_file, "r") as file:
            self.battle_royale_tokens = file.readlines()

        return add_token(token, self.battle_royale_tokens, self.tokens_file)

    def list_tokens(self):
        with open(self.tokens_file, "r") as file:
            self.battle_royale_tokens = set(file.readlines())

        return show_tokens(self.battle_royale_tokens)

    def clear_tokens(self):
        return clear_tokens(self.tokens_file.format("Battle royale"))


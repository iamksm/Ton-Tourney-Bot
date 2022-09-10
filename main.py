import asyncio
import json
import os
import platform
import random
from datetime import datetime
from more_itertools import grouper

import discord
import pandas
import pytz
import requests
from discord.ext import commands
from replit import db

from keep_alive import keep_alive
from leaderboard_processing import _add_token, _show_tokens

intents = discord.Intents.all()
intents.members = True
intents.typing = True
intents.presences = True
intents.reactions = True

client = commands.Bot(command_prefix="#", intents=intents)
APEX_ENDPOINT = "https://r5-crossplay.r5prod.stryder.respawn.com/privatematch/?token={}"

# Role IDs
ORGANIZERS = 819527735478321152
PARTNERS = 855159806808555590
CASTERS = 820221405261594625
JUMPMASTER_ROLE_ID = 819527931327807489
leaderboard = {}


def local_datetime(datetime_obj):
    utcdatetime = datetime_obj.replace(tzinfo=pytz.utc)
    tz = "Africa/Nairobi"
    return utcdatetime.astimezone(pytz.timezone(tz))


__games__ = [
    (discord.ActivityType.playing, "with iamksm"),
    (discord.ActivityType.playing, "on World's Edge"),
    (discord.ActivityType.playing, "Ranked"),
    (discord.ActivityType.playing, "on King's Canyon"),
    (discord.ActivityType.playing, "on Olympus"),
    (discord.ActivityType.playing, "Arenas"),
    (discord.ActivityType.playing, "Duos"),
    (discord.ActivityType.playing, "Trios"),
    (discord.ActivityType.playing, "on 300 Ping 😭"),
    (discord.ActivityType.playing, "in Skull Town"),
    (discord.ActivityType.playing, "in Storm Point"),
    (discord.ActivityType.watching, "over {members} Members"),
    (discord.ActivityType.watching, "the NoticeBoard"),
]
__gamesTimer__ = 60 * 60  # 60 minutes


@client.event
async def on_ready():
    print("Bot's Ready")
    if not db.get("tokens"):
        db["tokens"] = {}

    if not db.get("players"):
        db["players"] = {}

    if not db.get("match_ids"):
        db["match_ids"] = []

    while True:
        guildCount = len(client.guilds)
        memberCount = len(list(client.get_all_members()))
        randomGame = random.choice(__games__)
        await client.change_presence(
            activity=discord.Activity(
                type=randomGame[0],
                name=randomGame[1].format(guilds=guildCount, members=memberCount),
            )
        )
        await asyncio.sleep(__gamesTimer__)


def populate_kills_leaderboard(match):
    player_results = match["player_results"]

    for player in player_results:
        player_name = player["playerName"]
        try:
            leaderboard[player_name] += player["kills"]
        except KeyError:
            leaderboard[player_name] = player["kills"]

    return leaderboard


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


@client.event
async def on_message(message):
    """Automatically deletes discord link messages"""
    if "https://discord.gg/" in message.content:
        await message.delete()
        await message.author.send(f"{message.author.mention} Don't send Invite links!")
    else:
        await client.process_commands(message)


@client.command()
@commands.has_permissions(administrator=True)
async def results(ctx, token, match_no=None):
    """Command to generate results pulled from Apex API"""
    # only admins can run this
    if not token:
        return
    response = requests.get(APEX_ENDPOINT.format(token))
    if response.status_code != requests.codes.ok:
        return
    matches = response.json().get("matches")
    if not matches:
        return
    matches.reverse()
    match_count = 0
    for match in matches:
        match_data, time_started = prepare_match_details(match)
        file_name = f"/tmp/Match-{match_count +  1}-{time_started.date()}.xlsx"
        match_data.sort_values("Team Position", ascending=True, inplace=True)
        match_data.to_excel(file_name, index=False)
        if not match_no:
            await ctx.send(file=discord.File(file_name))
            os.remove(file_name)
            match_count += 1
            continue

        if match_no and int(match_no) - 1 == match_count:
            await ctx.send(file=discord.File(file_name))
            os.remove(file_name)
            break
        match_count += 1


@client.command()
@commands.has_permissions(manage_messages=True)
async def eleaderboard(ctx):
    """To be used by casters to generate excel"""
    with open("leaderboard.json", "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
            data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
            df = pandas.DataFrame.from_dict(
                {"Names": data.keys(), "Kills": data.values()}
            )
        except Exception as e:
            await ctx.send(f"Error: {e}")
            return

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

    await ctx.send(file=discord.File(file_name))
    os.remove(file_name)


@client.command()
@commands.has_permissions(administrator=True)
async def add_token(ctx, token):
    """On the start of a new season, ensure you add tokens one by one to be used"""
    await ctx.send(_add_token(token, db["tokens"]))


@client.command()
@commands.has_permissions(administrator=True)
async def clear_tokens(ctx):
    """Clears all stored tokens"""
    db["tokens"] = {}
    await ctx.send("Tokens successfully cleared")


@client.command()
@commands.has_permissions(administrator=True)
async def list_tokens(ctx):
    """Shows all registered tokens"""
    await ctx.send(_show_tokens(db["tokens"]))


@client.command()
@commands.has_permissions(administrator=True)
async def clear_match_ids(ctx):
    """Clear Match IDs, BE CAREFULL WITH THIS COMMAND!"""
    if db["match_ids"].value:
        db["match_ids"] = []
        await ctx.send("Match IDs cleared")
    else:
        await ctx.send("No match id recorded")


@client.command()
@commands.has_permissions(administrator=True)
async def match_ids(ctx):
    """Shows processed matches (For dev purposes)"""
    if db["match_ids"].value:
        await ctx.send(db["match_ids"].value)
    else:
        await ctx.send("No match id recorded")


def process_bulk_results(embed, matches_across_tokens):
    global leaderboard
    the_leaderboard = {}
    for matches in matches_across_tokens:
        for match in matches:
            if match["match_start"] not in db["match_ids"].value:
                populate_kills_leaderboard(match)
                db["match_ids"].append(match["match_start"])

    leaders = dict(sorted(leaderboard.items(), key=lambda x: x[1], reverse=True))
    for position, player in enumerate(leaders, start=1):
        the_leaderboard[player] = leaders[player]

    kills_JSON = json.dumps(the_leaderboard)
    with open("leaderboard.json", "r+", encoding="utf8") as file:
        try:
            file_data = json.load(file)
            team_data = json.loads(kills_JSON)
            file_data.update(team_data)
            leaders = dict(sorted(file_data.items(), key=lambda x: x[1], reverse=True))
            for position, player in enumerate(leaders, start=1):
                the_leaderboard[player] = leaders[player]
                embed.add_field(
                    name=f"{position}. {player}",
                    value=f"Total Kils - {leaders[player]}",
                    inline=True,
                )
            file.seek(0)
            json.dump(file_data, file, indent=4)
        except json.decoder.JSONDecodeError:
            team_data = json.loads(kills_JSON)
            leaders = dict(sorted(team_data.items(), key=lambda x: x[1], reverse=True))
            for position, player in enumerate(leaders, start=1):
                the_leaderboard[player] = leaders[player]
                embed.add_field(
                    name=f"{position}. {player}",
                    value=f"Total Kils - {leaders[player]}",
                    inline=True,
                )
            json.dump(team_data, file, indent=4)


@client.command()
async def standings(ctx):
    """Shows current leaderboard standings"""
    today = local_datetime(datetime.today())
    today = today.strftime("%d/%m/%Y, %H:%M:%S")

    with open("leaderboard.json", "r+", encoding="utf8") as file:
        try:
            file_data = json.load(file)
            leaders = dict(sorted(file_data.items(), key=lambda x: x[1], reverse=True))
            position = 1
            for results in grouper(leaders, 20):
                if int(leaders[results[0]]) == 0:
                    break
                embed = discord.Embed(
                    title="**THE SKULLS PIT LEAGUE**",
                    description=f"Kills leaderboard as at {today}",
                    color=discord.Color.red(),
                )
                embed.set_thumbnail(url=str(ctx.guild.icon_url))
                for player in results:
                    if not player:
                        continue

                    if int(leaders[player]) == 0:
                        break

                    embed.add_field(
                        name=f"{position}. {player}",
                        value=f"Total Kils - {leaders[player]}",
                        inline=True,
                    )
                    position += 1
                file.seek(0)
                json.dump(file_data, file, indent=4)
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error: {e}")
            return
    await ctx.send(embed=embed)


@client.command()
@commands.has_permissions(administrator=True)
async def token_kills(ctx, token=None):
    """Get leaderboard standings per token, can be used to get monthly results"""
    # only admins can run this
    # Show kills from matches in the specified token
    if not token:
        await ctx.send("Use #token_kills token")
        return

    response = requests.get(APEX_ENDPOINT.format(token))
    if response.status_code != requests.codes.ok:
        return
    matches = response.json().get("matches")
    if not matches:
        return
    matches.reverse()
    today = local_datetime(datetime.today())
    today = today.strftime("%d/%m/%Y, %H:%M:%S")
    embed = discord.Embed(
        title="**THE SKULLS PIT LEAGUE**",
        description=f"Kills leaderboard as at {today}",
        color=discord.Color.red(),
    )
    embed.set_thumbnail(url=str(ctx.guild.icon_url))

    global leaderboard
    leaderboard = {}
    for match in matches:
        leaderboard.update(populate_kills_leaderboard(match))

    leaders = dict(sorted(leaderboard.items(), key=lambda x: x[1], reverse=True))
    for position, player in enumerate(leaders, start=1):
        embed.add_field(
            name=f"{position}. {player}",
            value=f"Total Kils - {leaders[player]}",
            inline=True,
        )
    leaderboard = {}
    await ctx.send(embed=embed)


@client.command()
@commands.has_permissions(administrator=True)
async def reset_leaderboard(ctx):
    """Reset the leaderboard, to be used at the end of a league/season"""
    with open("leaderboard.json", "r+", encoding="utf8") as file:
        try:
            file.truncate()
            global leaderboard
            global the_leaderboard
            leaderboard = {}
            the_leaderboard = {}
            db["match_ids"] = []
            await ctx.send("**Leaderboard and Match IDs** have been cleared")
        except Exception as e:
            await ctx.send(f"Error in clearing: {e}")


def update_leaderboard_json(matches):
    global leaderboard
    leaderboard = {}
    for match in matches:
        populate_kills_leaderboard(match)

    leaders = dict(sorted(leaderboard.items(), key=lambda x: x[1], reverse=True))
    for position, player in enumerate(leaders, start=1):
        the_leaderboard[player] = leaders[player]

    kills_JSON = json.dumps(the_leaderboard)
    with open("leaderboard.json", "r+", encoding="utf8") as file:
        try:
            file_data = json.load(file)
            team_data = json.loads(kills_JSON)
            file_data.update(team_data)
            file.seek(0)
            json.dump(file_data, file, indent=4)
        except json.decoder.JSONDecodeError:
            team_data = json.loads(kills_JSON)
            json.dump(team_data, file, indent=4)


@client.command()
@commands.has_permissions(administrator=True)
async def update_leaderboard(ctx, token=None):
    """Get new data from new matches played to update standings"""
    if not token:
        if db["tokens"]:
            matches_across_tokens = []
            for token in db["tokens"]:
                response = requests.get(APEX_ENDPOINT.format(token))
                if response.status_code != requests.codes.ok:
                    continue
                if matches := response.json().get("matches"):
                    matches_across_tokens.append(matches)

            today = local_datetime(datetime.today())
            today = today.strftime("%d/%m/%Y, %H:%M:%S")
            embed = discord.Embed(
                title="**THE SKULLS PIT LEAGUE**",
                description=f"Kills leaderboard as at {today}",
                color=discord.Color.red(),
            )
            embed.set_thumbnail(url=str(ctx.guild.icon_url))
            process_bulk_results(embed, matches_across_tokens)
            await ctx.send(embed=embed)
            return
        return

    response = requests.get(APEX_ENDPOINT.format(token))
    if response.status_code != requests.codes.ok:
        return
    matches = response.json().get("matches")
    if not matches:
        return
    matches.reverse()
    today = local_datetime(datetime.today())
    today = today.strftime("%d/%m/%Y, %H:%M:%S")
    embed = discord.Embed(
        title="**THE SKULLS PIT LEAGUE**",
        description=f"Kills leaderboard as at {today}",
        color=discord.Color.red(),
    )
    embed.set_thumbnail(url=str(ctx.guild.icon_url))
    update_leaderboard_json(matches)
    await ctx.send("**Leaderboard** has been updated")


# @client.event
# # @commands.has_any_role(ORGANIZERS)
# async def on_message(message):
"""
A Functionality to enable the bot to reflect the message you send to it
to the discord channel of your choosing
"""
#     empty_array = []
#     message_channel = discord.utils.get(client.get_all_channels(),
#                                         name="😃-welcome")

# bot = discord.ClientUser.bot
# if message.author is bot:
#     return

#     if str(message.channel.type) == "private":
#         if message.attachments != empty_array:
#             files = message.attachments
#             await message_channel.send("[" + message.author.display_name + "]")

#             for file in files:
#                 await message_channel.send(file.url)

#         else:
#             await message_channel.send(message.content)

#     await client.process_commands(message)


@client.event
async def on_member_join(member):
    """Assigning default role when member joins"""
    role = discord.utils.get(member.guild.roles, name="🤓 LEGENDS")
    await member.add_roles(role)


@client.command()
@commands.has_permissions(administrator=True)
async def remove_role(ctx):
    """Command to remove Jumpmaster role from everyone after a Tournament"""
    JUMPMASTER_ROLE = discord.utils.get(ctx.guild.roles, id=JUMPMASTER_ROLE_ID)
    members = ctx.guild.members
    for member in members:
        if member.top_role == JUMPMASTER_ROLE:
            await member.remove_roles(JUMPMASTER_ROLE)


@client.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=10):
    """Used to clear bulk messages, Default is 10"""
    await ctx.channel.purge(limit=amount)


@client.command()
@commands.has_permissions(administrator=True)
async def ping(ctx):
    """Measure the Response Time"""
    ping = ctx.message
    pong = await ctx.send("**:ping_pong:** Pong!")
    delta = pong.created_at - ping.created_at
    delta = int(delta.total_seconds() * 1000)
    await pong.edit(
        content=f":ping_pong: Pong! ({delta} ms)\n*Discord WebSocket latency: {round(client.latency, 5)} ms*"  # noqa
    )


def check_if_member_is_creating_or_updating(username):
    if username in db["players"].keys():
        return True
    else:
        # Add the name to the db
        return False


@client.command()
@commands.has_permissions(administrator=True)
async def remove_team(ctx, teamname):
    """Remove a team from the roster using the exact team name they used to register"""
    teamname = teamname.replace("_", " ").replace("-", " ")
    with open("roster.json", "r+", encoding="utf8") as file:
        try:
            file_data = json.load(file)
            file_data.pop(teamname)
            file.seek(0)
            file.truncate()
            json.dump(file_data, file, indent=4)
            await ctx.send(f"**{teamname}** has been cleared from the roster")
        except Exception as e:
            await ctx.send(f"Error in removing your team {e}")


@client.command()
async def register(
    ctx, teamname, jumpmaster, teammate_1="None", teammate_2="None", teammate_3="None"
):
    """Command used to register teams"""
    the_role = "🤠 JUMP MASTERS"
    if the_role not in [role.name for role in ctx.author.roles]:
        for role in ctx.guild.roles:
            if role.name == the_role:
                mention = role.mention
                embed = discord.Embed(
                    title="🤔 Error",
                    description=f"Only Members with {str(mention)} Role Can register Teams. Contact Admin for Assistance",  # noqa
                )
                await ctx.send(embed=embed)

    else:
        is_db = check_if_member_is_creating_or_updating(ctx.author.name)
        if not is_db["players"]:
            teamname = teamname.replace("_", " ").replace("-", " ")
            db["players"][ctx.author.name] = teamname
            team = {
                teamname: {
                    "Team Leader": jumpmaster,
                    "Teammate 1": teammate_1,
                    "Teammate 2": teammate_2,
                    "Sub": teammate_3,
                }
            }

            team_JSON = json.dumps(team)

            with open("roster.json", "r+") as file:
                try:
                    file_data = json.load(file)
                    team_data = json.loads(team_JSON)
                    file_data.update(team_data)
                    file.seek(0)
                    json.dump(file_data, file, indent=4)
                except json.decoder.JSONDecodeError:
                    team_data = json.loads(team_JSON)
                    json.dump(team_data, file, indent=4)
        else:
            team_to_remove = db["players"].get(ctx.author.name)
            teamname = teamname.replace("_", " ").replace("-", " ")
            db["players"][ctx.author.name] = teamname
            team = {
                teamname: {
                    "Team Leader": jumpmaster,
                    "Teammate 1": teammate_1,
                    "Teammate 2": teammate_2,
                    "Sub": teammate_3,
                }
            }
            team_JSON = json.dumps(team)
            with open("roster.json", "r+") as file:
                try:
                    file_data = json.load(file)
                    team_data = json.loads(team_JSON)

                    if team_to_remove:
                        del file_data[team_to_remove]

                    file_data.update(team_data)
                    file.seek(0)
                    json.dump(file_data, file, indent=4)
                except json.decoder.JSONDecodeError:
                    team_data = json.loads(team_JSON)
                    json.dump(team_data, file, indent=4)

        embed = discord.Embed(
            title="TOURNAMENT REGISTRATION",
            description=f"Team Name - {teamname}",
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name="Team Leader", value=jumpmaster, inline=False)
        embed.add_field(name="Teammate 1", value=teammate_1, inline=False)
        embed.add_field(name="Teammate 2", value=teammate_2, inline=False)
        embed.add_field(name="Sub", value=teammate_3, inline=False)
        await ctx.send(embed=embed)


@client.command()
@commands.has_permissions(administrator=True)
async def add_team(
    ctx, teamname, jumpmaster, teammate_1="None", teammate_2="None", teammate_3="None"
):
    """Used by admins to manually add a team to the roster"""
    teamname = teamname.replace("_", " ").replace("-", " ")
    team = {
        teamname: {
            "Team Leader": jumpmaster,
            "Teammate 1": teammate_1,
            "Teammate 2": teammate_2,
            "Sub": teammate_3,
        }
    }

    team_JSON = json.dumps(team)

    with open("roster.json", "r+") as file:
        try:
            file_data = json.load(file)
            team_data = json.loads(team_JSON)
            file_data.update(team_data)
            file.seek(0)
            json.dump(file_data, file, indent=4)
        except json.decoder.JSONDecodeError:
            team_data = json.loads(team_JSON)
            json.dump(team_data, file, indent=4)

    embed = discord.Embed(
        title="TOURNAMENT REGISTRATION",
        description=f"Team Name - {teamname}",
        color=discord.Color.red(),
    )
    embed.set_thumbnail(url=ctx.author.avatar_url)
    embed.add_field(name="Team Leader", value=jumpmaster, inline=False)
    embed.add_field(name="Teammate 1", value=teammate_1, inline=False)
    embed.add_field(name="Teammate 2", value=teammate_2, inline=False)
    embed.add_field(name="Sub", value=teammate_3, inline=False)
    await ctx.send(embed=embed)


@client.command()
@commands.has_any_role(ORGANIZERS, PARTNERS, CASTERS)
async def teams(ctx):
    """Command used to display currently db teams"""
    with open("roster.json", "r+") as file:
        try:
            roster = json.load(file)
            embed = discord.Embed(
                title="TOURNAMENT ROSTER",
                description="These are the db Teams",
                color=discord.Color.red(),
            )
            count = 1
            for team in roster:
                print(f"\nTeam Name - {team}")
                teams = roster[team]
                team_details = []
                for title in teams:
                    print(f"{title} - {teams[title]}")
                    detail = f"{title} - {teams[title]}"
                    team_details.append(detail)
                embed.add_field(
                    name=f"{count}: {team}", value="\n".join(team_details), inline=True
                )
                count = count + 1
            embed.set_footer(text="Bot by iamksm")
            await ctx.send(embed=embed)

        except json.decoder.JSONDecodeError:
            embed = discord.Embed(
                title="😭 Error",
                description="No Teams Have db at the moment",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


@client.command()
@commands.has_permissions(administrator=True)
async def renew(ctx):
    """Command used to renew the team roster"""
    for key in db["players"].keys():
        del db["players"][key]

    with open("roster.json", "r+") as file:
        file.seek(0)
        file.truncate()
    embed = discord.Embed(
        title="🥳 Successfully Deleted Data",
        description="Team Roster has been Renewed",
        color=discord.Color.red(),
    )
    await ctx.send(embed=embed)


@client.command()
@commands.has_permissions(administrator=True)
async def generate(ctx):
    """Used to generate an excel of db teams"""
    with open("roster.json", "r+") as file:
        try:
            db_teams = json.load(file)
            team_names = []
            roles = []
            player_names = []
            for team in db_teams:
                for role in db_teams[team]:
                    team_names.append(team)
                    roles.append(role)
                    player = db_teams[team][role]
                    player_names.append(player)
            roster = pandas.DataFrame.from_dict(
                {
                    "Team Name": team_names,
                    "Role": roles,
                    "Player Name": player_names,
                }
            )
            writer = pandas.ExcelWriter("Tournament-Roster.xlsx")
            roster.to_excel(writer, index=False, sheet_name="sheet1", na_rep="NaN")
            for column in roster:
                column_width = max(
                    roster[column].astype(str).map(len).max(), len(column)
                )
                col_idx = roster.columns.get_loc(column)
                writer.sheets["sheet1"].set_column(col_idx, col_idx, column_width)
            writer.save()
            await ctx.send(file=discord.File(writer))
            os.remove(writer)

        except json.decoder.JSONDecodeError:
            embed = discord.Embed(
                title="😭 Error",
                description="No Teams Have db at the moment",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


@client.command()
async def server(ctx):
    """Displays info. about the server"""
    name = str(ctx.guild.name)
    description = str(ctx.guild.description)

    owner = str(ctx.guild.owner)
    id = str(ctx.guild.id)
    region = str(ctx.guild.region)
    member_count = str(ctx.guild.member_count)

    icon = str(ctx.guild.icon_url)

    embed = discord.Embed(
        title=name + " Server Info", description=description, color=discord.Color.blue()
    )
    embed.set_thumbnail(url=icon)
    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="Server ID", value=id, inline=True)
    embed.add_field(name="Region", value=region, inline=False)
    embed.add_field(name="Member Count", value=member_count, inline=True)

    if ctx.guild.premium_subscribers:
        names = ctx.guild.premium_subscribers
        mentions = [str(name.mention) for name in names]
        del names
        embed.add_field(
            name="Current Server Boosters", value="\n".join(mentions), inline=False
        )

    embed.add_field(
        name="Server Creation Date",
        value=local_datetime(ctx.guild.created_at).strftime(
            "%A, %B %d %Y @ %H:%M:%S %p %Z"
        ),
        inline=False,
    )

    if ctx.guild.system_channel:
        embed.add_field(
            name="Standard Channel", value=f"#{ctx.guild.system_channel}", inline=True
        )
        embed.add_field(
            name="AFK Voice Timeout",
            value=f"{int(ctx.guild.afk_timeout / 60)} min",
            inline=True,
        )
        embed.add_field(name="Guild Shard", value=ctx.guild.shard_id, inline=True)

    roles = sorted([role for role in ctx.guild.roles], reverse=True)
    mentions = [str(role.mention) for role in roles]
    del roles

    embed.add_field(name="Roles", value="\n".join(mentions), inline=False)
    embed.set_footer(text="Bot by iamksm")
    await ctx.send(embed=embed)


@client.event
async def on_raw_reaction_add(payload):
    """An event to handle role assignment upon reacting to an emoji"""
    message_id = payload.message_id
    if message_id == 839734116059971594:
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)

        if payload.emoji.name == "PC":
            role = discord.utils.get(guild.roles, name="PC")

        elif payload.emoji.name == "PS":
            role = discord.utils.get(guild.roles, name="Playstation")

        elif payload.emoji.name == "Xbox":
            role = discord.utils.get(guild.roles, name="Xbox")

        else:
            role = discord.utils.get(guild.roles, name=payload.emoji.name)

        if role is not None:
            member = guild.get_member(payload.user_id)
            # member = payload.member
            if member:
                await member.add_roles(role)
                print("done")
            else:
                print("Member Not found.")
        else:
            print("Role not found.")


@client.event
async def on_raw_reaction_remove(payload):
    """An event to handle role removal upon unreacting to an emoji"""
    message_id = payload.message_id
    if message_id == 839734116059971594:
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)

        if payload.emoji.name == "PC":
            role = discord.utils.get(guild.roles, name="PC")

        elif payload.emoji.name == "PS":
            role = discord.utils.get(guild.roles, name="Playstation")

        elif payload.emoji.name == "Xbox":
            role = discord.utils.get(guild.roles, name="Xbox")

        else:
            role = discord.utils.get(guild.roles, name=payload.emoji.name)

        if role is not None:
            # member = payload.member
            member = guild.get_member(payload.user_id)

            if member:
                await member.remove_roles(role)
                print("done")
            else:
                print("Member Not found.")
        else:
            print("Role not found.")


@client.command()
async def whois(ctx, member: discord.Member):
    """Command used to display info about a discord user"""
    embed = discord.Embed(
        title=member.name, description=member.mention, color=discord.Color.blue()
    )
    embed.add_field(
        name="Name and Tag",
        value="{}#{}".format(member.name, member.discriminator),
        inline=True,
    )
    embed.add_field(name="User ID", value=member.id, inline=True)
    embed.add_field(
        name="Account Creation Date",
        value=local_datetime(member.created_at).strftime(
            "%A, %B %d %Y @ %H:%M:%S %p %Z"
        ),
        inline=False,
    )
    embed.add_field(
        name="Joined Server On",
        value=local_datetime(member.joined_at).strftime(
            "%A, %B %d %Y @ %H:%M:%S %p %Z"
        ),
        inline=False,
    )

    all_activities = []
    spotify = None
    for activity in member.activities:
        activity_name = activity.name
        if "spotify" in activity_name.lower():
            spotify = activity
        all_activities.append(activity_name)
    activities = "\n".join(all_activities) if all_activities else None
    embed.add_field(name="Activities", value=activities, inline=True)

    if spotify:
        embed.add_field(
            name="Spotify", value=f"{spotify.artist} - {spotify.title}", inline=True
        )

    roles = sorted([role for role in member.roles], reverse=True)
    mentions = [str(role.mention) for role in roles]
    del roles
    embed.add_field(name="Top Role", value=member.top_role, inline=False)
    embed.add_field(name="Roles", value=" , ".join(mentions), inline=False)

    embed.set_thumbnail(url=member.avatar_url)
    embed.set_footer(
        icon_url=ctx.author.avatar_url, text=f"Requested by {ctx.author.name}"
    )

    await ctx.send(embed=embed)


def get_uptime(days, hours, minutes, seconds):
    uptime = "None"
    seconds = int(seconds)
    minutes = int(minutes)
    hours = int(hours)
    days = int(days)

    min_stat = "Minutes" if int(minutes) > 1 else "Minute"
    sec_stat = "Seconds" if seconds > 1 else "Second"
    hour_stat = "Hours" if hours > 1 else "Hour"
    day_stat = "Days" if days > 1 else "Day"

    if seconds > 0:
        uptime = f"{seconds} {sec_stat}"

    if minutes > 0:
        uptime = f"{minutes} {min_stat} and {seconds} {sec_stat}"

    if hours > 0:
        uptime = f"{hours} {hour_stat}, {minutes} {min_stat} and {seconds} {sec_stat}"

    if days > 0:
        uptime = f"{days} {day_stat}, {hours} {hour_stat}, {minutes} {min_stat} and {seconds} {sec_stat}"  # noqa

    return uptime


@client.command()
async def stats(ctx):
    """
    A useful command that displays bot statistics.
    """
    starttime = datetime.now()
    pythonVersion = platform.python_version()
    dpyVersion = discord.__version__
    serverCount = len(client.guilds)
    memberCount = len(set(client.get_all_members()))

    _time = datetime.now() - starttime
    days = ((_time.seconds / 3600) / 24) % 24
    hours = _time.seconds / 3600
    minutes = (_time.seconds / 60) % 60
    seconds = _time.seconds % 60

    uptime = get_uptime(days, hours, minutes, seconds)

    embed = discord.Embed(
        title=f"{client.user.name} Stats",
        description="",
        colour=ctx.author.colour,
        timestamp=ctx.message.created_at,
    )

    embed.add_field(name="Bot Version:", value="0.0.10")
    embed.add_field(name="Python Version:", value=pythonVersion)
    embed.add_field(name="Discord.Py Version", value=dpyVersion)
    embed.add_field(name="Total Guilds:", value=serverCount)
    embed.add_field(name="Total Users:", value=memberCount)
    embed.add_field(name="Uptime", value=uptime)
    embed.add_field(name="Bot Developer:", value="<@459338191892250625>")

    embed.set_footer(text=f"Say hello to my little friend | {client.user.name}")
    embed.set_author(name=client.user.name, icon_url=client.user.avatar_url)

    await ctx.send(embed=embed)


keep_alive()
client.run(os.getenv("TOKEN"))

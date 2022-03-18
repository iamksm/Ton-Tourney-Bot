import asyncio
import json
import os
import platform
import random
from datetime import datetime

import discord
import pandas
import pytz
import requests
from discord.ext import commands
from replit import db as registered

from keep_alive import keep_alive

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
        content=f":ping_pong: Pong! ({delta} ms)\n*Discord WebSocket latency: {round(client.latency, 5)} ms*"
    )


def check_if_member_is_creating_or_updating(username):
    if username in registered.keys():
        return True
    else:
        # Add the name to the db
        return False


@client.command()
@commands.has_permissions(administrator=True)
async def remove_team(ctx, teamname):
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
                    description=f"Only Members with {str(mention)} Role Can register Teams. Contact Admin for Assistance",
                )
                await ctx.send(embed=embed)

    else:
        is_registered = check_if_member_is_creating_or_updating(ctx.author.name)
        if not is_registered:
          teamname = teamname.replace("_", " ").replace("-", " ")
          registered[ctx.author.name] = teamname
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
            team_to_remove = registered.get(ctx.author.name)
            teamname = teamname.replace("_", " ").replace("-", " ")
            registered[ctx.author.name] = teamname
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
async def add_team(ctx, teamname, jumpmaster, teammate_1="None", teammate_2="None", teammate_3="None"):
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
    """Command used to display currently registered teams"""
    with open("roster.json", "r+") as file:
        try:
            roster = json.load(file)
            embed = discord.Embed(
                title="TOURNAMENT ROSTER",
                description="These are the Registered Teams",
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
                description="No Teams Have Registered at the moment",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


@client.command()
@commands.has_permissions(administrator=True)
async def renew(ctx):
    """Command used to renew the team roster"""
    for key in registered.keys():
        del registered[key]

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
    """Used to generate and excel of registered teams"""
    with open("roster.json", "r+") as file:
        try:
            registered_teams = json.load(file)
            team_names = []
            roles = []
            player_names = []
            for team in registered_teams:
                for role in registered_teams[team]:
                    team_names.append(team)
                    roles.append(role)
                    player = registered_teams[team][role]
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
                description="No Teams Have Registered at the moment",
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

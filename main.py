import discord
from keep_alive import keep_alive
import os
from discord.ext import commands
import random
import pytz
from collections import Counter
import asyncio

def local_datetime(datetime_obj):
  utcdatetime = datetime_obj.replace(tzinfo=pytz.utc)
  tz = 'Africa/Nairobi'
  return utcdatetime.astimezone(pytz.timezone(tz))

intents = discord.Intents.all()
intents.members = True
intents.typing = True
intents.presences = True
intents.reactions = True

client = commands.Bot(command_prefix="*", intents=intents)

__games__ = [
    (discord.ActivityType.playing, 'with iamksm'),
    (discord.ActivityType.playing, 'with Team Efficiency'),
    (discord.ActivityType.watching, 'over {guilds} Server'),
    (discord.ActivityType.watching, 'over {members_count} Members'),
    (discord.ActivityType.watching, 'you right now'),
]
__gamesTimer__ = 60 * 60 #60 minutes

@client.event
async def on_ready():
    print("Bot's Ready")
    while True:
            guildCount = len(client.guilds)
            memberCount = len(list(client.get_all_members()))
            randomGame = random.choice(__games__)
            await client.change_presence(activity=discord.Activity(type=randomGame[0], name=randomGame[1].format(guilds = guildCount, members = memberCount)))
            await asyncio.sleep(__gamesTimer__)

# @client.event
# # @commands.has_any_role('🔱 ORGANIZERS')
# async def on_message(message):
#     empty_array = []
#     message_channel = discord.utils.get(client.get_all_channels(),
#                                         name="ℹ-notice-board")

#     if message.author == client.user:
#         return

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
  role = discord.utils.get(member.guild.roles, name='🤓 GAMERS')
  await member.add_roles(role)

@client.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=10):
    await ctx.channel.purge(limit=amount)

@client.command()
async def ping(ctx):
    '''Measure the Response Time'''
    ping = ctx.message
    pong = await ctx.send('**:ping_pong:** Pong!')
    delta = pong.created_at - ping.created_at
    delta = int(delta.total_seconds() * 1000)
    await pong.edit(content=f':ping_pong: Pong! ({delta} ms)\n*Discord WebSocket latency: {round(client.latency, 5)} ms*')

@client.command(aliases=['activities'])
async def games(ctx, *scope):
    '''Shows which games and how often are currently being played on the server'''
    games = Counter()
    for member in ctx.guild.members:
        for activity in member.activities:
          if not member.bot:
              if isinstance(activity, discord.Game):
                  games[str(activity)] += 1
              elif isinstance(activity, discord.Activity):
                  games[activity.name] += 1
    msg = ':chart: Games currently being played on this server\n'
    msg += '```js\n'
    msg += '{!s:40s}: {!s:>3s}\n'.format('Name', 'Number')
    chart = sorted(games.items(), key=lambda t: t[1], reverse=True)
    for index, (name, amount) in enumerate(chart):
        if len(msg) < 1950:
            msg += '{!s:40s}: {!s:>3s}\n'.format(name, amount)
        else:
            amount = len(chart) - index
            msg += f'+ {amount} Others'
            break
    msg += '```'
    await ctx.send(msg)

@client.command()
async def server(ctx):
    name = str(ctx.guild.name)
    description = str(ctx.guild.description)

    owner = str(ctx.guild.owner)
    id = str(ctx.guild.id)
    region = str(ctx.guild.region)
    member_count = str(ctx.guild.member_count)

    icon = str(ctx.guild.icon_url)

    embed = discord.Embed(title=name + " Server Info",
                          description=description,
                          color=discord.Color.blue())
    embed.set_thumbnail(url=icon)
    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="Server ID", value=id, inline=True)
    embed.add_field(name="Region", value=region, inline=False)
    embed.add_field(name="Member Count", value=member_count, inline=True)

    if ctx.guild.premium_subscribers:
      names = ctx.guild.premium_subscribers
      mentions = [str(name.mention) for name in names]
      del names
      embed.add_field(name="Current Server Boosters", value='\n'.join(mentions), inline=False)

    embed.add_field(name = "Server Creation Date" , value = local_datetime(ctx.guild.created_at).strftime("%A, %B %d %Y @ %H:%M:%S %p %Z"), inline = False)

    if ctx.guild.system_channel:
      embed.add_field(name='Standard Channel', value=f'#{ctx.guild.system_channel}', inline=True)
      embed.add_field(name='AFK Voice Timeout', value=f'{int(ctx.guild.afk_timeout / 60)} min', inline=True)
      embed.add_field(name='Guild Shard', value=ctx.guild.shard_id, inline=True)

    roles = sorted([role for role in ctx.guild.roles], reverse=True)
    mentions = [str(role.mention) for role in roles]
    del roles

    embed.add_field(name = 'Roles', value= '\n'.join(mentions), inline = False)
    # emojis = ctx.guild.emojis
    # the_emojis = [str(emoji.name) for emoji in emojis]
    # del emojis

    # embed.add_field(name='Custom Emojis', value='\n'.join(the_emojis), inline=True)

    embed.set_footer(text="Bot by iamksm")
    await ctx.send(embed=embed)

keep_alive()
client.run(os.getenv('TOKEN'))
import discord
from discord.ext import commands
import os
import config
import traceback
import asyncio 
import time 
import json 

def get_prefix(bot, message):
    file_path = 'data/prefixes.json'
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({}, f)
    try:
        with open(file_path, 'r') as f:
            prefixes = json.load(f)
    except json.JSONDecodeError:
        prefixes = {}
        with open(file_path, 'w') as f:
            json.dump(prefixes, f)
    return prefixes.get(str(message.guild.id), '!')
    
bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"\nConnected to {bot.user}\n")
    await load_extensions()    
    await sync_commands()
    activity = discord.Game(name="with your balls")
    await bot.change_presence(activity=activity)

async def load_extensions():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'commands.{filename[:-3]}')
                print(f"[+] {filename[:-3]}.py — online")
            except commands.ExtensionError as e:
                print(f"[-] {filename[:-3]} — offline ({e})")

async def sync_commands():
    synced = await bot.tree.sync()
    print(f"\nSynced {len(synced)} commands")

async def is_dev(ctx):
    allowed_ids = [918862839316373554]
    return ctx.author.id in allowed_ids

async def evaluate(ctx, code):
    try:
        result = eval(code)
        if asyncio.iscoroutine(result):
            return await result
        else:
            return result
    except Exception as e:
        return e

@bot.command(name="sync", description="Sync slash commands")
@commands.check(is_dev)
async def _sync(ctx):
    synced = await bot.tree.sync()
    await ctx.reply(embed=discord.Embed(description=f"Synced **{len(synced)}** command(s)", color=0x51cd87), allowed_mentions=discord.AllowedMentions.none())

@bot.command(name='evaluate', aliases=['eval', 'e', 'execute', 'exec'], usage="<code>", description="Evaluates your python code", pass_context=True)
@commands.check(is_dev)
async def eval_command(ctx, *, code):
    try:
        start_time = time.monotonic()
        result = await evaluate(ctx, code)
        end_time = time.monotonic()
        execution_time = (end_time - start_time) * 1000

        result_str = str(result)

        if isinstance(result, Exception):
            raise result

        if len(result_str) > 1800:
            embed = discord.Embed(color=0x27272f)
            embed.set_author(name=f"Evaluation by {ctx.author.name} - {ctx.author.id}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_footer(text=f"{execution_time:.2f} ms")

            chunks = [result_str[i:i+1800] for i in range(0, len(result_str), 1800)]
            for chunk in chunks:
                embed.description = f"```py\n{chunk}\n```"
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description=f"```py\n{result_str}\n```", color=0x27272f)
            embed.set_author(name=f"Evaluation by {ctx.author.name} - {ctx.author.id}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_footer(text=f"{execution_time:.2f} ms")
            await ctx.send(embed=embed)

    except Exception as e:
        tb = traceback.format_exc()
        embed = discord.Embed(description=f"```{tb}```", color=0x27272f)
        embed.set_author(name=f"Evaluation by {ctx.author.name} - {ctx.author.id}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_footer(text=e)
        await ctx.message.add_reaction('❌')
        await ctx.send(embed=embed)

@bot.command(name='setprefix', usage="<new prefix>", description="Set the bot's prefix for this server.")
@commands.has_permissions(manage_guild=True)
async def set_prefix(ctx, prefix):
    file_path = 'data/prefixes.json'
    with open(file_path, 'r') as f:
        prefixes = json.load(f)
    prefixes[str(ctx.guild.id)] = prefix
    with open(file_path, 'w') as f:
        json.dump(prefixes, f)
        await ctx.reply(f'`{prefix}` is my new prefix.', allowed_mentions=discord.AllowedMentions.none())

@bot.event
async def on_message(message):
    if not message.author.bot:
        await bot.process_commands(message)
        
bot.remove_command('help')
bot.run(config.TOKEN)
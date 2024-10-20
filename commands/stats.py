import discord
from discord.ext import commands
from discord import app_commands
import config
import psutil
import platform 
import datetime
import os

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()

    @app_commands.command(name="stats", description="Check bot's statistics")
    @app_commands.guild_only()
    async def _stats(self, interaction: discord.Interaction):
        shard_latency = self.bot.latency * 1000
        process = psutil.Process(os.getpid())
        cpu_usage = psutil.cpu_percent(interval=.1)  
        
        mem_used = process.memory_full_info().uss / (1024**2)
        uptime = f"<t:{int(self.start_time.timestamp())}:f>"

        cogs_count = len(self.bot.cogs)
        cogs_names = ', '.join(self.bot.cogs.keys())
        
        embed = discord.Embed(title='Bot Stats', color=0xff0000)
        embed.add_field(name=f"[{cogs_count}] Modules Loaded", value=f'-# {cogs_names}', inline=False)
        embed.add_field(name='⏱️ Uptime', value=f'{config.REPLY} {uptime}', inline=True)
        embed.add_field(name=f'{config.LATENCY} Shard Latency', value=f'{config.REPLY} {shard_latency:.2f}ms', inline=True)
        embed.add_field(name=f'{config.CPU} CPU Usage', value=f'{config.REPLY} {cpu_usage:.2f}%', inline=True)
        embed.add_field(name=f'{config.MEMORY} Memory Usage', value=f'{config.REPLY} {mem_used:.2f} MB / 512 MB', inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Stats(bot))

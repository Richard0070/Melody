import discord
from discord.ext import commands, tasks
import json
import os
import config 

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_servers = self.load_allowed_servers()
        self.check_servers.start()

    def load_allowed_servers(self):
        if not os.path.exists('data/servers.json'):
            with open('data/servers.json', 'w') as f:
                json.dump([], f)
        with open('data/servers.json', 'r') as f:
            return json.load(f)

    def save_allowed_servers(self):
        with open('data/servers.json', 'w') as f:
            json.dump(self.allowed_servers, f, indent=4)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def allow_server(self, ctx, server_id: int):
        if server_id not in self.allowed_servers:
            self.allowed_servers.append(server_id)
            self.save_allowed_servers()
            await ctx.send(f"{config.SUCCESS} Server `{server_id}` is now allowed to use Melody.")
        else:
            await ctx.send(f"{config.ERROR} Server `{server_id}` is already allowed.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unallow_server(self, ctx, server_id: int):
        if server_id in self.allowed_servers:
            self.allowed_servers.remove(server_id)
            self.save_allowed_servers()
            await ctx.send(f"{config.SUCCESS} Server `{server_id}` is now unallowed.")
        else:
            await ctx.send(f"{config.ERROR} Server `{server_id}` was not allowed.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def servers(self, ctx):
        embed = discord.Embed(title="Servers the bot is in")
        for guild in self.bot.guilds:
            invite = await guild.text_channels[0].create_invite(max_age=300)
            embed.add_field(name=guild.name, value=f"{guild.id} ([Invite]({invite.url}))", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx):
        for guild in self.bot.guilds:
            if guild.id not in self.allowed_servers:
                await guild.leave()
        await ctx.send("📤 Left all unallowed servers.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild.id not in self.allowed_servers:
            await guild.leave()

    @tasks.loop(minutes=10)
    async def check_servers(self):
        for guild in self.bot.guilds:
            if guild.id not in self.allowed_servers:
                await guild.leave()

async def setup(bot):
    await bot.add_cog(Developer(bot))
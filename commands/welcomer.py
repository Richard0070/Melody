import discord
from discord.ext import commands, tasks
import requests
import json
import os
import yaml 

class Welcomer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = os.path.join('data', 'welcome.json')
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.welcome_data = json.load(f)
        else:
            self.welcome_data = {}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.welcome_data, f)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        server_id = str(member.guild.id)
        if server_id in self.welcome_data:
            channel_id = self.welcome_data[server_id]
            channel = self.bot.get_channel(int(channel_id))
            await self.send_welcome_embed(channel, member)

    async def send_welcome_embed(self, channel, member):
        display_name = member.display_name.replace(" ", "%20")
        avatar = member.avatar.url if member.avatar else member.default_avatar.url
        api = f"https://api-denzel.vercel.app/welcome?avatar={avatar}&username={member.name}&displayname={display_name}"
        embed = discord.Embed(title="Welcome! <a:blob_wave:1175022141599658054>", description="We are thrilled to have you in our community! Feel free to introduce yourself in <#1139591850567676104>.", color=0xffffff)
        embed.set_image(url=api)
        embed.set_footer(text=f"Account Created on {member.created_at.strftime('%d-%m-%Y')}")
        await channel.send(member.mention, embed=embed)

    @commands.command(name='set_welcome_channel', aliases=['swc'], usage="<channel>", description="Set the welcome channel for the server.")
    @commands.has_permissions(manage_guild=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        server_id = str(ctx.guild.id)
        self.welcome_data[server_id] = str(channel.id)
        self.save_data()
        await ctx.reply(f"Welcome channel set to {channel.mention}.", allowed_mentions=discord.AllowedMentions.none())

class MemberStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('dashboard.yaml', 'r') as file:
            dashboard = yaml.safe_load(file)
        self.dashboard = dashboard        
        self.member_stats_channel_id = self.dashboard['channels']['memberstats']
        self.update_channel_name.start()
                
    @tasks.loop(minutes=10)
    async def update_channel_name(self):
        guild = self.bot.get_guild(975033657658052630)
        if guild:
            channel = guild.get_channel(self.member_stats_channel_id)
            if channel:
                member_count = sum(1 for member in guild.members if not member.bot)
                await channel.edit(name=f'✦ {member_count} Members ✦')

    @update_channel_name.before_loop
    async def before_update_channel_name(self):
        await self.bot.wait_until_ready()
    
async def setup(bot):
    await bot.add_cog(Welcomer(bot))
    await bot.add_cog(MemberStats(bot))
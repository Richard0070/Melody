import discord
from discord.ext import commands
import json
import os
import config

class Cloner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clone", description="Generates data of the server.")
    @commands.has_permissions(administrator=True)
    async def clone_server(self, ctx):
        guild = ctx.guild
        server_data = {
            "name": guild.name,
            "id": guild.id,
            "channels": [],
            "roles": [],
        }
        for role in guild.roles:
            server_data["roles"].append({
                "name": role.name,
                "permissions": role.permissions.value,
                "color": role.color.value,
                "position": role.position,
                "mentionable": role.mentionable,
            })
        for channel in guild.channels:
            channel_data = {
                "name": channel.name,
                "id": channel.id,
                "type": str(channel.type),
                "position": channel.position,
            }
            if isinstance(channel, discord.TextChannel):
                channel_data["topic"] = channel.topic
                channel_data["nsfw"] = channel.is_nsfw()
            elif isinstance(channel, discord.VoiceChannel):
                channel_data["bitrate"] = channel.bitrate
                channel_data["user_limit"] = channel.user_limit
            channel_data["overwrites"] = []
            for role, overwrite in channel.overwrites.items():
                channel_data["overwrites"].append({
                    "role_name": role.name,
                    "permissions": overwrite.pair()[0].value,
                    "denied_permissions": overwrite.pair()[1].value,
                })
            server_data["channels"].append(channel_data)
        filename = f"{guild.name}-{guild.id}.json"
        with open(filename, "w") as file:
            json.dump(server_data, file, indent=4)
        await ctx.send(file=discord.File(filename))
        os.remove(filename)

    @commands.command(name="permission", aliases=["perms", "permissions", "perm"], usage="<integer>", description="Permissions checker.")
    @commands.has_permissions(administrator=True)
    async def check_permissions(self, ctx, perms_integer: int):
        permissions = discord.Permissions(perms_integer)
        description = ""
        for perm, value in permissions:
            description += f"{f'{config.SUCCESS}' if value else '❌'} **`{perm.replace('_', ' ').title()}`**\n"

        # Split description into chunks if it exceeds 2000 characters
        chunks = [description[i:i+2000] for i in range(0, len(description), 2000)]

        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title="Permissions Check" if i == 0 else f"Permissions Check {i+1}",
                description=chunk
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cloner(bot))
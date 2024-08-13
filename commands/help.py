import discord 
from discord import app_commands
from discord.ext import commands 
import config 
import os
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

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Get all the information about a specific command")
    @app_commands.guild_only()
    @app_commands.describe(command="Select a command")
    async def _help_command(self, interaction: discord.Interaction, command: str):
        cmd = self.bot.get_command(command)
        if cmd is None:
            await interaction.response.send_message(f"{config.ERROR} Command **{command}** not found.", ephemeral=True)
            return

        desc = cmd.description or "No description available."
        prefix = get_prefix(self.bot, interaction) if interaction.guild else '!'
        usage = f"{prefix}{cmd.qualified_name} {cmd.signature}" if cmd.signature else f"/{cmd.qualified_name}"
        aliases = ", ".join(cmd.aliases) if cmd.aliases else "No aliases."
        category = cmd.cog_name or "General"

        help_embed = discord.Embed(title=desc, color=0xff0000)
        help_embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        help_embed.add_field(name="Aliases", value=aliases, inline=False)
        help_embed.set_footer(text=f"{category} - {command}")
        
        await interaction.response.send_message(embed=help_embed)

    @_help_command.autocomplete('command')
    async def autocomplete_command(self, interaction: discord.Interaction, current: str):
        commands_list = [cmd.qualified_name for cmd in self.bot.commands if cmd.qualified_name.startswith(current)]
        return [app_commands.Choice(name=cmd, value=cmd) for cmd in commands_list]

async def setup(bot):
    await bot.add_cog(Help(bot))

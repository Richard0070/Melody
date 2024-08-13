import discord
from discord.ext import commands
from discord import app_commands as s
import config

class BotManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @s.command(name="manage", description="Manage the bot")
    @s.guild_only()
    @s.default_permissions(administrator=True)
    async def _botmanager(self, interaction: discord.Interaction):
        if interaction.user.id != 918862839316373554:
            await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
            return

        app = await self.bot.application_info()
        visibility = "Public" if app.bot_public else "Private"
        bio = app.description
        app_name = app.name
        app_id = app.id        
        my_bot = await self.bot.fetch_user(app_id)
        basic_info = f"**`{app_name}`**, **`{app_id}`**, **`{visibility}`**\n\n```\n{bio}\n```"         
        manager = discord.Embed(title=f"{config.SETUP} Bot Manager", description=f"** **\n>>> {basic_info}")
       
        if my_bot.banner:
            manager.set_image(url=my_bot.banner)        
                    
        await interaction.response.send_message(embed=manager, view=ManagerButtons(self.bot))

class ManagerButtons(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Cogs", style=discord.ButtonStyle.primary, emoji=config.VIEW, row=1)
    async def _cogs(self, interaction: discord.Interaction, button: discord.ui.Button):
        cogs = ', '.join(self.bot.cogs.keys())
        cogs_count = len(self.bot.cogs)
        c = discord.Embed(description=f">>> {cogs}")
        c.set_footer(text=f"[{cogs_count}] cogs loaded")
        await interaction.response.send_message(embed=c, ephemeral=True)

    @discord.ui.button(label="Load", style=discord.ButtonStyle.gray, emoji="📥", row=1)
    async def _load_cog(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CogsManager(self.bot, "load"))
        await interaction.response.defer()
       
    @discord.ui.button(label="Unload", style=discord.ButtonStyle.gray, emoji="📤", row=1)
    async def _unload_cog(self, interaction: discord.Interaction, button: discord.ui.Button):
         await interaction.response.send_modal(CogsManager(self.bot, "unload"))
         await interaction.response.defer()

async def setup(bot):
    await bot.add_cog(BotManager(bot))
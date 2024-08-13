import discord
from discord.ext import commands
from discord import app_commands
from googletrans import Translator

class Translate(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.translator = Translator()
        self.ctx_menu = app_commands.ContextMenu(
            name='Translate',
            callback=self.translate,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def translate(self, interaction: discord.Interaction, message: discord.Message) -> None:
        text = message.content
        try:
            if text:
                translated_text = self.translator.translate(text=text, dest='en').text

                view = OriginalMessageView(message.jump_url)

                await interaction.response.send_message(f'>>> {translated_text}', view=view)
            else:
                await interaction.response.send_message("Please provide some text to translate.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Translation failed: {e}", ephemeral=True)

class OriginalMessageView(discord.ui.View):
    def __init__(self, original_message_url):
        super().__init__()
        self.add_item(discord.ui.Button(label='Original Message', url=original_message_url))

async def setup(bot):
    await bot.add_cog(Translate(bot))
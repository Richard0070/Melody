import discord
from discord.ext import commands
from discord import app_commands
import config
from gemini import Gemini

class Translate(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
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
                # Create the query and the Gemini client
                query = f"what's the translation for \"{text}\"? just send the translated text in English. do not add anything else. if it's a slur, just censor the slurs with **`#####`**. No need to act like a chatbot. You're just a translator model whose sole purpose is to translate texts. Don't provide any remarks at all. If you can't translate then simply say that you can't translate. Do not add any context to your response. Do not add any explanation to your response. Just translate. However if my message contains a slur, simply censor it but atleast translate rest of the text."
                cookies = {"__Secure-1PSID": config.BARD}
                try:
                    client = Gemini(cookies=cookies)
                    translation = client.generate_content(query)
                    translation_text = translation.payload.get('candidates', [{}])[0].get('text', '').strip()
                except Exception as e:
                    translation_text = f"Translation failed: {e}"

                # Create view to link the original message
                view = OriginalMessageView(message.jump_url)

                await interaction.response.send_message(f'>>> {translation_text}', view=view)
            else:
                await interaction.response.send_message("Please provide some text to translate.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class OriginalMessageView(discord.ui.View):
    def __init__(self, original_message_url):
        super().__init__()
        self.add_item(discord.ui.Button(label='Original Message', url=original_message_url))

async def setup(bot):
    await bot.add_cog(Translate(bot))

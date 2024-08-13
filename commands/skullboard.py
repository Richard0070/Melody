import discord
from discord.ext import commands
import json
from helpers.starboardutils import StarboardView
import yaml

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.starboard_msgs_file = "data/starboard_msgs.json"
        self.starboard_settings_file = "data/starboard_settings.json"
        self.load_starboard_msgs()
        self.load_starboard_settings()
        with open('dashboard.yaml', 'r') as file:
            dashboard = yaml.safe_load(file)
        self.dashboard = dashboard        
        self.skullboard  = self.dashboard['channels']['skullboard']               
        
    def load_starboard_msgs(self):
        try:
            with open(self.starboard_msgs_file, "r") as f:
                self.starboard_msgs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.starboard_msgs = []

    def save_starboard_msgs(self):
        with open(self.starboard_msgs_file, "w") as f:
            json.dump(self.starboard_msgs, f, indent=4)

    def load_starboard_settings(self):
        try:
            with open(self.starboard_settings_file, "r") as f:
                settings = json.load(f)
                self.star_emoji = settings.get("emoji", "💀")
                self.star_threshold = settings.get("threshold", 3)
        except (FileNotFoundError, json.JSONDecodeError):
            self.star_emoji = "💀"
            self.star_threshold = 3
                
    def save_starboard_settings(self):
        settings = {"emoji": self.star_emoji, "threshold": self.star_threshold}
        with open(self.starboard_settings_file, "w") as f:
            json.dump(settings, f, indent=4)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name == self.star_emoji:
            print('step 1 pass')
            channel = self.bot.get_channel(payload.channel_id)
            if channel.id == self.skullboard:
                print('skullboard channel')
                return
            message = await channel.fetch_message(payload.message_id)
            if payload.message_id not in self.starboard_msgs:
                print('step 2 pass')
                star_count = 0
                for reaction in message.reactions:
                  if str(reaction.emoji) == self.star_emoji:
                    star_count = reaction.count
                    break
                print(f"Star count: {star_count}, Threshold: {self.star_threshold}")
                
                if star_count >= self.star_threshold:
                    print(f"{star_count} sc >= {self.star_threshold} st")
                    await self.post_to_starboard(channel, message)
                    self.starboard_msgs.append(payload.message_id)
                    self.save_starboard_msgs()

    async def post_to_starboard(self, channel, message):
        starboard_channel_id = self.skullboard
        starboard_channel = self.bot.get_channel(starboard_channel_id)
        webhooks = await starboard_channel.webhooks()
        webhook = None
        for wh in webhooks:
            if wh.name == "Starboard Webhook":
                webhook = wh
                break
        if webhook is None:
            webhook = await starboard_channel.create_webhook(name="Starboard Webhook")

        starboard_content = f"{message.content}"

        attachments = [f"{attachment.url}" for attachment in message.attachments]
        if attachments:
            starboard_content += "\n".join(attachments)

        avatar_url = message.author.avatar.url if message.author.avatar else message.author.default_avatar.url

        await webhook.send(starboard_content, username=message.author.display_name, avatar_url=avatar_url, view=StarboardView(channel, message))

    @commands.command(name="set_emoji", usage="<emoji>", description="Set the emoji for the starboard.")
    @commands.has_permissions(manage_guild=True)
    async def set_emoji(self, ctx, emoji: str):
        self.star_emoji = emoji
        self.save_starboard_settings()
        await ctx.reply(f"Starboard emoji set to \"{emoji}\"", allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="set_threshold", usage="<threshold>", description="Set the threshold for the starboard.")
    @commands.has_permissions(manage_guild=True)
    async def set_threshold(self, ctx, threshold: int):
        self.star_threshold = threshold
        self.save_starboard_settings()
        await ctx.reply(f"🍀 Starboard threshold set to **{threshold}**.", allowed_mentions=discord.AllowedMentions.none())        

async def setup(bot):
    await bot.add_cog(Starboard(bot))
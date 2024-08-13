import discord
import json

class StarboardView(discord.ui.View):
    def __init__(self, channel, message):
        super().__init__()
        self.starboard_settings_file = "data/starboard_settings.json"
        self.channel = channel.name
        self.message = message.jump_url
        self.load_starboard_settings()
        self.add_item(discord.ui.Button(label=f'#{self.channel}', emoji=self.star_emoji, url=self.message))

    def load_starboard_settings(self):
        try:
            with open(self.starboard_settings_file, "r") as f:
                settings = json.load(f)
                self.star_emoji = settings.get("emoji", "💀")
        except (FileNotFoundError, json.JSONDecodeError):
            self.star_emoji = "💀"
          
import discord
from discord.ext import commands
from discord import app_commands
import random
import pymongo
import yaml
import config
import json 
import os 

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

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = pymongo.MongoClient(config.MONGO)
        self.db = self.client['discord_bot']
        self.collection = self.db['levels']
        self.cd_mapping = commands.CooldownMapping.from_cooldown(1, 30, commands.BucketType.member)

        with open('dashboard.yaml', 'r') as file:
            self.config = yaml.safe_load(file)

        self.bot_commands = [command.name for command in bot.commands]        

    def get_user_data(self, user_id):
        user = self.collection.find_one({'_id': user_id})
        if user is None:
            user = {'_id': user_id, 'xp': 0, 'level': 0}
            self.collection.insert_one(user)
        return user

    def get_multiplier(self, member):
        highest_multiplier = 1.0
        if 'multiplier' in self.config['levels']:
            for role in member.roles:
                role_id = str(role.id)
                if role_id in self.config['levels']['multiplier']:
                    highest_multiplier = max(highest_multiplier, self.config['levels']['multiplier'][role_id])
        return highest_multiplier

    def calculate_next_level_xp(self, level):
        return 75 + (level * 100)

    async def add_xp(self, user_id, member, channel, xp):
        user = self.get_user_data(user_id)
        multiplier = self.get_multiplier(member)
        new_xp = user['xp'] + int(xp * multiplier)
        new_level = user['level']
        next_level_xp = self.calculate_next_level_xp(new_level)

        level_up = False
        while new_xp >= next_level_xp:
            new_level += 1
            new_xp -= next_level_xp
            next_level_xp = self.calculate_next_level_xp(new_level)
            level_up = True

        self.collection.update_one(
            {'_id': user_id},
            {'$set': {'xp': new_xp, 'level': new_level}},
            upsert=True
        )

        if level_up:
            await self.check_rewards(member, channel, new_level)

        return new_level

    async def check_rewards(self, member, channel, level):
        if 'rewards' in self.config['levels']:
            roles_to_remove = [int(role_id) for role_id in self.config['levels'].get('roles', {}).keys()]
            roles_to_remove = [discord.utils.get(member.guild.roles, id=role_id) for role_id in roles_to_remove]

            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove)
                except discord.Forbidden:
                    print(f"Bot doesn't have permissions to remove roles from {member.display_name}.")
                except Exception as e:
                    print(f"Error removing roles: {e}")

            if str(level) in self.config['levels']['rewards']:
                role_id = int(self.config['levels']['rewards'][str(level)])
                role = discord.utils.get(member.guild.roles, id=role_id)
                if role:
                    try:
                        await member.add_roles(role)
                        if channel:
                            await channel.send(f'🎊 Congratulations {member.mention}! You are now **level {level}**.')
                    except discord.Forbidden:
                        print(f"Bot doesn't have permissions to add roles or send messages in #{channel.name}.")
                    except Exception as e:
                        print(f"Error adding role: {e}")

    def set_user_xp(self, user_id, xp):
        user = self.get_user_data(user_id)
        new_level = user['level']
        next_level_xp = self.calculate_next_level_xp(new_level)

        while xp >= next_level_xp:
            xp -= next_level_xp
            new_level += 1
            next_level_xp = self.calculate_next_level_xp(new_level)

        self.collection.update_one(
            {'_id': user_id},
            {'$set': {'xp': xp, 'level': new_level}},
            upsert=True
        )

    @commands.Cog.listener()
    async def on_message(self, message):       
        bucket = self.cd_mapping.get_bucket(message)
        
        if message.author.bot:
            return

        if 'levels' in self.config and 'whitelisted' in self.config['levels']:
            whitelisted_channels = map(str, self.config['levels']['whitelisted'])
            if str(message.channel.id) not in whitelisted_channels:
                return

        if message.author == self.bot.user:
            return

        prefix = get_prefix(self.bot, message)
        if not message.content.startswith(prefix):
            return

        command = message.content[len(prefix):].split()[0].lower()
        if command in self.bot_commands:
            return

        msg_sent_already = bucket.update_rate_limit()
        
        if msg_sent_already:
            return
           
        xp = random.randint(15, 40)
        new_level = await self.add_xp(message.author.id, message.author, message.channel, xp)
        
    @commands.command()
    async def level(self, ctx):
        user_data = self.get_user_data(ctx.author.id)
        current_level = user_data['level']
        current_xp = user_data['xp']
        next_level_xp = self.calculate_next_level_xp(current_level)
        xp_needed = next_level_xp - current_xp # will use it later
        await ctx.send(f'You are level {current_level} [{current_xp}/{next_level_xp}]')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_xp(self, ctx, member: discord.Member, xp: int):
        self.set_user_xp(member.id, xp)
        await ctx.send(f'{member.mention}\'s XP has been set to {xp}.')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_multiplier(self, ctx, role: discord.Role, multiplier: float):
        role_id = str(role.id)
        if 'multiplier' not in self.config['levels']:
            self.config['levels']['multiplier'] = {}
        self.config['levels']['multiplier'][role_id] = multiplier

        with open('dashboard.yaml', 'w') as file:
            yaml.safe_dump(self.config, file)

        await ctx.send(f'The XP multiplier for role {role.name} has been set to {multiplier}.')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_level(self, ctx, member: discord.Member, level: int):
        self.collection.update_one(
            {'_id': member.id},
            {'$set': {'level': level, 'xp': 0}},
            upsert=True
        )
        await ctx.send(f"{member.mention}'s level has been set to {level}")

async def setup(bot):
    await bot.add_cog(Leveling(bot))

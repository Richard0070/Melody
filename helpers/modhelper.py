import discord
from discord.ext import tasks, commands
import asyncio
from datetime import datetime, timedelta
import os
import json
import pymongo
import config
from humanize import naturaltime
import yaml

mongo_uri = config.MONGO
success_emoji = config.SUCCESS

class ModHelp:
    def __init__(self, bot):
        self.bot = bot
        self.last_dm_attempt = {}
        self.warn_count = {}
        self.data_file = "data/warn_count.json"
        self.mongo_client = pymongo.MongoClient(mongo_uri)
        self.db = self.mongo_client["Moderation"]
        self.cases_collection = self.db["cases2"]
        self.dm_status = True
        self.muted_users_file = "data/muted_users.json"
        self.check_mutes.start()
        self.auto_pardon.start()
        with open('dashboard.yaml', 'r') as file:
            self.config_yaml = yaml.safe_load(file)
        self.role_levels = self.config_yaml['role_levels']
        self.log_channels = self.config_yaml['log_channels']

    def save_data(self, user_id, warn_count):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                self.warn_count = json.load(f)

        user_id_str = str(user_id)
        if user_id_str in self.warn_count:
            self.warn_count[user_id_str] += warn_count

        else:
            self.warn_count[user_id_str] = warn_count

        with open(self.data_file, "w") as f:
            json.dump(self.warn_count, f, indent=4)

    async def send_dm(self, user, message, color):
        success = True
        now = datetime.utcnow()
        last_attempt = self.last_dm_attempt.get(user.id)

        if last_attempt and now - last_attempt < timedelta(minutes=5):
            return False

        try:
            dm_embed =discord.Embed(description=message, color=color)
            await user.send(embed=dm_embed)
            success = True
            self.dm_status = True
        except discord.Forbidden:
            self.last_dm_attempt[user.id] = now
            success = False
            self.dm_status = False
        except discord.HTTPException:
            self.last_dm_attempt[user.id] = now
            success = False
            self.dm_status = False

        return success

    async def notify_user(self, ctx, user, emoji, action, color, reason=None, duration=None):
        if reason is None:
            reason = "No reason provided"
        reason = self.add_attachments_to_reason(ctx, reason)
        success = await self.send_dm(
            user,
            f"{emoji} You have been {action}{' from' if action.lower() in ['banned', 'kicked'] else ' in'} **{ctx.guild.name}** for **{reason}**"
            +
            ('\n**Appeal Here:** [Redacted]\n**Invite Link:** https://discord.gg/PPuqNUfQhX'
             if action.lower() in ['banned', 'kicked'] else '') +
            (f'\n**Duration:** {duration}\n_ _' if action.lower() == 'muted'
             and duration is not None else ''), color)

        if success:
            return "(user notified with a direct message)"
        else:
            return "(couldn't notify the user with direct message)"

    def add_attachments_to_reason(self, ctx, reason):
        attachments = ctx.message.attachments
        
        if attachments:
            attachment_links = [
                f"{attachment.url}" for attachment in attachments
            ]
            reason_with_attachments = f"{reason} " + " ".join(
                attachment_links) + " "
            return reason_with_attachments
        else:
            return reason

    def generate_case_data(self, ctx, user_id, action, reason):
        case_count = self.cases_collection.count_documents({})
        case_id = case_count + 1
        if reason is None:
            reason = "No reason provided"
        reason = self.add_attachments_to_reason(ctx, reason)
        date = datetime.utcnow()

        action_data = {
            "case_id": case_id,
            "moderator": ctx.author.id,
            "date": date,
            "user": user_id,
            "action": action,
            "reason": reason,
            "hidden": False,
            "dm_status": self.dm_status
        }
        
        return action_data

    def generate_case_data_silent(self, ctx, user_id, action, reason, silent):
        case_count = self.cases_collection.count_documents({})
        case_id = case_count + 1
        if reason is None:
            reason = "No reason provided"
        reason = self.add_attachments_to_reason(ctx, reason)

        action_data = {
            "case_id": case_id,
            "moderator": ctx.author.id,
            "date": datetime.utcnow(),
            "user": user_id,
            "action": action,
            "reason": reason,
            "hidden": False,
            "dm_status": silent
        }
        return action_data

    def get_warn_count(self):
        try:
            with open(self.data_file, "r") as f:
                self.warn_count = json.load(f)
        except FileNotFoundError:
            self.warn_count = {}
        return self.warn_count

    def set_warn_count(self, user_id, warn_count):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                self.warn_count = json.load(f)

        user_id_str = str(user_id)
        if user_id_str in self.warn_count:
            self.warn_count[user_id_str] = warn_count

        else:
            self.warn_count[user_id_str] = warn_count

        with open(self.data_file, "w") as f:
            json.dump(self.warn_count, f, indent=4)

    async def set_warns(self, ctx, user: discord.User, count: int):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send("You don't have permission to set warns.")
            return

        self.set_warn_count(str(user.id), count)

    async def show_warns(self, ctx, user: discord.User):
        warn_count = self.get_warn_count()
        user_warns = warn_count.get(str(user.id), 0)
        await ctx.send(
            f"**{user.name}#{user.discriminator}** has **{user_warns}** warns."
        )

    @tasks.loop(minutes=1)
    async def check_mutes(self):
        await self.check_expired_mutes()

    async def mute_user(self,
                        ctx,
                        user: discord.Member,
                        duration: str = None,
                        reason: str = None):
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(
                name="Muted", reason="Mute functionality")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False)

        await user.add_roles(muted_role)
        
        unmute_time = None
        if duration:
            unmute_time = self.parse_duration(duration)

        mute_data = {
            "user_id": str(user.id),
            "unmute_time": str(unmute_time),
            "reason": reason,
            "guild_id": str(ctx.guild.id)
        }

        try:
            with open(self.muted_users_file, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}

        if str(user.id) in data:
            del data[str(user.id)]

        data[str(user.id)] = mute_data

        with open(self.muted_users_file, "w") as f:
            json.dump(data, f, indent=4)

        if unmute_time:
            await self.schedule_unmute(ctx, user, unmute_time)

    def parse_duration(self, duration: str) -> datetime:
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        duration = duration.lower().strip()
        total_seconds = 0

        while duration:
            for unit in multipliers:
                if duration.endswith(unit):
                    value = int(duration[:-1])
                    total_seconds += value * multipliers[unit]
                    duration = duration[:-1]
                    break
            else:
                value = int(duration)
                total_seconds += value
                break

        return datetime.utcnow() + timedelta(seconds=total_seconds)

    async def schedule_unmute(self, ctx, user: discord.Member,
                              unmute_time: datetime):
        now = datetime.utcnow()
        time_until_unmute = (unmute_time -
                             now).total_seconds() if unmute_time else 0
        await asyncio.sleep(time_until_unmute)

        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role in user.roles:
            await user.remove_roles(muted_role)

        with open(self.muted_users_file, "r+") as f:
            data = json.load(f)
            if str(user.id) in data:
                del data[str(user.id)]
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

    def generate_case_data_for_mute(self, ctx, user_id, action, reason,
                                    duration):
        case_count = self.cases_collection.count_documents({})
        case_id = case_count + 1
        if reason is None:
            reason = "No reason provided"
        reason = self.add_attachments_to_reason(ctx, reason)
        if duration is None:
            duration = "Indefinitely"

        action_data = {
            "case_id": case_id,
            "moderator": ctx.author.id,
            "date": datetime.utcnow(),
            "user": user_id,
            "action": action,
            "reason": reason,
            "hidden": False,
            "dm_status": self.dm_status,
            "duration": duration
        }
        return action_data

    async def check_expired_mutes(self):
        now = datetime.utcnow()
        with open(self.muted_users_file, "r+") as f:
            data = json.load(f)
            for user_id, mute_data in list(data.items()):
                try:
                    if mute_data["unmute_time"] is not None:
                        unmute_time = datetime.fromisoformat(
                            mute_data["unmute_time"])
                        if now > unmute_time:
                            guild_id = int(mute_data["guild_id"])
                            guild = self.bot.get_guild(guild_id)
                            if guild:
                                user = guild.get_member(int(user_id))
                                if user:
                                    muted_role = discord.utils.get(
                                        guild.roles, name="Muted")
                                    if muted_role in user.roles:
              
                                        await user.remove_roles(muted_role)
                                        del data[user_id]
                except ValueError:
                    pass

            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    async def unmute_user(self, ctx, user: discord.Member):
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role in user.roles:
            await user.remove_roles(muted_role)

        try:
            with open(self.muted_users_file, "r+") as f:
                data = json.load(f)
                if str(user.id) in data:
                    del data[str(user.id)]
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
        except FileNotFoundError:
            pass

    async def get_cases(self, user):
        query = {}
        if user:
            query["moderator"] = user.id

        cases = self.cases_collection.find(query)

        return list(cases)

    def chunk_cases(self, prefix, cases, user):
        prefix = prefix
        cases = sorted(cases, key=lambda x: x['date'], reverse=True)
        chunks = [cases[i:i + 10] for i in range(0, len(cases), 10)]

        embeds = []

        for i, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(title="‎", color=0xe0ebff)
            embed.set_author(
                name=
                f"Most recent cases {i}-{i+len(chunk)-1} of {len(cases)} by {user.name}#{user.discriminator}",
                icon_url=user.avatar.url
                if user.avatar else user.default_avatar.url)
            description = ""

            actions = {
                "warn": "⚠️",
                "mute": "🔇",
                "kick": "👢",
                "ban": "🔨",
                "unmute": "🔊",
                "unban": f"☑️",
                "unkick": f"☑️",
                "note": "📝"
            }

            for case in chunk:
                if case.get('hidden'):
                    continue

                action = case["action"]
                dm_status = case.get("dm_status", False)
                reason = case["reason"]
                emoji = actions.get(action, "❓")
                date_diff = datetime.utcnow() - case["date"]
                if dm_status == True:
                    dm_message = "__[User notified with a direct message]__"
                elif dm_status == "silent":
                    dm_message = "__[Punishment executed silently]__"
                else:
                    dm_message = "__[Failed to message user: Cannot send messages to this user]__"

                if date_diff >= timedelta(days=7):
                    timestamp = case["date"].strftime("%b %d, %Y")
                else:
                    timestamp = naturaltime(date_diff)

                if len(reason) > 170:
                    reason = reason[:167] + "..."

                description += f"{emoji} **`{case['action'].upper()}`** `[{timestamp}]` #{case['case_id']} {dm_message} {reason}\n"

            embed.description = description
            embed.description += f"\nUse `{prefix}case <num>` to see more information about an individual case\nUse `{prefix}cases <user>` to see a specific user's cases\n"
            embeds.append(embed)
        return embeds
        
    async def auto_warn_pardon(self):
        warn_cases = self.cases_collection.find({"action": "warn"})
        current_time = datetime.utcnow()
        warns = self.load_warn_counts()

        for case in warn_cases:
            case_time = case["date"]
            if current_time - case_time > timedelta(days=30):
                user_id = str(case["user"])
                if user_id in warns and warns[user_id] > 0:
                    warns[user_id] -= 1
                    if warns[user_id] == 0:
                        del warns[user_id]

        self.save_warn_counts(warns)

    def load_warn_counts(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as file:
                return json.load(file)
        return {}

    def save_warn_counts(self, warns):
        with open(self.data_file, 'w') as file:
            json.dump(warns, file)

    @tasks.loop(hours=24)
    async def auto_pardon(self):
        await self.auto_warn_pardon()

    @auto_pardon.before_loop
    async def before_auto_pardon(self):
        await self.bot.wait_until_ready()

    def get_role_level(self, member: discord.Member):
        max_level = 0 
        relevant_roles = [role for role in member.roles if role.id in self.role_levels]

        for role in relevant_roles:
            level = self.role_levels.get(role.id, 0)
            if level > max_level:
                max_level = level

        return max_level

    async def has_higher_role(self, ctx, target_user):
        if not ctx.guild:
            raise commands.CheckFailure("⚠ Command must be used in a guild.")

        if not ctx.guild.me.guild_permissions.ban_members:
            raise commands.CheckFailure("⚠ I do not have permission to ban members.")
            

        author = ctx.author
        bot_level = self.get_role_level(ctx.guild.me)

        try:
            target_member = ctx.guild.get_member(target_user.id)
            if target_member:
                target_level = self.get_role_level(target_member)
            else:
                target_level = 0       
        except:
            target_level = 0

        author_level = self.get_role_level(author)

        if author_level <= target_level:
            raise commands.CheckFailure(f"⚠ Failed: target permission level is equal or higher to yours, {target_level} >= {author_level}")
            
        return True

    async def check_permission(self, ctx, user):
        try:
            await self.has_higher_role(ctx, user)
            return True
        except commands.CheckFailure as e:
            await ctx.send(e)

    async def case_logging(self, ctx, user, moderator, action, case_id, reason=None):
      channel_id = self.log_channels.get("case_logs")
      channel = ctx.guild.get_channel(channel_id)
      if reason is None:
          reason = "No reason provided"

      if len(reason) > 1024:
          reason = reason[:1021] + "..."
           
      if action == "warn":
        title = "⚠️ WARN"
        embed_color = 0xffec00
      elif action == "kick":
        title = "👢 KICK"
        embed_color = 0xcd5906
      elif action == "ban":
        title = "🔨 BAN"
        embed_color = 0xff0000
      elif action == "unmute":
        title = "🔊 UNMUTE"
        embed_color = 0x00e357
      elif action == "unban":
        title = f"☑️ UNBAN"
        embed_color = 0x00e357
      else:
        title = "📝 NOTE"
        embed_color = 0xb000dc

      old_date = datetime.utcnow()
      date = old_date.strftime("%b %d, %Y at %H:%M")
        
      if channel:
        embed = discord.Embed(title=f"{title} - Case #{case_id}", color=embed_color)
        embed.add_field(name="User", value=f"{user.name}#{user.discriminator}\n{user.mention}", inline=False)
        embed.add_field(name="Moderator", value=f"{moderator.name}#{moderator.discriminator}\n{moderator.mention}", inline=False)   
        embed.add_field(name=f"{moderator.name}#{moderator.discriminator} at {date} UTC", value=reason, inline=False)
        embed.set_footer(text=f"Case generated on {date} UTC")
        await channel.send(embed=embed)
      else:
        print("Channel not found. Please check the channel ID in mod-config.yaml.")
          
    async def case_logging_for_mute(self, ctx, user, moderator, case_id, duration, reason=None):
      channel_id = self.log_channels.get("case_logs")
      channel = ctx.guild.get_channel(channel_id)
                
           
      title = "🔇 MUTE"
      old_date = datetime.utcnow()
      date = old_date.strftime("%b %d, %Y at %H:%M")
  
      if reason is None:
          reason = "No reason provided"

      if len(reason) > 1024:
          reason = reason[:1021] + "..."
      if duration is None:
          duration = "Indefinitely"
          
      if channel:
        embed = discord.Embed(title=f"{title} - Case #{case_id}", color=0xe2e2e2)
        embed.add_field(name="User", value=f"{user.name}#{user.discriminator}\n{user.mention}", inline=False)
        embed.add_field(name="Moderator", value=f"{moderator.name}#{moderator.discriminator}\n{moderator.mention}", inline=False)   
        embed.add_field(name=f"{moderator.name}#{moderator.discriminator} at {date} UTC", value=f"({duration}) - {reason}", inline=False)
        embed.set_footer(text=f"Case generated on {date} UTC")
        await channel.send(embed=embed)
      else:
        print("Channel not found. Please check the channel ID in mod-config.yaml.")

    def add_attachments_to_reason_log(self, ctx, reason):
        attachments = ctx.message.attachments
        if reason is None:
            reason = "No reason provided"
        if attachments:
            attachment_links = [
                f"{attachment.url}" for attachment in attachments
            ]
            reason_with_attachments = f"{reason} " + " ".join(
                attachment_links) + " "
            return reason_with_attachments
        else:
            return reason
            
    async def punishments(self, ctx, user: discord.Member):
        warn_count = self.get_warn_count().get(str(user.id), 0)
        duration = "0s"
        wc = 0

        if warn_count == 2:
            duration = "30m"
            wc = 2
        elif warn_count == 4:
            duration = "2h"
            wc = 4
        elif warn_count == 6:
            duration = "6h"
            wc = 6
        elif warn_count == 8:
            duration = "24h"
            wc = 8
        elif warn_count >= 10:
            reason = "Autoban for reaching 10 warns"
            action_data = self.generate_case_data(ctx, user.id, "ban", reason)
            self.cases_collection.insert_one(action_data)

            await self.case_logging(ctx, user, self.bot.user, "ban", action_data['case_id'], reason)
            await self.notify_user(ctx, user, "🔨", "banned", reason)
            await ctx.guild.ban(user, reason=reason)
            
            return
            
        if wc > 0:
            reason = f"Exceeded warn limit - {wc} warns"
            action_data = self.generate_case_data_automod_log(user.id, self.bot.user,  duration, reason)
            self.cases_collection.insert_one(action_data)

            await self.case_logging_for_mute(ctx, user, self.bot.user, action_data['case_id'], duration, reason)
            await self.mute_user(ctx, user, duration, reason)            

    def generate_case_data_automod_log(self, user_id, moderator, duration, reason):
        case_count = self.cases_collection.count_documents({})
        case_id = case_count + 1

        action_data = {
            "case_id": case_id,
            "moderator": moderator.id,
            "date": datetime.utcnow(),
            "user": user_id,
            "action": "mute",
            "reason": reason,
            "hidden": False,
            "dm_status": "silent",
            "duration": duration
        }
        return action_data     
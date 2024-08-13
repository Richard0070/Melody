import discord
from discord.ext import commands
import pymongo
from datetime import datetime, timedelta
from helpers.modhelper import ModHelp
from humanize import naturaltime
import re
import asyncio
import yaml
import config
from config import is_staff

success_emoji = config.SUCCESS
mongo_uri = config.MONGO

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helper = ModHelp(bot)
        self.mongo_client = pymongo.MongoClient(mongo_uri)
        self.db = self.mongo_client["Moderation"]
        self.cases_collection = self.db["cases2"]

    @commands.command(name="warn", usage="<user> (reason)", description="Warns a user.")
    @commands.check(is_staff)
    async def warn(self, ctx, user: discord.Member, *, reason: str = None):
        if not await self.helper.check_permission(ctx, user): return

        notify_msg = await self.helper.notify_user(ctx, user, "⚠️", "warned", 0xffcc00, reason)

        action_data = self.helper.generate_case_data(ctx, user.id, "warn", reason)
        self.helper.cases_collection.insert_one(action_data)
        self.helper.save_data(user.id, 1)

        msg = f"{success_emoji} Warned **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"
        msg += f" {notify_msg}"
        await ctx.send(msg)

        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        
        await self.helper.case_logging(ctx, user, ctx.author, "warn", action_data['case_id'], reason)
        await self.helper.punishments(ctx, user)                
    @commands.command(name="mute", usage="<user> <optional_duration> (reason)", description="Mutes a user.")
    @commands.check(is_staff)
    async def mute(self, ctx, user: discord.Member, *, args: str = None):
        duration = None
        reason = None
        if not await self.helper.check_permission(ctx, user): return
        if args:
            split_args = args.split()
            for arg in split_args:
              if re.match(r'\d+[hms]', arg):
                  duration = arg
              else:
                if reason is None:
                    reason = arg
                else:
                    reason += ' ' + arg
                    
            
        notify_msg = await self.helper.notify_user(ctx, user, "🔇", "muted", 0xeff4fe, reason, duration)

        action_data = self.helper.generate_case_data_for_mute(ctx, user.id, "mute", reason, duration)
        self.helper.cases_collection.insert_one(action_data)           
        msg = f"{success_emoji} Muted **{user.name}#{user.discriminator}**"
            
        msg += f" (Case #{action_data['case_id']}) {notify_msg}"
        await ctx.send(msg)
        await self.helper.mute_user(ctx, user, duration, reason)

        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        await self.helper.case_logging_for_mute(ctx, user, ctx.author, action_data['case_id'], duration, reason)
        
    @commands.command(name="unmute", usage="<user> (reason)", description="Unmutes a user.")
    @commands.check(is_staff)
    async def unmute(self, ctx, user: discord.Member, *, reason: str = None):

        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        
        if muted_role not in user.roles:
          await ctx.send("⚠ User isn't muted.")
          return

        notify_msg = await self.helper.notify_user(ctx, user, "🔊", "unmuted", 0x7fff55, reason)

        action_data = self.helper.generate_case_data(ctx, user.id, "unmute", reason)
        self.helper.cases_collection.insert_one(action_data)           
        msg = f"{success_emoji} Unmuted **{user.name}#{user.discriminator}**"

        msg += f" (Case #{action_data['case_id']}) {notify_msg}"
        await ctx.send(msg)
        await self.helper.unmute_user(ctx, user)
        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        await self.helper.case_logging(ctx, user, ctx.author, "unmute", action_data['case_id'], reason)

    @commands.command(name="ban", usage="<user> [-silent] (reason)", aliases=["yeet"], description="Bans a user.")
    @commands.check(is_staff)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.User, *args: str):
        if not await self.helper.check_permission(ctx, user): return
        
        reason = None
        silent = False

        for arg in args:
          if arg.lower() == "-silent":
            silent = True
          else:
            if reason is None:
                reason = arg
            else:
                reason += ' ' + arg
                

        bans = [entry async for entry in ctx.guild.bans(limit=None)]
        if user in [ban.user for ban in bans]:
          await ctx.send("⚠ User is already banned.")
          return

        if silent:                  
          action_data = self.helper.generate_case_data_silent(ctx, user.id, "ban", reason, "silent")
          msg = f"{success_emoji} Banned **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"
        else:
          notify_msg = await self.helper.notify_user(ctx, user, "🔨", "banned", 0xff0000, reason)  
          action_data = self.helper.generate_case_data(ctx, user.id, "ban", reason)
          msg = f"{success_emoji} Banned **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"
          msg += f" {notify_msg}"
        self.helper.cases_collection.insert_one(action_data)
        
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(msg)
        await self.helper.set_warns(ctx, user, 0)

        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        await self.helper.case_logging(ctx, user, ctx.author, "ban", action_data['case_id'], reason)

    @commands.command(name="kick", usage="<user> [-silent] (reason)", description="Kicks a user.")
    @commands.check(is_staff)
    @commands.has_permissions(ban_members=True)
    async def kick(self, ctx, user: discord.User, *args: str):
        if not await self.helper.check_permission(ctx, user): return
        reason = None
        silent = False

        for arg in args:
          if arg.lower() == "-silent":
            silent = True
          else:
            if reason is None:
                reason = arg
            else:
                reason += ' ' + arg
                

        if silent:          
          action_data = self.helper.generate_case_data_silent(ctx, user.id, "kick", reason, "silent")
          msg = f"{success_emoji} Kicked **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"
        else:
          notify_msg = await self.helper.notify_user(ctx, user, "👢", "kicked", 0xc86049, reason)  
          action_data = self.helper.generate_case_data(ctx, user.id, "kick", reason)
          msg = f"{success_emoji} Kicked **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"
          msg += f" {notify_msg}"
        self.helper.cases_collection.insert_one(action_data)
        
        await ctx.guild.kick(user, reason=reason)
        await ctx.send(msg)
        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        await self.helper.case_logging(ctx, user, ctx.author, "kick", action_data['case_id'], reason)
            
    @commands.command(name="unban", usage="<user> (reason)", description="Unbans a user.")
    @commands.check(is_staff)
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str = None):

        bans = [entry async for entry in ctx.guild.bans(limit=None)]
        if user not in [ban.user for ban in bans]:
          await ctx.send("⚠ User is not banned.")
          return

        action_data = self.helper.generate_case_data(ctx, user.id, "unban", reason)
        msg = f"{success_emoji} Unbanned **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"

        self.helper.cases_collection.insert_one(action_data)
        await ctx.guild.unban(user, reason=reason)      
        await ctx.send(msg)

        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        await self.helper.case_logging(ctx, user, ctx.author, "unban", action_data['case_id'], reason)
            
    @commands.command(name="note", usage="<user> (add your note)", description="Adds a note to a user.")
    @commands.check(is_staff)
    async def note(self, ctx, user: discord.User, *, reason: str = None):
        action_data = self.helper.generate_case_data(ctx, user.id, "note", reason)
        self.helper.cases_collection.insert_one(action_data)
        msg = f"{success_emoji} Note (Case #{action_data['case_id']}) added on **{user.name}#{user.discriminator}**"
        await ctx.send(msg)
        reason = self.helper.add_attachments_to_reason_log(ctx, reason)
        await self.helper.case_logging(ctx, user, ctx.author, "note", action_data['case_id'], reason)

    @commands.command(name="case", usage="<case_id>", description="Shows details of a case.")
    @commands.check(is_staff)
    async def case(self, ctx, case_id: int):
        case_data = self.cases_collection.find_one({"case_id": case_id})

        if case_data:
            moderator_id = case_data["moderator"]
            user_id = case_data["user"]
            
            user = ctx.guild.get_member(user_id)
            if user is None:
              try:
                user = await self.bot.fetch_user(user_id)
              except discord.NotFound:
                user = None

            moderator = ctx.guild.get_member(moderator_id)
            if moderator is None:
              try:
                moderator = await self.bot.fetch_user(moderator_id)
              except discord.NotFound:
                moderator = None
                
            date = case_data["date"].strftime("%b %d, %Y at %H:%M")
            action = case_data["action"]
            original_reason = case_data["reason"]
            updated_reasons = case_data.get("updated_reasons", [])

            if len(original_reason) > 1024:
                original_reason = original_reason[:1021] + "..."

            if action == "warn":
                title = "⚠️ WARN"
            elif action == "mute":
                title = "🔇 MUTE"
            elif action == "kick":
                title = "👢 KICK"
            elif action == "ban":
                title = "🔨 BAN"
            elif action == "unmute":
                title = "🔊 UNMUTE"
            elif action == "unban":
                title = f"☑️ UNBAN"
            else:
                title = "📝 NOTE"

            embed = discord.Embed(title=f"{title} - Case #{case_id}", color=0xcf25ff)
            embed.add_field(name="User", value=f"{user.name}#{user.discriminator}\n{user.mention}", inline=False)
            embed.add_field(name="Moderator", value=f"{moderator.name}#{moderator.discriminator}\n{moderator.mention}", inline=False)
            embed.add_field(name=f"{moderator.name}#{moderator.discriminator} at {date} UTC", value=original_reason, inline=False)

            for index, updated_reason in enumerate(updated_reasons, start=1):
                updater_mod = ctx.guild.get_member(updated_reason['moderator'])
                update_info = f"{updater_mod.name}#{updater_mod.discriminator} at {updated_reason['date'].strftime('%b %d, %Y at %H:%M')} UTC"
                if len(updated_reason['reason']) > 1024:
                    updated_reason['reason'] = updated_reason['reason'][:1021] + "..."
                embed.add_field(name=update_info, value=updated_reason['reason'], inline=False)

            embed.set_footer(text=f"Case generated on {date} UTC")

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠ Case not found.")

    @commands.command(name="delcase", aliases=["casedel", "deletecase", "casedelete"], usage="<case_id>", description="Deletes a case.")
    @commands.has_permissions(manage_guild=True)
    async def delcase(self, ctx, case_id: int):
        result = self.cases_collection.delete_one({"case_id": case_id})
        if result.deleted_count == 1:
            await ctx.send(f"{success_emoji} Case `#{case_id}` deleted.")
        else:
            await ctx.send(f"⚠ Case not found.")

    @commands.command(name="update", usage="<case_id> <new_reason>", description="Updates a case.")
    @commands.check(is_staff)
    async def update(self, ctx, case_id: int, *, new_reason: str = None):
        if new_reason is None and not ctx.message.attachments:
            await ctx.send("⚠ Please provide a new reason or attachment to update the case.")
            return

        if new_reason == None:
            new_reason = ""
        new_reason = self.helper.add_attachments_to_reason(ctx, new_reason)
        update_data = {
            "moderator": ctx.author.id,
            "date": datetime.utcnow(),
            "reason": new_reason
        }
        result = self.cases_collection.update_one({"case_id": case_id}, {"$push": {"updated_reasons": update_data}})
        if result.modified_count == 1:
            await ctx.send(f"{success_emoji} Case `#{case_id}` updated.")
        else:
            await ctx.send(f"⚠ Case not found or unable to update.")

    @commands.command(name="cases", usage="<user> [-hidden]", description="Shows all cases of a user.")
    @commands.check(is_staff)
    async def cases(self, ctx, user: discord.User = None, *, flag: str = ""):
        
        if user is None:
            user = ctx.author
            
        prefix = ctx.prefix
        show_hidden = flag.lower() == "-hidden"

        if show_hidden:
            user_cases = self.cases_collection.find({"user": user.id})
        else:
            user_cases = self.cases_collection.find({"user": user.id, "hidden": False})

        total_cases = 0
        hidden_count = 0
        for _ in user_cases:
            total_cases += 1
        user_cases.rewind()

        actions = {
            "warn": "⚠️",
            "mute": "🔇",
            "kick": "👢",
            "ban": "🔨",
            "unmute": "🔊",
            "unban": f"☑️",
            "note": "📝"
        }

        embeds = []
        case_count = 0
        description = ""
        for case_data in user_cases:
            case_count += 1
            action = case_data["action"]
            date_difference = datetime.utcnow() - case_data["date"]
            if date_difference >= timedelta(days=7):
                timestamp = case_data["date"].strftime("%b %d, %Y")    

            else:
                timestamp = naturaltime(date_difference)

            original_reason = case_data["reason"]
            updated_reasons = case_data.get("updated_reasons", [])
            emoji = actions.get(action, "❓")
            dm_status = case_data.get("dm_status", False)

            if len(original_reason) > 170:
                original_reason = original_reason[:167] + "..."
            
            if action.lower() == "mute":
                duration = f'**({case_data.get("duration", "")})** -'
            else:
                duration = ""
                
            if dm_status == True:
                dm_message = "__[User notified with a direct message]__"
            elif dm_status == "silent":
                dm_message = "__[Punishment executed silently]__"
            else:
                dm_message = "__[Failed to message user: Cannot send messages to this user]__"

            if updated_reasons:
                new_reason = updated_reasons[-1]["reason"]
                full_reason = f"{original_reason} **[Updated]** {new_reason}"

                if len(full_reason) > 180:
                    full_reason = full_reason[:177] + "..."

                if action.lower() in ["note", "unban", "unkick"]:
                    description += f"{emoji} **`{action.upper()}`** `[{timestamp}]` `#{case_data['case_id']}` {full_reason}\n"
                else:
                    description += f"{emoji} **`{action.upper()}`** `[{timestamp}]` `#{case_data['case_id']}` {dm_message} {duration} {full_reason}\n"

            else:

                if action.lower() in ["note", "unban", "unkick"]:
                    description += f"{emoji} **`{action.upper()}`** `[{timestamp}]` `#{case_data['case_id']}` {original_reason}\n"
                else:
                    description += f"{emoji} **`{action.upper()}`** `[{timestamp}]` `#{case_data['case_id']}` {dm_message} {duration} {original_reason}\n"

            if case_count >= 10:
                embed = discord.Embed(color=0xe0ebff)
                embed.set_author(name=f"Cases {case_count-9}-{case_count} of {total_cases} for {user.name}#{user.discriminator}",
                                 icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
                embed.description = description
                embeds.append(embed)
                description = ""
                case_count = 0

        hidden_cases = self.cases_collection.find({"user": user.id})

        total_cases_count = 0

        for _ in hidden_cases:
            total_cases_count += 1
        hidden_cases.rewind()

        for case_data2 in hidden_cases:
            if case_data2.get("hidden") == True:
                hidden_count += 1

        if total_cases_count == 0 and not show_hidden:
            await ctx.send(f"No cases found for **{user.name}#{user.discriminator}**")

        elif total_cases == 0 and hidden_count:
            await ctx.send(f"No normal cases found for **{user.name}#{user.discriminator}**. Use `-hidden` to show {hidden_count} hidden case(s).")

        elif total_cases != 0 and description:
            embed = discord.Embed(title="‎", color=0xe0ebff)
            embed.set_author(name=f"Cases {total_cases - case_count + 1}-{total_cases} of {total_cases} for {user.name}#{user.discriminator}",
                             icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.description = description

            if not show_hidden:
                if hidden_count:
                    embed.description += f"\n*+{hidden_count} hidden cases, use `-hidden` to show them.*"
                else:
                    embed.description += f"\nUse `{prefix}case <num>` to see more information about an individual case."
            if show_hidden:
                embed.description += f"\nUse `{prefix}case <num>` to see more information about an individual case."

            embeds.append(embed)

        for embed in embeds:
            await ctx.send(embed=embed)

    @commands.command(name="unhidecase", usage="<case_id>", description="Unhides a case.")
    @commands.check(is_staff)
    async def unhidecase(self, ctx, *case_ids: int):
        if not case_ids:
            await ctx.send("Please provide at least one case ID.")
            return

        if len(case_ids) == 1:
            case_ids = [case_ids[0]]

        result = self.cases_collection.update_many({"case_id": {"$in": case_ids}}, {"$set": {"hidden": False}})

        await ctx.send(f"{success_emoji} {result.modified_count} cases are now unhidden!")

    @commands.command(name="hidecase", usage="<case_id>", description="Hides a case.")
    @commands.check(is_staff)
    async def hidecase(self, ctx, *case_ids: int):
        if not case_ids:
            await ctx.send("Please provide at least one case ID.")
            return

        if len(case_ids) == 1:
            case_ids = [case_ids[0]]

        result = self.cases_collection.update_many({"case_id": {"$in": case_ids}}, {"$set": {"hidden": True}})

        await ctx.send(f"{success_emoji} {result.modified_count} cases are now hidden! Use `unhidecase` to unhide them.")

    @commands.command(name="warns", usage="<user> [-set] (amount)", description="Shows/sets the warn count of a user.")
    @commands.check(is_staff)
    async def warns(self, ctx, user: discord.User, *, arg: str = None):
      if arg is None:
        await self.helper.show_warns(ctx, user)
        return

      parts = arg.split()
      flag = parts[0] if parts else None
      count = int(parts[1]) if len(parts) > 1 else None

      if flag and flag.lower() == "-set":
        if count is None:
          await ctx.send("⚠ Please provide a count to set warns.")
          return
        await self.helper.set_warns(ctx, user, count)        
        await ctx.send(f"{success_emoji} **{user.name}#{user.discriminator}'s** warn count set to **{count}**.")
      else:
         await self.helper.show_warns(ctx, user)
          
    @commands.command(name="modcases", usage="<user>", description="Shows all mod cases of a user.")
    @commands.check(is_staff)
    async def modcases(self, ctx, user: discord.User = None):
        
      prefix = ctx.prefix
        
      if user is None:
          user = ctx.author

      cases = await self.helper.get_cases(user)

      if not cases:
          await ctx.send(f"No modcases found for **{user.name}#{user.discriminator}**")
          return


      chunked_embeds = self.helper.chunk_cases(prefix, cases, user)

      current_page = 0
      total_pages = len(chunked_embeds)

      embed_message = await ctx.send(embed=chunked_embeds[current_page])

      if total_pages > 1:
        await embed_message.add_reaction("⬅️")
        await embed_message.add_reaction("➡️")

      def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

      while True:
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)

            if str(reaction.emoji) == "➡️" and current_page < total_pages - 1:
                current_page += 1
                await embed_message.edit(embed=chunked_embeds[current_page])
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await embed_message.edit(embed=chunked_embeds[current_page])

            await embed_message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            break

    @commands.command(name="massban", usage="<user 1> <user 2>", description="Bans multiple users at once.")
    @commands.has_permissions(manage_guild=True)
    @commands.check(is_staff)
    async def massban(self, ctx, users: commands.Greedy[discord.User]):
        
        if not users:
            await ctx.send("⚠ Please provide at least one user to ban.")
            return

        await ctx.send("What would be the reason for massban? 'skip' to continue without putting a reason. 'cancel' to cancel the massban")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            reason_msg = await self.bot.wait_for("message", timeout=60, check=check)
            reason = reason_msg.content.strip()
            
            if reason.lower() == "cancel":
                await ctx.send("Massban cancelled.")
                return

            if reason == "":
                reason = "No reason provided."
                
            if reason_msg.attachments:
                attachment_urls = [attachment.url for attachment in reason_msg.attachments]
                reason += " " + " ".join(attachment_urls)
                
            for user in users:
            
                if not ctx.guild.get_member(user.id):
                    await ctx.send(f"⚠ {user.name}#{user.discriminator} is not a member of this guild.")
                    continue

                if not await self.helper.check_permission(ctx, user):
                    continue 

                bans = [entry async for entry in ctx.guild.bans(limit=None)]
                if user in [ban.user for ban in bans]:
                    await ctx.send(f"⚠ {user.name}#{user.discriminator} is already banned.")
                    continue

                try:
                    notify_msg = await self.helper.notify_user(ctx, user, "🔨", "banned", 0xff0000, reason)
                    await ctx.guild.ban(user, reason=reason)
                    action_data = self.helper.generate_case_data_silent(ctx, user.id, "ban", reason, "silent")
                    self.helper.cases_collection.insert_one(action_data)
                                    
                    await self.helper.set_warns(ctx, user, 0)
                    reason = self.helper.add_attachments_to_reason_log(ctx, reason)
                    await self.helper.case_logging(ctx, user, ctx.author, "ban", action_data['case_id'], reason)
                    
                    msg = f"{success_emoji} Banned **{user.name}#{user.discriminator}** (Case #{action_data['case_id']})"
                    msg += f" {notify_msg}"
                    await ctx.send(msg)
                except discord.Forbidden:
                    await ctx.send(f"⚠ Failed to ban **{user.name}#{user.discriminator}**. Missing permissions.")
                except discord.HTTPException as e:
                    await ctx.send(f"⚠ An error occurred while banning **{user.name}#{user.discriminator}**: {str(e)}")

        except asyncio.TimeoutError:
            await ctx.send("⚠ Timeout reached. Massban cancelled.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))

import discord
from discord.ext import commands
from config import is_staff

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="post", aliases=['send'], usage="-c <channel> -m <message>", description="Send a message through the bot")
    @commands.has_permissions(manage_guild=True)
    @commands.check(is_staff)
    async def _post(self, ctx, *, args=None):
        
        if args is None:
            await ctx.send("You need to provide a message!")
            return
        
        args = args.split(' ')
        channel = ctx.channel
        message = ""
        i = 0
        while i < len(args):
            if args[i] == '-c' and i + 1 < len(args):
                channel = discord.utils.get(ctx.guild.channels, mention=args[i + 1])
                i += 1
            elif args[i] == '-m' and i + 1 < len(args):
                message = ' '.join(args[i + 1:])
                break
            i += 1

        if not message:
            await ctx.send("You need to provide a message after -m!")
            return

        if not channel:
            await ctx.send("The specified channel was not found!")
            return
        
        await channel.send(message)

    @commands.command(name="avatar", aliases=["av"], usage="<optional_user>", description="Get a user's avatar")
    @commands.check(is_staff)
    async def avatar(self, ctx, user: discord.Member = None):
        if user is None:
            user = ctx.author

        av = user.avatar.url if user.avatar else user.default_avatar.url
        embed = discord.Embed(title=f"Avatar of **{user.name}**", color=0xcda69b)
        embed.set_image(url=av)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))

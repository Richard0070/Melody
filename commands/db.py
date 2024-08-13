import discord
from discord.ext import commands
from pymongo import MongoClient
import config

MONGO_DB = config.MONGO
cluster = MongoClient(MONGO_DB)

async def is_dev(ctx):
    allowed_ids = [918862839316373554]
    return ctx.author.id in allowed_ids

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='database', usage="<database> <collection>", aliases=['db'], description='Fetches all data from the database')
    @commands.check(is_dev)
    async def db(self, ctx, db_name: str, collection_name: str):
        db = cluster[db_name]
        collection = db[collection_name]
        cursor = collection.find({})

        content = [doc for doc in cursor]

        if not content:
            await ctx.reply(f"{config.ERROR} The collection is empty.", allowed_mentions=discord.AllowedMentions.none())
            return

        formatted_content = '\n'.join(str(doc) for doc in content)

        chunks = [formatted_content[i:i + 1600] for i in range(0, len(formatted_content), 1600)]

        for chunk in chunks:
            await ctx.send(f"🗂️ `{db_name}` :: 📂 `{collection_name}`\n\n```py\n{chunk}\n```")

    @commands.command(name='delete_database', usage="<database> <collection>", aliases=['deldb', 'delete_db'], description='Deletes an entire collection')
    @commands.check(is_dev)
    async def del_db(self, ctx, db_name: str, collection_name: str):
        db = cluster[db_name]
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
            await ctx.send(f"{config.SUCCESS} Collection `{collection_name}` from database `{db_name}` has been deleted.")
        else:
            await ctx.send(f"❌ Collection `{collection_name}` does not exist in database `{db_name}`.")

async def setup(bot):
    await bot.add_cog(Database(bot))
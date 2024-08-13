import json
import discord
from discord import app_commands
from discord.ext import commands
import os
import config

class FAQs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add-faq", description="Add frequently asked question")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(question="What will be the question?")
    @app_commands.describe(answer="What will be the answer?")
    async def _add_faq(self, interaction: discord.Interaction, question: str, answer: str):
        questions_file = 'data/faqs.json'
        if not os.path.exists(questions_file):
            with open(questions_file, 'w') as f:
                json.dump({"questions": []}, f, indent=4)

        with open(questions_file, 'r+') as f:
            data = json.load(f)
            question_number = len(data["questions"]) + 1

            question_data = {
                "question": question,
                "answer": answer,
                "id": question_number
            }
            data["questions"].append(question_data)
            f.seek(0)
            json.dump(data, f, indent=4)

        await interaction.response.send_message(f"FAQ **#{question_number}** added successfully!")

    @app_commands.command(name="delete-faq", description="Delete a FAQ")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(question="Select the question to delete")
    async def _delete_faq(self, interaction: discord.Interaction, question: str):
        questions_file = 'data/faqs.json'
        if not os.path.exists(questions_file):
            await interaction.response.send_message(f"{config.ERROR} Couldn't find the FAQs file.", ephemeral=True)
            return

        with open(questions_file, 'r+') as f:
            data = json.load(f)
            question_to_delete = next((q for q in data["questions"] if q["question"] == question), None)

            if question_to_delete is None:
                await interaction.response.send_message(f"{config.ERROR} I couldn't find that FAQ.", ephemeral=True)
                return

            number = question_to_delete["id"]
            data["questions"].remove(question_to_delete)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)

        await interaction.response.send_message(f"FAQ **#{number}** deleted successfully!")

    @_delete_faq.autocomplete('question')
    async def autocomplete_label(self, interaction: discord.Interaction, current: str):
        questions_file = 'data/faqs.json'
        if not os.path.exists(questions_file):
            return []

        with open(questions_file, 'r') as f:
            data = json.load(f)
            return [
                app_commands.Choice(name=q["question"], value=q["question"])
                for q in data["questions"] if current.lower() in q["question"].lower()
            ]

    @app_commands.command(name="faq", description="Get the answer to a frequently asked question")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(question="Frequently Asked Question")
    @app_commands.describe(user="The user you want to ping")
    async def _faq(self, interaction: discord.Interaction, question: str, user: discord.User=None):
        
        questions_file = 'data/faqs.json'
        if not os.path.exists(questions_file):
            await interaction.response.send_message(f"{config.ERROR} Couldn't find the FAQs file.", ephemeral=True)
            return

        with open(questions_file, 'r') as f:
            data = json.load(f)
            faq = next((q for q in data["questions"] if q["question"] == question), None)

            if faq is None:
                await interaction.response.send_message(f"{config.ERROR} I couldn't find that FAQ.", ephemeral=True)
                return

            embed = discord.Embed(title=faq["question"], description=faq["answer"], color=0xcda69b)
            channel = interaction.channel

            if user is None:
                await channel.send(embed=embed)
                await interaction.response.send_message(f"{config.SUCCESS} Done!", ephemeral=True)                  
            else:
                await channel.send(f"{user.mention}", embed=embed)
                await interaction.response.send_message(f"{config.SUCCESS} Done!", ephemeral=True)                
    
    @_faq.autocomplete('question')
    async def autocomplete_faq(self, interaction: discord.Interaction, current: str):
        questions_file = 'data/faqs.json'
        if not os.path.exists(questions_file):
            return []

        with open(questions_file, 'r') as f:
            data = json.load(f)
            return [
                app_commands.Choice(name=q["question"], value=q["question"])
                for q in data["questions"] if current.lower() in q["question"].lower()
            ]

async def setup(bot):
    await bot.add_cog(FAQs(bot))

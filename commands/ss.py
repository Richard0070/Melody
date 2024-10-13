import discord
from discord.ext import commands
from playwright.async_api import async_playwright
import os
import asyncio 

class Screenshot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="screenshot", aliases=["ss"], usage="<url>", description="Take a screenshot of a website.")
    @commands.has_permissions(administrator=True)
    async def screenshot(self, ctx, url: str):
        m = await ctx.send('📸 Taking screenshot...')
        async with async_playwright() as p:
            # Launch the browser
            browser = await p.chromium.launch()

            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to the URL and disable Safe Search on the same page
            await page.goto(url, waitUntil='load')  # Wait for page to load before disabling Safe Search

            # Take the screenshot
            screenshot_path = f'screenshot_{ctx.message.id}.png'
            await page.screenshot(path=screenshot_path)
            await browser.close()        
            await m.delete()

            # Send the screenshot back to Discord & then remove the screenshot file from the directory
            await ctx.send(file=discord.File(screenshot_path))
            os.remove(screenshot_path)

async def setup(bot):
    await bot.add_cog(Screenshot(bot))

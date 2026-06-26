import discord
from discord.ext import commands
import asyncio
from config import Config
from utils.logger import log
from database import db

class NoctraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        log.info("Loading Cogs...")
        cogs = ["cogs.admin", "cogs.shop", "cogs.tickets", "cogs.reviews"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"Cog {cog} successfully loaded.")
            except Exception as e:
                log.error(f"Failed to load cog {cog}: {e}")
        
        # Syncing Application Commands
        self.loop.create_task(self.sync_commands())

    async def sync_commands(self):
        await self.wait_until_ready()
        if Config.GUILD_ID:
            guild = discord.Object(id=Config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"Slash Commands Synchronized to Guild {Config.GUILD_ID}.")
        else:
            await self.tree.sync()
            log.info("Slash Commands Synchronized Globally.")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name=f"{Config.BRAND_NAME} Storefront"
            )
        )

if __name__ == "__main__":
    bot = NoctraBot()
    bot.run(Config.TOKEN)

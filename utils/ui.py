import discord
from config import Config

class PremiumEmbed(discord.Embed):
    """Unified premium style embed layout ensuring complete visual synchronization across features."""
    def __init__(self, title=None, description=None, color=Config.COLOR_PRIMARY, **kwargs):
        super().__init__(title=title, description=description, color=color, **kwargs)
        self.set_footer(text=Config.FOOTER_TEXT)

    @classmethod
    def error(cls, title="Error Occurred", description="An error has occurred during this transaction."):
        return cls(title=f"| {title}", description=description, color=Config.COLOR_DANGER)

    @classmethod
    def success(cls, title="Operation Successful", description="Your action completed successfully."):
        return cls(title=f"| {title}", description=description, color=Config.COLOR_SUCCESS)

    @classmethod
    def info(cls, title, description):
        return cls(title=f"| {title}", description=description, color=Config.COLOR_SECONDARY)

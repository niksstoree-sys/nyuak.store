import discord
from discord import app_commands
from discord.ext import commands
from database import db
from utils.ui import PremiumEmbed
from config import Config

class TicketActionsView(discord.ui.View):
    def __init__(self, bot, ticket_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_id = ticket_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="btn_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketCloseModal(self.ticket_id))


class TicketCloseModal(discord.ui.Modal):
    def __init__(self, ticket_id):
        super().__init__(title="Archiving Service Session")
        self.ticket_id = ticket_id
        self.reason = discord.ui.TextInput(
            label="Provide Closure Validation Reason",
            placeholder="Manual checkout verified / query answered",
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db.execute(
            "UPDATE tickets SET status = 'Closed', close_reason = ? WHERE id = ?",
            (self.reason.value, self.ticket_id)
        )
        await interaction.followup.send("Archiving sequence initiating. Channel will delete shortly.", ephemeral=True)
        await interaction.channel.delete(reason="Ticket Session finalized through modal system.")


class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket", description="Establish automated communication channel regarding orders.")
    async def create_ticket(self, interaction: discord.Interaction, order_id: int):
        await interaction.response.defer(ephemeral=True)
        
        # Verify valid order ownership
        order = db.fetch_one("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, interaction.user.id))
        if not order:
            await interaction.followup.send(
                embed=PremiumEmbed.error("System Check", "No matched order validation found matching provided ID parameters."),
                ephemeral=True
            )
            return

        # Setup channel hierarchy structure
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{order_id}",
            overwrites=overwrites,
            topic=f"Billing Session verification relating to digital receipt ID: {order_id}"
        )

        ticket_id = db.execute(
            "INSERT INTO tickets (user_id, order_id, channel_id, status) VALUES (?, ?, ?, 'Open')",
            (interaction.user.id, order_id, channel.id)
        )

        embed = PremiumEmbed.info(
            f"Service Session Initialized: #{ticket_id}",
            f"Please upload payment confirmations block. Our administration agents will verify orders manually.\n\n"
            f"Order: #{order_id}\n"
            f"Payment Status: {order['payment_status']}"
        )
        await channel.send(content=interaction.user.mention, embed=embed, view=TicketActionsView(self.bot, ticket_id))
        
        await interaction.followup.send(f"Secure support room established. Direct access: {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))

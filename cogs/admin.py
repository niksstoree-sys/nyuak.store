import discord
from discord import app_commands
from discord.ext import commands
from database import db
from utils.ui import PremiumEmbed
import json

class AdminCog(commands.GroupCog, name="admin"):
    def __init__(self, bot):
        self.bot = bot

    # Category admin management
    @app_commands.command(name="category-create", description="[Admin] Create a product category.")
    @app_commands.checks.has_permissions(administrator=True)
    async def cat_create(self, interaction: discord.Interaction, title: str, description: str, position: int = 0):
        db.execute(
            "INSERT INTO categories (title, description, position) VALUES (?, ?, ?)",
            (title, description, position)
        )
        embed = PremiumEmbed.success("Category Created", f"The category [{title}] has been established.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Product admin management
    @app_commands.command(name="product-create", description="[Admin] Add a product to a category.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        product_type=[
            app_commands.Choice(name="Manual Delivery", value="Manual"),
            app_commands.Choice(name="Automatic Delivery", value="Auto"),
            app_commands.Choice(name="Digital Product", value="Digital"),
            app_commands.Choice(name="Service Product", value="Service")
        ],
        stock_type=[
            app_commands.Choice(name="Unlimited", value="Unlimited"),
            app_commands.Choice(name="Manual Stock Control", value="Manual")
        ]
    )
    async def prod_create(self, interaction: discord.Interaction, category_id: int, title: str, description: str, product_type: str, stock_type: str, stock_count: int = 0, image_url: str = None):
        db.execute(
            "INSERT INTO products (category_id, title, description, type, stock_type, stock_count, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (category_id, title, description, product_type, stock_type, stock_count, image_url)
        )
        embed = PremiumEmbed.success("Product Created", f"The product [{title}] was initialized inside Category #{category_id}.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Variant management
    @app_commands.command(name="variant-add", description="[Admin] Add product variant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def var_add(self, interaction: discord.Interaction, product_id: int, title: str, description: str, price: float, discount: float = 0.0):
        db.execute(
            "INSERT INTO variants (product_id, title, description, price, discount) VALUES (?, ?, ?, ?, ?)",
            (product_id, title, description, price, discount)
        )
        embed = PremiumEmbed.success("Variant Loaded", f"The variant [{title}] is now tied to Product #{product_id}.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Custom dynamic field builder
    @app_commands.command(name="field-add", description="[Admin] Build dynamic input fields for a product purchase modal.")
    @app_commands.checks.has_permissions(administrator=True)
    async def field_add(self, interaction: discord.Interaction, product_id: int, label: str, placeholder: str, is_required: bool = True, min_len: int = 1, max_len: int = 100):
        db.execute(
            "INSERT INTO custom_fields (product_id, label, placeholder, is_required, min_length, max_length) VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, label, placeholder, 1 if is_required else 0, min_len, max_len)
        )
        embed = PremiumEmbed.success("Dynamic Field Added", f"Dynamic modal requirement [{label}] assigned to Product #{product_id}.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Custom payment system admin
    @app_commands.command(name="payment-add", description="[Admin] Create payment gateway system.")
    @app_commands.checks.has_permissions(administrator=True)
    async def pay_add(self, interaction: discord.Interaction, name: str, instructions: str):
        db.execute(
            "INSERT INTO payment_methods (name, instructions) VALUES (?, ?)",
            (name, instructions)
        )
        embed = PremiumEmbed.success("Payment Method Configured", f"Active gateway [{name}] has been created.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Order processing command
    @app_commands.command(name="order-process", description="[Admin] Update payment/order state of a client transaction.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        pay_status=[
            app_commands.Choice(name="Pending", value="Pending"),
            app_commands.Choice(name="Paid", value="Paid"),
            app_commands.Choice(name="Expired", value="Expired"),
            app_commands.Choice(name="Cancelled", value="Cancelled")
        ],
        order_status=[
            app_commands.Choice(name="Pending", value="Pending"),
            app_commands.Choice(name="Processing", value="Processing"),
            app_commands.Choice(name="Completed", value="Completed"),
            app_commands.Choice(name="Cancelled", value="Cancelled"),
            app_commands.Choice(name="Refunded", value="Refunded")
        ]
    )
    async def order_process(self, interaction: discord.Interaction, order_id: int, pay_status: str, order_status: str):
        db.execute(
            "UPDATE orders SET payment_status = ?, order_status = ? WHERE id = ?",
            (pay_status, order_status, order_id)
        )
        embed = PremiumEmbed.success("Order Processed", f"Order #{order_id} state changed.\n\nPayment Status: {pay_status}\nOrder Status: {order_status}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))

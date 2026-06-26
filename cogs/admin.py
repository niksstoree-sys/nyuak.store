import discord
from discord import app_commands
from discord.ext import commands
from database import db
from utils.ui import PremiumEmbed
from utils.logger import log
import json

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- GROUP: CATEGORY ---
    category_group = app_commands.Group(name="category", description="Manage store categories")

    @category_group.command(name="create", description="Create a new store category")
    @app_commands.checks.has_permissions(administrator=True)
    async def cat_create(self, interaction: discord.Interaction, title: str, description: str, position: int = 0):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute(
                "INSERT INTO categories (title, description, position, enabled) VALUES (?, ?, ?, 1)",
                (title, description, position)
            )
            embed = PremiumEmbed.success("Category Created", f"Category [{title}] has been successfully created at position {position}.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error creating category: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to create category."), ephemeral=True)

    @category_group.command(name="edit", description="Edit an existing store category")
    @app_commands.checks.has_permissions(administrator=True)
    async def cat_edit(self, interaction: discord.Interaction, category_id: int, title: str = None, description: str = None, position: int = None, enabled: bool = None):
        await interaction.response.defer(ephemeral=True)
        try:
            current = db.fetch_one("SELECT * FROM categories WHERE id = ?", (category_id,))
            if not current:
                await interaction.followup.send(embed=PremiumEmbed.error("Not Found", f"Category #{category_id} does not exist."), ephemeral=True)
                return

            new_title = title if title is not None else current["title"]
            new_desc = description if description is not None else current["description"]
            new_pos = position if position is not None else current["position"]
            new_val = 1 if (enabled if enabled is not None else bool(current["enabled"])) else 0

            db.execute(
                "UPDATE categories SET title = ?, description = ?, position = ?, enabled = ? WHERE id = ?",
                (new_title, new_desc, new_pos, new_val, category_id)
            )
            embed = PremiumEmbed.success("Category Updated", f"Category #{category_id} [{new_title}] has been updated.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error updating category: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to update category."), ephemeral=True)

    @category_group.command(name="delete", description="Delete a store category")
    @app_commands.checks.has_permissions(administrator=True)
    async def cat_delete(self, interaction: discord.Interaction, category_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            embed = PremiumEmbed.success("Category Deleted", f"Category #{category_id} and its associations have been removed.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error deleting category: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to delete category."), ephemeral=True)


    # --- GROUP: PRODUCT ---
    product_group = app_commands.Group(name="product", description="Manage store products")

    @product_group.command(name="create", description="Create a new product")
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
            app_commands.Choice(name="Manual Stock", value="Manual")
        ]
    )
    async def prod_create(self, interaction: discord.Interaction, category_id: int, title: str, description: str, product_type: str, stock_type: str, stock_count: int = 0, image_url: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute(
                "INSERT INTO products (category_id, title, description, type, stock_type, stock_count, image_url, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                (category_id, title, description, product_type, stock_type, stock_count, image_url)
            )
            embed = PremiumEmbed.success("Product Created", f"Product [{title}] created under Category #{category_id}.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error creating product: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to create product."), ephemeral=True)

    @product_group.command(name="edit", description="Edit an existing product")
    @app_commands.checks.has_permissions(administrator=True)
    async def prod_edit(self, interaction: discord.Interaction, product_id: int, title: str = None, description: str = None, stock_count: int = None, visibility: bool = None, image_url: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            current = db.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
            if not current:
                await interaction.followup.send(embed=PremiumEmbed.error("Not Found", "Product not found."), ephemeral=True)
                return

            new_title = title if title is not None else current["title"]
            new_desc = description if description is not None else current["description"]
            new_stock = stock_count if stock_count is not None else current["stock_count"]
            new_vis = 1 if (visibility if visibility is not None else bool(current["visibility"])) else 0
            new_img = image_url if image_url is not None else current["image_url"]

            db.execute(
                "UPDATE products SET title = ?, description = ?, stock_count = ?, visibility = ?, image_url = ? WHERE id = ?",
                (new_title, new_desc, new_stock, new_vis, new_img, product_id)
            )
            embed = PremiumEmbed.success("Product Updated", f"Product #{product_id} has been modified.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error editing product: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to edit product."), ephemeral=True)

    @product_group.command(name="delete", description="Delete a product")
    @app_commands.checks.has_permissions(administrator=True)
    async def prod_delete(self, interaction: discord.Interaction, product_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            embed = PremiumEmbed.success("Product Deleted", f"Product #{product_id} has been permanently deleted.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error deleting product: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to delete product."), ephemeral=True)


    # --- GROUP: VARIANT ---
    variant_group = app_commands.Group(name="variant", description="Manage product variants")

    @variant_group.command(name="add", description="Add a variant to a product")
    @app_commands.checks.has_permissions(administrator=True)
    async def var_add(self, interaction: discord.Interaction, product_id: int, title: str, description: str, price: float, discount: float = 0.0):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute(
                "INSERT INTO variants (product_id, title, description, price, discount, availability) VALUES (?, ?, ?, ?, ?, 1)",
                (product_id, title, description, price, discount)
            )
            embed = PremiumEmbed.success("Variant Created", f"Variant [{title}] added to Product #{product_id}.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error creating variant: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to add variant."), ephemeral=True)

    @variant_group.command(name="delete", description="Remove a variant")
    @app_commands.checks.has_permissions(administrator=True)
    async def var_delete(self, interaction: discord.Interaction, variant_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute("DELETE FROM variants WHERE id = ?", (variant_id,))
            embed = PremiumEmbed.success("Variant Deleted", f"Variant #{variant_id} deleted successfully.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error deleting variant: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to delete variant."), ephemeral=True)


    # --- GROUP: PAYMENT ---
    payment_group = app_commands.Group(name="payment", description="Manage store payment gateways")

    @payment_group.command(name="add", description="Create an enabled payment method")
    @app_commands.checks.has_permissions(administrator=True)
    async def pay_add(self, interaction: discord.Interaction, name: str, instructions: str):
        await interaction.response.defer(ephemeral=True)
        try:
            db.execute("INSERT INTO payment_methods (name, instructions, enabled) VALUES (?, ?, 1)", (name, instructions))
            embed = PremiumEmbed.success("Payment Gateway Added", f"Payment method [{name}] has been created.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error configuring payment: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to add payment method."), ephemeral=True)

    @payment_group.command(name="toggle", description="Enable or disable a payment method")
    @app_commands.checks.has_permissions(administrator=True)
    async def pay_toggle(self, interaction: discord.Interaction, method_id: int, enabled: bool):
        await interaction.response.defer(ephemeral=True)
        try:
            val = 1 if enabled else 0
            db.execute("UPDATE payment_methods SET enabled = ? WHERE id = ?", (val, method_id))
            status = "enabled" if enabled else "disabled"
            embed = PremiumEmbed.success("Status Toggled", f"Payment method #{method_id} is now {status}.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error toggling payment: {e}")

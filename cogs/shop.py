import discord
from discord import app_commands
from discord.ext import commands
from database import db
from utils.ui import PremiumEmbed
import json

class CustomFieldModal(discord.ui.Modal):
    """Dynamic client inputs generated programmatically matching store items selection."""
    def __init__(self, product_id, variant_id, custom_fields):
        super().__init__(title="Required Product Information")
        self.product_id = product_id
        self.variant_id = variant_id
        self.fields_metadata = custom_fields
        self.text_inputs = []

        for f in self.fields_metadata:
            t_input = discord.ui.TextInput(
                label=f["label"],
                placeholder=f["placeholder"],
                required=bool(f["is_required"]),
                min_length=f["min_length"],
                max_length=f["max_length"]
            )
            self.add_item(t_input)
            self.text_inputs.append(t_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Structure answers into key value array and serialize
        answers = {}
        for i, f in enumerate(self.fields_metadata):
            answers[f["label"]] = self.text_inputs[i].value

        answers_json = json.dumps(answers)
        variant = db.fetch_one("SELECT * FROM variants WHERE id = ?", (self.variant_id,))
        final_price = variant["price"] - variant["discount"]

        # Fetch Enabled Payment Options
        gateways = db.fetch_all("SELECT * FROM payment_methods WHERE enabled = 1")
        if not gateways:
            await interaction.followup.send(
                embed=PremiumEmbed.error("Configuration Required", "Store is temporarily locked (No active payment mechanisms)."),
                ephemeral=True
            )
            return

        order_id = db.execute(
            "INSERT INTO orders (user_id, product_id, variant_id, custom_inputs, price, payment_status, order_status) VALUES (?, ?, ?, ?, ?, 'Pending', 'Pending')",
            (interaction.user.id, self.product_id, self.variant_id, answers_json, final_price)
        )

        # Build interactive invoice gateway selector
        selector_view = PaymentGatewayView(order_id, gateways, final_price)
        invoice_embed = PremiumEmbed.info(
            f"Invoice Created: #{order_id}",
            f"Please complete verification parameters below.\n\n"
            f"Item ID: {self.product_id}\n"
            f"Subtotal: {final_price:.2f} USD\n"
            f"System: Noctra Vault System"
        )
        await interaction.followup.send(embed=invoice_embed, view=selector_view, ephemeral=True)


class PaymentGatewayView(discord.ui.View):
    def __init__(self, order_id, gateways, price):
        super().__init__(timeout=120)
        self.order_id = order_id
        self.price = price
        self.add_item(PaymentSelect(order_id, gateways))


class PaymentSelect(discord.ui.Select):
    def __init__(self, order_id, gateways):
        self.order_id = order_id
        options = [
            discord.SelectOption(label=g["name"], value=str(g["id"]), description=f"Process invoice via {g['name']}")
            for g in gateways
        ]
        super().__init__(placeholder="Select Payment Gateway System", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        method_id = int(self.values[0])
        gateway = db.fetch_one("SELECT * FROM payment_methods WHERE id = ?", (method_id,))
        
        db.execute(
            "UPDATE orders SET payment_method_id = ? WHERE id = ?",
            (method_id, self.order_id)
        )

        instruction_embed = PremiumEmbed.info(
            f"Invoice Setup Complete: #{self.order_id}",
            f"Instructions:\n"
            f"{gateway['instructions']}\n\n"
            f"Please complete payment and open a Support Ticket linking Order ID: {self.order_id}."
        )
        await interaction.followup.send(embed=instruction_embed, ephemeral=True)


class VariantSelect(discord.ui.Select):
    def __init__(self, product_id, variants, fields):
        self.product_id = product_id
        self.fields = fields
        options = [
            discord.SelectOption(
                label=f"{v['title']} - ${(v['price'] - v['discount']):.2f}",
                value=str(v["id"]),
                description=v["description"][:100]
            ) for v in variants
        ]
        super().__init__(placeholder="Select Variant", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        variant_id = int(self.values[0])
        if self.fields:
            # Trigger dynamic modal UI requirements to prevent interaction timeout
            modal = CustomFieldModal(self.product_id, variant_id, self.fields)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.defer(ephemeral=True)
            variant = db.fetch_one("SELECT * FROM variants WHERE id = ?", (variant_id,))
            final_price = variant["price"] - variant["discount"]
            gateways = db.fetch_all("SELECT * FROM payment_methods WHERE enabled = 1")
            
            if not gateways:
                await interaction.followup.send(
                    embed=PremiumEmbed.error("Config Required", "Store has no active payment methods setup."),
                    ephemeral=True
                )
                return

            order_id = db.execute(
                "INSERT INTO orders (user_id, product_id, variant_id, custom_inputs, price, payment_status, order_status) VALUES (?, ?, ?, ?, ?, 'Pending', 'Pending')",
                (interaction.user.id, self.product_id, variant_id, "{}", final_price)
            )
            selector_view = PaymentGatewayView(order_id, gateways, final_price)
            invoice_embed = PremiumEmbed.info(
                f"Invoice Created: #{order_id}",
                f"Item Selected: {variant['title']}\n"
                f"Price Due: {final_price:.2f} USD"
            )
            await interaction.followup.send(embed=invoice_embed, view=selector_view, ephemeral=True)


class VariantView(discord.ui.View):
    def __init__(self, product_id, variants, fields):
        super().__init__(timeout=120)
        self.add_item(VariantSelect(product_id, variants, fields))


class ProductSelect(discord.ui.Select):
    def __init__(self, products):
        options = [
            discord.SelectOption(label=p["title"], value=str(p["id"]), description=p["description"][:100])
            for p in products
        ]
        super().__init__(placeholder="Select Product to Purchase", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        product_id = int(self.values[0])
        
        variants = db.fetch_all("SELECT * FROM variants WHERE product_id = ? AND availability = 1", (product_id,))
        fields = db.fetch_all("SELECT * FROM custom_fields WHERE product_id = ?", (product_id,))
        
        if not variants:
            await interaction.followup.send(
                embed=PremiumEmbed.error("Out of Stock", "This system currently does not have active variants configuration."),
                ephemeral=True
            )
            return

        variant_view = VariantView(product_id, variants, fields)
        prompt_embed = PremiumEmbed.info(
            "Product Customizations",
            "Select product configuration specifications from the selector block."
        )
        await interaction.followup.send(embed=prompt_embed, view=variant_view, ephemeral=True)


class ProductView(discord.ui.View):
    def __init__(self, products):
        super().__init__(timeout=120)
        self.add_item(ProductSelect(products))


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the boutique catalog interface.")
    async def shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        categories = db.fetch_all("SELECT * FROM categories WHERE enabled = 1 ORDER BY position ASC")
        if not categories:
            await interaction.followup.send(
                embed=PremiumEmbed.error("Catalog Unavailable", "No catalog configurations active yet."),
                ephemeral=True
            )
            return

        class ShopCategorySelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(label=c["title"], value=str(c["id"]), description=c["description"][:100])
                    for c in categories
                ]
                super().__init__(placeholder="Select Catalog Section", min_values=1, max_values=1, options=options)

            async def callback(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                cat_id = int(self.values[0])
                products = db.fetch_all("SELECT * FROM products WHERE category_id = ? AND visibility = 1", (cat_id,))
                
                if not products:
                    await inter.followup.send(
                        embed=PremiumEmbed.error("Storefront Empty", "No products available under this category currently."),
                        ephemeral=True
                    )
                    return

                prod_view = ProductView(products)
                prod_embed = PremiumEmbed.info("Selected Category Products", f"Browsing Category #{cat_id}")
                await inter.followup.send(embed=prod_embed, view=prod_view, ephemeral=True)

        view = discord.ui.View(timeout=120)
        view.add_item(ShopCategorySelect())
        
        main_embed = PremiumEmbed.info(
            f"{Config.BRAND_NAME} Virtual Storefront",
            "Browse categories by making a selection below."
        )
        await interaction.followup.send(embed=main_embed, view=view, ephemeral=True)

    @app_commands.command(name="orders", description="View purchase history.")
    async def orders(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        records = db.fetch_all("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10", (interaction.user.id,))
        if not records:
            await interaction.followup.send(
                embed=PremiumEmbed.info("Order Registry Empty", "No order profiles match your unique Snowflake Identifier."),
                ephemeral=True
            )
            return

        desc = ""
        for r in records:
            desc += f"Order ID: #{r['id']} | Total: {r['price']:.2f} USD\nPayment: {r['payment_status']} | Order: {r['order_status']}\n\n"

        embed = PremiumEmbed.info("Noctra Order History", desc)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

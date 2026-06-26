import discord
from discord import app_commands
from discord.ext import commands
from database import db
from utils.ui import PremiumEmbed

class ReviewSubmitModal(discord.ui.Modal):
    def __init__(self, product_id, order_id):
        super().__init__(title="Product Performance Review Form")
        self.product_id = product_id
        self.order_id = order_id
        
        self.rating = discord.ui.TextInput(
            label="Rating (1 to 5 stars only)",
            placeholder="5",
            min_length=1,
            max_length=1
        )
        self.review_text = discord.ui.TextInput(
            label="Provide purchase testimonial validation text",
            style=discord.TextStyle.paragraph,
            placeholder="Excellent digital product delivery speed.",
            required=True
        )
        self.anonymous = discord.ui.TextInput(
            label="Anonymous option (YES or NO)",
            placeholder="NO",
            required=True,
            max_length=3
        )
        self.add_item(self.rating)
        self.add_item(self.review_text)
        self.add_item(self.anonymous)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            val_rating = int(self.rating.value)
            if val_rating < 1 or val_rating > 5:
                raise ValueError()
        except ValueError:
            await interaction.followup.send(
                embed=PremiumEmbed.error("Submission Exception", "The rating input variable can only range between 1 and 5."),
                ephemeral=True
            )
            return

        is_anon = 1 if self.anonymous.value.upper() == "YES" else 0

        # Create validation model
        db.execute(
            "INSERT INTO reviews (user_id, product_id, order_id, rating, review_text, anonymous, approved) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (interaction.user.id, self.product_id, self.order_id, val_rating, self.review_text.value, is_anon)
        )

        success_embed = PremiumEmbed.success(
            "Review Sent for Validation",
            "Thank you. Your feedback profile has been logged and awaits manual admin approval."
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class ReviewsCog(commands.GroupCog, name="review"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="submit", description="Leave a performance testimonial review of a completed item order.")
    async def review_submit(self, interaction: discord.Interaction, order_id: int):
        await interaction.response.defer(ephemeral=True)
        
        # Pull details of order
        order = db.fetch_one("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, interaction.user.id))
        if not order:
            await interaction.followup.send(
                embed=PremiumEmbed.error("Verification Refused", "Verification mapping validation parameters failed matching order."),
                ephemeral=True
            )
            return

        if order["order_status"] != "Completed":
            await interaction.followup.send(
                embed=PremiumEmbed.error("Action Prohibited", "Reviews are permitted solely on status: Completed transaction modules."),
                ephemeral=True
            )
            return

        # Check existing evaluations
        existing = db.fetch_one("SELECT * FROM reviews WHERE order_id = ?", (order_id,))
        if existing:
            await interaction.followup.send(
                embed=PremiumEmbed.error("Action Blocked", "Testimonial parameters mapping to Order ID already logged in system database."),
                ephemeral=True
            )
            return

        # Launch UI modal sequence
        await interaction.followup.send("Establishing review protocol interface...", ephemeral=True)
        modal = ReviewSubmitModal(order["product_id"], order_id)
        await interaction.followup.send_modal(modal)

    @app_commands.command(name="list", description="Review overall performance rating analysis block.")
    async def review_list(self, interaction: discord.Interaction, product_id: int):
        await interaction.response.defer(ephemeral=True)
        reviews = db.fetch_all("SELECT * FROM reviews WHERE product_id = ? AND approved = 1 ORDER BY id DESC LIMIT 5", (product_id,))
        stats = db.fetch_one("SELECT AVG(rating) as avg, COUNT(id) as cnt FROM reviews WHERE product_id = ? AND approved = 1", (product_id,))
        
        if not reviews:
            await interaction.followup.send(
                embed=PremiumEmbed.info("Empty Feedback File", "This asset segment lacks approved product rating entries."),
                ephemeral=True
            )
            return

        avg_score = stats["avg"] if stats["avg"] else 0.0
        total_counts = stats["cnt"]
        
        perf_data = f"Average Performance: {avg_score:.1f} / 5.0 Rating Points\nTotal Customer Validated Logins: {total_counts}\n\nRecent Submissions:\n"
        for r in reviews:
            user_label = "Anonymous Customer" if r["anonymous"] == 1 else f"UID: {r['user_id']}"
            perf_data += f"User: {user_label}\nScore: {r['rating']}/5\nNote: {r['review_text']}\n" + ("-"*20) + "\n"

        embed = PremiumEmbed.info(f"System Statistics: Product #{product_id}", perf_data)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="approve", description="[Admin] Approve user testimonial review.")
    @app_commands.checks.has_permissions(administrator=True)
    async def review_approve(self, interaction: discord.Interaction, review_id: int):
        db.execute("UPDATE reviews SET approved = 1 WHERE id = ?", (review_id,))
        embed = PremiumEmbed.success("Verification Handshake", f"Review reference #{review_id} approved for global directory.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReviewsCog(bot))

import discord
from discord import app_commands
from discord.ext import commands
from database import db
from utils.ui import PremiumEmbed
from utils.logger import log

class ReviewSubmitModal(discord.ui.Modal):
    def __init__(self, product_id, order_id):
        super().__init__(title="Leave a Review")
        self.product_id = product_id
        self.order_id = order_id
        
        self.rating = discord.ui.TextInput(
            label="Rating (1-5)",
            placeholder="5",
            min_length=1,
            max_length=1,
            required=True
        )
        self.review_text = discord.ui.TextInput(
            label="Review Text",
            style=discord.TextStyle.paragraph,
            placeholder="Write your honest opinion about the service here.",
            required=True,
            max_length=500
        )
        self.anonymous = discord.ui.TextInput(
            label="Anonymous option (YES/NO)",
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
                embed=PremiumEmbed.error("Error", "Rating must be a whole number between 1 and 5."),
                ephemeral=True
            )
            return

        is_anon = 1 if self.anonymous.value.upper() == "YES" else 0

        try:
            db.execute(
                "INSERT INTO reviews (user_id, product_id, order_id, rating, review_text, anonymous, approved) VALUES (?, ?, ?, ?, ?, ?, 0)",
                (interaction.user.id, self.product_id, self.order_id, val_rating, self.review_text.value, is_anon)
            )
            embed = PremiumEmbed.success(
                "Review Submitted", 
                "Your review has been captured and logged in our system. It is currently awaiting review and approval by an administrator."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error submitting review modal: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to save your review."), ephemeral=True)


class ReviewsCog(commands.GroupCog, name="review"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="submit", description="Submit a review for a completed order")
    async def review_submit(self, interaction: discord.Interaction, order_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            order = db.fetch_one("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, interaction.user.id))
            if not order:
                await interaction.followup.send(embed=PremiumEmbed.error("Access Denied", "No matching order record was found for your account."), ephemeral=True)
                return

            if order["order_status"] != "Completed":
                await interaction.followup.send(embed=PremiumEmbed.error("Invalid Order Status", "You can only review orders that have been successfully set to 'Completed'."), ephemeral=True)
                return

            if order["payment_status"] != "Paid":
                await interaction.followup.send(embed=PremiumEmbed.error("Invalid Payment Status", "You can only review orders where the payment is marked as 'Paid'."), ephemeral=True)
                return

            existing = db.fetch_one("SELECT * FROM reviews WHERE order_id = ?", (order_id,))
            if existing:
                await interaction.followup.send(embed=PremiumEmbed.error("Limit Exceeded", "You have already submitted a review for this order."), ephemeral=True)
                return

            modal = ReviewSubmitModal(order["product_id"], order_id)
            await interaction.followup.send_modal(modal)
        except Exception as e:
            log.error(f"Error checking review eligibility: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("System Error", "An error occurred. Please try again."), ephemeral=True)

    @app_commands.command(name="list", description="List reviews for a product with ratings distribution statistics")
    async def review_list(self, interaction: discord.Interaction, product_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            product = db.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
            if not product:
                await interaction.followup.send(embed=PremiumEmbed.error("Not Found", "Product does not exist."), ephemeral=True)
                return

            reviews = db.fetch_all("SELECT * FROM reviews WHERE product_id = ? AND approved = 1 ORDER BY id DESC LIMIT 5", (product_id,))
            stats = db.fetch_one("SELECT AVG(rating) as avg, COUNT(id) as cnt FROM reviews WHERE product_id = ? AND approved = 1", (product_id,))
            
            # Calculate Rating Distribution
            distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            dist_data = db.fetch_all("SELECT rating, COUNT(id) as cnt FROM reviews WHERE product_id = ? AND approved = 1 GROUP BY rating", (product_id,))
            for d in dist_data:
                distribution[d["rating"]] = d["cnt"]

            avg_score = stats["avg"] if stats["avg"] else 0.0
            total_counts = stats["cnt"]

            # Visual Distribution Bar Builder (using ASCII Blocks as custom styling)
            dist_str = ""
            for star in range(5, 0, -1):
                count = distribution[star]
                pct = (count / total_counts) if total_counts > 0 else 0
                bar_len = int(pct * 10)
                bar = "█" * bar_len + "░" * (10 - bar_len)
                dist_str += f"{star} Star | {bar} | {count} ({int(pct*100)}%)\n"

            desc = f"Average Rating: {avg_score:.1f} / 5.0\nTotal Reviews: {total_counts}\n\n"
            desc += f"Rating Distribution:\n{dist_str}\n"
            desc += "Recent Reviews:\n" + ("="*25) + "\n\n"

            for r in reviews:
                user_label = "Anonymous Reviewer" if r["anonymous"] == 1 else f"User ID: {r['user_id']}"
                desc += f"Customer: {user_label}\n"
                desc += f"Verified Purchase Indicator: [ YES ]\n"
                desc += f"Rating: {'★' * r['rating']}{'☆' * (5 - r['rating'])}\n"
                desc += f"Comment: {r['review_text']}\n"
                desc += ("-"*25) + "\n\n"

            embed = PremiumEmbed.info(f"Customer Testimonials: {product['title']}", desc)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error rendering review listings: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("System Error", "An error occurred retrieving reviews."), ephemeral=True)

    @app_commands.command(name="approve", description="[Admin] Approve or reject a submitted review")
    @app_commands.checks.has_permissions(administrator=True)
    async def review_approve(self, interaction: discord.Interaction, review_id: int, approve: bool):
        await interaction.response.defer(ephemeral=True)
        try:
            if approve:
                db.execute("UPDATE reviews SET approved = 1 WHERE id = ?", (review_id,))
                embed = PremiumEmbed.success("Approved", f"Review #{review_id} has been approved and is now visible in listings.")
            else:
                db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
                embed = PremiumEmbed.success("Rejected", f"Review #{review_id} has been rejected and permanently deleted.")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error approving/rejecting review: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("Database Error", "Failed to update review status."), ephemeral=True)

    @app_commands.command(name="delete", description="[Admin/User] Delete a review")
    async def review_delete(self, interaction: discord.Interaction, review_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            review = db.fetch_one("SELECT * FROM reviews WHERE id = ?", (review_id,))
            if not review:
                await interaction.followup.send(embed=PremiumEmbed.error("Not Found", "Review not found."), ephemeral=True)
                return

            # Allow deletion only if the requester is an administrator OR the owner of the review
            is_admin = interaction.user.guild_permissions.administrator
            is_owner = (review["user_id"] == interaction.user.id)

            if not (is_admin or is_owner):
                await interaction.followup.send(embed=PremiumEmbed.error("Permission Denied", "You do not have permission to delete this review."), ephemeral=True)
                return

            db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            embed = PremiumEmbed.success("Review Removed", f"Review #{review_id} has been deleted.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error deleting review: {e}")
            await interaction.followup.send(embed=PremiumEmbed.error("System Error", "Could not complete the delete action."), ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReviewsCog(bot))

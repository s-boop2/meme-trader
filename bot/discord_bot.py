import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))  # Set in .env for faster sync

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global state
db = None


class TradingCog(commands.Cog):
    """Trading commands cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
    
    @app_commands.command(name="balance", description="Check your trading balance")
    async def balance_cmd(self, interaction: discord.Interaction):
        """Get current wallet balance"""
        try:
            doc = await self.db.wallet.find_one({"key": "global"})
            balance = float(doc["balance"]) if doc else 1000.0
            
            embed = discord.Embed(
                title="💰 Wallet Balance",
                description=f"Current Balance: **${balance:,.2f}**",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="🤖 Meme Trader Bot")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="positions", description="View all open positions")
    async def positions_cmd(self, interaction: discord.Interaction):
        """Get all open positions"""
        try:
            positions = await self.db.positions.find({"status": "open"}).to_list(None)
            
            if not positions:
                embed = discord.Embed(
                    title="📊 Open Positions",
                    description="No open positions",
                    color=discord.Color.greyple(),
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                desc = ""
                for i, pos in enumerate(positions, 1):
                    change_pct = ((pos["current_price"] - pos["entry_price"]) / pos["entry_price"] * 100) if pos["entry_price"] > 0 else 0
                    emoji = "📈" if change_pct >= 0 else "📉"
                    desc += f"{i}. **{pos['symbol']}** {emoji}\n"
                    desc += f"   Entry: ${pos['entry_price']:.12f}\n"
                    desc += f"   Current: ${pos['current_price']:.12f}\n"
                    desc += f"   Change: {change_pct:+.2f}%\n"
                    desc += f"   Invested: ${pos['invested_usd']:.2f}\n\n"
                
                embed = discord.Embed(
                    title="📊 Open Positions",
                    description=desc,
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
            
            embed.set_footer(text="🤖 Meme Trader Bot")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="open", description="Open a new trading position")
    @app_commands.describe(symbol="Token symbol", mint="Token mint address")
    async def open_position(self, interaction: discord.Interaction, symbol: str, mint: str):
        """Open a new position"""
        try:
            await interaction.response.defer()
            
            # Get engine instance
            from backend.engine import PaperEngine
            engine = PaperEngine(self.db)
            
            result = await engine.open_position(mint, symbol.upper())
            
            if result["ok"]:
                embed = discord.Embed(
                    title="✅ Position Opened",
                    description=f"Successfully opened position for **{symbol.upper()}**",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Entry Price", value=f"${result['price']:.12f}", inline=True)
                embed.add_field(name="Position ID", value=result["position_id"][:8] + "...", inline=True)
                embed.set_footer(text="🤖 Meme Trader Bot")
            else:
                embed = discord.Embed(
                    title="❌ Failed to Open Position",
                    description=f"Reason: {result.get('reason', 'Unknown error')}",
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="close", description="Close a position")
    @app_commands.describe(position_id="Position ID to close")
    async def close_position(self, interaction: discord.Interaction, position_id: str):
        """Close a position"""
        try:
            await interaction.response.defer()
            
            from backend.engine import PaperEngine
            engine = PaperEngine(self.db)
            
            result = await engine.close_position(position_id)
            
            if result["ok"]:
                pnl = result["pnl"]
                pnl_pct = result["pnl_pct"]
                emoji = "✅" if pnl >= 0 else "❌"
                
                embed = discord.Embed(
                    title=f"{emoji} Position Closed",
                    description=f"Position closed successfully",
                    color=discord.Color.green() if pnl >= 0 else discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="P&L", value=f"${pnl:+.2f}", inline=True)
                embed.add_field(name="P&L %", value=f"{pnl_pct:+.2f}%", inline=True)
                embed.set_footer(text="🤖 Meme Trader Bot")
            else:
                embed = discord.Embed(
                    title="❌ Failed to Close Position",
                    description=f"Reason: {result.get('reason', 'Unknown error')}",
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="settings", description="View trading settings")
    async def settings_cmd(self, interaction: discord.Interaction):
        """Get current settings"""
        try:
            doc = await self.db.settings.find_one({"key": "global"})
            if not doc:
                await interaction.response.send_message("Settings not found", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="⚙️ Trading Settings",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Max Positions", value=doc["max_positions"], inline=True)
            embed.add_field(name="Buy Size", value=f"${doc['buy_size']}", inline=True)
            embed.add_field(name="Stop Loss", value=f"{doc['stop_loss_pct']}%", inline=True)
            embed.add_field(name="Take Profit 1", value=f"+{doc['tp1_pct']}%", inline=True)
            embed.add_field(name="Take Profit 2", value=f"+{doc['tp2_pct']}%", inline=True)
            embed.add_field(name="AI Filter", value="✅ ON" if doc["ai_filter_enabled"] else "❌ OFF", inline=True)
            embed.set_footer(text="🤖 Meme Trader Bot")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="help", description="Show help menu")
    async def help_cmd(self, interaction: discord.Interaction):
        """Show help"""
        embed = discord.Embed(
            title="🤖 Meme Trader Bot - Help",
            description="High-performance paper trading bot with Discord integration",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="💰 /balance", value="Check your wallet balance", inline=False)
        embed.add_field(name="📊 /positions", value="View all open positions", inline=False)
        embed.add_field(name="📈 /open", value="Open a new trading position", inline=False)
        embed.add_field(name="📉 /close", value="Close a position", inline=False)
        embed.add_field(name="⚙️ /settings", value="View trading settings", inline=False)
        embed.add_field(name="❓ /help", value="Show this help menu", inline=False)
        embed.set_footer(text="🤖 Meme Trader Bot")
        
        await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():
    """Bot ready event"""
    logger.info(f"✅ Bot logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"🔄 Syncing commands...")
    
    try:
        if GUILD_ID:
            synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            logger.info(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            logger.info(f"✅ Synced {len(synced)} commands globally")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
    
    # Set status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="🚀 Trading | /help for commands"
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)
    logger.info("🟢 Bot is ready!")


async def main():
    """Main bot initialization"""
    global db
    
    # Initialize MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client["meme_trader"]
    
    # Add cog
    cog = TradingCog(bot)
    cog.db = db
    await bot.add_cog(cog)
    
    logger.info("🚀 Starting Discord Trading Bot...")
    logger.info(f"📡 MongoDB: {MONGODB_URI}")
    logger.info(f"💬 Discord Token: {'✅' if DISCORD_TOKEN else '❌'}")
    
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")

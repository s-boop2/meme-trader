import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from backend.engine import PaperEngine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main bot startup"""
    
    # MongoDB Connection
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["meme_trader"]
    
    logger.info("🚀 Initializing Meme Trader Engine...")
    
    # Initialize Engine
    engine = PaperEngine(db)
    await engine.initialize()
    
    # Get initial state
    settings = await engine.settings()
    balance = await engine.balance()
    
    logger.info(f"✅ Paper Trading Engine started!")
    logger.info(f"💰 Starting Balance: ${balance:.2f}")
    logger.info(f"📊 Max Positions: {settings['max_positions']}")
    logger.info(f"🎯 Stop Loss: {settings['stop_loss_pct']}%")
    logger.info(f"📈 TP1: +{settings['tp1_pct']}% | TP2: +{settings['tp2_pct']}%")
    logger.info(f"🤖 AI Filter: {'ENABLED' if settings['ai_filter_enabled'] else 'DISABLED'}")
    logger.info(f"\n🔄 Starting monitor loop (interval={20}s)...\n")
    
    # Start monitoring loop
    try:
        await engine.monitor_loop(interval=20)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        client.close()
        logger.info("🔌 Database connection closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")

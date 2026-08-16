import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from typing import Optional, Dict
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Discord notification types"""
    POSITION_OPEN = "position_open"
    POSITION_CLOSE = "position_close"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    ERROR = "error"
    STATUS = "status"
    WARNING = "warning"


class DiscordNotifier:
    """Discord webhook integration for real-time notifications"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self.color_map = {
            NotificationType.POSITION_OPEN: 0x00FF00,      # Green
            NotificationType.POSITION_CLOSE: 0x0099FF,     # Blue
            NotificationType.TAKE_PROFIT: 0x00FF00,        # Green
            NotificationType.STOP_LOSS: 0xFF0000,          # Red
            NotificationType.WARNING: 0xFFFF00,            # Yellow
            NotificationType.ERROR: 0xFF0000,              # Red
            NotificationType.STATUS: 0x808080,             # Gray
        }
        
        if self.enabled:
            logger.info(f"✅ Discord notifications ENABLED")
        else:
            logger.warning("⚠️ Discord webhook not configured")
    
    async def start(self):
        """Initialize aiohttp session"""
        if self.enabled and not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Discord session started")
    
    async def stop(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Discord session closed")
    
    async def send_embed(self, title: str, description: str, 
                        notification_type: NotificationType = NotificationType.STATUS,
                        fields: Optional[Dict[str, str]] = None,
                        footer: Optional[str] = None) -> bool:
        """Send rich embed message to Discord"""
        if not self.enabled or not self.session:
            return False
        
        try:
            embed = {
                "title": title,
                "description": description,
                "color": self.color_map.get(notification_type, 0x808080),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fields": []
            }
            
            # Add custom fields
            if fields:
                for field_name, field_value in fields.items():
                    embed["fields"].append({
                        "name": field_name,
                        "value": field_value,
                        "inline": True
                    })
            
            # Add footer
            if footer:
                embed["footer"] = {"text": footer}
            else:
                embed["footer"] = {"text": "🤖 Meme Trader Bot"}
            
            payload = {"embeds": [embed]}
            
            async with self.session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 204:
                    return True
                else:
                    logger.warning(f"Discord API returned {resp.status}")
                    return False
        
        except asyncio.TimeoutError:
            logger.warning("Discord notification timeout")
            return False
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False
    
    async def notify_position_open(self, symbol: str, entry_price: float, 
                                   amount: float, invested_usd: float) -> bool:
        """Notify when position opens"""
        return await self.send_embed(
            title=f"📈 Position Opened: {symbol}",
            description=f"Entered at ${entry_price:.12f}",
            notification_type=NotificationType.POSITION_OPEN,
            fields={
                "Amount": f"{amount:.2e}",
                "Invested": f"${invested_usd:.2f}",
            }
        )
    
    async def notify_position_close(self, symbol: str, exit_price: float,
                                    pnl_usd: float, pnl_pct: float,
                                    reason: str = "Manual Close") -> bool:
        """Notify when position closes"""
        emoji = "✅" if pnl_usd >= 0 else "❌"
        return await self.send_embed(
            title=f"{emoji} Position Closed: {symbol}",
            description=f"Exit at ${exit_price:.12f}",
            notification_type=NotificationType.POSITION_CLOSE if pnl_usd >= 0 else NotificationType.STOP_LOSS,
            fields={
                "P&L": f"${pnl_usd:+.2f}",
                "P&L %": f"{pnl_pct:+.2f}%",
                "Reason": reason,
            }
        )
    
    async def notify_take_profit(self, symbol: str, tp_level: int,
                                 current_price: float, tp_price: float) -> bool:
        """Notify when take profit is hit"""
        return await self.send_embed(
            title=f"🎯 Take Profit Hit: {symbol}",
            description=f"TP{tp_level} triggered!",
            notification_type=NotificationType.TAKE_PROFIT,
            fields={
                "Current Price": f"${current_price:.12f}",
                f"TP{tp_level} Price": f"${tp_price:.12f}",
            }
        )
    
    async def notify_stop_loss(self, symbol: str, stop_price: float,
                               current_price: float, loss_pct: float) -> bool:
        """Notify when stop loss is hit"""
        return await self.send_embed(
            title=f"🛑 Stop Loss Hit: {symbol}",
            description=f"Position closed at ${current_price:.12f}",
            notification_type=NotificationType.STOP_LOSS,
            fields={
                "Stop Price": f"${stop_price:.12f}",
                "Loss %": f"{loss_pct:.2f}%",
            }
        )
    
    async def notify_error(self, error_title: str, error_message: str) -> bool:
        """Notify on errors"""
        return await self.send_embed(
            title=f"⚠️ {error_title}",
            description=error_message,
            notification_type=NotificationType.ERROR
        )
    
    async def notify_status(self, balance: float, open_positions: int,
                           total_pnl: float) -> bool:
        """Send status update"""
        return await self.send_embed(
            title="📊 Trading Status Update",
            description="Current portfolio snapshot",
            notification_type=NotificationType.STATUS,
            fields={
                "Balance": f"${balance:.2f}",
                "Open Positions": str(open_positions),
                "Total P&L": f"${total_pnl:+.2f}",
            }
        )
    
    async def notify_warning(self, warning_title: str, warning_message: str) -> bool:
        """Send warning notification"""
        return await self.send_embed(
            title=f"⚠️ {warning_title}",
            description=warning_message,
            notification_type=NotificationType.WARNING
        )

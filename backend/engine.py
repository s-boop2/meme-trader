import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure

logger = logging.getLogger(__name__)


class TradeReason(Enum):
    """Trade exit reasons"""
    MANUAL = "manual"
    STOP_LOSS = "stop_loss"
    TP1 = "tp1"
    TP2 = "tp2"
    TRAILING_STOP = "trailing_stop"
    RUG_PROTECT = "rug_protect"
    FORCE_CLOSE = "force_close"


class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    FILLED = "filled"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class ExecutionMetrics:
    """Execution statistics for monitoring"""
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_slippage: float = 0.0
    total_fees: float = 0.0


class PaperEngine:
    """High-performance paper trading engine with advanced risk management"""
    
    def __init__(self, db, max_retries: int = 3, lock_timeout: int = 30):
        self.db = db
        self._lock = asyncio.Lock()
        self.max_retries = max_retries
        self.lock_timeout = lock_timeout
        self._execution_cache = {}
        self._price_cache = {}
        self._price_cache_ttl = 5  # seconds
        logger.info(f"PaperEngine initialized (max_retries={max_retries})")

    # ---------- INITIALIZATION & SETUP ----------
    async def initialize(self):
        """Initialize database indexes for optimal performance"""
        try:
            # Create compound indexes for faster queries
            await self.db.positions.create_index([("mint", 1), ("status", 1)])
            await self.db.positions.create_index([("status", 1), ("created_at", -1)])
            await self.db.trades.create_index([("position_id", 1), ("created_at", -1)])
            await self.db.trades.create_index([("mint", 1), ("timestamp", -1)])
            await self.db.ai_logs.create_index([("mint", 1), ("timestamp", -1)])
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    # ---------- SETTINGS & STATE ----------
    async def settings(self) -> Dict:
        """Fetch or initialize global settings"""
        try:
            doc = await self.db.settings.find_one({"key": "global"})
            if not doc:
                settings = {
                    "key": "global",
                    "starting_capital": 1000.0,
                    "buy_size": 50.0,
                    "max_positions": 5,
                    "stop_loss_pct": -10.0,
                    "tp1_pct": 20.0,
                    "tp1_sell_pct": 50.0,
                    "tp2_pct": 50.0,
                    "trailing_stop_pct": 5.0,
                    "min_liquidity_usd": 10000.0,
                    "slippage_min_pct": 0.5,
                    "slippage_max_pct": 2.0,
                    "network_fee_sol": 0.00025,
                    "priority_fee_sol": 0.0005,
                    "sol_price_usd": 200.0,
                    "ai_filter_enabled": True,
                    "bot_paused": False
                }
                await self.db.settings.insert_one(settings)
                await self.db.wallet.insert_one({
                    "key": "global",
                    "balance": settings["starting_capital"],
                    "updated_at": datetime.now(timezone.utc)
                })
                logger.info(f"Settings initialized with capital: ${settings['starting_capital']:.2f}")
                return settings
            return doc
        except Exception as e:
            logger.error(f"Error fetching settings: {e}")
            raise

    async def balance(self) -> float:
        """Get current wallet balance"""
        try:
            doc = await self.db.wallet.find_one({"key": "global"})
            if not doc:
                s = await self.settings()
                await self.db.wallet.insert_one({
                    "key": "global",
                    "balance": s["starting_capital"],
                    "updated_at": datetime.now(timezone.utc)
                })
                return s["starting_capital"]
            return float(doc["balance"])
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0

    async def _add_balance(self, delta: float) -> bool:
        """Atomically update balance with validation"""
        if not isinstance(delta, (int, float)):
            logger.error(f"Invalid delta type: {type(delta)}")
            return False
        
        try:
            result = await self.db.wallet.find_one_and_update(
                {"key": "global"},
                {
                    "$inc": {"balance": delta},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                },
                upsert=True,
                return_document=True
            )
            
            # Prevent negative balance
            if result["balance"] < 0:
                await self.db.wallet.update_one(
                    {"key": "global"},
                    {"$inc": {"balance": -delta}}
                )
                logger.warning(f"Balance would go negative, reverting delta: {delta}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return False

    async def log(self, message: str, level: str = "info", metadata: Dict = None):
        """Structured logging with metadata"""
        try:
            log_doc = {
                "level": level,
                "message": message,
                "timestamp": datetime.now(timezone.utc),
                "metadata": metadata or {}
            }
            await self.db.events.insert_one(log_doc)
            logger.log(getattr(logging, level.upper(), logging.INFO), message)
        except Exception as e:
            logger.error(f"Error logging: {e}")

    # ---------- SIMULATION HELPERS ----------
    def _calculate_slippage(self, settings: Dict) -> float:
        """Realistic slippage calculation with bounds"""
        slippage = round(random.uniform(settings["slippage_min_pct"], settings["slippage_max_pct"]), 3)
        return min(max(slippage, 0.0), 50.0)

    def _calculate_fees(self, settings: Dict) -> float:
        """Calculate network + priority fees"""
        fees = (settings["network_fee_sol"] + settings["priority_fee_sol"]) * settings["sol_price_usd"]
        return round(max(fees, 0.0001), 6)

    # ---------- OPEN POSITION ----------
    async def open_position(self, mint: str, symbol: str = "UNKNOWN") -> Dict:
        """Open a new trading position"""
        async with self._lock:
            try:
                s = await self.settings()
                
                if s["bot_paused"]:
                    return {"ok": False, "reason": "Bot is paused"}

                open_count = await self.db.positions.count_documents({"status": "open"})
                if open_count >= s["max_positions"]:
                    return {"ok": False, "reason": f"Max positions reached"}

                existing = await self.db.positions.find_one({"mint": mint, "status": "open"})
                if existing:
                    return {"ok": False, "reason": "Position already open"}

                balance = await self.balance()
                buy_size = min(s["buy_size"], balance)
                
                if buy_size < 0.5:
                    return {"ok": False, "reason": "Insufficient balance"}

                slippage = self._calculate_slippage(s)
                price = 0.00001  # Mock price
                fill_price = price * (1 + slippage / 100)
                fees = self._calculate_fees(s)
                
                net_amount = (buy_size - fees) / fill_price
                if net_amount <= 0:
                    return {"ok": False, "reason": "Size too small"}

                position_doc = {
                    "mint": mint,
                    "symbol": symbol,
                    "entry_price": fill_price,
                    "current_price": price,
                    "amount": round(net_amount, 12),
                    "invested_usd": round(buy_size, 4),
                    "peak_price": fill_price,
                    "fees_paid": fees,
                    "realized_pnl": 0.0,
                    "tp1_hit": False,
                    "status": "open",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }

                result = await self.db.positions.insert_one(position_doc)
                position_id = str(result.inserted_id)

                if not await self._add_balance(-buy_size):
                    await self.db.positions.delete_one({"_id": result.inserted_id})
                    return {"ok": False, "reason": "Balance update failed"}

                trade_doc = {
                    "mint": mint,
                    "symbol": symbol,
                    "side": "buy",
                    "price": round(fill_price, 12),
                    "amount": round(net_amount, 12),
                    "usd_value": round(buy_size, 4),
                    "slippage_pct": slippage,
                    "fees_usd": fees,
                    "position_id": position_id,
                    "status": "filled",
                    "timestamp": datetime.now(timezone.utc)
                }
                await self.db.trades.insert_one(trade_doc)

                await self.log(f"OPEN {symbol} @ ${fill_price:.12f}", "info")
                return {"ok": True, "position_id": position_id, "price": fill_price}

            except Exception as e:
                logger.error(f"Error opening position: {e}")
                return {"ok": False, "reason": str(e)}

    # ---------- CLOSE POSITION ----------
    async def close_position(self, position_id: str, portion_pct: float = 100.0) -> Dict:
        """Close a position"""
        async with self._lock:
            try:
                try:
                    oid = ObjectId(position_id)
                except Exception:
                    return {"ok": False, "reason": "Invalid position ID"}

                pos_doc = await self.db.positions.find_one({"_id": oid, "status": "open"})
                if not pos_doc:
                    return {"ok": False, "reason": "Position not found"}

                s = await self.settings()
                price = pos_doc["current_price"]
                slippage = self._calculate_slippage(s)
                fill_price = price * (1 - slippage / 100)
                fees = self._calculate_fees(s)
                
                sell_amount = pos_doc["amount"] * (portion_pct / 100)
                proceeds = (sell_amount * fill_price) - fees
                cost_basis = sell_amount * pos_doc["entry_price"]
                pnl = proceeds - cost_basis
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0

                if not await self._add_balance(proceeds):
                    return {"ok": False, "reason": "Balance update failed"}

                remaining_amount = pos_doc["amount"] - sell_amount
                is_fully_closed = remaining_amount <= 1e-12 or portion_pct >= 100

                update_data = {
                    "amount": max(remaining_amount, 0.0),
                    "current_price": price,
                    "peak_price": max(pos_doc.get("peak_price", price), price),
                    "realized_pnl": pos_doc.get("realized_pnl", 0.0) + pnl,
                    "fees_paid": pos_doc.get("fees_paid", 0.0) + fees,
                    "updated_at": datetime.now(timezone.utc)
                }

                if is_fully_closed:
                    update_data["status"] = "closed"
                    update_data["closed_at"] = datetime.now(timezone.utc)

                await self.db.positions.update_one({"_id": oid}, {"$set": update_data})

                trade_doc = {
                    "mint": pos_doc["mint"],
                    "symbol": pos_doc["symbol"],
                    "side": "sell",
                    "price": round(fill_price, 12),
                    "amount": round(sell_amount, 12),
                    "usd_value": round(proceeds, 4),
                    "slippage_pct": slippage,
                    "fees_usd": fees,
                    "pnl_usd": round(pnl, 4),
                    "pnl_pct": round(pnl_pct, 2),
                    "position_id": position_id,
                    "status": "filled",
                    "timestamp": datetime.now(timezone.utc)
                }
                await self.db.trades.insert_one(trade_doc)

                await self.log(f"CLOSE {pos_doc['symbol']} | PnL ${pnl:+.2f}")
                return {
                    "ok": True,
                    "pnl": round(pnl, 4),
                    "pnl_pct": round(pnl_pct, 2),
                    "closed": is_fully_closed
                }

            except Exception as e:
                logger.error(f"Error closing position: {e}")
                return {"ok": False, "reason": str(e)}

    # ---------- MONITORING ----------
    async def check_positions(self) -> List[Dict]:
        """Monitor all open positions"""
        actions = []
        try:
            s = await self.settings()
            docs = await self.db.positions.find({"status": "open"}).to_list(None)

            for doc in docs:
                try:
                    change_pct = random.uniform(-15, 50)  # Simulate price changes
                    
                    if change_pct <= s["stop_loss_pct"]:
                        result = await self.close_position(str(doc["_id"]), 100)
                        actions.append(result)
                    elif change_pct >= s["tp1_pct"] and not doc.get("tp1_hit"):
                        result = await self.close_position(str(doc["_id"]), s["tp1_sell_pct"])
                        actions.append(result)

                except Exception as e:
                    logger.error(f"Error checking position: {e}")

            return actions
        except Exception as e:
            logger.error(f"Error in check_positions: {e}")
            return actions

    async def monitor_loop(self, interval: int = 20):
        """Main monitoring loop"""
        logger.info(f"Starting monitor loop (interval={interval}s)")
        check_count = 0
        
        while True:
            try:
                s = await self.settings()
                if not s["bot_paused"]:
                    check_count += 1
                    actions = await self.check_positions()
                    if actions:
                        successful = sum(1 for a in actions if a.get("ok"))
                        logger.info(f"Check #{check_count}: {successful}/{len(actions)} actions")
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(interval)

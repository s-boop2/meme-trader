# Meme Trader Bot

High-performance paper trading engine for crypto tokens with advanced risk management.

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Setup MongoDB

### Local MongoDB
```bash
mongodb-community start
```

### Or use Docker
```bash
docker run -d -p 27017:27017 --name meme-trader-db mongo:latest
```

## Configuration

Edit `.env`:
```
MONGODB_URI=mongodb://localhost:27017
DISCORD_WEBHOOK_URL=your_webhook_here (optional)
BOT_ENABLED=true
CHECK_INTERVAL=20
```

## Running

```bash
python backend/main.py
```

## Features

- ✅ Paper Trading Simulation
- ✅ Atomic Database Operations
- ✅ Real-time Position Monitoring
- ✅ Advanced Risk Management (SL, TP1, TP2, Trailing Stop)
- ✅ Price Caching & Fallback
- ✅ Emergency Position Closing
- ✅ Structured Logging
- ✅ Async/Await Architecture

## API Endpoints (Coming Soon)

- `POST /api/positions/open` - Open position
- `POST /api/positions/close` - Close position
- `GET /api/positions` - Get all positions
- `GET /api/balance` - Get wallet balance
- `GET /api/metrics` - Trading metrics

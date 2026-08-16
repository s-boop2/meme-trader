# 🤖 Meme Trader - Paper Trading Bot

> High-performance paper trading engine with Discord integration, real-time notifications, and advanced risk management.

## ✨ Features

- 📊 **Paper Trading Engine** - Simulate trades with realistic slippage & fees
- 💬 **Discord Bot** - Full slash command support (`/balance`, `/open`, `/close`, `/stats`)
- 🔔 **Dual Notifications** - Webhook alerts + bot messages
- 📈 **Position Tracking** - Real-time P&L monitoring
- 🛡️ **Risk Management** - Stop loss, take profit, trailing stops
- 💾 **MongoDB Storage** - Persistent trading history
- 🐳 **Docker Ready** - One-command deployment
- 🔄 **CI/CD** - GitHub Actions pipeline

---

## 🚀 Quick Start

### 1️⃣ Clone & Setup

```bash
git clone https://github.com/s-boop2/meme-trader.git
cd meme-trader
cp .env.example .env
```

### 2️⃣ Configure .env

```env
MONGODB_URI=mongodb://localhost:27017
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_server_id_here
DISCORD_WEBHOOK_URL=your_webhook_url_here
```

### 3️⃣ Run Bot

```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB (if local)
mongod

# Run bot
python bot/discord_bot.py
```

### 4️⃣ Start Trading in Discord

Type `/help` in your Discord server to see all commands!

---

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `/balance` | Check wallet balance |
| `/positions` | View open positions |
| `/open <symbol> <mint>` | Open new position |
| `/close <position_id>` | Close position |
| `/settings` | View trading settings |
| `/stats` | View trading statistics |
| `/help` | Show all commands |

---

## 🛠️ Architecture

```
meme-trader/
├── bot/
│   └── discord_bot.py              # Discord.py bot with slash commands
├── backend/
│   ├── engine.py                   # Paper trading engine core
│   ├── discord_notifier.py         # Webhook notification system
│   └── main.py                     # Async loop for monitoring
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI/CD
├── docker-compose.yml              # Docker orchestration
├── Dockerfile                      # Container image
├── requirements.txt                # Python dependencies
├── SETUP.md                        # Detailed setup guide
└── README.md                       # This file
```

---

## 🔧 Configuration

Edit settings in Discord:
```
/settings  # View current settings
```

Or modify directly in MongoDB:
```json
{
  "max_positions": 5,
  "buy_size": 50.0,
  "stop_loss_pct": -10.0,
  "tp1_pct": 20.0,
  "tp2_pct": 50.0,
  "ai_filter_enabled": true
}
```

---

## 📊 How It Works

### 1. Position Opening
- User runs `/open SYMBOL MINT`
- Engine simulates buy with realistic slippage (0.5-2%)
- Calculates network fees (~$0.10 equivalent)
- Stores position in MongoDB
- Sends Discord notification (both bot + webhook)

### 2. Position Monitoring
- Checks positions every 20 seconds
- Monitors stop loss & take profit levels
- Simulates price changes
- Auto-closes on SL/TP hit

### 3. Position Closing
- User can manually close with `/close ID`
- Engine calculates P&L
- Updates wallet balance
- Sends detailed close notification

---

## 🔔 Notifications

### Discord Bot Messages
- Instant responses to commands
- Embedded position details
- Real-time balance updates

### Webhook Embeds
- Position open/close alerts
- Take profit hits
- Stop loss triggers
- Error warnings
- Status updates (every 10 checks)

---

## 🐳 Docker Deployment

```bash
# Build & start
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop
docker-compose down
```

---

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run linter
flake8 backend/ --max-line-length=120
```

---

## 📚 Documentation

- **[SETUP.md](./SETUP.md)** - Detailed setup guide
- **[Discord Developer Portal](https://discord.com/developers/applications)** - Bot configuration
- **[Discord.py Docs](https://discordpy.readthedocs.io/)** - Bot API reference
- **[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)** - Cloud database

---

## ⚠️ Disclaimer

**This is a PAPER TRADING simulator.** It does NOT execute real trades or connect to actual exchanges. All trades are simulated for educational purposes only.

---

## 📝 License

MIT License - Free to use and modify

---

## 🤝 Contributing

Pull requests welcome! Please ensure:
- Code passes linter: `flake8`
- Tests pass: `pytest`
- Clear commit messages

---

**Made with 🤖 & ❤️ by s-boop2**

# 🤖 Meme Trader Bot - Setup Guide

## Prerequisites
- Python 3.11+
- MongoDB (local or cloud)
- Discord Server (you must be admin)
- Discord Bot Token

---

## 🚀 Quick Start

### 1. Create Discord Bot & Get Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → Name it `Meme Trader Bot`
3. Go to **Bot** section → Click **Add Bot**
4. Under **TOKEN** → Click **Copy**
5. Paste into `.env` as `DISCORD_BOT_TOKEN`

#### 1b. Set Bot Permissions

1. Go to **OAuth2** → **URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Read Messages/View Channels
4. Copy generated URL and open in browser
5. Select your server and authorize

---

### 2. Get Guild ID (Server ID)

1. In Discord, enable **Developer Mode** (User Settings → Advanced → Developer Mode)
2. Right-click your server → **Copy Server ID**
3. Paste into `.env` as `DISCORD_GUILD_ID`

---

### 3. Setup Environment

```bash
# Clone repo (if not done)
git clone https://github.com/s-boop2/meme-trader.git
cd meme-trader

# Create .env from example
cp .env.example .env

# Edit .env with your tokens
nano .env
```

**Your .env should look like:**
```
MONGODB_URI=mongodb://localhost:27017
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/...
DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
DISCORD_GUILD_ID=YOUR_SERVER_ID_HERE
BOT_ENABLED=true
CHECK_INTERVAL=20
```

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
# Additional for bot
pip install discord.py motor pymongo
```

---

### 5. Start Bot

#### Option A: Direct Python
```bash
python bot/discord_bot.py
```

#### Option B: Docker Compose
```bash
docker-compose up -d
```

---

## 📊 Bot Commands

### Slash Commands (type `/` in Discord)

| Command | Description |
|---------|-------------|
| `/balance` | Check your wallet balance |
| `/positions` | View all open trading positions |
| `/open <symbol> <mint>` | Open a new trading position |
| `/close <position_id>` | Close an open position |
| `/settings` | View current trading settings |
| `/help` | Show all commands |

### Example Usage
```
/open symbol:DOGE mint:EPjFWaLb3bsqxL...
/balance
/positions
/close position_id:abc123def456
```

---

## 🔔 Notifications

The bot sends **2 types of notifications**:

### 1. **Discord Bot Messages** (Live in chat)
- Slash command responses
- Position updates in real-time
- Settings display

### 2. **Webhook Embeds** (Automatic alerts)
- Position opened/closed
- Take profit hits
- Stop loss triggered
- Errors & warnings
- Status updates (every 10 checks)

---

## 🛠️ Troubleshooting

### Bot not showing up in Discord
- ✅ Check bot has `applications.commands` scope
- ✅ Ensure `DISCORD_GUILD_ID` is set in .env
- ✅ Restart bot: `python bot/discord_bot.py`
- ✅ Type `/` and wait 5 seconds for commands to appear

### No notifications on Discord
- ✅ Check `DISCORD_WEBHOOK_URL` is correct in .env
- ✅ Verify MongoDB connection: `MONGODB_URI`
- ✅ Check bot logs: `tail -f bot/discord_bot.py`
- ✅ Try manual test:
  ```python
  python -c "from backend.discord_notifier import DiscordNotifier; import asyncio; notifier = DiscordNotifier(); asyncio.run(notifier.send_embed('Test', 'Testing webhook'))"
  ```

### MongoDB connection error
- ✅ Start MongoDB: `mongod` or `docker run -d -p 27017:27017 mongo`
- ✅ Check URI format: `mongodb://localhost:27017`

### Permission denied when pushing
- ✅ Check GitHub token permissions
- ✅ Ensure you're collaborator on repo
- ✅ Use personal access token (PAT)

---

## 📚 Architecture

```
meme-trader/
├── bot/
│   └── discord_bot.py          # Discord.py bot with slash commands
├── backend/
│   ├── engine.py               # Paper trading engine
│   ├── discord_notifier.py     # Webhook notifications
│   └── main.py                 # Async engine loop
├── .env.example                # Environment template
├── docker-compose.yml          # Docker setup
├── Dockerfile                  # Container image
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 🚀 Next Steps

1. ✅ Get Discord Bot Token
2. ✅ Configure .env
3. ✅ Start MongoDB
4. ✅ Run `python bot/discord_bot.py`
5. ✅ Use `/help` in Discord
6. ✅ Start trading!

---

## 📞 Support

If you run into issues:
1. Check the logs: `tail -f bot/discord_bot.py`
2. Verify all .env variables are set
3. Ensure MongoDB is running
4. Check Discord bot has correct permissions

**Happy Trading! 🚀**

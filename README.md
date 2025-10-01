# Discord Online Member Tracker Bot

A production-ready Discord bot that tracks and notifies about online members in your server with real-time updates and periodic summaries.

## Features

- 🟢 **Manual Online Check**: `/online` command to instantly see all online members
- ⚙️ **Admin Setup**: `/setchannel` command to designate notification channels
- 🔄 **Automatic Updates**: Periodic summaries every 5 minutes
- ⚡ **Real-time Notifications**: Instant alerts when members go online/offline
- 🤖 **Bot Filtering**: Excludes other bots from all tracking and notifications
- 🛡️ **Robust Error Handling**: Built-in rate limiting and error recovery
- 📊 **Status Grouping**: Organizes members by Online, Idle, and Do Not Disturb

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Discord Developer Portal Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select an existing one
3. Go to the "Bot" section
4. **CRITICAL**: Enable these Privileged Gateway Intents:
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **PRESENCE INTENT**
5. Copy your bot token

### 3. Environment Configuration

Create a `.env` file in the project directory:

```env
BOT_TOKEN=your_bot_token_here
```

**⚠️ Security Note**: Never commit your `.env` file to version control!

### 4. Bot Permissions

When inviting your bot to a server, ensure it has these permissions:
- ✅ Send Messages
- ✅ Use Slash Commands
- ✅ View Channels
- ✅ Embed Links
- ✅ Read Message History

**Quick Invite Link Format**:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=274877908992&scope=bot%20applications.commands
```

Replace `YOUR_BOT_CLIENT_ID` with your bot's client ID from the Developer Portal.

### 5. Run the Bot

```bash
python discord_bot.py
```

## Commands

### `/online`
Lists all currently online non-bot members, grouped by status:
- 🟢 Online
- 🟡 Idle  
- 🔴 Do Not Disturb

**Usage**: Anyone can use this command
**Example**: `/online`

### `/setchannel <channel>`
Sets the designated channel for automatic notifications.

**Usage**: Administrator only
**Example**: `/setchannel #online-updates`

**What happens after setup**:
- Automatic member summaries every 5 minutes
- Real-time online/offline notifications
- Test message sent to confirm setup

### `/removechannel`
Disables automatic notifications for the server.

**Usage**: Administrator only
**Example**: `/removechannel`

## File Structure

```
LMT/
├── discord_bot.py      # Main bot application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this)
├── README.md          # This documentation
├── bot_settings.json  # Auto-generated settings storage
└── bot.log           # Auto-generated log file
```

## How It Works

### Real-time Tracking
The bot uses Discord's `on_member_update` event to detect status changes instantly:
- When a member comes online: "🟢 UserX is now online!"
- When a member goes offline: "🔴 UserY went offline!"

### Periodic Updates
Every 5 minutes, the bot sends a comprehensive summary showing:
- Total online member count
- Members grouped by status (Online, Idle, DND)
- Timestamp of the update

### Data Storage
- Settings are stored in `bot_settings.json`
- Each server's notification channel is remembered
- No personal data is stored, only channel IDs

## Troubleshooting

### Common Issues

**"Bot not responding to commands"**
- Ensure the bot is online and has joined your server
- Check that slash commands are synced (happens automatically on startup)
- Verify the bot has necessary permissions

**"Missing Access" errors**
- Enable SERVER MEMBERS INTENT and PRESENCE INTENT in Developer Portal
- Restart the bot after enabling intents

**"Can't send messages to channel"**
- Ensure the bot has "Send Messages" permission in the target channel
- Check channel-specific permission overrides

**"No members showing as online"**
- Verify PRESENCE INTENT is enabled
- Some users may have invisible status
- Bots are intentionally excluded from all lists

### Log Files
Check `bot.log` for detailed error information and debugging.

### Rate Limiting
The bot includes built-in protections against Discord's rate limits:
- 1-second delays between guild updates
- Proper error handling for HTTP exceptions
- Automatic retry logic for failed requests

## Security Best Practices

1. **Never share your bot token**
2. **Use environment variables** for sensitive data
3. **Regularly rotate your bot token** if compromised
4. **Limit bot permissions** to only what's necessary
5. **Monitor bot logs** for unusual activity

## Support

If you encounter issues:
1. Check the `bot.log` file for error details
2. Verify all setup steps were completed correctly
3. Ensure your Discord server has the bot with proper permissions
4. Test with the `/online` command first before setting up automatic notifications

## License

This project is provided as-is for educational and practical use. Feel free to modify and distribute according to your needs.
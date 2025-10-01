# 🚀 Deploy Discord Bot to Render

## Why Render?
- ✅ **Free Tier Available** - 750 hours/month free
- ✅ **Always-On Services** - No sleeping like Heroku free tier
- ✅ **Automatic Deploys** - Deploy from GitHub automatically
- ✅ **Easy Setup** - Simple configuration
- ✅ **Docker Support** - Uses your Dockerfile

## Step-by-Step Deployment Guide

### 1. Prepare Your Repository

First, make sure your code is on GitHub:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit your changes
git commit -m "Discord bot ready for Render deployment"

# Add your GitHub repository
git remote add origin https://github.com/yourusername/your-repo-name.git

# Push to GitHub
git push -u origin main
```

### 2. Deploy to Render

1. **Go to Render**
   - Visit [render.com](https://render.com)
   - Sign up with your GitHub account

2. **Create New Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your Discord bot repository

3. **Configure Service Settings**
   ```
   Name: discord-bot (or your preferred name)
   Environment: Docker
   Region: Choose closest to you
   Branch: main
   Build Command: (leave empty)
   Start Command: python discord_bot.py
   ```

4. **Set Environment Variables**
   - Scroll down to "Environment Variables"
   - Click "Add Environment Variable"
   - Key: `BOT_TOKEN`
   - Value: `your_actual_discord_bot_token`
   - Click "Add"

5. **Choose Plan**
   - Select "Free" plan (750 hours/month)
   - For 24/7 operation, upgrade to "Starter" ($7/month)

6. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your bot

### 3. Monitor Your Bot

- **View Logs**: Click on your service → "Logs" tab
- **Check Status**: Service dashboard shows if bot is running
- **Auto-Deploy**: Any GitHub push will trigger automatic redeployment

## Important Notes

### Free Tier Limitations
- **750 hours/month** (about 25 days of 24/7 operation)
- **Spins down after 15 minutes** of inactivity (but Discord bots are always active)
- **Slower cold starts** when spinning up

### Upgrading to Paid Plan
- **$7/month Starter plan** for true 24/7 operation
- **No spin-down** - always running
- **Faster performance**

## Troubleshooting

### Common Issues:

1. **Bot Not Starting**
   - Check logs for errors
   - Verify `BOT_TOKEN` is correctly set
   - Ensure all dependencies are in requirements.txt

2. **Build Failures**
   - Check Dockerfile syntax
   - Verify requirements.txt is valid
   - Look at build logs for specific errors

3. **Bot Offline in Discord**
   - Check if service is running in Render dashboard
   - Verify bot token is valid
   - Check bot permissions in Discord server

### Checking Logs:
```bash
# In Render dashboard:
# 1. Go to your service
# 2. Click "Logs" tab
# 3. Look for startup messages and errors
```

## Environment Variables Needed

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Your Discord bot token | `MTQyMjkxOTI1OTI2ODQ0ODI2Nw...` |

## Cost Breakdown

| Plan | Price | Hours/Month | Best For |
|------|-------|-------------|----------|
| Free | $0 | 750 hours | Testing/Development |
| Starter | $7/month | Unlimited | Production 24/7 |

## Next Steps After Deployment

1. **Test Your Bot** - Verify it responds in Discord
2. **Monitor Logs** - Check for any errors
3. **Set Up Alerts** - Get notified if bot goes down
4. **Consider Upgrading** - For true 24/7 operation

## Support

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Discord.py Docs**: [discordpy.readthedocs.io](https://discordpy.readthedocs.io)

Your Discord bot will be live and running 24/7 on Render! 🎉
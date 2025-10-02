"""
Discord Online Member Tracker Bot

A production-ready Discord bot that tracks and notifies about online members in a server.

Features:
- /online command to list currently online non-bot members
- /setchannel command for admins to set notification channel
- Automatic periodic updates every 5 minutes
- Real-time status change notifications
- Proper error handling and rate limiting

Setup Instructions:
1. Install dependencies: pip install discord.py python-dotenv
2. Create a .env file with your bot token: BOT_TOKEN=your_bot_token_here
3. Enable SERVER MEMBERS INTENT and PRESENCE INTENT in Discord Developer Portal
4. Invite bot with Administrator permissions (or at minimum: Send Messages, Use Slash Commands, View Channels)

Required Discord Developer Portal Settings:
- Go to https://discord.com/developers/applications
- Select your application -> Bot
- Enable "SERVER MEMBERS INTENT" under Privileged Gateway Intents
- Enable "PRESENCE INTENT" under Privileged Gateway Intents
"""

import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, Set
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set console encoding to UTF-8 for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Bot configuration
SETTINGS_FILE = 'bot_settings.json'
UPDATE_INTERVAL_MINUTES = 5

class OnlineMemberTracker(commands.Bot):
    def __init__(self):
        # Required intents for member and presence tracking
        intents = discord.Intents.default()
        intents.members = True  # Required to access member list
        intents.presences = True  # Required to track online status
        intents.message_content = True  # For potential prefix commands
        
        super().__init__(
            command_prefix='!',  # Fallback prefix
            intents=intents,
            help_command=None
        )
        
        # Store notification channels per guild
        self.notification_channels: Dict[int, int] = {}
        # Store target roles per guild for notifications
        self.target_roles: Dict[int, int] = {}
        # Track previous online members for change detection
        self.previous_online: Dict[int, Set[int]] = {}
        
        # Load settings
        self.load_settings()
    
    def load_settings(self):
        """Load bot settings from file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.notification_channels = {int(k): v for k, v in data.get('notification_channels', {}).items()}
                    self.target_roles = {int(k): v for k, v in data.get('target_roles', {}).items()}
                    logger.info(f"Loaded settings for {len(self.notification_channels)} guilds")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save bot settings to file"""
        try:
            data = {
                'notification_channels': self.notification_channels,
                'target_roles': self.target_roles
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get_online_members(self, guild: discord.Guild) -> list:
        """Get list of online non-bot members"""
        online_members = []
        for member in guild.members:
            if (not member.bot and 
                member.status != discord.Status.offline and 
                member.status != discord.Status.invisible):
                online_members.append(member)
        return online_members
    
    async def send_online_summary(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send a summary of online members to the specified channel"""
        try:
            online_members = self.get_online_members(guild)
            
            if not online_members:
                embed = discord.Embed(
                    title="🌙✨ The Server is Sleeping...",
                    description="```\n🌟 Nobody's online right now 🌟\n```\n" +
                               "💤 **0** members currently active\n\n" +
                               "🔮 *The digital realm awaits your return...*",
                    color=discord.Color.from_rgb(47, 49, 54),
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="⏰ Auto-Updates",
                    value="```yaml\nNext check: 5 minutes\nStatus: Active 🟢\n```",
                    inline=True
                )
                embed.add_field(
                    name="💡 Pro Tip",
                    value="```css\n/* Be the first to wake up the server! */\n```",
                    inline=True
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/787038339664781322.png")
            else:
                # Group members by status
                status_groups = {
                    discord.Status.online: [],
                    discord.Status.idle: [],
                    discord.Status.dnd: []
                }
                
                for member in online_members:
                    if member.status in status_groups:
                        status_groups[member.status].append(member)
                
                # Create animated title based on member count
                if len(online_members) == 1:
                    title = "👋✨ A Lone Warrior Appears!"
                elif len(online_members) <= 3:
                    title = "🎭🎪 A Small Gathering!"
                elif len(online_members) <= 8:
                    title = "🎉🔥 Party Mode Activated!"
                elif len(online_members) <= 15:
                    title = "🚀⚡ Server Energy Rising!"
                else:
                    title = "🌟💫 MAXIMUM ACTIVITY DETECTED!"
                
                # Dynamic color based on activity level
                if len(online_members) <= 3:
                    color = discord.Color.from_rgb(87, 242, 135)  # Light green
                elif len(online_members) <= 8:
                    color = discord.Color.from_rgb(255, 231, 146)  # Yellow
                elif len(online_members) <= 15:
                    color = discord.Color.from_rgb(255, 159, 67)   # Orange
                else:
                    color = discord.Color.from_rgb(255, 107, 107)  # Red
                
                # Create progress bar for activity level
                total_members = len(guild.members)
                online_percentage = (len(online_members) / total_members) * 100
                progress_bars = int(online_percentage / 10)
                progress_bar = "🟩" * progress_bars + "⬜" * (10 - progress_bars)
                
                embed = discord.Embed(
                    title=title,
                    description=f"```ansi\n\u001b[1;32m▓▓▓ LIVE SERVER STATUS ▓▓▓\u001b[0m\n```\n" +
                               f"🎯 **{len(online_members)}** members online and ready!\n" +
                               f"📊 Activity Level: {progress_bar} **{online_percentage:.1f}%**\n\n" +
                               f"💬 *{self._get_activity_message(len(online_members))}*",
                    color=color,
                    timestamp=datetime.now()
                )
                
                # Enhanced status info with animations
                status_info = {
                    discord.Status.online: {
                        "emoji": "🟢",
                        "name": "🌟 Online & Active",
                        "description": "```diff\n+ Ready to chat and engage!\n```",
                        "animation": "⚡"
                    },
                    discord.Status.idle: {
                        "emoji": "🟡", 
                        "name": "🌙 Away",
                        "description": "```yaml\n~ Might be busy or AFK\n```",
                        "animation": "💤"
                    },
                    discord.Status.dnd: {
                        "emoji": "🔴",
                        "name": "🚫 Do Not Disturb",
                        "description": "```css\n/* Please respect their focus time */\n```",
                        "animation": "🔕"
                    }
                }
                
                # Add beautiful status fields
                for status, members in status_groups.items():
                    if members:
                        status_data = status_info[status]
                        
                        # Create animated member list
                        if len(members) <= 6:
                            member_list = "\n".join([f"{status_data['animation']} **{member.display_name}**" for member in members])
                        else:
                            member_list = "\n".join([f"{status_data['animation']} **{member.display_name}**" for member in members[:6]])
                            member_list += f"\n🎭 *...and {len(members) - 6} more amazing people!*"
                        
                        embed.add_field(
                            name=f"{status_data['emoji']} {status_data['name']} ({len(members)})",
                            value=f"{status_data['description']}\n{member_list}",
                            inline=True if len([g for g in status_groups.values() if g]) > 1 else False
                        )
                
                # Enhanced activity summary with visual elements
                embed.add_field(
                    name="📈🎯 Server Pulse",
                    value=f"```ini\n[Activity Level] = {online_percentage:.1f}%\n" +
                          f"[Online Now]    = {len(online_members)} members\n" +
                          f"[Total Members] = {total_members} people\n```\n" +
                          f"🎪 **Community Vibe:** {self._get_vibe_emoji(online_percentage)} {self._get_vibe_text(online_percentage)}",
                    inline=False
                )
                
                # Add a fun fact or tip
                embed.add_field(
                    name="🎲 Did You Know?",
                    value=f"```md\n# {self._get_fun_fact(len(online_members))}\n```",
                    inline=False
                )
            
            embed.set_footer(
                text=f"🏰 {guild.name} • 🔄 Auto-refresh every 5min",
                icon_url=guild.icon.url if guild.icon else None
            )
            
            await channel.send(embed=embed)
            
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending online summary: {e}")
        except Exception as e:
            logger.error(f"Error sending online summary: {e}")
    
    async def send_dm_notifications(self, member: discord.Member, target_role: discord.Role):
        """Send DM notifications to all users with the target role when someone comes online"""
        try:
            logger.info(f"Sending DM notifications for {member.display_name} coming online")
            
            # Get all members with the target role (excluding the member who just came online)
            members_to_notify = [m for m in target_role.members if m != member and not m.bot]
            
            if not members_to_notify:
                logger.info(f"No members to notify for {member.display_name} coming online")
                return
            
            # Create the DM embed
            embed = discord.Embed(
                title="🟢 Someone's Online!",
                description=f"**{member.display_name}** just came online in **{member.guild.name}**!",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name="💬 Ready to Chat",
                value="Perfect timing to start a conversation!",
                inline=False
            )
            embed.set_footer(
                text=f"From {member.guild.name}",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            
            # Send DMs to all members with the target role
            successful_dms = 0
            failed_dms = 0
            
            for notify_member in members_to_notify:
                try:
                    await notify_member.send(embed=embed)
                    successful_dms += 1
                    logger.info(f"✅ DM sent to {notify_member.display_name}")
                except discord.Forbidden:
                    failed_dms += 1
                    logger.warning(f"❌ Cannot send DM to {notify_member.display_name} (DMs disabled)")
                except discord.HTTPException as e:
                    failed_dms += 1
                    logger.error(f"❌ Failed to send DM to {notify_member.display_name}: {e}")
                except Exception as e:
                    failed_dms += 1
                    logger.error(f"❌ Unexpected error sending DM to {notify_member.display_name}: {e}")
            
            logger.info(f"DM notification summary: {successful_dms} sent, {failed_dms} failed")
            
        except Exception as e:
            logger.error(f"Error in send_dm_notifications: {e}")
    
    def _get_activity_message(self, count: int) -> str:
        """Get dynamic activity message based on member count"""
        if count == 1:
            return "A brave soul ventures into the digital realm!"
        elif count <= 3:
            return "A cozy gathering of digital friends!"
        elif count <= 8:
            return "The conversation is heating up!"
        elif count <= 15:
            return "This server is absolutely buzzing with energy!"
        else:
            return "MAXIMUM SOCIAL ENERGY ACHIEVED! 🚀"
    
    def _get_vibe_emoji(self, percentage: float) -> str:
        """Get vibe emoji based on activity percentage"""
        if percentage < 10:
            return "😴"
        elif percentage < 25:
            return "🌱"
        elif percentage < 50:
            return "🔥"
        elif percentage < 75:
            return "⚡"
        else:
            return "🌟"
    
    def _get_vibe_text(self, percentage: float) -> str:
        """Get vibe text based on activity percentage"""
        if percentage < 10:
            return "Peaceful & Quiet"
        elif percentage < 25:
            return "Growing Energy"
        elif percentage < 50:
            return "Active & Lively"
        elif percentage < 75:
            return "High Energy Zone"
        else:
            return "LEGENDARY ACTIVITY!"
    
    def _get_fun_fact(self, count: int) -> str:
        """Get a fun fact based on online member count"""
        facts = [
            f"With {count} people online, you could start a great conversation!",
            f"Did you know? {count} online members = infinite possibilities!",
            f"Fun fact: The perfect group size for discussions is 3-8 people!",
            f"Amazing! {count} digital souls are sharing this moment together!",
            f"Pro tip: The best conversations happen when people are genuinely engaged!",
            f"Cool fact: Online communities create bonds that last a lifetime!",
            f"Interesting: {count} people online means {count} unique perspectives!",
            f"Did you know? Active servers create the strongest friendships!"
        ]
        import random
        return random.choice(facts)
    
    def _get_engagement_suggestion(self, count: int) -> str:
        """Get engagement suggestions based on online member count"""
        if count == 1:
            return "Perfect time to share something interesting and draw others in!"
        elif count <= 3:
            return "Great for intimate discussions or planning something fun!"
        elif count <= 8:
            return "Ideal for group activities, games, or collaborative projects!"
        elif count <= 15:
            return "Amazing energy for events, contests, or community activities!"
        else:
            return "MAXIMUM POTENTIAL! Host events, start discussions, go wild!"
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status to "Watching Who's Online" with busy (DND) status
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="Who's Online"
            )
            await self.change_presence(
                status=discord.Status.dnd,  # "busy" status (Do Not Disturb)
                activity=activity
            )
            logger.info("Bot status set to: Watching Who's Online (DND)")
        except Exception as e:
            logger.error(f"Failed to set bot status: {e}")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        # Initialize previous online members tracking and debug member presence
        for guild in self.guilds:
            logger.info(f"Guild: {guild.name} ({guild.id})")
            logger.info(f"Total members: {guild.member_count}")
            logger.info(f"Cached members: {len(guild.members)}")
            
            # Check if we can see member presence
            online_count = 0
            offline_count = 0
            for member in guild.members:
                if not member.bot:
                    if member.status != discord.Status.offline and member.status != discord.Status.invisible:
                        online_count += 1
                    else:
                        offline_count += 1
            
            logger.info(f"Online members visible: {online_count}")
            logger.info(f"Offline members visible: {offline_count}")
            
            # Check target role
            if guild.id in self.target_roles:
                target_role_id = self.target_roles[guild.id]
                target_role = guild.get_role(target_role_id)
                if target_role:
                    logger.info(f"Target role: {target_role.name} ({target_role.id}) - {len(target_role.members)} members")
                    # List first few members with target role
                    for i, member in enumerate(target_role.members[:3]):
                        logger.info(f"  Member {i+1}: {member.display_name} - Status: {member.status}")
                else:
                    logger.warning(f"Target role {target_role_id} not found!")
            
            online_members = self.get_online_members(guild)
            self.previous_online[guild.id] = {member.id for member in online_members}
        
        # Periodic updates disabled - only role-specific real-time notifications
    
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member status changes for real-time notifications with beautiful embeds"""
        logger.info(f"on_member_update triggered for {after.display_name} ({after.id}) in guild {after.guild.name}")
        logger.info(f"Status: {before.status} -> {after.status}")
        logger.info(f"Activity: {before.activity} -> {after.activity}")
        logger.info(f"Roles: {[role.name for role in after.roles]}")
        
        # Only process status changes, not other updates
        if before.status == after.status:
            logger.info(f"No status change for {after.display_name}, skipping")
            return
        
        # Skip bots
        if after.bot:
            logger.info(f"Skipping bot {after.display_name}")
            return
        
        guild_id = after.guild.id
        logger.info(f"Status change detected for {after.display_name} in guild {guild_id}: {before.status} -> {after.status}")
        logger.info(f"Member {after.display_name} roles: {[role.name for role in after.roles]}")
        
        # Note: No longer requiring notification channel since we use DMs
        
        # Check if we have a target role set for this guild
        if guild_id not in self.target_roles:
            logger.info(f"No target role set for guild {guild_id}")
            return
        
        # Check if the member has the target role
        target_role_id = self.target_roles[guild_id]
        target_role = after.guild.get_role(target_role_id)
        if not target_role:
            logger.warning(f"Target role {target_role_id} not found in guild {guild_id}")
            return
        
        has_target_role = target_role in after.roles
        
        if not has_target_role:
            logger.info(f"{after.display_name} does not have the target role {target_role.name}")
            logger.info(f"Member roles: {[f'{role.name} ({role.id})' for role in after.roles]}")
            logger.info(f"Target role ID: {target_role_id}")
            return
        
        logger.info(f"{after.display_name} HAS the target role {target_role.name}")
        logger.info(f"Processing notification for {after.display_name}...")
        
        try:
            
            # Determine if member went online or offline
            was_online = (before.status != discord.Status.offline and 
                         before.status != discord.Status.invisible)
            is_online = (after.status != discord.Status.offline and 
                        after.status != discord.Status.invisible)
            
            if not was_online and is_online:
                # Member came online - send DM to users with target role
                logger.info(f"🟢 {after.display_name} came online!")
                await self.send_dm_notifications(after, target_role)
                
            elif was_online and not is_online:
                # Member went offline - just log it, don't send notification
                logger.info(f"🔴 {after.display_name} went offline (no notification sent)")
                
        except discord.HTTPException as e:
            logger.error(f"HTTP error in member update: {e}")
        except Exception as e:
            logger.error(f"Error in member update handler: {e}")
    
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        """Handle presence updates (status changes) for real-time notifications"""
        logger.info(f"PRESENCE UPDATE: {after.display_name} - Status: {before.status} -> {after.status}")
        if before.activity != after.activity:
            logger.info(f"  Activity: {before.activity} -> {after.activity}")
        
        # Only process status changes, not activity changes
        if before.status == after.status:
            logger.info(f"No status change for {after.display_name}, skipping")
            return
        
        # Skip bots
        if after.bot:
            logger.info(f"Skipping bot {after.display_name}")
            return
        
        guild_id = after.guild.id
        logger.info(f"Status change detected for {after.display_name} in guild {guild_id}: {before.status} -> {after.status}")
        
        # Note: No longer requiring notification channel since we use DMs
        
        # Check if we have a target role set for this guild
        if guild_id not in self.target_roles:
            logger.info(f"No target role set for guild {guild_id}")
            return
        
        # Check if the member has the target role
        target_role_id = self.target_roles[guild_id]
        target_role = after.guild.get_role(target_role_id)
        if not target_role:
            logger.warning(f"Target role {target_role_id} not found in guild {guild_id}")
            return
        
        has_target_role = target_role in after.roles
        
        if not has_target_role:
            logger.info(f"{after.display_name} does not have the target role {target_role.name}")
            logger.info(f"Member roles: {[f'{role.name} ({role.id})' for role in after.roles]}")
            logger.info(f"Target role ID: {target_role_id}")
            return
        
        logger.info(f"{after.display_name} HAS the target role {target_role.name}")
        logger.info(f"Processing notification for {after.display_name}...")
        
        try:
            
            # Determine if member went online or offline
            was_online = (before.status != discord.Status.offline and 
                         before.status != discord.Status.invisible)
            is_online = (after.status != discord.Status.offline and 
                        after.status != discord.Status.invisible)
            
            logger.info(f"Status transition: was_online={was_online}, is_online={is_online}")
            
            if not was_online and is_online:
                # Member came online - send DM to users with target role
                logger.info(f"🟢 {after.display_name} came online!")
                await self.send_dm_notifications(after, target_role)
                
            elif was_online and not is_online:
                # Member went offline - just log it, don't send notification
                logger.info(f"🔴 {after.display_name} went offline (no notification sent)")
                
        except Exception as e:
            logger.error(f"Error in presence update handler: {e}")
    
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Debug user updates"""
        logger.info(f"USER UPDATE: {after.display_name}")
    
    async def on_guild_join(self, guild):
        """Debug guild events"""
        logger.info(f"GUILD JOIN: {guild.name}")
    
    async def on_guild_remove(self, guild):
        """Debug guild events"""
        logger.info(f"GUILD REMOVE: {guild.name}")
    
    async def on_member_join(self, member):
        """Debug member events"""
        logger.info(f"MEMBER JOIN: {member.display_name} in {member.guild.name}")
    
    async def on_member_remove(self, member):
        """Debug member events"""
        logger.info(f"MEMBER REMOVE: {member.display_name} from {member.guild.name}")
    
    async def on_raw_member_update(self, payload):
        """Debug raw member updates"""
        logger.info(f"RAW MEMBER UPDATE: {payload}")
    
    @tasks.loop(minutes=UPDATE_INTERVAL_MINUTES)
    async def periodic_update(self):
        """Send periodic online member updates"""
        for guild in self.guilds:
            if guild.id in self.notification_channels:
                try:
                    channel = self.get_channel(self.notification_channels[guild.id])
                    if channel:
                        await self.send_online_summary(channel, guild)
                        # Small delay to avoid rate limits
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error in periodic update for guild {guild.id}: {e}")
    
    @periodic_update.before_loop
    async def before_periodic_update(self):
        """Wait until bot is ready before starting periodic updates"""
        await self.wait_until_ready()

# Initialize bot
bot = OnlineMemberTracker()

@bot.tree.command(name="online", description="🔍 Discover who's currently online and ready to chat!")
async def online_command(interaction: discord.Interaction):
    """Enhanced slash command to list online members with beautiful visuals"""
    try:
        await interaction.response.defer()
        
        online_members = bot.get_online_members(interaction.guild)
        
        if not online_members:
            embed = discord.Embed(
                title="🌙✨ The Digital Realm is Quiet...",
                description="```yaml\n🌟 Nobody's online right now 🌟\n```\n" +
                           "💤 **0** members currently active\n\n" +
                           "🔮 *Perfect time to be the first one to start the conversation!*",
                color=discord.Color.from_rgb(47, 49, 54),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="🎯 Quick Actions",
                value="```css\n• Send a message to wake everyone up!\n• Check back in a few minutes\n• Start an interesting topic\n```",
                inline=True
            )
            embed.add_field(
                name="⏰ Best Times",
                value="```ini\n[Peak Hours] = Usually evenings\n[Weekends]   = More activity\n[Events]     = Check announcements\n```",
                inline=True
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/787038339664781322.png")
        else:
            # Group members by status
            status_groups = {
                discord.Status.online: [],
                discord.Status.idle: [],
                discord.Status.dnd: []
            }
            
            for member in online_members:
                if member.status in status_groups:
                    status_groups[member.status].append(member)
            
            # Create spectacular animated title based on count
            if len(online_members) == 1:
                title = "👑✨ A Lone Digital Warrior!"
            elif len(online_members) <= 3:
                title = "🎭🎪 Intimate Gathering Mode!"
            elif len(online_members) <= 8:
                title = "🎉🔥 Party Time Activated!"
            elif len(online_members) <= 15:
                title = "🚀⚡ HIGH ENERGY DETECTED!"
            else:
                title = "🌟💫 LEGENDARY ACTIVITY LEVEL!"
            
            # Dynamic color scheme based on activity
            if len(online_members) <= 3:
                color = discord.Color.from_rgb(87, 242, 135)  # Light green
            elif len(online_members) <= 8:
                color = discord.Color.from_rgb(255, 231, 146)  # Yellow
            elif len(online_members) <= 15:
                color = discord.Color.from_rgb(255, 159, 67)   # Orange
            else:
                color = discord.Color.from_rgb(255, 107, 107)  # Red
            
            # Create stunning progress visualization
            total_members = len(interaction.guild.members)
            online_percentage = (len(online_members) / total_members) * 100
            progress_bars = int(online_percentage / 10)
            progress_bar = "🟩" * progress_bars + "⬜" * (10 - progress_bars)
            
            embed = discord.Embed(
                title=title,
                description=f"```ansi\n\u001b[1;36m▓▓▓ INSTANT SERVER SNAPSHOT ▓▓▓\u001b[0m\n```\n" +
                           f"🎯 **{len(online_members)}** amazing people online right now!\n" +
                           f"📊 Activity Meter: {progress_bar} **{online_percentage:.1f}%**\n\n" +
                           f"💫 *{bot._get_activity_message(len(online_members))}*",
                color=color,
                timestamp=datetime.now()
            )
            
            # Enhanced status info with spectacular animations
            status_info = {
                discord.Status.online: {
                    "emoji": "🟢",
                    "name": "🌟 Online & Ready",
                    "description": "```diff\n+ Active and ready to engage!\n```",
                    "animation": "⚡",
                    "subtitle": "Perfect for chatting!"
                },
                discord.Status.idle: {
                    "emoji": "🟡", 
                    "name": "🌙 Away Mode",
                    "description": "```yaml\n~ Might be multitasking or AFK\n```",
                    "animation": "💤",
                    "subtitle": "May respond slower"
                },
                discord.Status.dnd: {
                    "emoji": "🔴",
                    "name": "🚫 Focus Mode",
                    "description": "```css\n/* Deep work or important tasks */\n```",
                    "animation": "🔕",
                    "subtitle": "Please be respectful"
                }
            }
            
            # Add spectacular status fields with enhanced visuals
            for status, members in status_groups.items():
                if members:
                    status_data = status_info[status]
                    
                    # Create beautiful animated member list
                    if len(members) <= 8:
                        member_list = "\n".join([f"{status_data['animation']} **{member.display_name}**" for member in members])
                    else:
                        member_list = "\n".join([f"{status_data['animation']} **{member.display_name}**" for member in members[:8]])
                        member_list += f"\n🎭 *...and {len(members) - 8} more incredible people!*"
                    
                    embed.add_field(
                        name=f"{status_data['emoji']} {status_data['name']} ({len(members)})",
                        value=f"{status_data['description']}\n{member_list}\n\n*{status_data['subtitle']}*",
                        inline=True if len([g for g in status_groups.values() if g]) > 1 else False
                    )
            
            # Spectacular server analytics section
            embed.add_field(
                name="📈🎯 Live Server Analytics",
                value=f"```ini\n[Activity Level] = {online_percentage:.1f}%\n" +
                      f"[Online Now]    = {len(online_members)} members\n" +
                      f"[Total Members] = {total_members} people\n" +
                      f"[Server Vibe]   = {bot._get_vibe_text(online_percentage)}\n```\n" +
                      f"🎪 **Community Energy:** {bot._get_vibe_emoji(online_percentage)} {bot._get_vibe_text(online_percentage)}",
                inline=False
            )
            
            # Add interactive engagement section
            embed.add_field(
                name="🎮 Engagement Opportunities",
                value=f"```md\n# {bot._get_engagement_suggestion(len(online_members))}\n```\n" +
                      f"💡 *Perfect time to start conversations, share content, or collaborate!*",
                inline=False
            )
        
        embed.set_footer(
            text=f"🎭 Requested by {interaction.user.display_name} • 🏰 {interaction.guild.name} • ⚡ Instant results",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Add server icon as thumbnail for active servers
        if online_members and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in online command: {e}")
        error_embed = discord.Embed(
            title="⚠️ Oops! Something went wrong",
            description="```css\n/* Unable to fetch online members right now */\n```\n" +
                       "🔧 *Please try again in a moment or contact an admin if this persists.*",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="setchannel", description="Set the channel for automatic online member notifications")
@discord.app_commands.describe(channel="The channel to send notifications to")
async def setchannel_command(interaction: discord.Interaction, channel: discord.TextChannel):
    """Slash command to set notification channel (admin only)"""
    try:
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        # Check if bot can send messages in the channel
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {channel.mention}.", 
                ephemeral=True
            )
            return
        
        # Set the notification channel
        bot.notification_channels[interaction.guild.id] = channel.id
        bot.save_settings()
        
        embed = discord.Embed(
            title="✅ Notification Channel Set",
            description=f"Online member notifications will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📋 What happens next:",
            value=f"• Automatic updates every {UPDATE_INTERVAL_MINUTES} minutes\n• Real-time online/offline notifications\n• Use `/online` to manually check online members",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Send a test message to the channel
        test_embed = discord.Embed(
            title="🤖 Bot Setup Complete",
            description="This channel will now receive online member notifications!",
            color=discord.Color.blue()
        )
        await channel.send(embed=test_embed)
        
    except Exception as e:
        logger.error(f"Error in setchannel command: {e}")
        await interaction.response.send_message("❌ An error occurred while setting the channel.", ephemeral=True)

@bot.tree.command(name="removechannel", description="Remove automatic notifications for this server")
async def removechannel_command(interaction: discord.Interaction):
    """Slash command to remove notification channel (admin only)"""
    try:
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        if interaction.guild.id in bot.notification_channels:
            del bot.notification_channels[interaction.guild.id]
            bot.save_settings()
            
            embed = discord.Embed(
                title="✅ Notifications Disabled",
                description="Automatic online member notifications have been disabled for this server.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "❌ No notification channel is currently set for this server.", 
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error in removechannel command: {e}")
        await interaction.response.send_message("❌ An error occurred while removing the channel.", ephemeral=True)

@bot.tree.command(name="setrole", description="Set the target role for online/offline notifications")
@discord.app_commands.describe(role="The role to monitor for online/offline status changes")
async def setrole_command(interaction: discord.Interaction, role: discord.Role):
    """Set the target role for notifications"""
    try:
        guild_id = interaction.guild.id
        
        # Check if user has permission to manage roles
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the 'Manage Roles' permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Set the target role
        bot.target_roles[guild_id] = role.id
        bot.save_settings()
        
        embed = discord.Embed(
            title="✅ Target Role Set",
            description=f"Now monitoring **{role.name}** for online/offline status changes.\n\n" +
                       f"🎯 **Role:** {role.mention}\n" +
                       f"👥 **Members with this role:** {len(role.members)}\n\n" +
                       f"💡 *Only members with this role will trigger notifications when they go online or offline.*",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📋 Next Steps",
            value="• Make sure you've set a notification channel with `/setchannel`\n" +
                  "• Members with this role will now trigger notifications\n" +
                  "• Use `/removerole` to disable role-based filtering",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in setrole command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while setting the target role.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removerole", description="Remove role-based filtering for notifications")
async def removerole_command(interaction: discord.Interaction):
    """Remove target role filtering"""
    try:
        guild_id = interaction.guild.id
        
        # Check if user has permission to manage roles
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the 'Manage Roles' permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if guild_id not in bot.target_roles:
            embed = discord.Embed(
                title="❌ No Role Set",
                description="There's no target role set for this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Remove the target role
        del bot.target_roles[guild_id]
        bot.save_settings()
        
        embed = discord.Embed(
            title="✅ Role Filter Removed",
            description="Role-based filtering has been disabled.\n\n" +
                       "⚠️ **Note:** Since periodic updates are disabled, you won't receive any notifications until you set a new target role.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in removerole command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while removing the target role.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="checkrole", description="Check your current roles and target role status")
async def checkrole_command(interaction: discord.Interaction):
    """Check if the user has the target role for notifications"""
    try:
        guild_id = interaction.guild.id
        member = interaction.user
        
        # Get target role info
        target_role_id = bot.target_roles.get(guild_id)
        target_role = None
        has_target_role = False
        
        if target_role_id:
            target_role = interaction.guild.get_role(target_role_id)
            has_target_role = target_role in member.roles
        
        # Create embed
        embed = discord.Embed(
            title="🔍 Role Check Results",
            color=0x00ff00 if has_target_role else 0xff9900,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Your Username",
            value=member.display_name,
            inline=False
        )
        
        # Show all user roles
        user_roles = [role.name for role in member.roles if role.name != "@everyone"]
        embed.add_field(
            name="🎭 Your Roles",
            value=", ".join(user_roles) if user_roles else "No special roles",
            inline=False
        )
        
        # Show target role status
        if target_role:
            embed.add_field(
                name="🎯 Target Role",
                value=f"{target_role.name} ({target_role.id})",
                inline=False
            )
            
            embed.add_field(
                name="✅ Have Target Role?",
                value="Yes! You will receive notifications" if has_target_role else "No - You need this role to receive notifications",
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ Target Role",
                value="No target role set for this server",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in checkrole command: {e}")
        await interaction.response.send_message(f"❌ Error checking roles: {e}", ephemeral=True)

@bot.tree.command(name="testnotify", description="Test the notification system (Admin only)")
async def testnotify_command(interaction: discord.Interaction):
    """Test the notification system"""
    try:
        # Check if user has permission to manage roles
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the 'Manage Roles' permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        
        # Check configuration
        if guild_id not in bot.notification_channels:
            embed = discord.Embed(
                title="❌ No Channel Set",
                description="Please set a notification channel first with `/setchannel`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if guild_id not in bot.target_roles:
            embed = discord.Embed(
                title="❌ No Role Set", 
                description="Please set a target role first with `/setrole`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get the notification channel and target role
        channel = bot.get_channel(bot.notification_channels[guild_id])
        target_role = interaction.guild.get_role(bot.target_roles[guild_id])
        
        if not channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description="The notification channel could not be found.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not target_role:
            embed = discord.Embed(
                title="❌ Role Not Found",
                description="The target role could not be found.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Send test notification
        test_embed = discord.Embed(
            title="🧪✨ **NOTIFICATION SYSTEM TEST**",
            description=f"```ansi\n\u001b[1;32m▓▓▓ SYSTEM STATUS: OPERATIONAL ▓▓▓\u001b[0m\n```\n" +
                       f"🎯 **Target Role:** {target_role.mention}\n" +
                       f"📢 **Notification Channel:** {channel.mention}\n" +
                       f"👥 **Members with role:** {len(target_role.members)}\n\n" +
                       f"✅ **The notification system is working correctly!**\n" +
                       f"🔔 Members with the {target_role.name} role will trigger notifications when they go online/offline.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )

        test_embed.set_footer(text="🏰 LIMITLESS • Test completed successfully")
        
        await channel.send(embed=test_embed)
        
        # Response to user
        embed = discord.Embed(
            title="✅ Test Sent",
            description=f"Test notification sent to {channel.mention}!\n\n" +
                       f"The system is configured to monitor **{target_role.name}** role.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in testnotify command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while testing notifications.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="testdm", description="Test the DM notification system - sends you a sample DM")
async def testdm_command(interaction: discord.Interaction):
    """Test DM notifications by sending a sample DM to the user"""
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Create the same DM embed that would be sent for real notifications
        embed = discord.Embed(
            title="🟢 Someone's Online!",
            description=f"**{interaction.user.display_name}** just came online in **{interaction.guild.name}**!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(
            name="💬 Ready to Chat",
            value="Perfect timing to start a conversation!",
            inline=False
        )
        embed.set_footer(
            text=f"From {interaction.guild.name} • This is a test DM",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Try to send the DM
        try:
            await interaction.user.send(embed=embed)
            
            # Confirm in the channel
            success_embed = discord.Embed(
                title="✅ Test DM Sent!",
                description="Check your DMs to see how the notification looks.\n\n" +
                           "This is exactly what other users will receive when someone with the target role comes online.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Cannot Send DM",
                description="I couldn't send you a DM. Please check that:\n" +
                           "• You have DMs enabled from server members\n" +
                           "• You haven't blocked the bot",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in testdm command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while testing DM notifications.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    
    logger.error(f"Command error: {error}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with: BOT_TOKEN=your_bot_token_here")
        exit(1)
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token! Please check your BOT_TOKEN in the .env file.")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
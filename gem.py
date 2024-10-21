import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio

class Gem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gem_channel_id = None
        self.gem_reaction_emoji = "💎"  # Default gem emoji
        self.logger = logging.getLogger('gem_cog')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.gemed_messages = set()  # Track gemed messages


# Start the background task to ping Google every 30 minutes
        self.bot.loop.create_task(self.ping_google_task())

    # Function to ping google.com every 30 minutes
    async def ping_google_task(self):
        while True:
            await self.ping_google()
            await asyncio.sleep(3600)  # 1800 seconds = 30 minutes

    async def ping_google(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://www.google.com') as response:
                    if response.status == 200:
                        self.logger.info('Successfully pinged Google.com: Status 200')
                    else:
                        self.logger.warning(f'Failed to ping Google.com: Status {response.status}')
        except Exception as e:
            self.logger.error(f'Error pinging Google.com: {str(e)}')        

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if self.bot.user in message.mentions:
            ctx = await self.bot.get_context(message)
            content = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()
            command_parts = content.split(' ', 1)
            command_name = command_parts[0].lower()
            args = command_parts[1] if len(command_parts) > 1 else ''

            if command_name == "setgem":
                channel = next((c for c in message.channel_mentions if isinstance(c, discord.TextChannel)), None)
                if channel and ctx.author.guild_permissions.manage_channels:
                    await self.setgem(ctx, channel)
                else:
                    await ctx.send("You must mention a valid text channel and have 'Manage Channels' permission to set the gem channel.")
            elif command_name == "getgemchannel":
                await self.getgemchannel(ctx)
            elif command_name == "setgemreaction":
                await self.set_gem_reaction(ctx, args)

    async def setgem(self, ctx, channel: discord.TextChannel):
        """Set the channel where gem messages will be stored."""
        try:
            self.gem_channel_id = channel.id
            await ctx.send(f"Gem channel has been set to {channel.mention}!")
            self.logger.info(f"Gem channel set to: {channel.name} (ID: {channel.id})")
        except Exception as e:
            self.logger.error(f"Error in setgem command: {str(e)}")
            await ctx.send("An error occurred while setting the gem channel. Please check the bot's logs.")

    async def getgemchannel(self, ctx):
        """Get the current gem channel."""
        if self.gem_channel_id:
            gem_channel = self.bot.get_channel(self.gem_channel_id)
            if gem_channel:
                await ctx.send(f"The current gem channel is: {gem_channel.mention}")
            else:
                await ctx.send("The set gem channel ID is invalid or the channel no longer exists.")
        else:
            await ctx.send("The gem channel has not been set.")

    async def set_gem_reaction(self, ctx, emoji: str):
        """Set the emoji used for gem reactions."""
        if emoji:
            self.gem_reaction_emoji = emoji
            await ctx.send(f"The gem reaction emoji has been set to: {emoji}")
            self.logger.info(f"Gem reaction emoji set to: {emoji}")
        else:
            await ctx.send("Please provide a valid emoji.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Listen for gem reactions and save messages with the specified reaction."""
        if str(reaction.emoji) == self.gem_reaction_emoji and not user.bot:
            message = reaction.message
            
            # Check if the message is already gemed
            if message.id in self.gemed_messages:
                return
            
            if self.gem_channel_id and message.channel.id != self.gem_channel_id:
                # Check for a single gem reaction
                if reaction.count >= 1:
                    await self.save_gem_message(message)

    async def save_gem_message(self, message):
        try:
            gem_channel = self.bot.get_channel(self.gem_channel_id)
            if gem_channel:
                embed = discord.Embed(color=0x00FF00)
                embed.add_field(name="Sender", value=message.author.name, inline=False)
                embed.add_field(name="Content", value=message.content or "No content", inline=False)
                embed.add_field(name="Original Message", value=f"[Jump to message]({message.jump_url})", inline=False)

                # Send the embed and attach any files directly
                await gem_channel.send(embed=embed)

                # Send attachments if present
                if message.attachments:
                    for attachment in message.attachments:
                        await gem_channel.send(file=await attachment.to_file())

                await message.add_reaction("✅")
                
                # Mark this message as gemed to prevent duplication
                self.gemed_messages.add(message.id)
                
                self.logger.info(f"Saved gem message from {message.author.name} in {message.channel.name}")
            else:
                self.logger.error("Gem channel not found")
        except Exception as e:
            self.logger.error(f"Error saving gem message: {str(e)}")


async def setup(bot):
    await bot.add_cog(Gem(bot))

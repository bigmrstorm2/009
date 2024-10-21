import discord
from discord.ext import commands
import random
import requests
import json
import os
import asyncio
import economy
import gem
import webserver

DISCORD_TOKEN = os.environ['discordkey']

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = commands.Bot(command_prefix=["!"], intents=intents)

GELBOORU_API_URL = "https://gelbooru.com/index.php?page=dapi&s=post&q=index"
API_KEY = '6f284874e454ac97a694bb9cffb4a0faa0c19a3862d9855973fdcaf990fcd75f'  # Replace with your actual API key
USER_ID = '1571336'  # Replace with your actual user ID

used_numbers = set()
user_inventories = {}

def load_inventory():
    if os.path.exists('inventory.json'):
        with open('inventory.json', 'r') as f:
            return json.load(f)
    return {}

def save_inventory():
    with open('inventory.json', 'w') as f:
        json.dump(user_inventories, f)

user_inventories = load_inventory()

def format_number(number):
    return f"{number:03d}"

def generate_unique_number():
    available_numbers = set(range(1000)) - used_numbers
    if not available_numbers:
        return None
    number = random.choice(list(available_numbers))
    used_numbers.add(number)
    return format_number(number)

def fetch_gelbooru_image(tags):
    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "api_key": API_KEY,
        "user_id": USER_ID,
        "tags": tags,
        "limit": 100,
        "json": 1,
    }

    try:
        response = requests.get(GELBOORU_API_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            if data and 'post' in data and len(data['post']) > 0:
                post = random.choice(data['post'])
                if 'file_url' in post:
                    return {
                        "image_url": post['file_url'],
                        "owner": post.get('owner', 'Unknown'),
                        "source": "Gelbooru",
                        "created_at": post.get('created_at', 'Unknown'),
                        "tag": tags
                    }
                else:
                    return None
            else:
                return None
        else:
            return None

    except requests.RequestException as e:
        return None

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over your usernames"))

    # Call the setup function to add the Economy cog
    await economy.setup(client)
    await gem.setup(client)  

@client.event
async def on_member_join(member):
    number = generate_unique_number()
    if number is None:
        return

    try:
        await member.edit(nick=number)
        print(f'Changed {member.name}\'s name to {number}')
    except discord.Forbidden:
        print(f"Missing permissions to change nickname of {member.name}")
    except discord.HTTPException as e:
        print(f"Failed to change nickname for {member.name}: {e}")

@client.event
async def on_member_remove(member):
    if member.nick and member.nick.isdigit():
        used_numbers.discard(int(member.nick))

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if client.user in message.mentions:
        if "say" in message.content.lower():
            command_content = message.content.split("say", 1)[1].strip()
            if command_content:
                await message.delete()
                await message.channel.send(command_content)
            else:
                await message.reply("Please provide a message for me to say.")

        elif "search" in message.content.lower():
            category = message.content.lower().split("search", 1)[1].strip()
            image_data = fetch_gelbooru_image(category)

            if image_data and image_data['image_url']:
                embed = discord.Embed(
                    title="Image Information",
                    color=random.randint(0, 0xFFFFFF)
                )
                embed.add_field(name="Tag Used", value=image_data['tag'], inline=False)
                embed.add_field(name="Owner", value=image_data['owner'], inline=False)
                embed.add_field(name="Source", value=image_data['source'], inline=False)
                embed.add_field(name="Created At", value=image_data['created_at'], inline=False)
                embed.set_image(url=image_data['image_url'])

                msg = await message.reply(embed=embed)
                await msg.add_reaction("💾")

                def check_reaction(reaction, user):
                    return user == message.author and str(reaction.emoji) == "💾" and reaction.message.id == msg.id

                try:
                    reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check_reaction)

                    if message.author.id not in user_inventories:
                        user_inventories[message.author.id] = []
                    user_inventories[message.author.id].append(image_data)
                    save_inventory()
                    await message.channel.send("Image saved to your inventory!")

                except asyncio.TimeoutError:
                    pass

            else:
                await message.reply(f"Sorry, I couldn't find an image for the tag: {category}.")

        elif "inventory" in message.content.lower():
            await inventory(message)

        elif "help" in message.content.lower():
            await help_command(message)

        elif "8ball" in message.content.lower():
            responses = [
                "Yes.", "No.", "Maybe.", "Ask again later.", 
                "Definitely.", "Absolutely not.", "I wouldn't count on it.", 
                "It is certain.", "Don't hold your breath.", "Most likely."
            ]
            question = message.content.split("8ball", 1)[1].strip()
            if question:
                answer = random.choice(responses)
                await message.reply(answer)
            else:
                await message.reply("Please ask a question.")

    await client.process_commands(message)

async def inventory(message):
    if message.author.id not in user_inventories or not user_inventories[message.author.id]:
        await message.reply("Your inventory is empty.")
        return

    inventory = user_inventories[message.author.id]
    index = 0

    async def update_message(msg):
        embed = discord.Embed(
            title="Inventory Image",
            color=random.randint(0, 0xFFFFFF)
        )
        embed.add_field(name="Tag Used", value=inventory[index]['tag'], inline=False)
        embed.add_field(name="Owner", value=inventory[index]['owner'], inline=False)
        embed.add_field(name="Source", value=inventory[index]['source'], inline=False)
        embed.add_field(name="Created At", value=inventory[index]['created_at'], inline=False)
        embed.set_image(url=inventory[index]['image_url'])
        embed.set_footer(text=f"Image {index + 1} of {len(inventory)}")
        await msg.edit(embed=embed)

    embed = discord.Embed(
        title="Inventory Image",
        color=random.randint(0, 0xFFFFFF)
    )
    embed.add_field(name="Tag Used", value=inventory[0]['tag'], inline=False)
    embed.add_field(name="Owner", value=inventory[0]['owner'], inline=False)
    embed.add_field(name="Source", value=inventory[0]['source'], inline=False)
    embed.add_field(name="Created At", value=inventory[0]['created_at'], inline=False)
    embed.set_image(url=inventory[0]['image_url'])
    embed.set_footer(text=f"Image 1 of {len(inventory)}")
    msg = await message.reply(embed=embed)
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")

    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == msg.id

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check)

            if str(reaction.emoji) == "➡️":
                index = (index + 1) % len(inventory)
            elif str(reaction.emoji) == "⬅️":
                index = (index - 1) % len(inventory)

            await update_message(msg)
            await reaction.remove(user)

        except asyncio.TimeoutError:
            await msg.clear_reactions()
            break

import random  # Ensure you import random if not already done

async def help_command(message):
    help_embed = discord.Embed(
        title="Help - Bot Commands",
        description="Here are the commands you can use with this bot:",
        color=random.randint(0, 0xFFFFFF)
    )
    
    help_embed.add_field(name="@bot search <category>", value="Fetch a random image from Gelbooru based on the specified category.", inline=False)
    help_embed.add_field(name="@bot inventory", value="View all images you have saved in your inventory.", inline=False)
    help_embed.add_field(name="@bot say <message>", value="Make the bot repeat your message.", inline=False)
    help_embed.add_field(name="@bot 8ball <question>", value="Ask the magic 8-ball a question.", inline=False)
    
    # Adding economy commands
    help_embed.add_field(name="@bot wallet", value="Check your current coin balance.", inline=False)
    help_embed.add_field(name="@bot bank", value="View the amount of coins in your bank.", inline=False)
    help_embed.add_field(name="@bot daily", value="Claim your daily coins (10,000 coins).", inline=False)
    help_embed.add_field(name="@bot monthly", value="Claim your monthly coins (100,000 coins).", inline=False)
    help_embed.add_field(name="@bot deposit <amount>", value="Deposit coins into your bank.", inline=False)
    help_embed.add_field(name="@bot withdraw <amount>", value="Withdraw coins from your bank.", inline=False)
    help_embed.add_field(name="@bot <amount> @user", value="Share coins with another user.", inline=False)
    help_embed.add_field(name="@bot beg", value="Beg for coins with a chance of success or failure.", inline=False)
    help_embed.add_field(name="@bot work", value="Choose a job to earn coins. Work once every 48 hours.", inline=False)
    help_embed.add_field(name="@bot leaderboard", value="Display the top 5 richest users in the server.", inline=False)
    
    # Adding gem commands
    help_embed.add_field(name="@bot setgem #channel-name", value="Set the channel where gem messages will be stored.", inline=False)
    help_embed.add_field(name="@bot getgemchannel", value="Get the current gem channel where messages are saved.", inline=False)
    help_embed.add_field(name="@bot setgemreaction :emoji:", value="Set the emoji used for gem reactions.", inline=False)

    await message.reply(embed=help_embed)

webserver.keep_alive()

# Start the bot with your token

client.run(DISCORD_TOKEN)

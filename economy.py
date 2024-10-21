import discord
from discord.ext import commands
import aiosqlite
import asyncio
import random
from datetime import datetime, timedelta

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = "economy.db"
        self.job_pool = [
            "OnlyFans", "Miner", "Builder", "Chef", "Streamer",
            "Engineer", "Artist", "Musician", "Sex Worker", "Doctor",
            "Nurse", "Waiter", "Programmer", "Cashier",
            "Security", "Cleaner", "Scientist", "Mechanic", "Decorator",
            "Photographer", "Journalist", "Designer", "Researcher", "Dancer",
            "Salesperson", "Veterinarian", "Pilot", "Discord Mod", "Librarian",
            "Striper", "Plumber", "Customer Service"
        ]
        asyncio.create_task(self.create_db())

    async def create_db(self):
        async with aiosqlite.connect(self.database) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_balances (
                    user_id INTEGER PRIMARY KEY,
                    wallet_balance INTEGER DEFAULT 0,
                    bank_balance INTEGER DEFAULT 0,
                    last_daily DATETIME,
                    last_monthly DATETIME,
                    last_beg DATETIME,
                    job TEXT,
                    last_work DATETIME,
                    work_days INTEGER DEFAULT 0
                )
            ''')
            await db.commit()

    async def get_balance(self, user_id):
        async with aiosqlite.connect(self.database) as db:
            async with db.execute('SELECT wallet_balance, bank_balance, last_daily, last_monthly, last_beg, job, last_work, work_days FROM user_balances WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "wallet": row[0],
                        "bank": row[1],
                        "last_daily": row[2],
                        "last_monthly": row[3],
                        "last_beg": row[4],
                        "job": row[5],
                        "last_work": row[6],
                        "work_days": row[7]
                    }
                else:
                    return {"wallet": 0, "bank": 0, "last_daily": None, "last_monthly": None, "last_beg": None, "job": None, "last_work": None, "work_days": 0}
        
    async def update_balance(self, user_id, wallet=None, bank=None, last_daily=None, last_monthly=None, last_beg=None, job=None, last_work=None, work_days=None):
        balance = await self.get_balance(user_id)
        wallet_balance = wallet if wallet is not None else balance["wallet"]
        bank_balance = bank if bank is not None else balance["bank"]
        last_daily = last_daily if last_daily is not None else balance["last_daily"]
        last_monthly = last_monthly if last_monthly is not None else balance["last_monthly"]
        last_beg = last_beg if last_beg is not None else balance["last_beg"]
        job = job if job is not None else balance["job"]
        last_work = last_work if last_work is not None else balance["last_work"]
        work_days = work_days if work_days is not None else balance["work_days"]


        async with aiosqlite.connect(self.database) as db:
            await db.execute('''
                INSERT OR REPLACE INTO user_balances (user_id, wallet_balance, bank_balance, last_daily, last_monthly, last_beg, job, last_work, work_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, wallet_balance, bank_balance, last_daily, last_monthly, last_beg, job, last_work, work_days))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if self.bot.user in message.mentions:
            content = message.content.lower()

            if "wallet" in content:
                await self.handle_wallet(message)
            elif "bank" in content:
                await self.handle_bank(message)
            elif "daily" in content:
                await self.handle_daily(message)
            elif "monthly" in content:
                await self.handle_monthly(message)
            elif "deposit" in content:
                await self.handle_deposit(message)
            elif "withdraw" in content:
                await self.handle_withdraw(message)
            elif "share" in content:
                await self.handle_share(message)
            elif "beg" in content:
                await self.handle_beg(message)
            elif "work" in content:
                await self.handle_work(message)
            elif "leaderboard" in content:  # Add this line
                await self.handle_leaderboard(message)






    async def handle_work(self, message):
        user_id = message.author.id
        balance = await self.get_balance(user_id)

        # Create an embed for work-related messages
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)

        # Check if the user has a job
        if balance["job"] is None:
            # Select 10 random jobs from the pool
            selected_jobs = random.sample(self.job_pool, 10)
            job_selection_message = "Please select a job from the following options:\n" + "\n".join(selected_jobs)
            embed.title = "🛠️ Job Selection 🛠️"
            embed.description = job_selection_message
            await message.channel.send(embed=embed)

            def check(m):
                return m.author == message.author and m.channel == message.channel and m.content in selected_jobs

            try:
                job_response = await self.bot.wait_for('message', check=check, timeout=30)  # Wait for user to select a job
                await self.update_balance(user_id, job=job_response.content, work_days=1)  # Initialize work_days to 1
                embed.title = "✅ Job Chosen"
                embed.description = f"{message.author.mention}, you have chosen the job: **{job_response.content}**."
                await message.channel.send(embed=embed)
            except asyncio.TimeoutError:
                await message.channel.send(f"{message.author.mention}, you took too long to choose a job!")

        else:
            # Get last work date and check working cooldown
            last_work = balance.get("last_work")
            if last_work:
                last_work_time = datetime.fromisoformat(last_work)
                if datetime.now() < last_work_time + timedelta(hours=16):
                    await message.channel.send(f"{message.author.mention}, you can only work once every 16 hours!⏳")
                    return

            # Check if user has worked at least once in the last 48 hours
            if balance["work_days"] < 1:
                embed.title = "❌ Fired!"
                embed.description = f"{message.author.mention}, you have not worked today! You got fired for not showing up!"
                new_wallet_balance = balance["wallet"] - 5000
                await self.update_balance(user_id, wallet=new_wallet_balance, job=None, work_days=0)
                embed.add_field(name="Penalty", value="You lost your job and incurred a penalty of **5,000 coins**. You need to wait **24 hours** to reselect a new one.⏳", inline=False)
                await message.channel.send(embed=embed)
                return

            # Calculate earnings and update last work time
            earnings = random.randint(1500, 5000)
            new_wallet_balance = balance["wallet"] + earnings
            await self.update_balance(user_id, wallet=new_wallet_balance, last_work=datetime.now().isoformat())

            # Keep track of work days
            await self.update_balance(user_id, work_days=1)  # Retain work_days as 1 since user worked today

            embed.title = "💰 Earnings Received!"
            embed.description = f"{message.author.mention}, you worked as a **{balance['job']}** and earned **{earnings} coins**!"
            await message.channel.send(embed=embed)





    async def handle_wallet(self, message):
        user_id = message.author.id
        balance = await self.get_balance(user_id)

        # Create an embed for displaying the wallet balance
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
        embed.title = "💼 Your Wallet Balance 💼"
        embed.description = f"{message.author.mention}, here is your current wallet balance:"

        # Add the wallet balance to the embed
        embed.add_field(name="Wallet Balance", value=f"**{balance['wallet']} coins**", inline=True)

        # Send the embed message
        await message.channel.send(embed=embed)







    async def handle_bank(self, message):
        if len(message.mentions) > 1:
            target_user = message.mentions[1]
        else:
            target_user = message.author

        user_id = target_user.id
        balance = await self.get_balance(user_id)

        # Create an embed for displaying balance
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=target_user.name, icon_url=target_user.avatar.url)
    
        # Set the title and description based on the user being checked
        if target_user == message.author:
            embed.title = "💰 Your Bank and Wallet Balance 💰"
            embed.description = f"{message.author.mention}, here are your current balances:"
        else:
            embed.title = f"💰 {target_user.display_name}'s Balances 💰"
            embed.description = f"{message.author.mention}, here are the balances for {target_user.display_name}:"

        # Add fields for bank and wallet balance
        embed.add_field(name="Bank Balance", value=f"**{balance['bank']} coins**", inline=True)
        embed.add_field(name="Wallet Balance", value=f"**{balance['wallet']} coins**", inline=True)

        # Send the embed message
        await message.channel.send(embed=embed)






    async def handle_beg(self, message):
        user_id = message.author.id
        balance = await self.get_balance(user_id)

        if balance["last_beg"]:
            last_beg = datetime.fromisoformat(balance["last_beg"])
            cooldown = timedelta(hours=1)
            next_beg_time = last_beg + cooldown

            if datetime.now() < next_beg_time:
                remaining = next_beg_time - datetime.now()
                await message.channel.send(f"{message.author.mention}, you can't beg again yet! Try again in {remaining.seconds // 60} minutes⏳.")
                return

        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)

        if random.random() > 0.5:  # 50% chance of success
            beg_amount = random.randint(50, 300)
            new_wallet_balance = balance["wallet"] + beg_amount
            await self.update_balance(user_id, wallet=new_wallet_balance, last_beg=datetime.now().isoformat())
        
            embed.title = "🤲 Begging Success! 🎉"
            embed.description = f"{message.author.mention}, you begged and received **{beg_amount} coins**! Someone felt generous today! 🥳"
            embed.add_field(name="New Wallet Balance", value=f"{new_wallet_balance} coins", inline=False)

        else:  # 50% chance of failure
            total_balance = balance["wallet"] + balance["bank"]
            loss_percentage = random.uniform(0.01, 0.15)
            loss_amount = int(total_balance * loss_percentage)

            if balance["wallet"] >= loss_amount:
                new_wallet_balance = balance["wallet"] - loss_amount
                new_bank_balance = balance["bank"]
            else:
                new_wallet_balance = 0
                new_bank_balance = max(balance["bank"] - (loss_amount - balance["wallet"]), 0)

            await self.update_balance(user_id, wallet=new_wallet_balance, bank=new_bank_balance, last_beg=datetime.now().isoformat())
        
            embed.title = "😱 Begging Failure! 💔"
            embed.description = f"{message.author.mention}, a raccoon stole your money! You lost **{loss_amount} coins**. 😭"
            embed.add_field(name="New Wallet Balance", value=f"{new_wallet_balance} coins", inline=False)
            embed.add_field(name="Bank Balance", value=f"{new_bank_balance} coins", inline=False)

        await message.channel.send(embed=embed)






    async def handle_daily(self, message):
        user_id = message.author.id
        balance = await self.get_balance(user_id)

        if balance["last_daily"]:
            last_claim = datetime.fromisoformat(balance["last_daily"])
            next_claim = last_claim + timedelta(days=1)
            if datetime.now() < next_claim:
                remaining = next_claim - datetime.now()
                await message.channel.send(f"{message.author.mention}, you've already claimed your daily reward! Come back in {remaining.seconds // 3600} hours. ⏳")
                return

        new_wallet_balance = balance["wallet"] + 10000  # Add 10,000 coins
        await self.update_balance(user_id, wallet=new_wallet_balance, last_daily=datetime.now().isoformat())

        embed = discord.Embed(
            title="🌟 Daily Reward Claimed! 🌟",
            color=discord.Color.green(),
            description=f"{message.author.mention}, you have successfully claimed your daily reward!",
        )
        embed.add_field(name="Reward Amount", value="10,000 coins", inline=False)
        embed.add_field(name="New Wallet Balance", value=f"{new_wallet_balance} coins", inline=False)

        # Add user avatar
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="Remember to come back tomorrow for your next reward! 😊")

        await message.channel.send(embed=embed)







    async def handle_monthly(self, message):
        user_id = message.author.id
        balance = await self.get_balance(user_id)

        if balance["last_monthly"]:
            last_claim = datetime.fromisoformat(balance["last_monthly"])
            next_claim = last_claim + timedelta(days=30)
            if datetime.now() < next_claim:
                remaining = next_claim - datetime.now()
                await message.channel.send(f"{message.author.mention}, you've already claimed your monthly reward! Come back in {remaining.days} days. ⏳")
                return

        new_wallet_balance = balance["wallet"] + 100000  # Add 100,000 coins
        await self.update_balance(user_id, wallet=new_wallet_balance, last_monthly=datetime.now().isoformat())

        embed = discord.Embed(
            title="🎉 Monthly Reward Claimed! 🎉",
            color=discord.Color.gold(),
            description=f"{message.author.mention}, you have successfully claimed your monthly reward!",
        )
        embed.add_field(name="Reward Amount", value="100,000 coins", inline=False)
        embed.add_field(name="New Wallet Balance", value=f"{new_wallet_balance} coins", inline=False)

        # Add user avatar
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="Don't forget to come back next month for more rewards! 😊")

        await message.channel.send(embed=embed)







    async def handle_deposit(self, message):
        user_id = message.author.id
        try:
            amount = int(message.content.split("deposit", 1)[1].strip())
        except ValueError:
            await message.reply("Please provide a valid amount to deposit.")
            return
   
        balance = await self.get_balance(user_id)

        if amount > balance["wallet"]:
            await message.channel.send(f"{message.author.mention}, you don't have enough coins in your wallet to deposit! 💔")
            return

        new_wallet_balance = balance["wallet"] - amount
        new_bank_balance = balance["bank"] + amount
        await self.update_balance(user_id, wallet=new_wallet_balance, bank=new_bank_balance)

        embed = discord.Embed(
            title="🏦 Deposit Successful! 🏦",
            color=discord.Color.green(),
            description=f"{message.author.mention}, you have successfully deposited coins!",
        )
        embed.add_field(name="Amount Deposited", value=f"{amount} coins", inline=False)
        embed.add_field(name="New Wallet Balance", value=f"{new_wallet_balance} coins", inline=False)
        embed.add_field(name="New Bank Balance", value=f"{new_bank_balance} coins", inline=False)

        # Add user avatar
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="Keep saving and investing wisely! 😊")

        await message.channel.send(embed=embed)








    async def handle_withdraw(self, message):
        user_id = message.author.id
        try:
            amount = int(message.content.split("withdraw", 1)[1].strip())
        except ValueError:
            await message.reply("Please provide a valid amount to withdraw.")
            return

        balance = await self.get_balance(user_id)

        if amount > balance["bank"]:
            await message.channel.send(f"{message.author.mention}, you don't have enough coins in your bank to withdraw! 💔")
            return

        new_wallet_balance = balance["wallet"] + amount
        new_bank_balance = balance["bank"] - amount
        await self.update_balance(user_id, wallet=new_wallet_balance, bank=new_bank_balance)

        embed = discord.Embed(
            title="💰 Withdrawal Successful! 💰",
            color=discord.Color.blue(),
            description=f"{message.author.mention}, you have successfully withdrawn coins!",
        )
        embed.add_field(name="Amount Withdrawn", value=f"{amount} coins", inline=False)
        embed.add_field(name="New Wallet Balance", value=f"{new_wallet_balance} coins", inline=False)
        embed.add_field(name="Remaining Bank Balance", value=f"{new_bank_balance} coins", inline=False)

         # Add user avatar
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="Keep saving and spending wisely! 😊")

        await message.channel.send(embed=embed)







    async def handle_share(self, message):
        user_id = message.author.id

        # Check if a user is mentioned and amount is provided
        if len(message.mentions) < 2:
            await message.reply("Please mention a user to share coins with.")
            return

        target_user = message.mentions[1]
        try:
            amount = int(message.content.split("share", 1)[1].strip().split()[0])  # Get the amount to share
        except (ValueError, IndexError):
            await message.reply("Please provide a valid amount to share.")
            return

        balance = await self.get_balance(user_id)

        if amount > balance["wallet"]:
            await message.channel.send(f"{message.author.mention}, you don't have enough coins in your wallet to share! 💔")
            return

        # Update balances
        new_wallet_balance = balance["wallet"] - amount
        target_balance = await self.get_balance(target_user.id)
        new_target_wallet_balance = target_balance["wallet"] + amount

        await self.update_balance(user_id, wallet=new_wallet_balance)
        await self.update_balance(target_user.id, wallet=new_target_wallet_balance)

        embed = discord.Embed(
            title="💸 Coins Shared! 💸",
            color=discord.Color.green(),
            description=f"{message.author.mention} has shared coins with {target_user.mention}!",
        )
        embed.add_field(name="Amount Shared", value=f"{amount} coins", inline=False)
        embed.add_field(name="Your New Balance", value=f"{new_wallet_balance} coins", inline=False)

        # Add user avatars
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="Sharing is caring! 😊")

        await message.channel.send(embed=embed)



  
   



    async def handle_leaderboard(self, message):
        async with aiosqlite.connect(self.database) as db:
            async with db.execute('SELECT user_id, wallet_balance, bank_balance FROM user_balances') as cursor:
                rows = await cursor.fetchall()

        user_wealth = [(user_id, wallet + bank) for user_id, wallet, bank in rows]
        user_wealth.sort(key=lambda x: x[1], reverse=True)

        embed = discord.Embed(
            title="🏆 **Top 5 Richest Users** 🏆",
            color=discord.Color.gold(),
            description="Here are the wealthiest users in the server:",
        )

        for i, (user_id, total_wealth) in enumerate(user_wealth[:5], start=1):
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            username = user.name if user else 'Unknown User'
        
            embed.add_field(
                name=f"{i}. **{username}**",
                value=f"💰 **Total Wealth:** {total_wealth} coins",
                inline=False
            )

        embed.set_footer(text="Wealth can change daily! Keep working!")

        await message.channel.send(embed=embed)






async def setup(bot):
    await bot.add_cog(Economy(bot))

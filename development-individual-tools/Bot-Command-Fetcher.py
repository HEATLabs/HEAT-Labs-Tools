import json
import asyncio
import os
from discord.ext import commands
from dotenv import load_dotenv

ENV_PATH = "../../HEAT-Labs-Discord-Bot/bot-files/.env"
load_dotenv(dotenv_path=ENV_PATH)

TOKEN = os.getenv("DISCORD_TOKEN")
SAVE_PATH = "../../HEAT-Labs-Configs"
FILE_NAME = "bot_commands.json"

os.makedirs(SAVE_PATH, exist_ok=True)
full_path = os.path.join(SAVE_PATH, FILE_NAME)

bot = commands.Bot(command_prefix="!", intents=None)


@bot.event
async def on_ready():
    raw = await bot.http.get_global_commands(bot.application_id)

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(raw)} commands to {full_path}")
    await bot.close()


bot.run(TOKEN)

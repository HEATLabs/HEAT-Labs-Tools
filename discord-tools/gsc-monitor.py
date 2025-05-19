import logging
from discord_bot import client, DISCORD_TOKEN

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("gsc_bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger("gsc_discord_bot")


def main():
    logger.info("Starting GSC Discord Bot")
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()

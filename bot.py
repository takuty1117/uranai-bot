import os
import base64
import json
import random
import traceback
import logging
import sys

from dotenv import load_dotenv
import discord
from discord import HTTPException
from aiohttp import web
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

load_dotenv()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("unified_bot")

# --- Google credentials ---
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if credentials_b64:
    cred_data = json.loads(base64.b64decode(credentials_b64))
    if "private_key" in cred_data:
        cred_data["private_key"] = cred_data["private_key"].replace("\\n", "\n")
    with open("credentials.json", "w") as f:
        json.dump(cred_data, f)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
else:
    logger.error("GOOGLE_CREDENTIALS_B64 が見つかりません。")

# --- Config ---
URANAI_SPREADSHEET_ID = os.getenv(
    "URANAI_SPREADSHEET_ID", "1zIrZKLGHeYuhEHUvSn75qnZD5P7escBYZnL-3dvsNGs"
)
FOOD_SPREADSHEET_ID = os.getenv("FOOD_SPREADSHEET_ID", "")


# --- Google Sheets helper ---
def get_gspread_client():
    auth_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not auth_file or not os.path.exists(auth_file):
        raise FileNotFoundError(f"認証ファイルが見つかりません: {auth_file}")
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(auth_file, scope)
    return gspread.authorize(credentials)


# --- Discord Bot ---
class UnifiedBot(discord.Client):
    async def setup_hook(self):
        """Start health check HTTP server for UptimeRobot / Render."""
        app = web.Application()
        app.router.add_get("/", self._health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 10000))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Health check server started on port {port}")

    async def _health_check(self, request):
        return web.Response(
            text=f"OK | guilds={len(self.guilds)} | latency={self.latency:.2f}s"
        )

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (guilds: {len(self.guilds)})")

    async def on_disconnect(self):
        logger.warning("Discord gateway disconnected. Waiting for auto-reconnect...")

    async def on_resumed(self):
        logger.info("Discord gateway session resumed.")

    async def on_error(self, event, *args, **kwargs):
        logger.error(f"Event error ({event})")
        traceback.print_exc()

    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content == "今日の占い":
            await self.handle_uranai(message)
        elif message.content == "今日のご飯":
            await self.handle_food(message)
        elif message.content == "今日の全部":
            await self.handle_all(message)

    def _fetch_uranai(self):
        """Fetch a random fortune. Returns (title, desc) or None."""
        gs_client = get_gspread_client()
        spreadsheet = gs_client.open_by_key(URANAI_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet("シート1")
        data = pd.DataFrame(worksheet.get_all_values())
        rows = [
            (str(row[0]).strip(), str(row[1]).strip() if len(row) > 1 else "")
            for row in data.values.tolist()[1:]  # skip header
            if str(row[0]).strip()
        ]
        if not rows:
            logger.warning("占いデータが空です")
            return None
        title, desc = random.choice(rows)
        logger.info(f"占い結果取得: {title}")
        return (title, desc)

    def _fetch_food(self):
        """Fetch a random meal. Returns (menu, url) or None."""
        gs_client = get_gspread_client()
        spreadsheet = gs_client.open_by_key(FOOD_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet("メニュー")
        data = pd.DataFrame(worksheet.get_all_values())
        rows = [
            (row[0], row[1] if len(row) > 1 else "")
            for row in data.values.tolist()
            if row[0]
        ]
        if not rows:
            return None
        return random.choice(rows)

    async def handle_uranai(self, message):
        logger.info("占いコマンド受信")
        try:
            result = self._fetch_uranai()
            if not result:
                await message.reply("占いデータが見つかりませんでした。")
                return
            title, desc = result
            embed = discord.Embed(title="🔮 今日の占い", color=0x9B59B6)
            embed.add_field(name=title, value=desc or "\u200b", inline=False)
            await message.reply(embed=embed)
        except Exception as e:
            logger.error(f"占い実行エラー: {e}")
            traceback.print_exc()
            await message.channel.send(
                "エラーが発生しました。もう一度「今日の占い」と打ち込んでみてね〜"
            )

    async def handle_food(self, message):
        if not FOOD_SPREADSHEET_ID:
            logger.warning("FOOD_SPREADSHEET_ID が未設定")
            return
        logger.info("ご飯コマンド受信")
        try:
            result = self._fetch_food()
            if not result:
                await message.reply("メニューが見つかりませんでした。")
                return
            menu, url = result
            embed = discord.Embed(title="🍽️ 今日のご飯", color=0xE67E22)
            desc = f"**【{menu}】**"
            if url:
                desc += f"\n[アレンジレシピはこちら](<{url}>)"
            embed.description = desc
            await message.reply(embed=embed)
        except Exception as e:
            logger.error(f"メニュー取得エラー: {e}")
            traceback.print_exc()
            await message.reply("メニューの取得中にエラーが発生しました。")

    async def handle_all(self, message):
        logger.info("全部コマンド受信")
        embed = discord.Embed(title="✨ 今日の運勢", color=0x9B59B6)
        try:
            uranai = self._fetch_uranai()
            if uranai:
                title, desc = uranai
                embed.add_field(name=f"🔮 {title}", value=desc or "\u200b", inline=False)
            else:
                embed.add_field(name="🔮 占い", value="データが見つかりませんでした。", inline=False)
        except Exception as e:
            logger.error(f"占い実行エラー: {e}")
            embed.add_field(name="🔮 占い", value="取得に失敗しました…", inline=False)
        try:
            if FOOD_SPREADSHEET_ID:
                food = self._fetch_food()
                if food:
                    menu, url = food
                    food_text = f"**【{menu}】**"
                    if url:
                        food_text += f"\n[アレンジレシピはこちら](<{url}>)"
                    embed.add_field(name="🍽️ ご飯", value=food_text, inline=False)
                else:
                    embed.add_field(name="🍽️ ご飯", value="メニューが見つかりませんでした。", inline=False)
        except Exception as e:
            logger.error(f"メニュー取得エラー: {e}")
            embed.add_field(name="🍽️ ご飯", value="取得に失敗しました…", inline=False)
        await message.reply(embed=embed)


if __name__ == "__main__":
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN が見つかりません。")
        sys.exit(1)

    logger.info("Bot を起動します...")
    intents = discord.Intents.default()
    intents.message_content = True
    client = UnifiedBot(intents=intents)

    # Run Discord client as main process (not in a thread).
    # If it crashes or disconnects permanently, the process exits
    # and systemd will restart it.
    try:
        client.run(bot_token, log_handler=None)
    except Exception as e:
        logger.error(f"Bot が異常終了しました: {e}")
        traceback.print_exc()
        sys.exit(1)

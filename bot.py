import os
import base64
import random
import traceback
import asyncio
import threading
import math
import logging

from dotenv import load_dotenv
import discord
from discord import HTTPException
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from flask import Flask

load_dotenv()

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unified_bot")

# --- Google credentials ---
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(credentials_b64))
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


# --- Flask ---
app = Flask(__name__)


@app.route("/")
def health_check():
    is_ready = not client.is_closed() and client.is_ready()
    status = "Online" if is_ready else "Offline/Connecting"

    latency_val = client.latency
    if is_ready and latency_val is not None and not math.isnan(latency_val):
        latency = f"{round(latency_val * 1000)}ms"
    else:
        latency = "Calculating..."

    features = []
    if URANAI_SPREADSHEET_ID:
        features.append("占い")
    if FOOD_SPREADSHEET_ID:
        features.append("ご飯")

    return (
        f"Bot Status: {status}<br>"
        f"Latency: {latency}<br>"
        f"Features: {', '.join(features)}<br><br>"
        f"統合Bot、元気に稼働中！"
    ), 200


# --- Discord Bot ---
class UnifiedBot(discord.Client):
    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (guilds: {len(self.guilds)})")

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

    async def handle_uranai(self, message):
        logger.info("占いコマンド受信")
        try:
            gs_client = get_gspread_client()
            spreadsheet = gs_client.open_by_key(URANAI_SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet("シート1")
            data = pd.DataFrame(worksheet.get_all_values())

            n = random.randint(1, len(data) - 1)
            result = data.iloc[n, 0] + "\n" + data.iloc[n, 1]

            logger.info(f"占い結果送信 (Row {n})")
            await message.channel.send(result)

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
            gs_client = get_gspread_client()
            spreadsheet = gs_client.open_by_key(FOOD_SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet("メニュー")
            data = pd.DataFrame(worksheet.get_all_values())

            if data.empty:
                await message.reply("メニューが見つかりませんでした。")
                return

            rows = [
                (row[0], row[1] if len(row) > 1 else "")
                for row in data.values.tolist()
                if row[0]
            ]

            if not rows:
                await message.reply("メニューが見つかりませんでした。")
                return

            menu, url = random.choice(rows)
            reply = f"今日のおすすめのご飯は【{menu}】！"
            if url:
                reply += f"\nアレンジレシピは[こちら](<{url}>)"
            await message.reply(reply)

        except Exception as e:
            logger.error(f"メニュー取得エラー: {e}")
            traceback.print_exc()
            await message.reply("メニューの取得中にエラーが発生しました。")


intents = discord.Intents.default()
intents.message_content = True
client = UnifiedBot(intents=intents)


def run_bot(token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.start(token))
    except HTTPException as e:
        if e.status == 429:
            logger.error(
                "DiscordからRate Limitされています。"
                "Renderの 'Manual Deploy' > 'Clear Cache & Deploy' を実行してください。"
            )
        else:
            logger.error(f"HTTPエラー: {e}")
    except Exception as e:
        logger.error(f"Botスレッドでエラー: {e}")
        traceback.print_exc()
    finally:
        loop.close()


if __name__ == "__main__":
    logger.info("--- 起動診断開始 ---")
    bot_token = os.getenv("DISCORD_BOT_TOKEN")

    if bot_token:
        logger.info("DISCORD_BOT_TOKEN: 読み込み成功")
        logger.info("Botスレッドを起動します...")
        bot_thread = threading.Thread(target=run_bot, args=(bot_token,), daemon=True)
        bot_thread.start()
    else:
        logger.error("DISCORD_BOT_TOKEN が見つかりません。")

    logger.info("--- 診断終了。Webサーバーを起動します... ---")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

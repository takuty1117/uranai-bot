import os
from dotenv import load_dotenv
load_dotenv()
import discord
import random
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
import traceback
import asyncio
import time
import threading # ★ スレッドのために追加
from flask import Flask # ★ Flaskを追加

# .env ファイルを読み込む
load_dotenv()

# --- Google認証情報の設定 (変更なし) ---
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base66.b64decode(credentials_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
else:
    print("GOOGLE_CREDENTIALS_B64 環境変数が設定されていません。")

# --- Flask (Webサーバー) の設定 ---
# Renderがスリープしないように、外部からアクセスできるWebページを作る
app = Flask(__name__)

@app.route('/')
def hello():
    # このページが外部からアクセスされることで、Renderのスリープを防ぎます
    return "占いBot、元気に稼働中！"

# --- キャッシュ用グローバル変数 (変更なし) ---
cache = {"timestamp": 0, "result": None}

# --- Discordボットクラスの定義 (変更なし) ---
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        print(f"Message received: {message.content}")

        if message.author.bot:
            return

        if message.content == "今日の占い":
            print("Fortune-telling command received!")
            try:
                current_time = time.time()
                if current_time - cache["timestamp"] < 60 and cache["result"] is not None:
                    uranai = cache["result"]
                    print("Using cached fortune result.")
                else:
                    Auth = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                    if not Auth or not os.path.exists(Auth):
                        raise FileNotFoundError(f"認証ファイルが見つかりません: {Auth}")

                    print(f"Using Google credentials from: {Auth}")
                    scope = ['https://spreadsheets.google.com/feeds']
                    credentials = ServiceAccountCredentials.from_json_keyfile_name(Auth, scope)
                    gs_client = gspread.authorize(credentials)

                    spreadsheet = gs_client.open_by_key("1zIrZKLGHeYuhEHUvSn75qnZD5P7escBYZnL-3dvsNGs")
                    raw_data = spreadsheet.worksheet("シート1")
                    data = pd.DataFrame(raw_data.get_all_values())
                    print("Google Sheets accessed successfully.")

                    n = random.randint(0, len(data) - 1)
                    uranai = data.iloc[n, 0] + '\n' + data.iloc[n, 1]

                    cache["timestamp"] = current_time
                    cache["result"] = uranai

                print(f"Sending fortune result: {uranai}")
                await message.channel.send(uranai)

            except Exception as e:
                print(f"Error accessing Google Sheets: {e}")
                traceback.print_exc()
                await message.channel.send("エラーが発生しました。もう一度「今日の占い」と打ち込んでみてね〜")

# --- Discordボットの起動準備 ---
intents = discord.Intents.default()
intents.message_content = True
client = MyBot(intents=intents)

# Botを別スレッドで実行するための関数
def run_bot():
    # asyncioイベントループをスレッド内で作成・実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Botを起動し、完了するまで待つ
        loop.run_until_complete(client.start(os.getenv('DISCORD_BOT_TOKEN')))
    except Exception as e:
        print(f"Botスレッドでエラーが発生: {e}")
    finally:
        loop.close()

# --- アプリを起動する部分 ---
if __name__ == "__main__":
    # 1. Discord Botを「別スレッド」（裏側）で起動
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # 2. Flask Webサーバーを「メインスレッド」（表側）で起動
    # RenderはPORT環境変数で待ち受けるポート番号を指定してきます
    port = int(os.environ.get("PORT", 5001))
    # '0.0.0.0' で外部からのアクセスを受け付けられるようにします
    app.run(host="0.0.0.0", port=port)

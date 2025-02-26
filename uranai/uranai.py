import os
import discord
import random
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
import threading
import base64
import traceback
import asyncio
import time  # キャッシュのためのタイムスタンプ取得用

# Base64でエンコードされたGoogle認証情報をファイルとして保存
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(credentials_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
else:
    print("GOOGLE_CREDENTIALS_B64 環境変数が設定されていません。")

# Flaskアプリケーションを定義
app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

# キャッシュ用グローバル変数（60秒間有効）
cache = {"timestamp": 0, "result": None}

# Discordボットクラスの定義
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        print(f"Message received: {message.content}")  # メッセージ内容を表示

        if message.author.bot:
            return

        if message.content == "今日の占い":
            print("Fortune-telling command received!")

            try:
                # まずキャッシュの有効期限を確認（60秒間は再取得しない）
                current_time = time.time()
                if current_time - cache["timestamp"] < 60 and cache["result"] is not None:
                    uranai = cache["result"]
                    print("Using cached fortune result.")
                else:
                    # 環境変数からGoogleサービスのJSONファイルのパスを取得
                    Auth = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                    if not Auth or not os.path.exists(Auth):
                        raise FileNotFoundError(f"認証ファイルが見つかりません: {Auth}")

                    print(f"Using Google credentials from: {Auth}")
                    scope = ['https://spreadsheets.google.com/feeds']
                    credentials = ServiceAccountCredentials.from_json_keyfile_name(Auth, scope)
                    gs_client = gspread.authorize(credentials)

                    # スプレッドシートに接続
                    spreadsheet = gs_client.open_by_key("1zIrZKLGHeYuhEHUvSn75qnZD5P7escBYZnL-3dvsNGs")
                    raw_data = spreadsheet.worksheet("シート1")
                    data = pd.DataFrame(raw_data.get_all_values())
                    print("Google Sheets accessed successfully.")

                    # ランダムに占い結果を選ぶ
                    n = random.randint(0, len(data) - 1)
                    uranai = data.iloc[n, 0] + '\n' + data.iloc[n, 1]

                    # キャッシュを更新
                    cache["timestamp"] = current_time
                    cache["result"] = uranai

                print(f"Sending fortune result: {uranai}")
                await message.channel.send(uranai)

            except Exception as e:
                print(f"Error accessing Google Sheets: {e}")
                traceback.print_exc()
                await message.channel.send("エラーが発生しました。占いを取得できませんでした。")

# Discordボットを起動
intents = discord.Intents.default()
intents.message_content = True
client = MyBot(intents=intents)

# Flaskを別スレッドで実行する関数
def run_flask():
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)

# 再接続ロジックを追加
async def start_bot():
    while True:
        try:
            await client.start(os.getenv('DISCORD_BOT_TOKEN'))
        except Exception as e:
            print(f"Error occurred: {e}")
            await asyncio.sleep(5)  # エラー発生時に5秒待って再接続

# アプリを起動する部分
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    asyncio.run(start_bot())

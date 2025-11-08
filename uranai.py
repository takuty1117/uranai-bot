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
import threading
from flask import Flask

# .env ファイルを読み込む
load_dotenv()

# --- Google認証情報の設定 ---
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(credentials_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
else:
    # このプリントは起動時に一度だけ表示される
    print("★★★ (診断) GOOGLE_CREDENTIALS_B64 が .env または環境変数に見つかりません。")

# --- Flask (Webサーバー) の設定 ---
app = Flask(__name__)

@app.route('/')
def hello():
    return "占いBot、元気に稼働中！"

# --- キャッシュ用グローバル変数 ---
cache = {"timestamp": 0, "result": None}

# --- Discordボットクラスの定義 ---
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'★★★ ログイン成功！ Bot名: {self.user} ★★★') # ← Botが成功するとこれが出る

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
                print(f"★★★ 占い実行中にエラーが発生: {e} ★★★")
                traceback.print_exc()
                await message.channel.send("エラーが発生しました。もう一度「今日の占い」と打ち込んでみてね〜")

# --- Discordボットの起動準備 ---
intents = discord.Intents.default()
intents.message_content = True
client = MyBot(intents=intents)

# Botを別スレッドで実行するための関数
def run_bot(token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        print(f"★★★ Botスレッド: client.start() を実行します (トークン末尾: ...{token[-6:]}) ★★★")
        loop.run_until_complete(client.start(token))
    except Exception as e:
        print(f"★★★ Botスレッドで致命的なエラーが発生: {e} ★★★")
        traceback.print_exc() # エラーの詳細をログに出力
    finally:
        loop.close()

# --- アプリを起動する部分 (診断コード追加) ---
if __name__ == "__main__":
    
    # ★★★↓ ここから診断コード ↓★★★
    print("--- 起動診断開始 ---")
    bot_token = os.getenv('DISCORD_BOT_TOKEN')

    if bot_token:
        # トークン全体をログに出すのは危険なので、末尾6文字だけ表示
        print(f"DISCORD_BOT_TOKEN: 読み込み成功 (末尾: ...{bot_token[-6:]})")
        
        # 1. Discord Botを「別スレッド」（裏側）で起動
        print("Botスレッドを起動します...")
        bot_thread = threading.Thread(target=run_bot, args=(bot_token,))
        bot_thread.start()
        
    else:
        print("★★★ 致命的エラー: DISCORD_BOT_TOKEN が環境変数に見つかりません。 ★★★")
        print("★★★ Botスレッドは起動できませんでした。 ★★★")
    
    print("--- 診断終了。Webサーバーを起動します... ---")
    # 2. Flask Webサーバーを「メインスレッド」（表側）で起動
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)

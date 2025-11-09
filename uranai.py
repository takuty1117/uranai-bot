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
# import time # キャッシュ機能と一緒に削除
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
    print("★★★ (診断) GOOGLE_CREDENTIALS_B64 が .env または環境変数に見つかりません。")

# --- Flask (Webサーバー) の設定 ---
app = Flask(__name__)

@app.route('/')
def hello():
    return "占いBot、元気に稼働中！"

# --- キャッシュ用グローバル変数を削除 ---
# cache = {"timestamp": 0, "result": None} # 削除

# --- Discordボットクラスの定義 ---
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'★★★ ログイン成功！ Bot名: {self.user} ★★★') 

    async def on_message(self, message):
        print(f"Message received: {message.content}")

        if message.author.bot:
            return

        if message.content == "今日の占い":
            print("Fortune-telling command received!")
            try:
                # --- キャッシュのIF文をすべて削除 ---
                # if current_time ... else: を削除し、常にGoogle Sheetsから取得
                
                print("Cache removed. Always fetching from Google Sheets...")
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
                print(f"Google Sheets accessed successfully. Total rows (including header): {len(data)}")

                # ヘッダー行(インデックス 0)を避け、インデックス 1 (2行目) から
                # 最後の行 (len(data) - 1) までの間でランダムに選ぶ
                n = random.randint(1, len(data) - 1) 
                
                uranai = data.iloc[n, 0] + '\n' + data.iloc[n, 1]
                print(f"Randomly picked row index: {n}")

                # --- キャッシュ更新のコードを削除 ---
                # cache["timestamp"] = current_time
                # cache["result"] = uranai

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
        traceback.print_exc() 
    finally:
        loop.close()

# --- アプリを起動する部分 ---
if __name__ == "__main__":
    
    print("--- 起動診断開始 ---")
    bot_token = os.getenv('DISCORD_BOT_TOKEN')

    if bot_token:
        print(f"DISCORD_BOT_TOKEN: 読み込み成功 (末尾: ...{bot_token[-6:]})")
        
        print("Botスレッドを起動します...")
        bot_thread = threading.Thread(target=run_bot, args=(bot_token,))
        bot_thread.start()
        
    else:
        print("★★★ 致命的エラー: DISCORD_BOT_TOKEN が環境変数に見つかりません。 ★★★")
        print("★★★ Botスレッドは起動できませんでした。 ★★★")
    
    print("--- 診断終了。Webサーバーを起動します... ---")
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)

import os
from dotenv import load_dotenv
import discord
from discord import HTTPException
import random
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
import traceback
import asyncio
import threading
from flask import Flask
import logging

# .env ファイルを読み込む
load_dotenv()

# --- ログ設定 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('uranai_bot')

# --- Google認証情報の設定 ---
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(credentials_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
else:
    print("★★★ (診断) GOOGLE_CREDENTIALS_B64 が見つかりません。")

# --- Flask (Webサーバー) の設定 ---
app = Flask(__name__)

@app.route('/')
def health_check():
    # 自己検証機能: ブラウザでアクセスした時にBotの状態を返す
    status = "Online" if not client.is_closed() and client.is_ready() else "Offline/Connecting"
    latency = f"{round(client.latency * 1000)}ms" if client.latency and client.latency != float('inf') else "N/A"
    return f"Bot Status: {status}<br>Latency: {latency}<br><br>占いBot、元気に稼働中！", 200

# --- Discordボットクラスの定義 ---
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'★★★ ログイン成功！ Bot名: {self.user} ★★★') 

    async def on_error(self, event, *args, **kwargs):
        # イベント発生時のエラーを詳細に記録
        print(f"！！！ イベントエラー発生 ({event}) ！！！")
        traceback.print_exc()

    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content == "今日の占い":
            print("Fortune-telling command received!")
            try:
                print("Fetching from Google Sheets...")
                Auth = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if not Auth or not os.path.exists(Auth):
                    raise FileNotFoundError(f"認証ファイルが見つかりません: {Auth}")

                scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                credentials = ServiceAccountCredentials.from_json_keyfile_name(Auth, scope)
                gs_client = gspread.authorize(credentials)

                spreadsheet = gs_client.open_by_key("1zIrZKLGHeYuhEHUvSn75qnZD5P7escBYZnL-3dvsNGs")
                raw_data = spreadsheet.worksheet("シート1")
                data = pd.DataFrame(raw_data.get_all_values())
                
                # ヘッダーを除いてランダム抽出
                n = random.randint(1, len(data) - 1) 
                uranai = data.iloc[n, 0] + '\n' + data.iloc[n, 1]
                
                print(f"Sending result (Row {n}): {uranai[:20]}...")
                await message.channel.send(uranai)

            except Exception as e:
                print(f"★★★ 占い実行中にエラーが発生: {e} ★★★")
                traceback.print_exc()
                await message.channel.send("エラーが発生しました。もう一度「今日の占い」と打ち込んでみてね〜")

# --- Discordボットの起動準備 ---
intents = discord.Intents.default()
intents.message_content = True
client = MyBot(intents=intents)

def run_bot(token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        print(f"★★★ Botスレッド: client.start() を実行します ★★★")
        loop.run_until_complete(client.start(token))
    except HTTPException as e:
        if e.status == 429:
            print("\n" + "!"*50)
            print("【致命的エラー】DiscordからIPブロック（Rate Limit）されています。")
            print("対策：Renderの 'Manual Deploy' > 'Clear Cache & Deploy' を実行してください。")
            print("!"*50 + "\n")
        else:
            print(f"★★★ HTTPエラー発生: {e} ★★★")
    except Exception as e:
        print(f"★★★ Botスレッドで予期せぬエラーが発生: {e} ★★★")
        traceback.print_exc() 
    finally:
        loop.close()

# --- アプリを起動する部分 ---
if __name__ == "__main__":
    print("--- 起動診断開始 ---")
    bot_token = os.getenv('DISCORD_BOT_TOKEN')

    if bot_token:
        print(f"DISCORD_BOT_TOKEN: 読み込み成功")
        print("Botスレッドを起動します...")
        bot_thread = threading.Thread(target=run_bot, args=(bot_token,), daemon=True)
        bot_thread.start()
    else:
        print("★★★ 致命的エラー: DISCORD_BOT_TOKEN が見つかりません。 ★★★")
    
    print("--- 診断終了。Webサーバーを起動します... ---")
    # Renderのポート番号に対応
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

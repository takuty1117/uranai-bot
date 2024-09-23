import os
import discord
import random
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
import threading

# Flaskアプリケーションを定義
app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

# Discordボットクラスの定義
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content == "今日の占い":
            Auth = "/Users/t.n/Desktop/uranai/uranai-436517-66021ced1872.json"  # GoogleサービスのJSONファイルのパス
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = Auth
            scope = ['https://spreadsheets.google.com/feeds']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(Auth, scope)
            client = gspread.authorize(credentials)

            # スプレッドシートに接続
            spreadsheet = client.open_by_key("1zIrZKLGHeYuhEHUvSn75qnZD5P7escBYZnL-3dvsNGs")
            raw_data = spreadsheet.worksheet("シート1")
            data = pd.DataFrame(raw_data.get_all_values())

            # ランダムに占い結果を選ぶ
            n = random.randint(0, len(data) - 1)
            uranai = data.iloc[n, 0] + '\n' + data.iloc[n, 1]
            await message.channel.send(uranai)

# Discordボットを起動
intents = discord.Intents.default()
intents.message_content = True
client = MyBot(intents=intents)

# Flaskを別スレッドで実行する関数
def run_flask():
    port = int(os.environ.get("PORT", 5001))  # デフォルトでポート5001を使用
    app.run(host="0.0.0.0", port=port)

# アプリを起動する部分
if __name__ == "__main__":
    # Flaskを別スレッドで実行
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Discordボットを実行
    client.run(os.getenv('DISCORD_BOT_TOKEN'))

import os
import discord
import random
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
import threading
import base64  # Base64デコード用
import traceback  # エラーの詳細を出力するために追加


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

# Discordボットクラスの定義
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        print(f"Message received: {message.content}")  # メッセージを受け取った際に内容を表示する

        if message.author.bot:
            return

        if message.content == "今日の占い":
            print("Fortune-telling command received!")  # "今日の占い" コマンドを受け取ったら表示

            try:
                # 環境変数からGoogleサービスのJSONファイルのパスを取得
                Auth = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if not Auth or not os.path.exists(Auth):
                    raise FileNotFoundError(f"認証ファイルが見つかりません: {Auth}")

                print(f"Using Google credentials from: {Auth}")
                scope = ['https://spreadsheets.google.com/feeds']
                credentials = ServiceAccountCredentials.from_json_keyfile_name(Auth, scope)
                client = gspread.authorize(credentials)

                # スプレッドシートに接続
                spreadsheet = client.open_by_key("1zIrZKLGHeYuhEHUvSn75qnZD5P7escBYZnL-3dvsNGs")
                raw_data = spreadsheet.worksheet("シート1")
                data = pd.DataFrame(raw_data.get_all_values())
                print("Google Sheets accessed successfully.")  # スプレッドシートが正常にアクセスできたら表示

                # ランダムに占い結果を選ぶ
                n = random.randint(0, len(data) - 1)
                uranai = data.iloc[n, 0] + '\n' + data.iloc[n, 1]
                print(f"Sending fortune result: {uranai}")  # 占い結果を表示
                await message.channel.send(uranai)

            except Exception as e:
                print(f"Error accessing Google Sheets: {e}")  # エラーメッセージを表示
                traceback.print_exc()  # 詳細なエラー内容を出力
                await message.channel.send("エラーが発生しました。占いを取得できませんでした。")

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

import os
import discord
import random
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

# DiscordのBotクラスを作成
class MyBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content == '今日の占い':
            fortunes = [
                # 1. オーソドックスな占い
                "大吉\n今日は何をやっても成功しそう！",
                "中吉\nちょっとした幸運が訪れる予感。",
                "小吉\n何事も控えめにすれば吉。",
                "末吉\n小さな幸せがあなたを待っています。",
                "吉\n落ち着いた一日が過ごせそう。",
                "凶\n少し注意が必要な日です。",
                "大凶\n今日は慎重に行動するべきです。",
                
                # 2. 食べ物にまつわる占い結果
                "ラーメン運\n今日は美味しいラーメンに出会えるかも。",
                "カレー運\nスパイスの効いたカレーが吉。",
                "寿司運\n新鮮なネタに恵まれそう。",
                "チョコレート運\n甘いものが幸運を呼び込む。",
                "フルーツ運\nビタミンを摂ると元気が出ます。",
                "ピザ運\n家族と分け合うとさらに運気アップ。",
                "パスタ運\nクリームソースが特におすすめ。",
                "サラダ運\n健康的な食事が吉を呼びます。",
                "バーガー運\n贅沢なトッピングが今日のカギ。",
                "ドーナツ運\n円形のものがあなたに幸運をもたらす。",
                
                # 3. 色にまつわる占い結果
                "赤運\n今日は情熱的に行動してみて！",
                "青運\n冷静な判断が運を引き寄せる。",
                "緑運\n自然に触れることでリフレッシュ。",
                "黄色運\nポジティブな気持ちで吉。",
                "黒運\nシックな選択が成功を呼びます。",
                "白運\nシンプルに徹することが良い結果に。",
                "ピンク運\n今日は恋愛運が高まりそう！",
                "紫運\n神秘的な体験があるかも。",
                "オレンジ運\n元気いっぱいに過ごすのが吉。",
                "金色運\nリッチな気分で運気がアップします。",
                
                # 4. 人間関係にまつわる占い結果
                "友達運\n今日は友情が深まる一日です。",
                "家族運\n家族との時間を大切にしましょう。",
                "上司運\n尊敬する人との会話でヒントが得られます。",
                "同僚運\nチームワークがカギになります。",
                "ライバル運\nライバルから刺激を受ける日。",
                "新しい出会い運\n新しい友人と出会うチャンス。",
                "旧友運\n昔の友達と再会するかも。",
                "相談運\n誰かに相談すると解決の糸口が見つかります。",
                "部下運\nリーダーシップを発揮するのに最適な日。",
                "恋人運\nパートナーとの時間を大切にして吉。",
                
                # 5. 配信アプリIRIAMにまつわる占い結果
                "配信運\n今日の配信は特に盛り上がるでしょう！",
                "リスナー運\n新しいリスナーがたくさん来てくれる予感。",
                "スパチャ運\n思いがけないスパチャが期待できる日。",
                "コラボ運\n他の配信者とのコラボが大成功。",
                "トーク運\n今日はトークが冴えわたる一日。",
                "ファンアート運\n素敵なファンアートがもらえるかも。",
                "フォロワー運\nフォロワーが急増するチャンス。",
                "クリップ運\nバズるクリップが誕生するかも！",
                "プレゼント運\nリスナーから素敵なプレゼントが届くかも。",
                "イベント運\n特別なイベントを企画すると大成功。",
                
                # 6. アニメ、漫画、映画にまつわる占い結果
                "アニメ運\nお気に入りのアニメに新展開が！",
                "映画運\n映画館で感動的な作品に出会うかも。",
                "漫画運\n新刊が大ヒットの予感。",
                "声優運\n好きな声優さんの活躍が見られるかも。",
                "キャラクター運\n推しキャラのグッズが手に入りそう！",
                "コスプレ運\nコスプレを楽しむと運気アップ。",
                "原作運\n原作を読むと新たな発見があるかも。",
                "アニメイベント運\nイベントに参加すると素敵な体験が待っています。",
                "フィギュア運\n限定フィギュアが手に入る予感。",
                "主題歌運\nお気に入りのアニメの主題歌が耳に残る一日。",
                
                # 7. 恋愛にまつわる占い結果
                "片思い運\n今日は勇気を出してアプローチするべき！",
                "両思い運\n恋人と素敵な時間を過ごせる予感。",
                "告白運\n告白するには良いタイミングです。",
                "デート運\n今日は理想のデートが実現しそう！",
                "恋愛運\n今日は恋愛面で特別な日になりそうです。",
                "別れ運\n今は新しい一歩を踏み出す時かも。",
                "復縁運\n過去の恋が再び燃え上がる予感。",
                "婚約運\n婚約を考えるのに良い日です。",
                "プレゼント運\n恋人にプレゼントを渡すと喜ばれる日。",
                "新しい恋運\n新しい恋が始まるかも！",
                
                # 8. 金運にまつわる占い結果
                "大金運\n今日は臨時収入が期待できそう！",
                "節約運\n賢く節約すると運が良くなります。",
                "投資運\n今日は新しい投資を始めると良い結果に。",
                "買い物運\n今日は良い買い物ができるかも。",
                "宝くじ運\n思い切って宝くじを買うといい結果が！",
                "ビジネス運\n新しいビジネスチャンスが訪れる日。",
                "給料運\n昇給の話が進展しそう。",
                "副業運\n副業が成功するチャンス。",
                "貯金運\n貯金を増やすことに成功する日。",
                "借金運\n今日は借金を返すと運気が上がるでしょう。"
            ]
            fortune = random.choice(fortunes)
            await message.reply(f'今日の占い:\n{fortune}', mention_author=True)

intents = discord.Intents.default()
intents.message_content = True
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

client = MyBot(intents=intents)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    client.loop.create_task(app.run_task(host="0.0.0.0", port=port))
    client.run(TOKEN)

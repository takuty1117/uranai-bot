import base64

# credentials.json ファイルを読み込み、Base64にエンコード
with open("credentials.json", "rb") as f:
    encoded = base64.b64encode(f.read())

# エンコード結果を encoded_credentials.txt に保存
with open("encoded_credentials.txt", "wb") as f:
    f.write(encoded)
from javascript import require
from web3.auto import w3
from eth_account.messages import encode_defunct
import os
print(os.getcwd())
getL2Keys = require("./keys.js")

# приватник из Метамаска
key = "f19f167dc4e90b7aec96532c508245beac79af1e783dc9bb29d046ce9d9ccfcb"

# cообщение, которое нам сайт предлагает подписать в Метамаске
# для разных сетей оно немного отличается, в нашем случае подписываю для Arbitruma (в конце строки on arb)
message = encode_defunct(text="Please sign to confirm register DeBank L2 account nonce: 1 on bsc")

# получаем сигнатуру сообщения
signature = w3.eth.account.sign_message(message, key)['signature'].hex()

print(signature)

# функция getL2Keys возвращает приватный и публичный ключи
data = getL2Keys(signature)
print(1, data['pub'])

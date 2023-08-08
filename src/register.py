import os
import json
import time
import random
import web3.contract

from web3 import Web3
from loguru import logger
from requests import Response
from httpx import AsyncClient
from javascript import require
from web3.types import TxParams
from web3.types import ChecksumAddress
from capmonster_python import RecaptchaV2Task
from web3.middleware import geth_poa_middleware
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount

from src import settings as st
from src import constants as cst
from src.abis.erc20 import ERC20_ABI
from src.abis.reg_contract import ABI
from src.helper import sync_retry, async_retry


class Registrator:

    def __init__(self):
        self.node = "https://rpc.ankr.com/bsc"
        self.url = "https://api.debank.com/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/113.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self.url,
            "Content-Type": "application/json",
            "source": "web",
            "Origin": self.url,
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "TE": "trailers",
        }
        self.handles = {
            'sign': 'user/sign_v2',
            'login': 'user/login_v2'
        }
        self.captcha = {
            'api_key': st.CAPTCHA_KEY,
            'base_url': "https://debank.com/account",
            'site_key': "6LfoubcmAAAAAOa4nrHIf2O8iH4W-h91QohdhXTf",
        }

    async def register(self):
        """Функция регистрации аккаунтов"""

        keys = self.read_file()
        random.shuffle(keys)

        w3 = self.connect()
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        contract = self.get_contract(w3=w3, address=cst.REGISTRATOR, abi=ABI)

        for key in keys:

            account = w3.eth.account.from_key(key)
            wallet = account.address

            logger.info(f"Work with wallet {wallet}")

            l2_acc = contract.functions.l2Accounts(wallet).call()

            if not l2_acc:
                await self.register_account(w3=w3, account=account, wallet=wallet, contract=contract)
            else:
                logger.info(f"L2 account already exists, address - {l2_acc}")

            self.deposit(wallet=wallet, w3=w3, account=account)

    def connect(self) -> Web3:
        """Функция подключения к ноде"""

        conn = False

        while not conn:
            w3 = Web3(
                Web3.HTTPProvider(
                    endpoint_uri=self.node
                )
            )
            conn = w3.is_connected()

        return w3

    @async_retry
    async def register_account(
            self,
            w3: Web3,
            account: LocalAccount,
            wallet: ChecksumAddress,
            contract: web3.contract.Contract
    ):
        """Функция создания L2 аккаунта"""

        client = AsyncClient(
            http2=True
        )

        logger.info("Get sign message")

        json_data = {'id': wallet.lower()}
        response = await client.post(
            url=self.url + self.handles['sign'],
            json=json_data,
            headers=self.headers
        )
        self.check_response(response=response)
        sign_v2_text = response.json()["data"]["text"]

        delay = random.randint(st.DEFAULT_DELAY[0], st.DEFAULT_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        logger.info("Sign message")

        signature = account.sign_message(encode_defunct(text=sign_v2_text)).signature.hex()
        delay = random.randint(st.SIGN_DELAY[0], st.SIGN_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        logger.info("Start captcha solving")

        capmonster = RecaptchaV2Task(self.captcha['api_key'])
        task_id = capmonster.create_task(
            self.captcha['base_url'],
            self.captcha['site_key'],
            no_cache=True
        )
        result = capmonster.join_task_result(task_id)
        token = result.get("gRecaptchaResponse")
        delay = random.randint(st.SIGN_DELAY[0], st.SIGN_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        logger.info("Start authorization")
        json_data = {"id": wallet.lower(), "signature": signature, "token": token}
        response = await client.post(
            url=self.url + self.handles['login'],
            json=json_data,
            headers=self.headers
        )
        self.check_response(response=response)

        delay = random.randint(st.SIGN_DELAY[0], st.SIGN_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        logger.info("Getting l2 account address")

        l2_account = self.get_l2_account(account=account)
        delay = random.randint(st.SIGN_DELAY[0], st.SIGN_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        logger.info("Start l2 account registration")

        self.register_l2(
            w3=w3,
            account=account,
            contract=contract,
            l2_account=l2_account,
            wallet=wallet,
        )

    def register_l2(
            self,
            w3: Web3,
            l2_account: str,
            account: LocalAccount,
            wallet: ChecksumAddress,
            contract: web3.contract.Contract
    ):
        """Функция регистрации аккаунта"""

        transaction = contract.functions.register(l2_account).build_transaction({
            'gas': 0,
            'value': 0,
            'gasPrice': 0,
            'from': wallet,
            'nonce': w3.eth.get_transaction_count(wallet),
        })
        self.send_transaction(w3=w3, account=account, transaction=transaction)

        l2_acc = contract.functions.l2Accounts(wallet).call()
        assert l2_acc == l2_account  # проверка на соответствие адресов из ск и отправленным

    @sync_retry
    def deposit(self, w3: Web3, wallet: ChecksumAddress, account: LocalAccount):
        """Функция депозита в L2"""

        logger.info("Start deposit")

        data = self.check_balance(w3=w3, wallet=wallet)

        if not data:
            logger.error(f"Insufficient wallet balance, wallet - {wallet}")
            return

        token, contract = data[0], data[1]
        recipient = Web3.to_checksum_address(cst.VAULT['bsc'])

        transaction = contract.functions.transfer(recipient, cst.MIN_AMOUNT).build_transaction({
            'gas': 0,
            'value': 0,
            'gasPrice': 0,
            'from': wallet,
            'nonce': w3.eth.get_transaction_count(wallet),
        })
        self.send_transaction(w3=w3, account=account, transaction=transaction, low_gas=True)

    @staticmethod
    def send_transaction(
            w3: Web3,
            account: LocalAccount,
            transaction: TxParams,
            low_gas: bool = False
    ):
        """Функция отправки транзакции"""

        if low_gas:
            transaction['gasPrice'] = w3.to_wei(1, 'gwei')  # gas - 1 gwei
        else:
            transaction['gasPrice'] = w3.eth.gas_price

        transaction['gas'] = w3.eth.estimate_gas(transaction)

        logger.info("Transaction built")

        delay = random.randint(st.SIGN_DELAY[0], st.SIGN_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        signed_tx = account.sign_transaction(transaction_dict=transaction)
        logger.info("Transaction signed")

        delay = random.randint(st.SIGN_DELAY[0], st.SIGN_DELAY[1])
        logger.info(f"Wait {delay} sec")
        time.sleep(delay)

        status = 0

        try:
            tx = w3.eth.send_raw_transaction(transaction=signed_tx.rawTransaction)
            logger.info("Transaction sent")

            delay = random.randint(st.SEND_DELAY[0], st.SEND_DELAY[1])
            logger.info(f"Wait {delay} sec")
            time.sleep(delay)

            tx_rec = w3.eth.wait_for_transaction_receipt(tx)
            status = tx_rec['status']
            logger.info(f"Transaction - https://bscscan.com/tx/{tx.hex()}")
        except Exception as err:
            logger.error(err)
        assert status == 1  # проверка на успешное прохождение транзакции

    @staticmethod
    def check_balance(
            w3: Web3,
            wallet: ChecksumAddress
    ) -> [ChecksumAddress, web3.contract.Contract] or None:
        """Функция проверки баланса USDT и USDC"""

        abi = json.dumps(ERC20_ABI)

        for tkn in cst.TOKENS:
            token = Web3.to_checksum_address(tkn)
            contract = w3.eth.contract(address=token, abi=abi)
            balance = contract.functions.balanceOf(wallet).call()

            if balance >= cst.MIN_AMOUNT:
                return [token, contract]

    @staticmethod
    def get_l2_account(account: LocalAccount) -> str:
        """Функция генерации адреса l2 аккаунта"""

        get_l2_keys = require("./keys.js")
        signature = account.sign_message(encode_defunct(text=cst.L2_TEXT)).signature.hex()
        data = get_l2_keys(signature)

        return '0x' + data['pub']

    @staticmethod
    def get_contract(w3: Web3, address: str, abi: list) -> web3.contract.Contract:
        """Функция получения к контракта"""

        address = Web3.to_checksum_address(address)
        abi = json.dumps(abi)

        return w3.eth.contract(address=address, abi=abi)

    @staticmethod
    def read_file(filename: str = "keys.txt") -> list:
        """Функция чтения файла"""

        keys = list()
        file_path = os.path.join(os.getcwd(), filename)

        with open(file_path, 'r') as file:
            for line in file:

                keys.append(line.rstrip('\n'))

        return keys

    @staticmethod
    def check_response(response: Response):
        """Функция проверки статуса овтета сервера"""

        code = response.status_code

        if code != 200:
            logger.error(f"Error when trying to request to the server. Status code - {code}")
            raise Exception

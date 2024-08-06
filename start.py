import socket
import threading
import os
from config.trusted_ips import *
import time
import hashlib
import pip
from subprocess import check_call, call
import sys

UDP_MAX_SIZE = 65535
decode_method = 'ascii'


def install(package):
    try:
        pip.main(["install", package])
    except AttributeError:
        check_call([sys.executable, '-m', 'pip', 'install', package])
    call([sys.executable, __file__])


try:
    import hashlib
except ModuleNotFoundError:
    print("Hashlib is not installed. "
          + "Miner will try to automatically install it "
          + "If it fails, please manually execute "
          + "python3 -m pip install hashlib")
    install('hashlib')


class Block:
    def __init__(self, index, timestamp, transactions, proof, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.proof = proof
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        hash_string = str(self.index) + str(self.timestamp) + str(self.transactions) + str(self.proof) + str(self.previous_hash)
        # print(f"hash_string {hash_string}")
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def checking_calculate_hash(self, check_timestamp):

        hash_string = str(self.index) + str(check_timestamp) + str(self.transactions) + str(self.proof) + str(
            self.previous_hash)
        # print(f"index {self.index}")
        # print(f"hash_string {hash_string}")
        return hashlib.sha256(hash_string.encode()).hexdigest()


class Blockchain:
    def __init__(self, timestamp, transactions, proof, previous_hash):
        self.current_transactions = []
        self.chain = [self.import_genesis_block(timestamp, transactions, proof, previous_hash)]


    def import_genesis_block(self, timestamp, transactions, proof, previous_hash):
        return Block(0, timestamp, transactions, proof, previous_hash)

    def create_genesis_block(self):
        return Block(0, time.time(), self.current_transactions, "100", "Genesis Block")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, new_block):
        new_block.previous_hash = self.get_latest_block().hash
        new_block.hash = new_block.calculate_hash()
        self.chain.append(new_block)

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return int(self.get_latest_block().index) + 1

    def proof_of_work(self, last_block):
        last_proof = self.get_latest_block().proof
        last_hash = self.get_latest_block().hash

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:5] == "00000"

    def is_valid(self):
        for i in range(1, len(self.chain)):
            # print(self.chain[0].hash)
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            # print(f"{current_block.hash} = {current_block.calculate_hash()}")
            # print(f"{current_block.previous_hash} = {previous_block.hash}")
            if current_block.hash != current_block.checking_calculate_hash(current_block.timestamp):
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

        return True


def mine(miner_address, blockchain):
    last_block = blockchain.get_latest_block()
    start_mining_time = time.time()
    proof = blockchain.proof_of_work(last_block)
    print(f"Блок #{int(blockchain.get_latest_block().index)+1} найден!")
    print(f"Время нахождения блока: {time.time() - start_mining_time}")
    blockchain.current_transactions = []
    blockchain.new_transaction(
        sender="Coinbase",
        recipient=f"{miner_address}",
        amount=250+(0.1*(1-int(blockchain.get_latest_block().index))),
    )
    new_block = f"{str(int(blockchain.get_latest_block().index)+1)}|{str(time.time())}|{blockchain.current_transactions}|{proof}|{str(blockchain.get_latest_block().previous_hash)}"
    return new_block


def listen(s: socket.socket):
    s.send('/get_genesis_block'.encode('ascii'))
    while True:
        msg = s.recv(UDP_MAX_SIZE)
        s.send('/get_latest_block'.encode('ascii'))
        if msg.decode('ascii').startswith('/import_genesis_block'):
            shifted_string = msg.decode('ascii').split()
            # print(shifted_string)
            server_blockchain_index = shifted_string[1]
            server_blockchain_time = shifted_string[2]
            server_blockchain_transactions = shifted_string[3]
            server_blockchain_proof = shifted_string[4]
            server_blockchain_hash = shifted_string[5]
            server_blockchain_previoushash = shifted_string[6]
            if int(server_blockchain_index) == 0:
                print("\nИмпортируем генезиз блок...")
                blockchain = Blockchain(server_blockchain_time, server_blockchain_transactions, server_blockchain_proof, server_blockchain_previoushash)
        if msg.decode('utf-8').startswith('/update_blocks'):
            shifted_string = msg.decode('ascii').split()
            # print(shifted_string)
            server_blockchain_index = shifted_string[1]
            server_blockchain_time = shifted_string[2]
            server_blockchain_transactions = shifted_string[3]
            server_blockchain_proof = shifted_string[4]
            server_blockchain_hash = shifted_string[5]
            server_blockchain_previoushash = shifted_string[6]
            if int(server_blockchain_index) > int(blockchain.get_latest_block().index):
                index_difference = int(server_blockchain_index) - int(blockchain.get_latest_block().index)
                if index_difference == 1:
                    print("\nОбновление блоков...\n")
                    blockchain.add_block(Block(server_blockchain_index, server_blockchain_time, server_blockchain_transactions, server_blockchain_proof, server_blockchain_previoushash))
            else:
                print("\n")

        # else:
            # print('\r\r' + msg.decode('ascii') + '\n' + f'command: ', end='')
        try:
            s.send(f'/new_block|{mine(f"{wallet_address}", blockchain)}'.encode('ascii'))
        except Exception as err:
            print(err)
            print("Майнер не работает :(")

        time.sleep(2)


def connect(host: str = str(MAIN_SERVER), port: int = 5000):
    print(MAIN_SERVER)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    s.connect((host, port))

    threading.Thread(target=listen, args=(s,), daemon=True).start()

    s.send('__join'.encode('ascii'))

    while True:
        msg = input(f'\nПодключение... ')
        s.send(msg.encode('ascii'))


if __name__ == '__main__':
    global wallet_address
    os.system('cls' if os.name == 'nt' else 'clear')
    wallet_address = input('Введите адрес кошелька')
    if wallet_address.startswith('AVER'):
        connect()
    else:
        print("Неправильный адрес, запускается майнинг на кошелек разработчика...")
        wallet_address = "AVER75005d9f53b5238c5de337c059373091ceec70a8f95137e6b3b0a9280b5e56e5"
        connect()

import json
import os
import time
from datetime import datetime
from hashlib import sha256
from ecpy.keys import ECPublicKey, ECPrivateKey
from ecpy.ecdsa import ECDSA
import random
import DAL.dbs as db
import config
from Block.block import Block
from Blockchain import helper
from ecpy.curves import Curve, Point
from Transaction.transaction import verify
import Transaction.transaction as transaction
import Transaction.transaction_input as Txin
from Transaction.transaction_output import TX_OUT


# generate private/public key pair
def get_private_key():
    curve = Curve.get_curve('secp256k1')
    rand_32 = sha256(str(random.randint(1, 1000000)).encode('utf-8')).hexdigest()
    private_key = ECPrivateKey(int(rand_32, 16), curve)
    return private_key


'''
Blockchain class.
Handles Blockchain related logic
'''


class Blockchain:
    def __init__(self):
        self.private_key = None
        self.block_chain = []  # cache for blockchain

        # --- attributes for handling consensus block. ---
        self.candidate_chains = []
        self.candidate_blocks = []
        # ------------------------------------------------
        """
        utxo structure: 
        [
            [tx_id, [txout1, txout2, ...], [False, False, ...]],
            ...
        ]
        if a txout is used, change corresponding False to True BUT DO NOT delete.
        if all used flags are True, which means all txouts of a tx had been used, delete this record.
        """
        self.utxo = []  # redis cache
        self.unconfirmed_transactions = []  # transaction pool cache
        self.balance = 0
        self.address = ""  # initiated with public key
        self.handle_keys()

    # region goal 5 redis --- utxo handling ---

    # add a Tx in utxo
    def add_to_utxo(self, tx):
        self.utxo.append([tx.id, tx.tx_outs, [False] * len(tx.tx_outs)])

    def update_utxo(self):
        db.update_utxo(self.utxo)

    def load_utxo(self):
        self.utxo = db.load_utxo()

    # endregion

    # region goal 3 and fault tolerance handling --- transactions handling ---

    def update_transaction_pool(self):
        db.update_transaction_records(self.unconfirmed_transactions)

    def load_transactions(self):
        trans_str = db.load_transaction_records()
        trans_json = json.loads(trans_str)
        for trans in trans_json:
            tx = transaction.Transaction()
            tx.load_from_json(trans)
            self.unconfirmed_transactions.append(tx)

        return

    # endregion

    # region goal 2, 3 and 4 --- general private/public keys handling ---

    def handle_keys(self):  # generate private key/public key pairs when there is no key defined
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, 'keys.json')
        f = open(file_path)
        keys_json = json.load(f)  # resume previous defined key when node is down - handle node outage
        if 'private' not in keys_json.keys() or 'public' not in keys_json.keys():
            f.close()
            self.generate_keys()  # when no previous key stored -> new node, generate new key
            return

        self.private_key = ECPrivateKey(keys_json['private'], Curve.get_curve('secp256k1'))
        self.address = keys_json['public']

    # generate key pair when new node is initialized
    def generate_keys(self):
        self.private_key = get_private_key()
        # public key hash
        self.address = sha256(str(self.private_key.get_public_key()).encode('utf-8')).hexdigest()
        keys = {}
        keys['private'] = self.private_key.d
        keys['public'] = self.address

        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, 'keys.json')

        # save key pair into key file, used for node recovery from outage - fault tolerance.
        # save in json format.
        with open(file_path, 'w') as fp:
            json.dump(keys, fp)

    # endregion

    # region goal 1 and 2 --- genesis block ---
    def create_genesis(self):
        # ------genesis block-------------
        txout = TX_OUT(address=self.address, amount=50)
        coinbase = transaction.Transaction()
        coinbase.tx_ins = []
        coinbase.tx_outs.append(txout)
        coinbase.generate_transaction_id()

        genesis = Block(index=0,
                        prev_hash="",
                        timestamp=time.time(),
                        transactions=[],
                        difficulty=15,
                        nonce=0)
        genesis.transactions.append(coinbase)
        genesis.calculate_merkle_root()
        genesis.curr_hash = genesis.calculate_block_hash()
        self.block_chain.append(genesis)
        self.add_to_utxo(coinbase)  # save coinbase to utxo

        self.update_utxo()  # update redis

        self.update_db_storage()  # update block database
        self.balance = 50  # verification and testing purpose only, not a standard field to use.
        return True

    # endregion

    def get_latest_block(self) -> Block:
        return self.block_chain[-1]

    # region goal 2: --- mining ---
    def mine(self):
        if not self.utxo:  # for testing purpose, need to revert back.
            # if not self.unconfirmed_transactions:
            print("Node does not have utxo, too poor!!!")
            return False, None
        else:
            print("Mining Start")
            start_time = datetime.now()
            new_blk = self.find_new_block()  # get a new block
            prev_blk = self.get_latest_block() # get latest block
            if self.is_valid_new_block(new_blk, prev_blk): # valid check for new block

                # adjust utxo
                for tx in new_blk.transactions:
                    self.add_to_utxo(tx)  # append coinbase to utxo
                self.update_utxo()
                self.block_chain.append(new_blk)

                self.unconfirmed_transactions = []
                self.update_transaction_pool()

                self.balance = self.balance + 50
                end_time = datetime.now()
                elapsed = end_time - start_time
                print(f"{datetime.now()}: A new block found.")
                print(f'Time elapsed: {elapsed}')
                self.update_db_storage()
                return True, new_blk
        return False, None

    def is_valid_new_block(self, block: Block, previous_block: Block = None) -> bool:
        if len(self.block_chain) != 0:
            _prev_block = previous_block
            if _prev_block == None:
                _prev_block = self.block_chain[-1]
            if _prev_block.index + 1 != block.index:
                return False
            if _prev_block.curr_hash != block.prev_hash:
                return False
        else:
            if block.index != 0:
                return False

        if block.calculate_block_hash() != block.curr_hash:  # for testing purpose
            return False
        return True

    def generate_next_block(self) -> Block:
        previous_block = self.get_latest_block()
        next_index = previous_block.index + 1
        next_timestamp = time.time()
        blk = Block(timestamp=next_timestamp, index=next_index, prev_hash=previous_block.curr_hash,
                    difficulty=previous_block.difficulty, transactions=[])

        txout = TX_OUT(self.address, 50)
        coinbase = transaction.Transaction()  # create coinbase transaction whenever there is a new block
        coinbase.tx_outs.append(txout)
        coinbase.generate_transaction_id()

        blk.transactions.append((coinbase))
        for tx in self.unconfirmed_transactions:
            blk.transactions.append((tx))
        blk.calculate_merkle_root()
        return blk

    def find_new_block(self) -> Block:
        nonce = 0
        next_block = self.generate_next_block()  # generate next block
        next_difficulty = self.get_difficulty()  # find new difficulty for this mining task
        next_block.difficulty = next_difficulty
        print(f"Current Difficulty: {next_difficulty}")
        while True:
            next_block.nonce = nonce  # Goal 2 : mining
            new_hash = next_block.calculate_block_hash()
            if helper.hash_matches_difficulty(new_hash, next_difficulty):
                next_block.nonce = nonce
                next_block.curr_hash = new_hash
                return next_block
            nonce = nonce + 1

    # handle difficulty
    def get_difficulty(self) -> int:
        latest_block = self.get_latest_block()
        if latest_block.index % config.DIFFICULTY_ADJUSTMENT_INTERVAL == 0 \
                and latest_block.index != 0:
            return self.get_adjusted_difficulty(latest_block, self.block_chain)
        return latest_block.difficulty

    # goal 2: handle dynamic difficulty changes
    def get_adjusted_difficulty(self, latest_block: Block, a_blockchain) -> int:

        prev_adjustment_block = self.block_chain[len(a_blockchain) - config.DIFFICULTY_ADJUSTMENT_INTERVAL]
        time_expected = config.DIFFICULTY_ADJUSTMENT_INTERVAL * \
                        config.BLOCK_GENERATION_INTERVAL
        latest_ts = latest_block.timestamp
        prev_ts = prev_adjustment_block.timestamp
        time_taken = latest_ts - prev_ts
        if time_taken < time_expected / 2:
            return prev_adjustment_block.difficulty + 1
        elif time_taken > time_expected * 2:
            return prev_adjustment_block.difficulty - 1
        else:
            return prev_adjustment_block.difficulty

    # endregion

    # region  --- mongo use ---
    def update_db_storage(self):
        db.reset_mongo()
        for block in self.block_chain:
            if block.is_exist() == False:
                block.save(replace=False)

    def load_from_db(self):
        self.block_chain = []
        index = 0
        block = Block(index)
        while block.is_exist() == True:
            block.load(block.index)
            self.block_chain.append(block)
            index = index + 1
            block = Block(index)

    # endregion

    # region --- consensus ---

    # longest chain rule for block with same height at tail
    def resolve_same_height(self, blk):
        for cand_block in self.candidate_blocks:
            # for block in the candidate block - if its valid wth new coming block, means this fork is true.
            if self.is_valid_new_block(blk, previous_block=cand_block):
                self.block_chain[-1] = cand_block

    # longest chain rule for block with same height at middle
    def resolve_consensus(self):
        if self.block_chain:
            self.candidate_chains.append(self.block_chain)
        largest = 0
        candidate = None
        for chain in self.candidate_chains:
            if self.is_valid_chain(chain):
                if len(chain) > largest:
                    largest = len(chain)
                    candidate = chain
        self.block_chain = candidate

    def is_valid_chain(self, chain):  # check if chain is valid.
        for index, block in enumerate(chain):
            if index == 0:
                continue
            else:
                if block.prev_hash != chain[index - 1].curr_hash:
                    return False
                if block.index - 1 != chain[index - 1].index:
                    return False
                if block.calculate_block_hash() != block.curr_hash:
                    return False
        return True

    # endregion

    # region --- transaction pool operation ---

    def P2PKH(self, tx):  # pay to key public hash verification
        content = tx.get_tx_ins_content() + tx.get_tx_outs_content() + tx.id
        if len(tx.tx_ins) <= 0:
            return False

        result = True
        for tx_in in tx.tx_ins:
            signature, public_key_str = tx_in.signature.split("<-sig/PKey->")  # verify signature
            public_key_str = public_key_str.split("/")
            # generate public key from signature
            public_key = ECPublicKey(
                Point(int(public_key_str[0]), int(public_key_str[1]), Curve.get_curve('secp256k1')))
            pre_tx_id = tx_in.tx_out_id
            pre_tx_idx = tx_in.tx_out_index

            addr = ""
            for record in self.utxo:
                if record[0] == pre_tx_id:
                    addr = record[1][pre_tx_idx].address
                    break

            result = verify(addr, bytes.fromhex(signature), public_key, content)
            if result == False:
                return False

        return result


# endregion

# region --- helpers ---

def to_tx_in(data):
    if data == None:
        return None

    txin = Txin.TX_IN()
    for key, value in data.items():
        if key == 'tx_out_id':
            txin.tx_out_id = value
        if key == 'tx_out_index':
            txin.tx_out_index = value
        if key == 'signature':
            txin.signature = value
    return txin


def to_tx_out(data):
    txout = TX_OUT()
    for key, value in data.items():
        if key == 'address':
            txout.address = value
        if key == 'amount':
            txout.amount = value
    return txout


def to_transaction(data):
    print(type(data))
    trans = transaction.Transaction()
    for key, value in data.items():
        if key == 'tx_ins':
            for item in value:
                trans.tx_ins.append(to_tx_in(item))
        if key == 'tx_outs':
            for item in value:
                trans.tx_outs.append(to_tx_out(item))
        if key == 'id':
            trans.id = value
    return trans


def to_block(data):
    blk = Block()
    for key, value in data.items():
        if key == 'index':
            blk.index = value
        if key == 'curr_hash':
            blk.curr_hash = value
        if key == 'prev_hash':
            blk.prev_hash = value
        if key == 'timestamp':
            blk.timestamp = value
        if key == 'nonce':
            blk.nonce = value
        if key == 'difficulty':
            blk.difficulty = value
        if key == 'data':
            blk.data = data
        if key == 'merkle_root':
            blk.merkle_root = value
        if key == 'transactions':
            blk.transactions = []
            for transaction in value:
                blk.transactions.append(to_transaction(transaction))
    return blk

# endregion

import json

from hashlib import sha256
from DAL import connection
from Transaction.transaction import Transaction
from Block.merkletree import cal_merkle_root


# goal 1
# implementation of raw block
class Block:
    def __init__(self, index=-1, timestamp=0, prev_hash="", curr_hash="",
                 difficulty=0, nonce=0, merkle_root="", transactions=[]):
        self.index = index
        self.timestamp = timestamp
        self.prev_hash = prev_hash
        self.curr_hash = curr_hash
        self.difficulty = difficulty
        self.nonce = nonce
        self.merkle_root = merkle_root
        self.transactions = transactions
        # self calculation
        if self.transactions is not None and len(self.transactions) > 0:
            self.calculate_merkle_root()

    def reprJSON(self):
        return self.__dict__


    def calculate_block_hash(self):
        # return the hash the block encoded by SHA256
        ignore = ['curr_hash']
        block_params = {x: self.__dict__[x] for x in self.__dict__ if x not in ignore}
        block_string = json.dumps(block_params, default=lambda x: getattr(x, '__dict__', str(x)))
        return sha256(block_string.encode()).hexdigest()
    
    
    # should recalled when transaction changed
    def calculate_merkle_root(self):
        leaves = []
        for tx in self.transactions:
            leaf = json.dumps(tx.save_as_json())
            leaves.append(leaf)
        mr = cal_merkle_root(leaves)
        self.merkle_root = mr
        return mr
    
    # region --- goal 5: mongo db storage ---
    # # Show the block info
    def display(self):
        print("< -- Block Information -- >")
        print("< Index: ", self.index)
        print("< TimeStamp: ", self.timestamp)
        print("< PrevHash: ", self.prev_hash)
        print("< CurrHash: ", self.curr_hash)
        print("< Difficulty: ", self.difficulty)
        print("< Nonce: ", self.nonce)
        print("< MerkleRoot: ", self.merkle_root)
        print("< TransactionData: ", self.transactions)

    # check this block whether exists in db
    def is_exist(self):
        count = connection.blockchain_db.count_documents({"index":self.index})
        if count == 0:
            return False
        else:
            return True

    # Store data in Mongo
    def save(self, replace=False):
        status = self.is_exist()
        if status is True and replace is not False:
            return "Save failed: Index duplicated."
        else:
            txs_json = []
            for tx in self.transactions:
                tx_json = tx.save_as_json()
                txs_json.append(tx_json)
            
            dict = {
                "index": self.index,
                "timestamp": self.timestamp,
                "prev_hash": self.prev_hash,
                "curr_hash": self.curr_hash,
                "difficulty": self.difficulty,
                "nonce": self.nonce,
                "merkle_root": self.merkle_root,
                "transactions": txs_json
            }
            result = connection.blockchain_db.insert_one(dict)
            return result
    
    def load(self, index):
        condition = {"index": index}
        result = connection.blockchain_db.find_one(condition)
        self.index = index
        self.timestamp = result["timestamp"]
        self.prev_hash = result["prev_hash"]
        self.curr_hash = result["curr_hash"]
        self.difficulty = result["difficulty"]
        self.nonce = result["nonce"]
        self.merkle_root = result["merkle_root"]
        self.transactions = []
        for tx_json in result["transactions"]:
            tx = Transaction()
            tx.load_from_json(tx_json)
            self.transactions.append(tx)
        return result
    
    # endregion



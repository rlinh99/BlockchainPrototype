import json
from hashlib import sha256

# goal 3 - Transaction in class
class TX_IN:
    def __init__(self, pre_id="", pre_idx=0):
        # get index from previous block
        self.tx_out_index = pre_idx
        # get id from previous transaction
        self.tx_out_id = pre_id
        self.signature = ""

    def reprJSON(self):
        return self.__dict__

    @staticmethod
    def get_public_key(private_key):
        public_key = private_key.get_public_key()
        return public_key

    @staticmethod
    def get_address(public_key):
        return sha256(str(public_key).encode('utf-8')).hexdigest()

    # region goal 5: --- redis ---
    def get_content(self):
        params = {
            'tx_out_id': self.tx_out_id,
            'tx_out_index': self.tx_out_index,
            'signature': self.signature
        }
        string = json.dumps(params, sort_keys=True)  # convert to json object
        return string

    def load_from_str_json(self, str_json):
        dict = json.loads(str_json)
        self.tx_out_index = dict["tx_out_index"]
        self.tx_out_id = dict["tx_out_id"]
        self.signature = dict["signature"]
        return

    def display(self):
        print("< -- Transaction Input information -- >")
        print("< Transaction id: ", self.tx_out_id)
        print("< Transaction index: ", self.tx_out_index)
        print("< Signature: ", self.signature)
        return
    # endregion

    # region goal 5: --- mongo ---
    def save_as_json(self):
        dict = {
            'tx_out_id': self.tx_out_id,
            'tx_out_index': self.tx_out_index,
            'signature': self.signature
        }
        return dict

    def load_from_json(self, dict):
        self.tx_out_index = dict["tx_out_index"]
        self.tx_out_id = dict["tx_out_id"]
        self.signature = dict["signature"]
        return
    # endregion

from hashlib import sha256
from ecpy.ecdsa import ECDSA
import json

from Transaction.transaction_input import TX_IN
from Transaction.transaction_output import TX_OUT


# goal 3: Transaction Implementation
class Transaction:
    def __init__(self, tx_ins = [], tx_outs=[]):
        self.id = ""
        self.tx_ins = []
        self.tx_outs = []

    
    def reprJSON(self):
        return self.__dict__

    # generate transaction id
    def generate_transaction_id(self):
        tx_in_content = ''
        if len(self.tx_ins) != 0:
            tx_in_content = self.get_tx_ins_content()
        tx_out_content = ''
        if len(self.tx_outs) != 0:
            tx_out_content = self.get_tx_outs_content()
        tx_content = tx_in_content + tx_out_content
        transaction_id = sha256(tx_content.encode('utf-8')).hexdigest()
        self.id = transaction_id


    # generate signature for a transaction
    def generate_signature(self, private_key):
        tx_ins_str = self.get_tx_ins_content()
        tx_outs_str = self.get_tx_outs_content()
        message = tx_ins_str + tx_outs_str + self.id

        signer = ECDSA()
        sig = signer.sign(message.encode('utf-8'), private_key).hex()
        # concate signature and public key
        pk = private_key.get_public_key()
        
        sig = sig + "<-sig/PKey->" + str(pk.W.x) + "/" + str(pk.W.y)
        #  generate signare for all txins
        for txin in self.tx_ins:
            txin.signature = sig

        return sig

    # json stringify for txin content
    def get_tx_ins_content(self):
        txin_str = ''
        for txin in self.tx_ins:
            params = {
                'tx_out_id': txin.tx_out_id,
                'tx_out_index': txin.tx_out_index,
            }
            _txin_str = json.dumps(params, sort_keys=True)
            txin_str = txin_str + _txin_str  # convert to json object
        return txin_str


    # json stringify for txout content
    def get_tx_outs_content(self):
        txout_str = ''
        for txout in self.tx_outs:
            params = {
                'address': txout.address,
                'amount': txout.amount
            }
            _txout_str = json.dumps(params, sort_keys=True)
            txout_str = txout_str + _txout_str  # convert to json object
        return txout_str

    # region --- goal 5: mongoDB nested json handling ----
    def save_as_json(self):
        tx_ins_dict = []
        tx_outs_dict = []
        for tx_in in self.tx_ins:
            tx_ins_dict.append(tx_in.save_as_json())
        for tx_out in self.tx_outs:
            tx_outs_dict.append(tx_out.save_as_json())
        
        dict = {
            "id": self.id,
            "tx_ins": tx_ins_dict,
            "tx_outs": tx_outs_dict
        }
        return dict

    def load_from_json(self, dict):
        self.id = dict["id"]
        tx_ins_dict = dict["tx_ins"]
        tx_outs_dict = dict["tx_outs"]
        self.tx_ins = []
        self.tx_outs = []
        for tx_in_dict in tx_ins_dict:
            tx_in = TX_IN()
            tx_in.load_from_json(tx_in_dict)
            self.tx_ins.append(tx_in)
        
        for tx_out_dict in tx_outs_dict:    
            tx_out = TX_OUT()
            tx_out.load_from_json(tx_out_dict)
            self.tx_outs.append(tx_out)
        return

    def display(self):
        print("< -- Transaction information -->")
        print("< Transaction id: ", self.id)
        print("< Transaction input: ", self.tx_ins)
        print("< Transaction output: ", self.tx_outs)
        return
    # endregion


# goal 3: --- verify transaction ---
def verify(addr, signature, public_key, content):
    hash = sha256(str(public_key).encode('utf-8')).hexdigest()
    if addr != hash:
        return False
    
    result = ECDSA().verify(content.encode('utf-8'), signature, public_key)
    return result
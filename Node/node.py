import json
import socket
import requests
import config
import Transaction.transaction as trans
from Transaction.transaction import TX_IN, TX_OUT
from Blockchain.blockchain import Blockchain, to_block

'''
starting file for a running node. 
contains node broadcasting APIs and other methods.
'''
class Node():
    # use id + ip address as peer identifier since port number is not used for Django
    def __init__(self, blockchain):
        self.peers = []  # peer list of a node, peer store as (ip, port) tuple
        self.ip = my_ip
        self.address = blockchain.address #
        self.blockchain = blockchain
        self.check_db()  # resume blockchain from raw db
        self.check_utxo()
        # handle first node in the system. handle genesis block
        if config.IS_CENTER:
            self.peers.append(('127.0.0.1', 3456))
            if len(self.blockchain.block_chain) == 0:
                blockchain.create_genesis()  # create genesis at first start
        self.check_utxo()  # resume utxo from redis
        self.check_transactions()  # resume transactions from file

    # handle resume blockchain
    def check_db(self):
        self.blockchain.load_from_db()

    # handle resume utxo
    def check_utxo(self):
        self.blockchain.load_utxo()

    # handle resume transaction
    def check_transactions(self):
        self.blockchain.load_transactions()

    # handle receiving new block from other node (block broadcasted from other nodes.)
    def handle_new_block(self, blk_json):
        blk = to_block(blk_json)
        # consensus case - same height
        if len(self.blockchain.candidate_blocks) != 0:
            self.blockchain.resolve_same_height(blk)  # solve existing consensus height block with new coming block

        is_valid = blockchain.is_valid_new_block(block = blk)
        if is_valid:
            self.blockchain.candidate_blocks = []  # reset candidate block pool since consensus is solved.
            self.blockchain.block_chain.append(blk)
            self.blockchain.update_db_storage()
            return True, 'New block is valid.', 'normal'
        else:
            # handling same height fork. put candidate block into candidate pool
            latest_block = self.blockchain.block_chain[-1]
            if blk.index == latest_block.index: # handle fork situation
                self.blockchain.candidate_blocks.append(blk)
                return False, 'New block is invalid, here is a fork', 'fork'
            else:
                # for general invalid block
                # consensus work when new block is invalid
                for peer in self.peers:
                    if peer[1] != config.PORT:
                        chain = self.get_latest_chain(peer)  # get chain from other nodes
                        self.blockchain.candidate_chains.append(chain)
                        self.blockchain.resolve_consensus()
                print("new block is invalid, please try again. Got a longest valid train from peer")
                self.blockchain.update_db_storage()
                return False, 'New block is invalid', 'invalid'

    def handle_transaction(self, tx_json):
        tx = trans.Transaction()
        tx.load_from_json(tx_json)
        self.blockchain.add_to_utxo(tx)
        self.blockchain.update_utxo()
        self.blockchain.unconfirmed_transactions.append(tx)
        self.blockchain.update_transaction_pool()


    # uses ip + ad as identifier, accept connection from other source
    def add_peer(self, ip: str, port: int):
        if ip == self.ip and port == config.PORT:
            print("I am connected to myself.")
            return False
        if (ip, port) in self.peers:
            print(f"Node {ip}:{port} is already in the network")
            return False

        self.peers.append((ip, port))
        return True

    # connect to a peer, get a list of peers from the target
    def connect_to_peer(self, ip, port):
        url = f"http://{ip}:{port}/connect"
        request = {
            "port": config.PORT,
            "ip": my_ip
        }
        # get peer lists from this connected peer, added into this node.
        response = requests.post(url, json=request)
        response_json = response.json()
        status = response_json['status']

        if status == "Failed":  # return when connected peer refused connection
            print(response_json["message"])
            return False
        peer_list = response_json['nodes']
        for peer in peer_list:  # update peer list
            if (peer[0], peer[1]) not in self.peers:
                self.peers.append((peer[0], peer[1]))
        latest_chain_data = response_json['latest_chain']
        message = response_json['message']
        print(message)
        candidate_chain = []
        for block_value in latest_chain_data:
            latest_blk = to_block(block_value)
            candidate_chain.append(latest_blk)
        self.blockchain.candidate_chains.append(candidate_chain)

        for peer in self.peers:
            if peer[1] != config.PORT and peer[1] != config.KNOWN_CENTER_PORT:
                chain = self.get_latest_chain(peer) # get chain from other nodes
                self.blockchain.candidate_chains.append(chain)
        # to do - consensus work
        # -----------------------------
        self.blockchain.resolve_consensus()
        # -----------------------------
        blockchain.update_db_storage()
        return True

    def update_peers(self, peers):
        for peer in peers:
            self.add_peer(peer[0], peer[1])

    def get_latest_chain(self, peer):
        url = f"http://{peer[0]}:{peer[1]}/chain"
        request = {
            "port": config.PORT,
            "ip": my_ip
        }
        # get peer lists from this connected peer, added into this node.
        response = requests.get(url, json=request)
        response_json = response.json()
        latest_chain_data = response_json['latest_chain']
        message = response_json['message']
        print(message)
        candidate_chain = []
        for block_value in latest_chain_data:
            latest_blk = to_block(block_value)
            candidate_chain.append(latest_blk)
        return candidate_chain


    # used when new block is found, send it to others
    # send latest block to other nodes -> controller/receive_new
    def send_latest_block(self, peer, block):
        url = f"http://{peer[0]}:{peer[1]}/receive_new"

        json_blk = json.dumps(block,
                              default=lambda x: getattr(x, '__dict__', str(x)))
        data = {
            "message": f"New block sent from {config.PORT}",
            "new_block": json_blk
        }

        response = requests.post(url, json=data)
        response_json = response.json()
        message = response_json['message']
        status = response_json['status']
        situation = response_json['situation']
        print(message)
        # handle consensus request initiated from peer.
        if status == 'failed':
            if situation == 'invalid':
                # when situation is fork, it will be handled at receipient side.
                for peer in self.peers:
                    if peer[1] != config.PORT and peer[1] != config.KNOWN_CENTER_PORT:
                        chain = self.get_latest_chain(peer)  # get chain from other nodes
                        self.blockchain.candidate_chains.append(chain)
                # to do - consensus work
                # -----------------------------
                self.blockchain.resolve_consensus()
                # -----------------------------
                blockchain.update_db_storage()

    def send_peerslist(self, peer):
        url = f"http://{peer[0]}:{peer[1]}/update_peers"
        data = {
            'peers': self.peers
        }
        json.dumps(self.peers,
                   default=lambda x: getattr(x, '__dict__', str(x)))
        requests.post(url, json = data)


    def broadcast_peerslist(self):
        for peer in self.peers:
            if peer[1] != config.PORT:
                self.send_peerslist(peer)
        return

    # broadcast new block to all peers
    def broadcast_blocks(self, block):
        if len(self.peers) == 0:
            print("Only current node is running, no other node is in the system")
            return
        for peer in self.peers:
            if peer[1] == config.PORT: # do not broadcast to self, causing duplication
                continue
            try:
                self.send_latest_block(peer, block)
            except Exception as e:
                print(e)
                print(f'node {peer[0]}:{peer[1]} is not active')
        return

    # broadcast transaction to all peers
    def broadcast_transaction(self, transaction):
        # refer to broadcast_blocks()
        tx_json = json.dumps(transaction.save_as_json())
        if len(self.peers) == 0:
            print("Only current node is running, no other node is in the system")
            return False
        for peer in self.peers:
            if peer[1] == config.PORT:
                continue
            try:
                url = f"http://{peer[0]}:{peer[1]}/receive_transaction"
                data = {
                    "message": f"New transaction from {config.PORT}",
                    "new_transaction": tx_json
                }
                requests.post(url, json = data)
            except Exception as e:
                print(e)
                print(f'node {peer[0]}:{peer[1]} is not active')
        return

    # create a transaction
    def create_transaction(self, recipient, amount):
        utxos = self.blockchain.utxo
        usable_tx = []
        accumulated_amount = 0
        insufficient = False
        for record in utxos:
            outs = record[1]
            used_flags = record[2]
            out_indexes = []
            for index, out in enumerate(outs): # find usable uxto in the pool
                if out.address == self.blockchain.address and used_flags[index] is not True:
                    out_indexes.append(index)
                    accumulated_amount += out.amount # verify utxo total amount
            
            if len(out_indexes) > 0:        
                usable_tx.append((record, out_indexes))

            if accumulated_amount >= amount:  # stop right after the balance is enough.
                # make sure no extra transaction is selected. Available transaction will be retried in FIFO
                print("This node has enough fund for this transaction")
                insufficient = False
                break
            else:
                insufficient = True

        if insufficient:  # if no enough balance, return fail.
            print("This node has insufficient fund. Create new transaction failed")
            return False, None

        new_tx = trans.Transaction()

        tx_out_outbound = TX_OUT(recipient, amount)  # txout amount to recipient
        tx_out_inbound = TX_OUT(self.address, accumulated_amount - amount)  # txout remain amount back to self

        new_tx_ins = []
        for record, indexes in usable_tx:  # loop through usable utxo for txins.
            id = record[0]
            for i in indexes:
                _new_txin = TX_IN(id, i)
                new_tx_ins.append(_new_txin)
        
        new_tx.tx_ins = new_tx_ins
        new_tx.tx_outs.append(tx_out_outbound)
        new_tx.tx_outs.append(tx_out_inbound)
        new_tx.generate_transaction_id()
        # generate signature with private key for transaction
        new_tx.generate_signature(self.blockchain.private_key) # new_tx is now ready to use
        
        # ---- P2PKH verification ----
        judge = self.blockchain.P2PKH(new_tx)
        if judge == False:
            return False, None
        # ---- P2PKH verification ----
        
        # modify used flag, check whether a tx can be deleted from utxo.
        for record, indexes in usable_tx:
            subscript = self.blockchain.utxo.index(record)
            for index in indexes:
                self.blockchain.utxo[subscript][2][index] = True
            
            del_flag = True
            for flag in self.blockchain.utxo[subscript][2]:
                if flag == False:
                    del_flag = False
                    
            if del_flag == True:
                self.blockchain.utxo.pop(subscript)

        # add new utxos in utxo pool
        self.blockchain.add_to_utxo(new_tx)
        self.blockchain.update_utxo()  # update redis

        # add to transaction pool
        self.blockchain.unconfirmed_transactions.append(new_tx)
        self.blockchain.update_transaction_pool()  # update transaction pool
        # update all pool
        # ---------------------------

        # ----------------------------
        return True, new_tx

    def send_transaction(self, recipient, amount):
        success, transaction = self.create_transaction(recipient, amount)
        if success:
            blockchain.balance -= amount
            self.broadcast_transaction(transaction)  # broadcast transaction to peers.
            return True, f"Transaction to {recipient} is sent."
        return False, f"Transaction to {recipient} failed."


    def get_peers(self):
        return self.peers

    def remove_last_block(self):
        self.blockchain.block_chain.pop()
        self.blockchain.update_db_storage()
# to do later
    

name = socket.gethostname()
my_ip = socket.gethostbyname(name)
blockchain = Blockchain()  # initialization of blockchain object
node = Node(blockchain)  # initialization node with this block chain

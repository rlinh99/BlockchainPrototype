import json
from Blockchain.blockchain import to_block
import config
from flask import Flask, request
from Node.node import node
import datetime

app = Flask(__name__)


# region Nodes Interations API
# accept connection from others， return latest block at the same time
@app.route('/connect', methods=['POST'])
def connect():
    client_info = request.get_json()
    ip = client_info['ip']
    port = client_info['port']
    added = node.add_peer(ip, port)
    if added:
        chain = node.blockchain.block_chain
        response = {
            "status": "Success",
            "message": f"You have been accepted by node {config.PORT}",
            "nodes": list(node.get_peers()),
            "latest_chain": chain,
            "public_key": node.blockchain.address
        }
        node.broadcast_peerslist()
    else:
        response = {
            "status": "Failed",
            "message": "You are already in the network.",
        }
    data = json.dumps(response, default=lambda x: getattr(x, '__dict__', str(x)))
    return data, 200

@app.route('/update_peers', methods=['POST'])
def update_peers():
    json_str = request.get_json()
    nodes_data = json_str['peers']
    node.update_peers(nodes_data)
    return "ok", 200

# return my latest block
@app.route('/get_latest', methods=['GET'])
def get_latest():
    latest_block = node.blockchain.get_latest_block()
    # json_str = json.dumps(latest_block.reprJSON(), cls=json_helper.ComplexEncoder)
    response = {
        "message": "Success, return my latest block",
        "latest_block": latest_block
    }
    data = json.dumps(response, default=lambda x: getattr(x, '__dict__', str(x)))
    return data, 200


# api for receiving latest block
@app.route('/receive_new', methods=['POST'])
def receive_new():
    # json from node to API
    data = request.get_json()
    message = data['message']
    print(f"{datetime.datetime.now()}: {message}")
    blk_json_str = data['new_block']
    blk_json = json.loads(blk_json_str)
    success, message, situation = node.handle_new_block(blk_json)
    if success:
        response = {
            'message': message,
            'status': 'success',
            'situation': situation
        }
    else:  # inform source node for invalid block, source node triggers longest valid chain rule
        response = {
            'message': message,
            'status': 'failed',
            'situation': situation

        }
    data = json.dumps(response, default=lambda x: getattr(x, '__dict__', str(x)))
    return data, 200


# may needs update
@app.route('/chain', methods=['GET'])
def get_chain():
    chain = node.blockchain.block_chain
    response = {
        "status": "Success",
        "message": f"retrieved chain from peer{config.PORT}",
        "latest_chain": chain,
    }
    data = json.dumps(response, default=lambda x: getattr(x, '__dict__', str(x)))
    return data, 200


# receive new transaction from
@app.route('/receive_transaction', methods=["POST"])
def receive_transaction():
    data = request.get_json()
    message = data['message']
    print(f"{datetime.datetime.now()}: {message}")
    tx_json_str = data["new_transaction"]
    tx_json = json.loads(tx_json_str)
    node.handle_transaction(tx_json)
    return "ok", 200


# endregion

# region User Interaction API

# goal 3: initialize transaction
@app.route('/send_transaction', methods=["POST"])
def send_transaction():
    data = request.get_json()
    required_field = ["recipient", "amount"]
    if not all(k in data for k in required_field):
        return json.dumps({'message': 'format is wrong, please retry'},
                          default=lambda x: getattr(x, '__dict__', str(x))), 400

    recipient = data['recipient']
    amount = data['amount']
    success, message = node.send_transaction(recipient, amount)

    if not success:
        response = {
            "message": message
        }
    else:
        response = {
            "message": f"Transaction to {recipient} is created successfully."
        }
    return response, 200


# goal 2: mine a block in this node
@app.route('/mine', methods=["POST"])
def mine():
    print("start mining")
    success, blk = node.blockchain.mine()
    if success:
        node.broadcast_blocks(blk)
        response = {
            "status": "Success",
            "message": "You have successfully mined a block, you earned 50 coins!",
            "balance": node.blockchain.balance,
            "address": node.blockchain.address
        }
    else:
        print(f"{datetime.datetime.now()}: mining failed.")
        print("Mining failed")
        response = {
            "status": "Failed",
            "message": "Failed to mine a new block, something wrong with the chain",
            "address": node.blockchain.address
        }
    return response, 200

# goal 4: control node to join the network -
@app.route('/join', methods=["POST"])
def join_network():
    if config.PORT == config.KNOWN_CENTER_PORT:
        response = {
            "status": "Skipped",
            "message": f"Node {config.PORT} is already in the network",
        }
        return response, 202
    else:
        # find peer list from known center node
        result = node.connect_to_peer(config.KNOWN_CENTER_NODE_IP, config.KNOWN_CENTER_PORT)
        if result:
            response = {
                "status": "Success",
                "message": f"Node {config.PORT} has connected",
            }
            return response, 202
        else:
            response = {
                "status": "Failed",
                "message": f"Node {config.PORT} already in the network",
            }
            return response, 409
# endregion

# region Testing API
@app.route('/show_wallet', methods=["GET"])
def show_wallet():
    balance = node.blockchain.balance
    address = node.blockchain.address
    nodeinfo = f'{node.id} {node.ip}'
    response = {
        "nodeinfo": nodeinfo,
        "balance:": balance,
        "address": address
    }
    return response, 200


# show block infos of blockchain
@app.route('/get_blocks_infos', methods=["GET"])
def get_blocks_infos():
    blocks = []
    for block in node.blockchain.block_chain:
        ignore = ['transactions']
        block_params = {x: block.__dict__[x] for x in block.__dict__ if x not in ignore}
        blocks.append(block_params)

    response = {
        "Number of blocks": len(node.blockchain.block_chain),
        "Blocks": blocks
    }
    return response, 200


# show tx infos of unconfirmed pool
@app.route('/get_txs_infos', methods=["GET"])
def get_tx_infos():
    txs = []
    for tx in node.blockchain.unconfirmed_transactions:
        txs.append(tx.save_as_json())
    response = {
        "Number of transactions": len(node.blockchain.unconfirmed_transactions),
        "Transactions": txs
    }
    return response, 200


# show utxo infos
@app.route('/get_utxo_infos', methods=["GET"])
def get_utxo_infos():
    records = []
    for record in node.blockchain.utxo:
        new_record = []
        new_record.append(record[0])
        txouts_json = []
        for tx_out in record[1]:
            tx_out_json = tx_out.save_as_json()
            txouts_json.append(tx_out_json)

        new_record.append(txouts_json)
        new_record.append(record[2])
        records.append(new_record)

    response = {
        "Number of utxos": len(node.blockchain.utxo),
        "UTXOs": records
    }
    return response, 200


@app.route('/test/peer', methods=['GET'])
def get_peer_info():
    message = {'peers': node.peers}
    return message, 200


@app.route('/test/show_address', methods=['GET'])
def show_address():
    message = {
        # 'private_key': node.blockchain.private_key,
        'address': node.blockchain.address
    }
    return message, 200


@app.route('/test/utxo', methods=['GET'])
def get_utxo():
    utxo = node.blockchain.utxo
    # pkl = pickle.dumps(utxo)
    json_str = json.dumps(utxo, default=lambda x: getattr(x, '__dict__', str(x)))
    message = {
        'uxto': json_str
    }
    return message, 200


@app.route('/test/to_block', methods=['POST'])
def attempt_to_block():
    blk = node.blockchain.block_chain[-1]
    json_str = json.dumps(blk, default=lambda x: getattr(x, '__dict__', str(x)))
    nde = node
    app = json.loads(json_str)

    block = to_block(app)
    b = block.calculate_block_hash()
    current_hash = blk.curr_hash
    cal_current_hash = blk.calculate_block_hash()
    return "ok", 200


# demo for goal 1.
@app.route('/test/display_block', methods=['GET'])
def display_last_block():
    blk = node.blockchain.block_chain[-1]
    message = {
        "block": blk
    }
    json_str = json.dumps(message, default=lambda x: getattr(x, '__dict__', str(x)))

    return json_str, 200


@app.route('/test/remove_last_block', methods=['POST'])
def remove_last_block():
    node.remove_last_block()
    message = {
        "warning": "This method is for testing and demo. Do not use in normal operation",
        "message": "last block is removed from chain"
    }
    return message, 200

# endregion

import json

from DAL.connection import utxo_db, blockchain_db, transaction_file
from Transaction.transaction_input import TX_IN
from Transaction.transaction_output import TX_OUT

L1_SPILTER = "/split1/"
L2_SPLITER = "/split2/"


#  region goal 5: --- redis use ---
# update UTXOs in redis
def update_utxo(utxos=[]):
    reset_redis()
    for record in utxos:
        save_utxo(record)
    return


def save_utxo(record=[]):
    id = record[0]
    str_txouts = ""
    str_flags = ""
    for tx_out, flag in zip(record[1], record[2]):
        str_txouts = str_txouts + tx_out.get_content() + L1_SPILTER
        str_flags = str_flags + str(flag) + L1_SPILTER

    str_data = id + L2_SPLITER + str_txouts + L2_SPLITER + str_flags
    utxo_db.rpush("utxo", str_data)
    return record


def load_utxo():
    len = utxo_db.llen("utxo")
    utxo = []
    for index in range(len):
        str_data = utxo_db.lindex("utxo", index).decode('utf-8')
        id, str_txouts, str_flags = str_data.split(L2_SPLITER)
        str_txouts = str_txouts.split(L1_SPILTER)[0: -1]
        str_flags = str_flags.split(L1_SPILTER)[0: -1]

        txouts = []
        flags = []

        for str_txout, str_flag in zip(str_txouts, str_flags):
            txout = TX_OUT()
            txout.load_from_str_json(str_txout)
            txouts.append(txout)

            flags.append(False if str_flag == "False" else True)

        record = [id, txouts, flags]
        utxo.append(record)

    return utxo


def reset_redis():
    for key in utxo_db.keys():
        utxo_db.delete(key)
    return


# endregion

# region goal 5: --- transaction file use ---
def update_transaction_records(txs):
    txs_json = json.dumps(txs, default=lambda x: getattr(x, '__dict__', str(x)))
    with open(transaction_file, 'w') as fp:
        fp.write(txs_json)


def load_transaction_records():
    with open(transaction_file, 'r') as fp:
        trans_jsons = fp.read()

    return trans_jsons


# load a transaction from Tx pool
""" def load_from_pool(tx_id):
    tx = Transaction()
    tx.id = tx_id
    tx.tx_ins = []
    tx.tx_outs = []
    
    data = transaction_pool.get(tx_id).decode('utf-8')
    tx_ins_str, tx_outs_str = data.split(L2_SPLITER)
    
    if tx_ins_str != "":
        tx_ins_str = tx_ins_str.split(L1_SPILTER)[0:-1]
        for tx_in_str in tx_ins_str:
            tx_in = TX_IN()
            tx_in.load_from_str_json(tx_in_str)
            tx.tx_ins.append(tx_in)
        
    if tx_outs_str != "":
        tx_outs_str = tx_outs_str.split(L1_SPILTER)[0:-1]
        for tx_out_str in tx_outs_str:
            tx_out = TX_OUT()
            tx_out.load_from_str_json(tx_out_str)
            tx.tx_outs.append(tx_out)
    
    return tx """


# endregion

# region goal 5: --- mongo use ----
def get_mongo_len():
    return blockchain_db.count_documents()


def reset_mongo():
    blockchain_db.drop()
# endregion

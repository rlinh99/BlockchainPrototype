import os
import config
import pymongo
import redis

# goal 5: set up connection for 3 types of storage.
# database connection configuration
db_name = config.MONGODB_NAME
db_client = pymongo.MongoClient(config.CONNECTION_STR)
my_db = db_client[db_name]
blockchain_db = my_db[config.MONGO_COLLECTION]
utxo_db = redis.StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB_NUMBER)
script_dir = os.path.dirname(__file__)
transaction_file = os.path.join(script_dir, 'transactions.json')


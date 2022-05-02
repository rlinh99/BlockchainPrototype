# testing environment is in same pc, only use port for identification purpose
PORT = 3456

# 1 for center node, 0 otherwise
IS_CENTER = 1

# known active node.
KNOWN_CENTER_NODE_IP = '127.0.0.1'

KNOWN_CENTER_PORT = 3456  # in blockchain system, there should be a known active node

COINBASE_AMOUNT = 50

DIFFICULTY_ADJUSTMENT_INTERVAL = 5

BLOCK_GENERATION_INTERVAL = 60  # in minute

# db configs
MONGODB_NAME = "blockchain_test"

MONGO_COLLECTION = "blockchain_test_1"

CONNECTION_STR = "mongodb://localhost:27017/"

REDIS_HOST = "localhost"

REDIS_PORT = 6379

REDIS_DB_NUMBER = 0

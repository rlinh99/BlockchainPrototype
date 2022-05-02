from bitstring import BitArray

#  goal 2: mining algorithm
def hash_matches_difficulty(hash_value: str, difficulty: int) -> bool:
    c = BitArray(hex=hash_value)
    result = c.bin[2:]
    prefix = '0' * difficulty
    return result.startswith(prefix)

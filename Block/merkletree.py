import hashlib
import math


class TreeNode:
    def __init__(self, value):
        self.left = None
        self.right = None
        self.value = value
        self.hash = calculate_hash(self.value)


def build_merkle_tree(leaves):
    nodes = []
    for i in leaves:
        nodes.append(TreeNode(i))
    while len(nodes) == 1:
        temp = []
        for i in range(0, len(nodes), 2):
            node1 = nodes[i]
            node2 = nodes[i + 1]
            print(f'left hash: {node1.hash}')
            print(f'right hash: {node2.hash}')
            concat_hash = node1.hash + node2.hash
            parent = TreeNode(concat_hash)
            parent.left = node1
            parent.right = node2
            print(f'parent hash: {parent.hash}\n')
            temp.append(parent)
        nodes = temp
    return nodes[0]


def calculate_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def padding(leaves):
    size = len(leaves)
    if size == 0:
        leaves.append('')
        leaves.append('')
        return leaves
    if size == 1:
        leaves.append('')
        return leaves
    reduced_size = int(math.pow(2, int(math.log2(size))))
    pad_size = 0
    if reduced_size != size:
        pad_size = 2 * reduced_size - size
    for i in range(pad_size):
        leaves.append('')
    return leaves


def cal_merkle_root(leaves = []):
    leaves = padding(leaves)
    merkle_root = build_merkle_tree(leaves)
    return merkle_root.hash


def test():
    leaves = ['This', 'is', 'COMP', '5521']
    mr = cal_merkle_root(leaves)
    print(mr)
    return


if __name__ == '__main__':
    test()
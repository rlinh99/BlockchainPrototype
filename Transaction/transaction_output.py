import json

# goal 3 - transaction out class
class TX_OUT:
    def __init__(self, address = '', amount = -1):
        # address, aka - Public Key Hash
        self.address = address
        # amount in the output
        self.amount = amount


    def reprJSON(self):
        return self.__dict__


    # region goal 5: --- redis ---
    def get_content(self):
        temp = []
        params = {x: self.__dict__[x] for x in self.__dict__ if x not in temp}
        string = json.dumps(params, sort_keys=True)
        return string
    
    
    def load_from_str_json(self, str_json):
        dic = json.loads(str_json)
        self.address = dic["address"]
        self.amount = dic["amount"]
        return
    # endregion
    
    # region goal 5: --- mongo ---
    def save_as_json(self):
        dict = {
            "address": self.address,
            "amount": self.amount
        }
        return dict
    
    
    def load_from_json(self, dict):
        self.address = dict["address"]
        self.amount = dict["amount"]
        return
    
    
    def display(self):
        print("< -- Transaction output information -- >")
        print("< address:", self.address)
        print("< amount:", self.amount)
        return
    # endregion



from json import JSONEncoder


class Encoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

class ComplexEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'reprJSON'):
            return obj.reprJSON()
        else:
            return JSONEncoder.default(self, obj)
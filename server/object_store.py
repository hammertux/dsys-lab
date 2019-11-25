import uuid

class ObjectStore:
  def __init__(self):
    self.objects = {}
  
  def add(self, obj):
    uuid_value = uuid.uuid4() # UUID4 generates a random UUID
    self.objects[uuid_value] = obj
    return uuid_value
  
  def retrieve(self, uuid):
    return self.objects[uuid]

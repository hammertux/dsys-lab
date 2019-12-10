from .consistency_requirement import ConsistencyRequirement
from threading import Condition
class OrderError(Exception):
  pass

class OrderErrorLimiter(ConsistencyRequirement):
  def __init__(self, max_order_error):
    self.max_order_error = max_order_error
    self.last_commit_number = None
    self.last_commit_number_condition = Condition()
  
  def set_maximum(self, max_order_error):
    self.max_order_error = max_order_error
  
  def calculate_order_error(self, write):
    if self.last_commit_number is None:
      return 0
    return self.last_commit_number - write.last_commit_number_received_by_sender

  def can_commit(self, write):
    return self.calculate_order_error(write) < self.max_order_error

  def perform_commit(self, write, timeout, commit_function):
    if not self.can_commit(write):
      raise OrderError
    commit_function(write)
    self.last_commit_number = write.commit_number
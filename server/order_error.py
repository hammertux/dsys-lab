from .consistency_requirement import ConsistencyRequirement
from threading import Condition
import os
import csv
import time

class OrderError(Exception):
  pass

class OrderErrorLimiter(ConsistencyRequirement):
  def __init__(self, max_order_error):
    self.max_order_error = max_order_error
    self.last_commit_number = None
    self.last_commit_number_condition = Condition()
    self.pid = str(os.getpid())
  
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
    self.log_order_error(write)
    commit_function(write)
    self.last_commit_number = write.commit_number

  def log_order_error(self, write):
    with open('./logs/server_errors_' + self.pid + '.csv', 'a', newline='') as file:
      logger = csv.writer(file)
      ### type: 0 = staleness received, 1 = staleness sending, 2 = numerical, 3 = order
      logger.writerow([time.time(), self.calculate_order_error(write), 3])

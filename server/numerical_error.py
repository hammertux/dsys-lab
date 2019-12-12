from .consistency_requirement import ConsistencyRequirement, CommitTooLate
from threading import Condition
import os
import csv
import time

class NumericalError(Exception):
  pass
class NumericalErrorLimiter(ConsistencyRequirement):
  def __init__(self, max_numerical_error):
    self.pid = str(os.getpid())
    # the current numerical error
    self.numerical_error = 0
    self.log_numerical_error()
    # the maximum numerical error allowed
    self.max_numerical_error = max_numerical_error
    self.at_maximum_condition = Condition()

  def set_maximum(self, max_numerical_error):
    with self.at_maximum_condition:
      old_max_numerical_error = max_numerical_error
      self.max_numerical_error = max_numerical_error
      if max_numerical_error > old_max_numerical_error:
        self.at_maximum_condition.notify(max_numerical_error - old_max_numerical_error)

  def not_at_maximum(self):
    return self.numerical_error < self.max_numerical_error

  def __increment_numerical_error(self):
    self.numerical_error += 1
    self.log_numerical_error()

  def log_numerical_error(self):
    with open('./logs/server_errors_' + self.pid + '.csv', 'a', newline='') as file:
      logger = csv.writer(file)
      ### type: 0 = staleness received, 1 = staleness sending, 2 = numerical, 3 = order
      logger.writerow([time.time(), self.numerical_error, 2])

  def perform_commit(self, write, timeout, commit_function):
    with self.at_maximum_condition:
      if self.not_at_maximum():
        commit_function(write)
        self.__increment_numerical_error()
        return
      elif self.at_maximum_condition.wait_for(self.not_at_maximum, timeout):
        try:
          commit_function(write)
          self.__increment_numerical_error()
          return
        except CommitTooLate:
          raise NumericalError
      else:
        raise NumericalError

  def decrease_numerical_error_by(self, amount = 1):
    if amount < 0:
      raise ValueError("Amount cannot be negative")
    if amount == 0:
      return
    with self.at_maximum_condition:
      self.numerical_error -= amount
      self.log_numerical_error()
      self.at_maximum_condition.notify(min(amount, self.max_numerical_error - self.numerical_error))

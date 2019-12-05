from threading import Event, Thread
from time import time

"""Timer that is guaranteed to run after the specified deadline (and not before)"""
class DeadlineTimer(Thread):
  def __init__(self, deadline, function):
    self.deadline = deadline
    self.is_cancelled_event = Event()
    self.function = function
  
  def cancel(self):
    self.is_cancelled_event.set()
  
  def run(self):
    while not self.is_cancelled_event.is_set() and time() < self.deadline:
      self.is_cancelled_event.wait(self.deadline - time())
    self.function()

from threading import Lock, RLock, Thread, Event
from queue import deque
from time import time
from .deadline_timer import DeadlineTimer

class Acknowledgeable:
  def __init__(self):
    self.is_acknowledged = False
    self.auto_acknowledge_time = None
    self.timer = None
    self.lock = Lock()
    self.after_acknowledge = lambda : None
  
  def acknowledge(self):
    self.is_acknowledged = True
    if self.timer is not None:
      self.timer.cancel()
    self.after_acknowledge()
  
  def set_on_auto_acknowledge(self, function):
    self.__on_auto_acknowledge = function
  
  def set_auto_acknowledge(self, auto_acknowledge_time):
    with self.lock:
      if self.auto_acknowledge_time is not None and auto_acknowledge_time < self.auto_acknowledge_time:
        return
      self.auto_acknowledge_time = auto_acknowledge_time
    if not self.is_acknowledged:
      self.timer = DeadlineTimer(auto_acknowledge_time, self.__on_auto_acknowledge)
      self.timer.start()

class MultiAcknowledgeable(Acknowledgeable):
  def __init__(self, acknowledgements_needed):
    Acknowledgeable.__init__(self)
    self.acknowledgements_needed = acknowledgements_needed
    self.acknowledgements_received = 0
    self.lock = Lock()
  
  def acknowledge(self):
    with self.lock:
      self.acknowledgements_received += 1
      if self.acknowledgements_received >= self.acknowledgements_needed:
        Acknowledgeable.acknowledge(self)

class ProxyAcknowledgeable(Acknowledgeable):
  def __init__(self, inner_acknowledgeable):
    Acknowledgeable.__init__(self)
    self.__inner_acknowledgeable = inner_acknowledgeable
  
  def acknowledge(self):
    if self.is_acknowledged:
      return
    Acknowledgeable.acknowledge(self)
    self.__inner_acknowledgeable.acknowledge()

class AcknowledgementTracker:
  def __init__(self):
    self.lock = RLock()
    self.unacknowledged_count = 0
    self.acknowledged_count = 0
    self.queue = deque()
  
  def add_unacknowledged(self, acknowledgeable):
    with self.lock:
      acknowledgeable.set_on_auto_acknowledge(self.do_auto_acknowledge)
      self.unacknowledged_count += 1
      self.queue.append(acknowledgeable)
  
  def _after_acknowledge(self, count):
    pass

  def _do_acknowledge(self):
    if len(self.queue) == 0:
      raise ValueError("Too many acknowledgements")
    self.queue[0].acknowledge()
    if self.queue[0].is_acknowledged:
      self.__update_stats()
  
  def acknowledge(self):
    with self.lock:
      old_unacknowledged_count = self.unacknowledged_count
      self._do_acknowledge()
      new_unacknowledged_count = self.unacknowledged_count
      self._after_acknowledge(old_unacknowledged_count - new_unacknowledged_count)
  
  def __update_stats(self):
    while len(self.queue) > 0 and self.queue[0].is_acknowledged:
      self.queue.popleft()
      self.unacknowledged_count -= 1
      self.acknowledged_count += 1
    
  def on_acknowledge(self):
    with self.lock:
      old_unacknowledged_count = self.unacknowledged_count
      self.__update_stats()
      new_unacknowledged_count = self.unacknowledged_count
      self._after_acknowledge(old_unacknowledged_count - new_unacknowledged_count)
  
  def do_auto_acknowledge(self):
    with self.lock:
      old_unacknowledged_count = self.unacknowledged_count
      while len(self.queue) > 0:
        first = self.queue[0]
        if first.auto_acknowledge_time is None or first.auto_acknowledge_time > time():
          return
        self._do_acknowledge()
      new_unacknowledged_count = self.unacknowledged_count
      self._after_acknowledge(old_unacknowledged_count - new_unacknowledged_count)

  def set_auto_acknowledge(self, acknowledgeable, time):
    acknowledgeable.set_auto_acknowledge(time)

  def acknowledge_upto(self, new_acknowledged_count):
    if new_acknowledged_count <= self.acknowledged_count:
      return
    with self.lock:
      while new_acknowledged_count > self.acknowledged_count:
        self._do_acknowledge()

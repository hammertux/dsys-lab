import os
import subprocess
import time
from threading import Thread

def get_load():
  pid = str(os.getpid())
  try:
    # Run top
    cmd = subprocess.Popen('top -p ' + pid + ' -n1', shell=True, stdout=subprocess.PIPE)
    # Parse the output
    for line in cmd.stdout:
      d = line.decode('UTF-8')
      if pid in d:
          d_s = d.split()
          index = d_s.index('python3')
          cpu = d_s[index - 3]
          ram = d_s[index - 2]
          break
    cpu = float(cpu.replace(',', '.'))
    ram = float(ram.replace(',', '.'))
  except:
    print('load not working')
    return 1
  return (cpu + ram)  / 2

class ThreadConfiguration:
  def __init__(self, max_numerical_error, max_order_error, max_staleness, session_length = None, session_refresh_time = None):
    self.max_numerical_error = max_numerical_error
    self.max_order_error = max_order_error
    self.max_staleness = max_staleness
    self.session_length = session_length if session_length is not None else self.max_staleness
    if self.session_length > self.max_staleness:
      raise ValueError("Session length cannot be longer than max staleness")
    self.session_refresh_time = session_refresh_time if session_refresh_time is not None else (self.session_length // 2)
    if self.session_refresh_time > self.session_length:
      raise ValueError("Session refresh time cannot be longer than the session length")
  
  def copy(self):
    return ThreadConfiguration(self.max_numerical_error, self.max_order_error, self.max_staleness, self.session_length, self.session_refresh_time)

  @staticmethod
  def get_default(cls):
    return ThreadConfiguration(100, 10, 10, 10, 5)

class ThreadConfigurationFactory:
  def __init__(self, configuration):
    self.__configuration = configuration
  
  def get_configuration(self):
    return self.__configuration

class LoadThresholdThreadConfigurationFactory:
  def __init__(self, normal_configuration, threshold, high_load_configuration):
    self.normal_configuration = normal_configuration
    self.threshold = threshold
    self.high_load_configuration = high_load_configuration
  
  def get_configuration(self):
    return self.normal_configuration if get_load() < self.threshold else self.high_load_configuration

class DoubleErrorUnderLoadThreadConfigurationFactory(LoadThresholdThreadConfigurationFactory):
  def __init__(self, normal_configuration, threshold):
    self.normal_configuration = normal_configuration
    self.threshold = threshold
    self.high_load_configuration = ThreadConfiguration(
      normal_configuration.max_numerical_error * 2,
      normal_configuration.max_order_error * 2,
      normal_configuration.max_staleness * 2,
      normal_configuration.session_length * 2,
      normal_configuration.session_refresh_time * 2
    )
  
  def get_configuration(self):
    return self.normal_configuration if get_load() < self.threshold else self.high_load_configuration

class ThreadConfigurationPolicy:
  def __init__(self, thread_configuration):
    self.__thread_configuration = thread_configuration
  
  def get_configuration(self):
    return self.__thread_configuration

  def add_on_change(self, on_change):
    pass

class FixedIntervalFactoryThreadConfigurationPolicy(ThreadConfigurationPolicy):
  def __init__(self, interval, thread_configuration_factory):
    self.interval = interval
    self.thread_configuration_factory = thread_configuration_factory
    self.__thread_configuration = thread_configuration_factory.get_configuration()
    self.__listeners = []
    def run_on_change():
      while True:
        time.sleep(self.interval)
        if self.thread_configuration_factory.get_configuration() != self.__thread_configuration:
          self.__thread_configuration = self.thread_configuration_factory.get_configuration()
          for listener in self.__listeners.copy():
            listener(self.get_configuration())
    Thread(target=run_on_change).start()

  def get_configuration(self):
    return self.__thread_configuration

  def add_on_change(self, on_change):
    self.__listeners.append(on_change)
    
class SimpleLoadBasedThreadConfigurationPolicy(FixedIntervalFactoryThreadConfigurationPolicy):
  def __init__(self, interval, load_threshold, thread_configuration):
    FixedIntervalFactoryThreadConfigurationPolicy.__init__(self, interval, DoubleErrorUnderLoadThreadConfigurationFactory(thread_configuration, load_threshold))

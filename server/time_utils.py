import time
def current_server_time():
  return int(round(time.time() * 1000 * 1000))
def to_python_time(time):
  return time / (1000 * 1000)
import time
def current_server_time():
  return int(round(time.time() * 1000 * 1000))
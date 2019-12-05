from queue import Full
class QueueGenerator:
  def __init__(self, queue):
    self.queue = queue
  
  """This method should only be called once per queue."""
  def generate(self):
    while True:
      yield self.queue.get()

class StoppableQueueGenerator(QueueGenerator):
  def __init__(self, queue):
    QueueGenerator.__init__(self, queue)
    self.should_stop = False
  
  def stop(self):
    self.should_stop = True

    # make sure there is something in the queue
    try:
      self.queue.put_nowait(None)
    except Full:
      pass

  def generate(self):
    for item in QueueGenerator.generate(self):
      if self.should_stop:
        break
      yield item

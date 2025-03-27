import queue
import threading

from src.backend.jobs import IJob


class JobRunner:

    def __init__(self):
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def work(self):
        while True:
            job: IJob = self.queue.get()  # blocking
            job.run()
            self.queue.task_done()  # tells the queue that next item can be processed

    def push(self, job: IJob):
        self.queue.put(job)

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
            print("waiting for new job")
            job: IJob = self.queue.get()  # blocking
            print(f"worker took job #{job.id}")
            job.run()
            print(f"job #{job.id} completed")
            self.queue.task_done()  # tells the queue that next item can be processed

    def push(self, job: IJob):
        self.queue.put(job)

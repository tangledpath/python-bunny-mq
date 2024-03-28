import queue
import signal
from threading import Thread, Event
from typing import Dict, Any, Callable

from loguru import logger

class BunnyMQ(Thread):
    """
    Lightweight message queue for intra-process pub-sub communication.

    Usage:
    ```
    def foo_handler(message):
        print(f"Message: {message}")

    bunny = BunnyMQ(interval=0.1)
    try:
        bunny.register_handler("foo", foo_handler)
        bunny.start()
        bunny.send_message(type='foo', body="foobar")
        time.sleep(1)
    finally:
        bunny.stop()
    ```
    """
    def __init__(self, interval=0.5):
        """
        Constructs a new BunnyMQ
        :param interval: Interval in seconds between processing messages:
        """
        Thread.__init__(self)
        self.queue = queue.Queue()
        self.handlers: Dict[str, Callable] = {}
        self.interval = interval
        self.stopped = Event()

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """
        Registers a handler for given message_typ
        :param message_type: The message type
        :param handler: The callable to register; this will be passed the messag
        """
        logger.info(f"Registering handler for {message_type}")
        self.handlers[message_type] = handler

    def execute(self):
        """
        Begin execution of the queue.  this starts the underlying thread, which
        will call `run`.  It also registers handlers for SIGTERM and SIGINT, so we
        can cleanly shut down:
        """
        signal.signal(signal.SIGTERM, self.__signal_shutdown)
        signal.signal(signal.SIGINT, self.__signal_shutdown)
        self.start()


    def run(self):
        """ This is the underlying Thread's run method; called via `execute->start` """
        while not self.stopped.wait(self.interval):
            self.handle_message()

    def handle_message(self):
        """
        Handles the next message from the queue; calling any registered
        handlers with the message
        """
        try:
            message: Dict[str] = self.queue.get(block=False)
            logger.info(f"Received message: {message}")
            message_type = message["type"]
            handler = self.handlers.get(message_type, None)
            handler(message)
        except queue.Empty:
            pass

    def stop(self):
        """ Stop processing messages and shuts down the queue. """
        logger.info(f"Stopping queue with: {self.queue.qsize()} items left.")
        self.stopped.set()
        self.join(self.interval)

    def send_message(self, **message: Dict[str, Any]):
        """ Stores a message in the queue, to processed by any registered handlers"""
        logger.info(f"Sending message: {message}")
        self.queue.put(message)

    def __signal_shutdown(self, _signum, _frame):
        """ Called because of a SIGTERM or SIGINT signal"""
        self.stop()

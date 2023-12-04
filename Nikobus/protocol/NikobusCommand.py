from java.util.concurrent import Callable
from java.util.concurrent.atomic import AtomicBoolean
from java.util.function import Consumer
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.slf4j import Logger, LoggerFactory

@NonNullByDefault
class NikobusCommand:
    class Result:
        def __init__(self, result):
            self.callable = lambda: result

        def __init__(self, exception):
            self.callable = lambda: exception

        def get(self):
            return self.callable()

    class ResponseHandler:
        def __init__(self, response_length, address_start, response_code, result_consumer):
            self.logger = LoggerFactory.getLogger(ResponseHandler)
            self.result_consumer = result_consumer
            self.response_length = response_length
            self.address_start = address_start
            self.response_code = response_code
            self.is_completed = AtomicBoolean()

        def is_completed(self):
            return self.is_completed.get()

        def complete(self, result):
            if self.is_completed.getAndSet(True):
                return False

            try:
                self.result_consumer.accept(result)
            except RuntimeException as e:
                self.logger.warn("Processing result {} failed with {}".format(result, e.getMessage()), e)

            return True

        def complete_exceptionally(self, exception):
            return self.complete(NikobusCommand.Result(exception))

        def get_response_length(self):
            return self.response_length

        def get_address_start(self):
            return self.address_start

        def get_response_code(self):
            return self.response_code

    def __init__(self, payload, response_length=None, address_start=None, response_code=None, result_consumer=None):
        self.payload = payload + '\r'
        if response_length is not None:
            self.response_handler = NikobusCommand.ResponseHandler(response_length, address_start, response_code, result_consumer)
        else:
            self.response_handler = None

    def get_payload(self):
        return self.payload

    def get_response_handler(self):
        return self.response_handler

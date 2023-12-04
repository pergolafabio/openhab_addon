from typing import Callable, List, Union

class NikobusPcLinkHandler(BaseBridgeHandler):
    def __init__(self, bridge, serial_port_manager):
        super().__init__(bridge)
        self.logger = LoggerFactory.getLogger(NikobusPcLinkHandler.__class__)
        self.command_listeners = {}
        self.pending_commands = []
        self.string_builder = StringBuilder()
        self.serial_port_manager = serial_port_manager
        self.connection = None
        self.current_command = None
        self.scheduled_refresh_future = None
        self.scheduled_send_command_watchdog_future = None
        self.ack = None
        self.unhandled_commands_processor = None
        self.refresh_thing_index = 0

    def initialize(self):
        self.ack = None
        self.string_builder.setLength(0)

        self.update_status(ThingStatus.UNKNOWN)

        port_name = self.get_config().get(NikobusBindingConstants.CONFIG_PORT_NAME)
        if not port_name:
            self.update_status(ThingStatus.OFFLINE, ThingStatusDetail.OFFLINE.CONFIGURATION_ERROR, "Port must be set!")
            return

        self.connection = NikobusConnection(self.serial_port_manager, port_name, self.process_received_value)

        refresh_interval = int(self.get_config().get(CONFIG_REFRESH_INTERVAL))
        self.scheduled_refresh_future = scheduler.schedule_with_fixed_delay(self.refresh, refresh_interval, refresh_interval,
                                                                           TimeUnit.SECONDS)

    def dispose(self):
        super().dispose()

        Utils.cancel(self.scheduled_send_command_watchdog_future)
        self.scheduled_send_command_watchdog_future = None

        Utils.cancel(self.scheduled_refresh_future)
        self.scheduled_refresh_future = None

        connection = self.connection
        self.connection = None

        if connection:
            connection.close()

    def handle_command(self, channel_uid, command):
        # Noop.
        pass

    def get_services(self):
        return {NikobusDiscoveryService}

    def process_received_value(self, value):
        self.logger.trace("Received {}".format(value))

        if value == 13:
            command = self.string_builder.toString()
            self.string_builder.set_length(0)

            self.logger.debug("Received command '{}', ack = '{}'".format(command, self.ack))

            try:
                if command.startswith("$"):
                    ack = self.ack
                    self.ack = None

                    self.process_response(command, ack)
                else:
                    listener = self.command_listeners.get(command)
                    if listener:
                        listener.run()
                    else:
                        processor = self.unhandled_commands_processor
                        if processor:
                            processor.accept(command)
            except Exception as e:
                self.logger.debug("Processing command '{}' failed due {}".format(command, e.message), e)
        else:
            self.string_builder.append(chr(value))

            # Take ACK part, i.e. "$0512"
            if len(self.string_builder) == 5:
                payload = self.string_builder.toString()
                if payload.startswith("$05"):
                    self.ack = payload
                    self.logger.debug("Received ack '{}'".format(self.ack))
                    self.string_builder.set_length(0)
            elif len(self.string_builder) > 128:
                # Fuse, if for some reason we don't receive \r don't fill buffer.
                self.string_builder.set_length(0)
                self.logger.warn("Resetting read buffer, should not happen, am I connected to Nikobus?")

    def add_listener(self, command, listener):
        if self.command_listeners.put(command, listener):
            self.logger.warn("Multiple registrations for '{}'".format(command))

    def remove_listener(self, command):
        self.command_listeners.pop(command, None)

    def set_unhandled_command_processor(self, processor):
        if self.unhandled_commands_processor:
            self.logger.debug("Unexpected override of unhandled_commands_processor")
        self.unhandled_commands_processor = processor

    def reset_unhandled_command_processor(self):
        self.unhandled_commands_processor = None

    def process_response(self, command_payload, ack):
        command = None
        with self.pending_commands:
            command = self.current_command

        if not command:
            self.logger.debug("Processing response but no command pending")
            return

        response_handler = command.get_response_handler()
        if not response_handler:
            self.logger.debug("No response expected for current command")
            return

        if not ack:
            self.logger.debug("No ack received")
            return

        request_command_id = command.get_payload()[3:5]
        ack_command_id = ack[3:5]
        if ack_command_id != request_command_id:
            self.logger.debug("Unexpected command's ack '{}' != '{}'".format(request_command_id, ack_command_id))
            return

        # Check if response has expected length.
        if len(command_payload) != response_handler.get_response_length():
            self.logger.debug("Unexpected response length")
            return

        if not command_payload.startswith(response_handler.get_response_code()):
            self.logger.debug("Unexpected response command code")
            return

        request_command_address = command.get_payload()[5:9]
        ack_command_address = command_payload[response_handler.get_address_start():
                                              response_handler.get_address_start() + 4]
        if request_command_address != ack_command_address:
            self.logger.debug("Unexpected response address")
            return

        if response_handler.complete(command_payload):
            self.reset_processing_and_process_next()

    def send_command(self, command):
        with self.pending_commands:
            self.pending_commands.append(command)

        scheduler.submit(self.process_command)

    def process_command(self):
        command = None
        with self.pending_commands:
            if self.current_command:
                return

            command = self.pending_commands.pop(0)
            if not command:
                return

            self.current_command = command

        self.send_command(command, 3)

    def send_command(self, command, retry):
        self.logger.debug("Sending retry = {}, command '{}'".format(retry, command.get_payload()))

        connection = self.connection
        if not connection:
            return

        try:
            self.connect_if_needed(connection)

            output_stream = connection.get_output_stream()
            if not output_stream:
                return

            output_stream.write(command.get_payload().encode())
            output_stream.flush()
        except IOException as e:
            self.logger.debug("Sending command failed due {}".format(e.message), e)
            connection.close()
            self.update_status(ThingStatus.OFFLINE, ThingStatusDetail.COMMUNICATION_ERROR, e.message)
        finally:
            response_handler = command.get_response_handler()
            if not response_handler:
                self.reset_processing_and_process_next()
            elif retry > 0:
                self.schedule_send_command_timeout(
                    lambda: self.send_command(command, retry - 1)
                )
            else:
                self.schedule_send_command_timeout(
                    lambda: self.process_timeout(response_handler)
                )

    def schedule_send_command_timeout(self, command):
        self.scheduled_send_command_watchdog_future = scheduler.schedule(command, 2, TimeUnit.SECONDS)

    def process_timeout(self, response_handler):
        if response_handler.complete_exceptionally(TimeoutException("Waiting for response timed-out.")):
            self.reset_processing_and_process_next()

    def reset_processing_and_process_next(self):
        Utils.cancel(self.scheduled_send_command_watchdog_future)
        with self

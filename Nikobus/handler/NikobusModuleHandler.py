from java.util import EnumSet
from java.util.concurrent import HashMap, HashSet, Map, Future, TimeUnit
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.openhab.binding.nikobus.internal.protocol import NikobusCommand, SwitchModuleCommandFactory, SwitchModuleGroup
from org.openhab.core.thing import Channel, ChannelUID, ThingStatus, ThingStatusDetail
from org.openhab.core.types import Command, RefreshType, State
from org.slf4j import Logger, LoggerFactory

@NonNullByDefault
class NikobusModuleHandler(NikobusBaseThingHandler):
    def __init__(self, thing):
        super().__init__(thing)
        self.pending_refresh = EnumSet.noneOf(SwitchModuleGroup)
        self.logger = LoggerFactory.getLogger(NikobusModuleHandler)
        self.cached_states = HashMap()

    def initialize(self):
        super().initialize()

        if self.thing.get_status() != ThingStatus.OFFLINE:
            # Fetch all linked channels to get initial values.
            for channel in self.thing.get_channels():
                self.refresh_channel(channel.get_uid())

    def dispose(self):
        super().dispose()

        with self.cached_states:
            self.cached_states.clear()

        with self.pending_refresh:
            self.pending_refresh.clear()

    def handle_command(self, channel_uid, command):
        self.logger.debug("handleCommand '{}' for channel '{}'", command, channel_uid.get_id())

        if isinstance(command, RefreshType):
            self.refresh_channel(channel_uid)
        else:
            self.process_write(channel_uid, command)

    def refresh_channel(self, channel_uid):
        self.logger.debug("Refreshing channel '{}'", channel_uid.get_id())

        if not self.is_linked(channel_uid):
            self.logger.debug("Refreshing channel '{}' skipped since it is not linked", channel_uid.get_id())
            return

        self.update_group(SwitchModuleGroup.map_from_channel(channel_uid))

    def refresh_module(self):
        groups = HashSet()
        for channel in self.thing.get_channels():
            channel_uid = channel.get_uid()
            if self.is_linked(channel_uid):
                groups.add(SwitchModuleGroup.map_from_channel(channel_uid))

        if groups.is_empty():
            self.logger.debug("Nothing to refresh for '{}'", self.thing.get_uid())
            return

        self.logger.debug("Refreshing {} - {}", self.thing.get_uid(), groups)

        for group in groups:
            self.update_group(group)

    def request_status(self, group):
        self.update_group(group)

    def update_group(self, group):
        with self.pending_refresh:
            if group in self.pending_refresh:
                self.logger.debug("Refresh already scheduled for group {} of module '{}'", group, self.get_address())
                return

            self.pending_refresh.add(group)

        self.logger.debug("Refreshing group {} of switch module '{}'", group, self.get_address())

        pc_link = self.get_pc_link()
        if pc_link is not None:
            command = SwitchModuleCommandFactory.create_read_command(self.get_address(), group,
                                                                     lambda result: self.process_status_update(result, group))
            pc_link.send_command(command)

    def process_status_update(self, result, group):
        try:
            response_payload = result.get()

            self.logger.debug("processStatusUpdate '{}' for group {} in module '{}'", response_payload, group,
                              self.get_address())

            if self.thing.get_status() != ThingStatus.ONLINE:
                self.update_status(ThingStatus.ONLINE)

            # Update channel's statuses based on response.
            for i in range(group.get_count()):
                channel_id = CHANNEL_OUTPUT_PREFIX + (i + group.get_offset())
                response_digits = response_payload.substring(9 + (i * 2), 11 + (i * 2))

                value = int(response_digits, 16)

                self.update_state_and_cache_value(channel_id, value)
        except Exception as e:
            self.logger.warn("Processing response for '{}'-{} failed with {}".format(self.get_address(), group, e))
            self.update_status(ThingStatus.OFFLINE, ThingStatusDetail.COMMUNICATION_ERROR, str(e))
        finally:
            with self.pending_refresh:
                self.pending_refresh.remove(group)

    def update_state_and_cache_value(self, channel_id, value):
        if not (0x00 <= value <= 0xff):
            raise ValueError("Invalid range. 0x00 - 0xff expected but got value {}".format(value))

        self.logger.debug("setting channel '{}' to {}".format(channel_id, value))

        with self.cached_states:
            previous_value = self.cached_states.put(channel_id, value)

        if previous_value is None or previous_value != value:
            self.update_state(channel_id, self.state_from_value(channel_id, value))

    def process_write(self, channel_uid, command):
        command_payload = StringBuilder()
        group = SwitchModuleGroup.map_from_channel(channel_uid)

        for i in range(group.get_offset(), group.get_offset() + group.get_count()):
            channel_id = CHANNEL_OUTPUT_PREFIX + i
            digits = None

            if channel_id == channel_uid.get_id():
                digits = self.value_from_command(channel_id, command)
                self.update_state_and_cache_value(channel_id, digits)
            else:
                with self.cached_states:
                    digits = self.cached_states.get(channel_id)

            if digits is None:
                command_payload.append("00")
                self.logger.warn("no cached value found for '{}' in module '{}'".format(channel_id, self.get_address()))
            else:
                command_payload.append("{:02X}".format(digits))

        pc_link = self.get_pc_link()
        if pc_link is not None:
            pc_link.send_command(SwitchModuleCommandFactory.create_write_command(self.get_address(), group,
                                                                                  command_payload.to_string(),
                                                                                  self.process_write_command_response))

    def process_write_command_response(self, result):
        try:
            response_payload = result.get()

            self.logger.debug("processWriteCommandResponse '{}'".format(response_payload))

            if self.thing.get_status() != ThingStatus.ONLINE:
                self.update_status(ThingStatus.ONLINE)
        except Exception as e:
            self.logger.warn("Processing write confirmation failed with {}".format(e))
            self.update_status(ThingStatus.OFFLINE, ThingStatusDetail.COMMUNICATION_ERROR, str(e))

    def value_from_command(self, channel_id, command):
        raise NotImplementedError("Subclasses must implement this method")

    def state_from_value(self, channel_id, value):
        raise NotImplementedError("Subclasses must implement this method")

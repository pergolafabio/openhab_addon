from java.util import List, Map, Optional
from java.util.concurrent import ConcurrentHashMap, CopyOnWriteArrayList, Future, TimeUnit
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.openhab.binding.nikobus.internal.utils import Utils
from org.openhab.core.library.types import DecimalType, OnOffType, PercentType, StopMoveType, UpDownType
from org.openhab.core.thing import Channel, ChannelUID, Thing, ThingStatus
from org.openhab.core.types import Command, State
from org.slf4j import Logger, LoggerFactory

@NonNullByDefault
class NikobusRollershutterModuleHandler(NikobusModuleHandler):
    def __init__(self, thing):
        super(NikobusRollershutterModuleHandler, self).__init__(thing)
        self.logger = LoggerFactory.getLogger(NikobusRollershutterModuleHandler)
        self.position_estimators = CopyOnWriteArrayList()
        self.direction_configurations = ConcurrentHashMap()

    def initialize(self):
        super().initialize()

        if self.thing.get_status() == ThingStatus.OFFLINE:
            return

        self.position_estimators.clear()
        self.direction_configurations.clear()

        for channel in self.thing.get_channels():
            config = channel.get_configuration().as_(PositionEstimatorConfig)
            if config.delay >= 0 and config.duration > 0:
                self.position_estimators.add(PositionEstimator(channel.get_uid(), config))

            configuration = DirectionConfiguration.REVERSED if config.reverse else DirectionConfiguration.NORMAL
            self.direction_configurations[channel.get_uid().get_id()] = configuration

        self.logger.debug("Position estimators for {} = {}".format(self.thing.get_uid(), self.position_estimators))

    def dispose(self):
        for estimator in self.position_estimators:
            estimator.destroy()
        super().dispose()

    def value_from_command(self, channel_id, command):
        position_estimator = self.get_position_estimator(channel_id)
        if isinstance(command, DecimalType):
            return position_estimator.process_set_position(command.int_value())
        result = self.convert_command_to_value(channel_id, command)
        position_estimator.cancel_stop_movement()
        return result

    def state_from_value(self, channel_id, value):
        if value == 0x00:
            return OnOffType.OFF
        configuration = self.get_direction_configuration(channel_id)
        if value == configuration.up:
            return UpDownType.UP
        if value == configuration.down:
            return UpDownType.DOWN
        raise ValueError("Unexpected value {} received".format(value))

    def update_state(self, channel_uid, state):
        self.logger.debug("updateState {} {}".format(channel_uid, state))

        position_estimator = self.get_position_estimator(channel_uid.get_id())
        if position_estimator:
            if state == UpDownType.UP:
                position_estimator.start(-1)
            elif state == UpDownType.DOWN:
                position_estimator.start(1)
            elif state == OnOffType.OFF:
                position_estimator.stop()
            else:
                self.logger.debug("Unexpected state update '{}' for '{}'".format(state, channel_uid))
        else:
            super().update_state(channel_uid, state)

    def update_state_percent(self, channel_uid, percent):
        super().update_state(channel_uid, PercentType(percent))

    def convert_command_to_value(self, channel_id, command):
        if command == StopMoveType.STOP:
            return 0x00
        if command == UpDownType.DOWN or command == StopMoveType.MOVE:
            return self.get_direction_configuration(channel_id).down
        if command == UpDownType.UP:
            return self.get_direction_configuration(channel_id).up
        raise ValueError("Command '{}' not supported".format(command))

    def get_position_estimator(self, channel_id):
        return next((estimator for estimator in self.position_estimators if channel_id == estimator.get_channel_uid().get_id()), None)

    def get_direction_configuration(self, channel_id):
        configuration = self.direction_configurations.get(channel_id)
        if configuration is None:
            raise ValueError("Direction configuration not found for {}".format(channel_id))
        return configuration

    class PositionEstimatorConfig:
        def __init__(self):
            self.duration = -1
            self.delay = 5
            self.reverse = False

    class PositionEstimator:
        update_interval_in_sec = 1

        def __init__(self, channel_uid, config):
            self.channel_uid = channel_uid
            self.duration_in_millis = config.duration * 1000
            self.delay_in_millis = config.delay * 1000
            self.position = 0
            self.turn_off_millis = 0
            self.start_time_millis = 0
            self.direction = 0
            self.update_estimate_future = None
            self.stop_movement_future = None

        def get_channel_uid(self):
            return self.channel_uid

        def destroy(self):
            Utils.cancel(self.update_estimate_future)
            self.update_estimate_future = None
            self.cancel_stop_movement()

        def start(self, direction):
            self.stop()
            with self:
                self.direction = direction
                self.turn_off_millis = self.delay_in_millis + self.duration_in_millis
                self.start_time_millis = System.currentTimeMillis()
            self.update_estimate_future = scheduler.schedule_with_fixed_delay(self.update_estimate, self.update_interval_in_sec, self.update_interval_in_sec, TimeUnit.SECONDS)

        def stop(self):
            Utils.cancel(self.update_estimate_future)
            self.update_estimate()
            with self:
                self.direction = 0
                self.start_time_millis = 0

        def process_set_position(self, percent):
            if percent < 0 or percent > 100:
                raise ValueError("Position % out of range - expecting [0, 100] but got {} for {}".format(percent, self.channel_uid.get_id()))

            self.cancel_stop_movement()

            new_position = int(percent * self.duration_in_millis / 100.0 + 0.5)
            delta = self.position - new_position

            self.logger.debug("Position set command {} for {}: delta = {}, current pos: {}, new position: {}".format(percent, self.channel_uid, delta, self.position, new_position))

            if delta == 0:
                return self.convert_command_to_value(self.channel_uid.get_id(), StopMoveType.STOP)

            time = abs(delta)
            if percent == 0 or percent == 100:
                time += 5000  # Make sure we get to completely open/closed position.

            self.stop_movement_future = scheduler.schedule(lambda: self.handle_command(self.channel_uid, StopMoveType.STOP), time, TimeUnit.MILLISECONDS)

            return self.convert_command_to_value(self.channel_uid.get_id(), UpDownType.UP if delta > 0 else UpDownType.DOWN)

        def cancel_stop_movement(self):
            Utils.cancel(self.stop_movement_future)
            self.stop_movement_future = None

        def update_estimate(self):
            direction = 0
            ellapsed_millis = 0

            with self:
                direction = self.direction
                if self.start_time_millis == 0:
                    ellapsed_millis = 0
                else:
                    current_time_millis = System.currentTimeMillis()
                    ellapsed_millis = int(current_time_millis - self.start_time_millis)
                    self.start_time_millis = current_time_millis

            self.turn_off_millis -= ellapsed_millis
            self.position = min(self.duration_in_millis, max(0, ellapsed_millis * direction + self.position))
            percent = int(self.position / self.duration_in_millis * 100.0 + 0.5)

            self.logger.debug("Update estimate for '{}': position = {}, percent = {}, elapsed = {}ms, duration = {}ms, delay = {}ms, turnOff = {}ms".format(
                self.channel_uid, self.position, percent, ellapsed_millis, self.duration_in_millis, self.delay_in_millis, self.turn_off_millis))

            self.update_state_percent(self.channel_uid, percent)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def __str__(self):
            return "PositionEstimator('{}', duration = {}ms, delay = {}ms)".format(self.channel_uid, self.duration_in_millis, self.delay_in_millis)

    class DirectionConfiguration:
        NORMAL = DirectionConfiguration(1, 2)
        REVERSED = DirectionConfiguration(2, 1)

        def __init__(self, up, down):
            self.up = up
            self.down = down

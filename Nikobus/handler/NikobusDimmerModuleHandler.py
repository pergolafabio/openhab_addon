from java.util.concurrent import Future, TimeUnit
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.openhab.binding.nikobus.internal.protocol import SwitchModuleGroup
from org.openhab.binding.nikobus.internal.utils import Utils
from org.openhab.core.library.types import PercentType
from org.openhab.core.thing import Thing
from org.openhab.core.types import Command, State

@NonNullByDefault
class NikobusDimmerModuleHandler(NikobusSwitchModuleHandler):
    def __init__(self, thing):
        super().__init__(thing)
        self.request_update_future = None

    def dispose(self):
        Utils.cancel(self.request_update_future)
        self.request_update_future = None
        super().dispose()

    def request_status(self, group):
        Utils.cancel(self.request_update_future)
        super().request_status(group)
        self.request_update_future = scheduler.schedule(lambda: super().request_status(group), 1, TimeUnit.SECONDS)

    def value_from_command(self, channel_id, command):
        if isinstance(command, PercentType):
            return round(command.float_value() / 100 * 255)

        return super().value_from_command(channel_id, command)

    def state_from_value(self, channel_id, value):
        result = round(value * 100 / 255)
        return PercentType(result)

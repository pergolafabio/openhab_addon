from org.openhab.core.library.types import OnOffType
from org.openhab.core.thing import Thing
from org.openhab.core.types import Command, State
from org.eclipse.jdt.annotation import NonNullByDefault

@NonNullByDefault
class NikobusSwitchModuleHandler(NikobusModuleHandler):
    def __init__(self, thing):
        super(NikobusSwitchModuleHandler, self).__init__(thing)

    def value_from_command(self, channel_id, command):
        if command == OnOffType.ON:
            return 0xFF

        if command == OnOffType.OFF:
            return 0x00

        raise ValueError("Command '{}' not supported".format(command))

    def state_from_value(self, channel_id, value):
        return OnOffType.ON if value != 0 else OnOffType.OFF

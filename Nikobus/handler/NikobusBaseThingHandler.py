from openhab.binding.nikobus.internal import NikobusBindingConstants
from openhab.core.thing import ThingStatus, ThingStatusDetail
from openhab.core.thing.binding import BaseThingHandler

class NikobusBaseThingHandler(BaseThingHandler):
    def __init__(self, thing):
        super().__init__(thing)
        self.address = None

    def initialize(self):
        self.address = self.get_config().get(NikobusBindingConstants.CONFIG_ADDRESS)
        if self.address is None:
            self.update_status(ThingStatus.OFFLINE, ThingStatusDetail.OFFLINE.CONFIGURATION_ERROR, "Address must be set!")
            return

        self.update_status(ThingStatus.UNKNOWN)

    def get_pc_link(self):
        bridge = self.get_bridge()
        if bridge is not None:
            return bridge.get_handler()
        return None

    def get_address(self):
        if self.address is None:
            raise ValueError("Address must be set")
        return self.address

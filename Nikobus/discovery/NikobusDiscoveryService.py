from typing import Optional, Dict
from java.util import Set, HashMap
from org.openhab.core.config.discovery import AbstractDiscoveryService, DiscoveryResultBuilder
from org.openhab.core.thing import ThingUID
from org.openhab.core.thing.binding import ThingHandlerService
from org.slf4j import Logger, LoggerFactory
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.openhab.binding.nikobus.internal.handler import NikobusPcLinkHandler
from org.openhab.binding.nikobus.internal.utils import Utils

@NonNullByDefault
class NikobusDiscoveryService(AbstractDiscoveryService, ThingHandlerService):
    CHANNEL_OUTPUT_PREFIX = "CHANNEL_OUTPUT_PREFIX"
    THING_TYPE_PUSH_BUTTON = "THING_TYPE_PUSH_BUTTON"
    CONFIG_ADDRESS = "CONFIG_ADDRESS"

    def __init__(self) -> None:
        super(NikobusDiscoveryService, self).__init__(Set.of(self.THING_TYPE_PUSH_BUTTON), 0)
        self.logger = LoggerFactory.getLogger(NikobusDiscoveryService)
        self.bridgeHandler: Optional[NikobusPcLinkHandler] = None

    def startScan(self) -> None:
        pass

    def stopBackgroundDiscovery(self) -> None:
        handler = self.bridgeHandler
        if handler:
            handler.resetUnhandledCommandProcessor()

    def startBackgroundDiscovery(self) -> None:
        handler = self.bridgeHandler
        if handler:
            handler.setUnhandledCommandProcessor(self.process)

    def process(self, command: str) -> None:
        if len(command) <= 2 or not command.startswith("#N"):
            self.logger.debug("Ignoring command() '{}'", command)
            return

        address = command[2:]
        self.logger.debug("Received address = '{}'", address)

        handler = self.bridgeHandler
        if handler:
            thingUID = ThingUID(self.THING_TYPE_PUSH_BUTTON, handler.getThing().getUID(), address)
            properties: Dict[str, object] = {self.CONFIG_ADDRESS: address}

            human_readable_nikobus_address = Utils.convertToHumanReadableNikobusAddress(address).upper()
            self.logger.debug("Detected Nikobus Push Button: '{}'", human_readable_nikobus_address)

            thing_discovered_result = DiscoveryResultBuilder.create(thingUID) \
                .withThingType(self.THING_TYPE_PUSH_BUTTON) \
                .withLabel(f"Nikobus Push Button {human_readable_nikobus_address}") \
                .withProperties(properties) \
                .withRepresentationProperty(self.CONFIG_ADDRESS) \
                .withBridge(handler.getThing().getUID()) \
                .build()

            self.thingDiscovered(thing_discovered_result)

    def setThingHandler(self, handler) -> None:
        if isinstance(handler, NikobusPcLinkHandler):
            self.bridgeHandler = handler

    def getThingHandler(self) -> Optional[ThingHandler]:
        return self.bridgeHandler

    def activate(self) -> None:
        super(NikobusDiscoveryService, self).activate(None)

    def deactivate(self) -> None:
        super(NikobusDiscoveryService, self).deactivate()

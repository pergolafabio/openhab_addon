from java.util import Collections, Set
from java.util.stream import Collectors, Stream
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.openhab.binding.nikobus.internal import NikobusBindingConstants
from org.openhab.binding.nikobus.internal.handler import (
    NikobusDimmerModuleHandler,
    NikobusPcLinkHandler,
    NikobusPushButtonHandler,
    NikobusRollershutterModuleHandler,
    NikobusSwitchModuleHandler
)
from org.openhab.core.io.transport.serial import SerialPortManager
from org.openhab.core.thing import Bridge, Thing, ThingTypeUID
from org.openhab.core.thing.binding import BaseThingHandlerFactory, ThingHandler, ThingHandlerFactory
from org.osgi.service.component.annotations import Component, Reference

@NonNullByDefault
@Component(configurationPid="binding.nikobus", service=ThingHandlerFactory)
class NikobusHandlerFactory(BaseThingHandlerFactory):

    SUPPORTED_THING_TYPES_UIDS = Collections.unmodifiableSet(
        Stream.of(
            NikobusBindingConstants.BRIDGE_TYPE_PCLINK,
            NikobusBindingConstants.THING_TYPE_PUSH_BUTTON,
            NikobusBindingConstants.THING_TYPE_SWITCH_MODULE,
            NikobusBindingConstants.THING_TYPE_DIMMER_MODULE,
            NikobusBindingConstants.THING_TYPE_ROLLERSHUTTER_MODULE
        ).collect(Collectors.toSet())
    )

    def __init__(self):
        self.serialPortManager = None

    def supportsThingType(self, thingTypeUID):
        return thingTypeUID in self.SUPPORTED_THING_TYPES_UIDS

    def createHandler(self, thing):
        thingTypeUID = thing.getThingTypeUID()

        if thingTypeUID == NikobusBindingConstants.BRIDGE_TYPE_PCLINK:
            return NikobusPcLinkHandler(thing, self.serialPortManager)

        if thingTypeUID == NikobusBindingConstants.THING_TYPE_PUSH_BUTTON:
            return NikobusPushButtonHandler(thing)

        if thingTypeUID == NikobusBindingConstants.THING_TYPE_SWITCH_MODULE:
            return NikobusSwitchModuleHandler(thing)

        if thingTypeUID == NikobusBindingConstants.THING_TYPE_DIMMER_MODULE:
            return NikobusDimmerModuleHandler(thing)

        if thingTypeUID == NikobusBindingConstants.THING_TYPE_ROLLERSHUTTER_MODULE:
            return NikobusRollershutterModuleHandler(thing)

        return None

    @Reference
    def setSerialPortManager(self, serialPortManager):
        self.serialPortManager = serialPortManager

    def unsetSerialPortManager(self, serialPortManager):
        self.serialPortManager = None

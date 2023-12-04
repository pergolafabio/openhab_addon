from org.openhab.core.thing import ThingTypeUID

class NikobusBindingConstants:
    BINDING_ID = "nikobus"

    # List of all Thing Type UIDs
    BRIDGE_TYPE_PCLINK = ThingTypeUID(BINDING_ID, "pc-link")

    THING_TYPE_PUSH_BUTTON = ThingTypeUID(BINDING_ID, "push-button")
    THING_TYPE_SWITCH_MODULE = ThingTypeUID(BINDING_ID, "switch-module")
    THING_TYPE_DIMMER_MODULE = ThingTypeUID(BINDING_ID, "dimmer-module")
    THING_TYPE_ROLLERSHUTTER_MODULE = ThingTypeUID(BINDING_ID, "rollershutter-module")

    # List of all Channel ids
    CHANNEL_BUTTON = "button"
    CHANNEL_TRIGGER_FILTER = "trigger-filter"
    CHANNEL_TRIGGER_BUTTON = "trigger-button"
    CHANNEL_OUTPUT_PREFIX = "output-"

    # Configuration parameters
    CONFIG_REFRESH_INTERVAL = "refreshInterval"
    CONFIG_IMPACTED_MODULES = "impactedModules"
    CONFIG_ADDRESS = "address"
    CONFIG_PORT_NAME = "port"

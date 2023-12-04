from typing import List, Optional, Union
from datetime import datetime, timedelta
from concurrent.futures import Future

class NikobusPushButtonHandler(NikobusBaseThingHandler):
    END_OF_TRANSMISSION = "\r#E1"

    def __init__(self, thing):
        super().__init__(thing)
        self.logger = LoggerFactory.getLogger(NikobusPushButtonHandler.__class__)
        self.impacted_modules = []
        self.trigger_processors = []
        self.request_update_future: Optional[Future] = None

    def initialize(self):
        super().initialize()

        if self.thing.get_status() == ThingStatus.OFFLINE:
            return

        self.impacted_modules.clear()
        self.trigger_processors.clear()

        impacted_modules_object = self.get_config().get(CONFIG_IMPACTED_MODULES)
        if impacted_modules_object is not None:
            try:
                bridge = self.get_bridge()
                if bridge is None:
                    raise ValueError("Bridge does not exist!")

                bridge_uid = self.thing.get_bridge_uid()
                if bridge_uid is None:
                    raise ValueError("Unable to read BridgeUID!")

                impacted_modules_string = impacted_modules_object.split(",")
                for impacted_module_string in impacted_modules_string:
                    impacted_module_uid = ImpactedModuleUID(impacted_module_string.strip())
                    thing_type_uid = ThingTypeUID(bridge_uid.get_binding_id(), impacted_module_uid.get_thing_type_id())
                    thing_uid = ThingUID(thing_type_uid, bridge_uid, impacted_module_uid.get_thing_id())

                    if not any(thing.uid == thing_uid for thing in bridge.get_things()):
                        raise ValueError(
                            f"Impacted module {thing_uid} not found for '{impacted_module_string}'"
                        )

                    self.impacted_modules.append(ImpactedModule(thing_uid, impacted_module_uid.get_group()))

            except Exception as e:
                self.update_status(ThingStatus.OFFLINE, ThingStatusDetail.CONFIGURATION_ERROR, str(e))
                return

            self.logger.debug(f"Impacted modules for {self.thing.uid} = {self.impacted_modules}")

        for channel in self.thing.get_channels():
            processor = self.create_trigger_processor(channel)
            if processor is not None:
                self.trigger_processors.append(processor)

        self.logger.debug(f"Trigger channels for {self.thing.uid} = {self.trigger_processors}")

        pc_link = self.get_pc_link()
        if pc_link is not None:
            pc_link.add_listener(self.get_address(), self.command_received)

    def dispose(self):
        super().dispose()

        Utils.cancel(self.request_update_future)
        self.request_update_future = None

        pc_link = self.get_pc_link()
        if pc_link is not None:
            pc_link.remove_listener(self.get_address())

    def handle_command(self, channel_uid, command):
        self.logger.debug(f"handle_command '{channel_uid}' '{command}'")

        if channel_uid.id != CHANNEL_BUTTON:
            return

        # Whenever the button receives an ON command,
        # we send a simulated button press to the Nikobus.
        if command == OnOffType.ON:
            pc_link = self.get_pc_link()
            if pc_link is not None:
                pc_link.send_command(NikobusCommand(self.get_address() + self.END_OF_TRANSMISSION))
            self.process_impacted_modules()

    def command_received(self):
        if self.thing.get_status() != ThingStatus.ONLINE:
            self.update_status(ThingStatus.ONLINE)

        self.update_state(CHANNEL_BUTTON, OnOffType.ON)

        if self.trigger_processors:
            current_time_millis = int(datetime.now().timestamp() * 1000)
            for processor in self.trigger_processors:
                processor.process(current_time_millis)

        self.process_impacted_modules()

    def process_impacted_modules(self):
        if self.impacted_modules:
            Utils.cancel(self.request_update_future)
            self.request_update_future = scheduler.schedule(self.update, 400, TimeUnit.MILLISECONDS)

    def update(self):
        for module in self.impacted_modules:
            switch_module = self.get_module_with_id(module.thing_uid)
            if switch_module is not None:
                switch_module.request_status(module.group)

    def get_module_with_id(self, thing_uid):
        bridge = self.get_bridge()
        if bridge is None:
            return None

        thing = bridge.get_thing(thing_uid)
        if thing is None:
            return None

        thing_handler = thing.get_handler()
        if isinstance(thing_handler, NikobusModuleHandler):
            return thing_handler

        return None

    def get_address(self):
        return "#N" + super().get_address()

    def create_trigger_processor(self, channel):
        channel_type_uid = channel.get_channel_type_uid()
        if channel_type_uid is not None:
            if channel_type_uid.id == CHANNEL_TRIGGER_FILTER:
                return TriggerFilter(channel)
            elif channel_type_uid.id == CHANNEL_TRIGGER_BUTTON:
                return TriggerButton(channel)

        return None

    class ImpactedModule:
        def __init__(self, thing_uid, group):
            self.thing_uid = thing_uid
            self.group = group

        def __str__(self):
            return f"'{self.thing_uid}'-{self.group}"

    class ImpactedModuleUID(AbstractUID):
        def __init__(self, uid):
            super().__init__(uid)

        def get_thing_type_id(self):
            return self.get_segment(0)

        def get_thing_id(self):
            return self.get_segment(1)

        def get_group(self):
            if self.get_segment(2) == "1":
                return SwitchModuleGroup.FIRST
            elif self.get_segment(2) == "2":
                return SwitchModuleGroup.SECOND
            else:
                raise ValueError(f"Unexpected group found {self.get_segment(2)}")

        def get_minimal

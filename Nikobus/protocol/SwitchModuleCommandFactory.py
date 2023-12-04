from org.openhab.binding.nikobus.internal.protocol import NikobusCommand
from org.eclipse.jdt.annotation import NonNullByDefault
from org.openhab.binding.nikobus.internal.utils import CRCUtil
from java.util.function import Consumer

@NonNullByDefault
class SwitchModuleCommandFactory:
    @staticmethod
    def create_read_command(address, group, result_consumer):
        SwitchModuleCommandFactory._check_address(address)
        command_payload = CRCUtil.appendCRC2(f"$10{CRCUtil.appendCRC(group.get_status_request() + address)}")
        return NikobusCommand(command_payload, 27, 3, "$1C", result_consumer)

    @staticmethod
    def create_write_command(address, group, value, result_consumer):
        SwitchModuleCommandFactory._check_address(address)
        if len(value) != 12:
            raise ValueError(f"Value must have 12 chars but got '{value}'")

        payload = group.get_status_update() + address + value + "FF"
        return NikobusCommand(CRCUtil.appendCRC2(f"$1E{CRCUtil.appendCRC(payload)}"), 13, 5, "$0E", result_consumer)

    @staticmethod
    def _check_address(address):
        if len(address) != 4:
            raise ValueError(f"Address must have 4 chars but got '{address}'")

from typing import Optional
from java.util.concurrent import Future
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable

@NonNullByDefault
class Utils:
    @staticmethod
    def cancel(future: Optional[Future]) -> None:
        if future is not None:
            future.cancel(True)

    @staticmethod
    def convert_to_human_readable_nikobus_address(address_string: str) -> str:
        try:
            address = int(address_string, 16)
            nikobus_address = 0

            for i in range(21):
                nikobus_address = (nikobus_address << 1) | ((address >> i) & 1)

            nikobus_address = (nikobus_address << 1)
            button = (address >> 21) & 0x07

            return Utils.left_pad_with_zeros(hex(nikobus_address)[2:], 6) + ":" + Utils.map_button(button)

        except ValueError:
            return "[" + address_string + "]"

    @staticmethod
    def map_button(button_index: int) -> str:
        button_mapping = {
            0: "1",
            1: "5",
            2: "2",
            3: "6",
            4: "3",
            5: "7",
            6: "4",
            7: "8"
        }
        return button_mapping.get(button_index, "?")

    @staticmethod
    def left_pad_with_zeros(text: str, size: int) -> str:
        return text.zfill(size)

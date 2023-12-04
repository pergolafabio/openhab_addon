from typing import Optional
from org.eclipse.jdt.annotation import NonNullByDefault, Nullable
from org.openhab.core.util import HexUtils
from org.openhab.binding.nikobus.internal.utils import Utils

@NonNullByDefault
class CRCUtil:
    CRC_INIT = 0xFFFF
    POLYNOMIAL = 0x1021

    @staticmethod
    def append_crc(input: Optional[str]) -> Optional[str]:
        if input is None:
            return None

        check = CRCUtil.CRC_INIT

        for b in HexUtils.hexToBytes(input):
            for i in range(8):
                if ((b >> (7 - i) & 1) == 1) ^ ((check >> 15 & 1) == 1):
                    check = (check << 1) ^ CRCUtil.POLYNOMIAL
                else:
                    check = check << 1

        check = check & CRCUtil.CRC_INIT
        checksum = Utils.leftPadWithZeros(hex(check)[2:], 4)
        return (input + checksum).upper()

    @staticmethod
    def append_crc2(input: str) -> str:
        check = 0

        for b in input.encode():
            check ^= b

            for i in range(8):
                if (check & 0xff) >> 7 != 0:
                    check = (check << 1) ^ 0x99
                else:
                    check = check << 1
                check = check & 0xff

        return input + Utils.leftPadWithZeros(hex(check)[2:], 2).upper()

class SwitchModuleGroup:
    CHANNEL_OUTPUT_PREFIX = "CHANNEL_OUTPUT_PREFIX"

    FIRST = ("12", "15", 1)
    SECOND = ("17", "16", 7)

    def __init__(self, status_request, status_update, offset):
        self.status_request = status_request
        self.status_update = status_update
        self.offset = offset

    def get_status_request(self):
        return self.status_request

    def get_status_update(self):
        return self.status_update

    def get_offset(self):
        return self.offset

    def get_count(self):
        return 6

    @classmethod
    def map_from_channel(cls, channel_uid):
        if not channel_uid.id_without_group.startswith(cls.CHANNEL_OUTPUT_PREFIX):
            raise ValueError(f"Unexpected channel {channel_uid.id}")

        channel_number = int(channel_uid.id_without_group[len(cls.CHANNEL_OUTPUT_PREFIX):])
        return cls.map_from_channel_number(channel_number)

    @classmethod
    def map_from_channel_number(cls, channel_number):
        max_value = cls.SECOND.get_offset() + cls.SECOND.get_count()
        if channel_number < cls.FIRST.get_offset() or channel_number > max_value:
            raise ValueError(
                f"Channel number should be between [{cls.FIRST.get_offset()}, {max_value}], but got {channel_number}")

        return cls.SECOND if channel_number >= cls.SECOND.get_offset() else cls.FIRST

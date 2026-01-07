from struct import pack, unpack

class FSNETCMD_REQUESTAIAIRPLANE_REMELIA:
    COMMAND_ID = 14

    PAYLOAD_FORMAT = "<32s32s32sdH"
    PAYLOAD_SIZE = 106  # 32+32+32+8+2

    def __init__(self, buffer: bytes, should_decode: bool = True):
        self.buffer = buffer
        
        self.aircraft_name = ""
        self.start_pos_name = ""
        self.ai_username = ""
        self.g_limit = 0.0
        self.iff = 0

        if should_decode:
            self.decode()

    def decode(self):
        payload = self.buffer[4:4 + self.PAYLOAD_SIZE]
        if len(payload) < self.PAYLOAD_SIZE:
            return  # Malformed packet

        unpacked = unpack(self.PAYLOAD_FORMAT, payload)

        self.aircraft_name = unpacked[0].decode("utf-8").strip("\x00")
        self.start_pos_name = unpacked[1].decode("utf-8").strip("\x00")
        self.ai_username = unpacked[2].decode("utf-8").strip("\x00")
        self.g_limit = unpacked[3]
        self.iff = unpacked[4]

    @staticmethod
    def encode(aircraft_name: str, start_pos_name: str, ai_username: str,
               g_limit: float, iff: int, with_size: bool = False) -> bytes:

        # Prepare fixed-length string fields
        aircraft_b = aircraft_name.encode("utf-8")[:31].ljust(32, b"\x00")
        startpos_b = start_pos_name.encode("utf-8")[:31].ljust(32, b"\x00")
        aiuser_b   = ai_username.encode("utf-8")[:31].ljust(32, b"\x00")

        payload = pack(
            FSNETCMD_REQUESTAIAIRPLANE_REMELIA.PAYLOAD_FORMAT,
            aircraft_b,
            startpos_b,
            aiuser_b,
            float(g_limit),
            iff
        )

        buffer = pack("<I", FSNETCMD_REQUESTAIAIRPLANE_REMELIA.COMMAND_ID) + payload

        if with_size:
            buffer = pack("<I", len(buffer)) + buffer

        return buffer


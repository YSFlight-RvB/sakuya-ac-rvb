from lib.Aircraft import Aircraft
from lib.PacketManager.packets import FSNETCMD_LOGON, FSNETCMD_ADDOBJECT


class EmptyStreamWriter:
    def __init__(self):
        self.is_empty = True
    def is_closing(self):
        return True

class Player:
    """
    A player class, this will hold info about the client, including which aircraft they're flying"""
    def __init__(self, server_messages=EmptyStreamWriter(), client_messages=EmptyStreamWriter(), streamWriterObject=EmptyStreamWriter()):

        self.username = ""
        self.alias = ""
        self.aircraft = Aircraft()
        self.version = 0
        self.ip = ""
        self.streamWriterObject = streamWriterObject
        self.serverWriter = None
        self.is_a_bot = True # We check if they are still present after LOGIN packet, then they're not a bot
        self.iff = 1
        self.connection_closed = False

    def set_aircraft(self, aircraft:Aircraft):
        self.aircraft = aircraft

    def login(self, packet:FSNETCMD_LOGON):
        self.username = packet.username
        self.alias = packet.alias
        self.version = packet.version

    def set_ip(self, ip):
        self.ip = ip

    def check_add_object(self, packet:FSNETCMD_ADDOBJECT):
        # we check the full name here
        if packet.pilot == self.alias:
            self.aircraft = Aircraft()
            self.aircraft.name = packet.identifier
            self.aircraft.id = packet.object_id
            self.aircraft.set_position(packet.pos)
            self.aircraft.set_initial_config({
                "IFF": packet.iff
            })
            return True
        return False

    def __str__(self):
        return f"Player {self.username} flying {self.aircraft.name} at {self.aircraft.position}, {type(self.serverWriter)}"

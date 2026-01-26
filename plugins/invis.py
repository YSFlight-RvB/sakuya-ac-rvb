from lib import YSchat, plugin_manager
from lib.PacketManager.packets import FSNETCMD_AIRCMD


ENABLED = False

class Plugin:
    def __init__(self):
        self.plugin_manager = None

    def register(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.plugin_manager.register_command('test', self.test)

    def test(self, full_message, player, message_to_client, message_to_server):
        print(1)
        d = FSNETCMD_AIRCMD.set_command(player.aircraft.id,
                                    "RADARCRS",
                                    0.00, True)
        print(2)
        print(self.plugin_manager.CONNECTED_PLAYERS)
        message_to_server.put_nowait(d)
        return True


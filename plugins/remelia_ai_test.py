from plugins.remelia.ai_packet import FSNETCMD_REQUESTAIAIRPLANE_REMELIA
from lib.YSchat import message

ENABLED = True

class Plugin:
    def __init__(self):
        self.plugin_manager = None

    def register(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.plugin_manager.register_command("spawn", self.spawn, "Remelia API usecase")

    def spawn(self, full_message, player, message_to_client, message_to_server):
        message_to_server.append(FSNETCMD_REQUESTAIAIRPLANE_REMELIA(b"").encode(
                with_size=True,
                aircraft_name="F-16C_FIGHTINGFALCON",
                ai_username=f"Sakuya Izayoi",
                start_pos_name="NORTH10000_01",
                iff=3, # IFF 4 in game is IFF 3 in sakuya, we subtract 1, so iff 1 in game is iff 0 in sakuya
                g_limit=99999,
                attackGround = True # we want to the ai aircraft to attack ground
                ))
        message_to_client.append(message("An AI aircraft has been spawned at NORTH10000_01"))
        return True

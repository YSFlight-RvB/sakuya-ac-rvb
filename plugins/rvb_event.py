from plugins.remelia.ai_packet import FSNETCMD_REQUESTAIAIRPLANE_REMELIA
from lib.PacketManager.packets import FSNETCMD_TEXTMESSAGE
from lib.YSchat import message, send
import struct
import socket
import asyncio

ENABLED = True


def get_tcp_rtt_ms(sock: socket.socket) -> tuple:
    """
    Returns a tuple[float, float] with rtt and variance in rtt
    """
    TCP_INFO = 11
    buf = sock.getsockopt(socket.IPPROTO_TCP, TCP_INFO, 104)
    # print(buf)
    unpacked = struct.unpack("8B24I", buf)
    rtt = (unpacked[23]*(10**(-3)), unpacked[24]*(10**(-6))) # rtt and variance in rtt, kernel returns in 10^-6 seconds
    return rtt


class Plugin:
    def __init__(self):
        self.plugin_manager = None
        self.red = []
        self.blue = []

    def register(self, plugin_manager):
        self.plugin_manager = plugin_manager
        
        self.plugin_manager.register_hook("on_login", self.on_login)
        self.plugin_manager.register_hook("on_chat", self.on_chat)
        
        self.plugin_manager.register_command("spawn", self.spawn, "Remelia API usecase")
        self.plugin_manager.register_command("ping", self.ping, "Test the current ping to server", "p")
        self.plugin_manager.register_command("global", self.global_chat, "Send a message to everyone in server", "g")

    def spawn(self, full_message, player, message_to_client, message_to_server):
        message_to_server.put_nowait(FSNETCMD_REQUESTAIAIRPLANE_REMELIA(b"").encode(
                with_size=True,
                aircraft_name="[RED]UCAV",
                ai_username=f"Sakuya Izayoi",
                start_pos_name="RW01_01",
                iff=3, # IFF 4 in game is IFF 3 in sakuya, we subtract 1, so iff 1 in game is iff 0 in sakuya
                g_limit=99999,
                patrolMode = True # we want to the ai aircraft to anchor
                ))
        message_to_client.put_nowait(message("An AI aircraft has been spawned."))
        return True

    def on_login(self, packet, player, message_to_client, message_to_server):
            if player.username == "USERNAME":
                player.streamWriterObject.write(message("Please join with a proper username!"))
                return False
            elif player.username.startswith("[AI]"):
                player.streamWriterObject.write(message("You are not allowed to use that prefix"))
                return False
            elif player.username.lower().startswith("[red]") or player.username.lower().startswith("[blue]"):
                if player.username.lower().startswith("[red]"):
                    self.red.append(player)
                else:
                    self.blue.append(player)
                return True
            else:
                player.streamWriterObject.write(message("You need join with your team in prefix\n"))
                player.streamWriterObject.write(message(f"For example if your username is '{player.username}'\nand if you are on Red team"))
                player.streamWriterObject.write(message(f"Your username should be '[RED]{player.username}'"))
                return False

    def ping(self, packet, player, message_to_client, message_to_server):
        def codn(ping, side):
            if side == "remi":
                if ping > 5:
                    return "Poor"
                if ping > 2 and ping <= 5:
                    return "Okay"
                if ping <= 2:
                    return "Excellent"
            elif side == "saku":
                if ping >= 500:
                    return "Poor"
                if ping >= 200 and ping < 500:
                    return "Okay"
                if ping < 200:
                    return "Excellent"

        client_ping = get_tcp_rtt_ms(player.streamWriterObject.transport.get_extra_info("socket"))
        server_ping = get_tcp_rtt_ms(player.serverWriter.transport.get_extra_info("socket"))
        msg = f"\n====AVERAGE RTT=====\nRemelia Ping[Host]: {server_ping[0]}ms\nVariance: {server_ping[1]}ms^2\n\nSakuya Ping[You]: {client_ping[0]}ms\nVariance: {client_ping[1]}ms^2\n"+20*"="+"\n"
        help_msg = f"Connection Detail\nYou [{codn(client_ping[0], 'saku')}]--> Sakuya --> Remelia [{codn(server_ping[0], 'remi')}]\n\n"+20*"="+"\n"
        message_to_client.put_nowait(message(msg))
        message_to_client.put_nowait(message(help_msg))
        return True

    def on_chat(self, packet, player, message_to_client, message_to_server):
        print(FSNETCMD_TEXTMESSAGE(packet).message)
        if FSNETCMD_TEXTMESSAGE(packet).message.startswith("/"):
            return False

        async def send_to_red(packet):
            for player in self.red:
                player.streamWriterObject.write(send(packet))

        async def send_to_blue(packet):
            for player in self.blue:
                player.streamWriterObject.write(send(packet))

        if player in self.red:
            asyncio.create_task(send_to_red(packet))
        else:
            asyncio.create_task(send_to_blue(packet))

        return False

    def global_chat(self, full_message, player, message_to_client, message_to_server):
        args = full_message.split()
        if len(args) == 1:
            message_to_client.put_nowait(message("Invalid command usage\nUsage : /g <message>"))
            message_to_client.put_nowait(message("Example : `/g hello everyone`"))
        else:
            message_to_server.put_nowait(message("(" + player.username + ")" + " ".join(args[1::])))
        return False


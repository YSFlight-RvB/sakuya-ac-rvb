import logging
from plugins.remelia.ai_packet import FSNETCMD_REQUESTAIAIRPLANE_REMELIA
from lib.PacketManager.packets import FSNETCMD_TEXTMESSAGE, FSNETCMD_REJECTJOINREQ, FSNETCMD_JOINREQUEST
from lib.PacketManager.packets import FSNETCMD_GETDAMAGE
from lib.YSchat import message, send
import struct
import socket
import asyncio
from dotenv import load_dotenv
import os

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

        # Timer specific variables
        self.timer_task = None
        self.game_running = False
        self.elapsed_seconds = 0
        # The variables in CAPITAL_LETTERS are the only one to configurable
        # please do not touch the variables in snake_casing.

        self.TIMER_INTERVAL = 5 # in seconds
        self.PASSWORD = "test1234"
        self.TOTAL_TIME = 3600
        self.WARN_INTERVALS = [900, 1800, 2400, 2700, 3000, 3300, 3420, 3480, 3540, 3570, 3580, 3590] # in seconds, must be multiple of TIMER_INTERVAL

        # wave specific settings

        self.WAVE_USERNAMES = [
            [   # red
                [   # Wave 1
                    ["Marisa", "AI_RED_NORTH"],
                    ["Alice", "AI_RED_EAST"],
                    ["Koishi", "AI_RED_SOUTH"],
                    ["Satori", "AI_RED_CARRIER"]
                ],
                [   # Wave 2
                    ["Reimu", "AI_RED_NORTH"],
                    ["Sakuya", "AI_RED_EAST"],
                    ["Patchouli", "AI_RED_SOUTH"],
                    ["Remilia", "AI_RED_CARRIER"]
                ],
                [   # Wave 3
                    ["Youmu", "AI_RED_NORTH"],
                    ["Yuyuko", "AI_RED_EAST"],
                    ["Aya", "AI_RED_SOUTH"],
                    ["Kanako", "AI_RED_CARRIER"]
                ],
                [   # Wave 4
                    ["Sanae", "AI_RED_NORTH"],
                    ["Cirno", "AI_RED_EAST"],
                    ["Meiling", "AI_RED_SOUTH"],
                    ["Flandre", "AI_RED_CARRIER"]
                ]
            ],
            [   # blue
                [   # Wave 1
                    ["Reisen", "AI_BLUE_NORTH"],
                    ["Eirin", "AI_BLUE_EAST"],
                    ["Kaguya", "AI_BLUE_SOUTH"],
                    ["Tewi", "AI_BLUE_CARRIER"]
                ],
                [   # Wave 2
                    ["Suika", "AI_BLUE_NORTH"],
                    ["Iku", "AI_BLUE_EAST"],
                    ["Tenshi", "AI_BLUE_SOUTH"],
                    ["Shion", "AI_BLUE_CARRIER"]
                ],
                [   # Wave 3
                    ["Byakuren", "AI_BLUE_NORTH"],
                    ["Shou", "AI_BLUE_EAST"],
                    ["Nue", "AI_BLUE_SOUTH"],
                    ["Ichirin", "AI_BLUE_CARRIER"]
                ],
                [   # Wave 4
                    ["Utsuho", "AI_BLUE_NORTH"],
                    ["Rin", "AI_BLUE_EAST"],
                    ["Parsee", "AI_BLUE_SOUTH"],
                    ["Yuugi", "AI_BLUE_CARRIER"]
                ]
            ]
        ]
        self.WAVE_INTERVALS = [10, 900, 1800, 2400] # please make sure same number of wave intervals and usernames
        self.wave_number = 0

    def register(self, plugin_manager):
        self.plugin_manager = plugin_manager

        # hooks
        self.plugin_manager.register_hook("on_login", self.on_login)
        self.plugin_manager.register_hook("on_chat", self.on_chat)
        self.plugin_manager.register_hook("on_join_request", self.on_join_request)
        self.plugin_manager.register_hook("on_prepare_simulation_server", self.on_prepare_simulation)

        # commands
        self.plugin_manager.register_command("spawn", self.spawn, "Remelia API usecase")
        self.plugin_manager.register_command("ping", self.ping, "Test the current ping to server", "p")
        self.plugin_manager.register_command("global", self.global_chat, "Send a message to everyone in server", "g")

        # time specific
        self.plugin_manager.register_command("timer", self.timer_status, "Check amount of time left", "t")
        self.plugin_manager.register_command("admin", self.admin_commands, "Run the admin commands")

        load_dotenv()
        # print(os.getenv("PASSWORD"))
        self.PASSWORD = os.getenv("PASSWORD")


########################## TIMER ONLY ##############################
    async def broadcast_message(self, packet, player=None, for_all_clients=False):
        """
        send the packet with size!!
        if player argument is None sends to server
        for_all_clients is a special argument, use this with player=None
                        sakuya sends these packets to each client without server help

        Helper to send messages from the timer context (external scope).
        We iterate over connected players to send data.
        """
        if player is not None:
            # send to player
            player.streamWriterObject.write(packet)
        else:
            server_writer = None
            all_players = self.red + self.blue
            if not for_all_clients:
                for user in all_players:
                    if user.serverWriter and not user.serverWriter.is_closing():
                        server_writer = user.serverWriter
                        break
                try:
                    if server_writer is not None:
                        server_writer.write(packet)
                except Exception as e:
                    # print(all_players)
                    logging.error(e)
            else:
                async def send_to_all(playerlist, reqPacket):
                    for user in playerlist:
                        if not user.streamWriterObject.is_closing():
                            user.streamWriterObject.write(reqPacket)
                asyncio.create_task(send_to_all(all_players, packet))


    async def game_timer_loop(self):
        """
        The main background task for the timer.
        """
        print("Game Timer Started")
        try:
            while self.game_running:
                await asyncio.sleep(self.TIMER_INTERVAL)
                self.elapsed_seconds += self.TIMER_INTERVAL

                # msg = f"[Timer] Match time: {self.elapsed_seconds // 60}m {self.elapsed_seconds % 60}s"
                # await self.broadcast_message(msg, to_server=False)
                if self.elapsed_seconds in self.WARN_INTERVALS:
                    left = self.TOTAL_TIME - self.elapsed_seconds
                    time_left_string = f"{left//60}m {left%60}s"
                    await self.broadcast_message(message("Only " + time_left_string + " remaining!"))

                if self.elapsed_seconds in self.WAVE_INTERVALS:
                    for bot in self.WAVE_USERNAMES[0][self.wave_number]: # Red
                        spawner = (FSNETCMD_REQUESTAIAIRPLANE_REMELIA(b"").encode(
                                        with_size=True,
                                        aircraft_name="[RED]UCAV",
                                        ai_username=f"[AI][RED]{bot[0]}",
                                        start_pos_name=bot[1],
                                        iff=3, # IFF 4 in game is IFF 3 in sakuya, we subtract 1, so iff 1 in game is iff 0 in sakuya
                                        g_limit=99999,
                                        patrolMode = True # we want to the ai aircraft to anchor
                                        ))
                        await self.broadcast_message(spawner)

                    for bot in self.WAVE_USERNAMES[1][self.wave_number]: # Blue
                        spawner = (FSNETCMD_REQUESTAIAIRPLANE_REMELIA(b"").encode(
                                        with_size=True,
                                        aircraft_name="[BLUE]UCAV",
                                        ai_username=f"[AI][BLUE]{bot[0]}",
                                        start_pos_name=bot[1],
                                        iff=0, # IFF 4 in game is IFF 3 in sakuya, we subtract 1, so iff 1 in game is iff 0 in sakuya
                                        g_limit=99999,
                                        patrolMode = True # we want to the ai aircraft to anchor
                                        ))
                        await self.broadcast_message(spawner)

                    await self.broadcast_message(message(f"Wave {self.wave_number+1} of AI Aircrafts have been spawned"))
                    self.wave_number += 1


                if self.elapsed_seconds == self.TOTAL_TIME:
                    await self.broadcast_message(message("GAME OVER!"))
                    playerlist = self.red + self.blue
                    async def send_to_all(playerlist):
                        for user in playerlist:
                            # print(user)
                            if not user.streamWriterObject.is_closing():
                                    # print(user.aircraft.id)
                                    if user.aircraft.id != -1:
                                        damage_packet = FSNETCMD_GETDAMAGE.encode(user.aircraft.id,
                                                                        1, 1,
                                                                        user.aircraft.id,
                                                                        100, 11,0, True)

                                        user.streamWriterObject.write(damage_packet)

                    # await self.broadcast_message(damage_packet, None, True)
                    asyncio.create_task(send_to_all(playerlist))
                    self.stop_timer()


        except asyncio.CancelledError:
            print("Game Timer Stopped")
        except Exception as e:
            print(f"Game Timer Error: {e}")
        finally:
            self.game_running = False
            self.timer_task = None

    def start_timer(self):
        if self.timer_task is None or self.timer_task.done():
            self.game_running = True
            self.timer_task = asyncio.create_task(self.game_timer_loop())
            return True
        return False

    def stop_timer(self):
        if self.timer_task:
            self.game_running = False
            self.timer_task.cancel()
            self.elapsed_seconds = 0
            self.wave_number = 0
            self.timer_task = None

    def timer_status(self, full_message, player, message_to_client, message_to_server):
        if self.game_running == False:
            msg = "Game not started yet"
        else:
            left = self.TOTAL_TIME - self.elapsed_seconds
            msg = f"{left // 60}m {left % 60}s remaining"
        message_to_client.put_nowait(message(msg))
        return True

    def admin_commands(self, full_message, player, message_to_client, message_to_server):
        args = full_message.split()
        if len(args) != 3:
            message_to_client.put_nowait(message("Usage : /admin <password> [start|stop]"))

        if args[1] == self.PASSWORD:
            if args[2].lower() == "start":
                if self.timer_task is None:
                    self.start_timer()
                    message_to_client.put_nowait(message("Succesful start"))
                    message_to_server.put_nowait(message("You can now join the game!"))
                else:
                    message_to_client.put_nowait(message("Game is aldready running!"))

                return True

            elif args[2].lower() == "stop":
                try:
                    self.stop_timer()
                except Exception as e:
                    logging.error(e)

                message_to_server.put_nowait(message("The game is has been stopped by admins."))
                playerlist = self.red + self.blue

                async def send_to_all(playerlist):
                    for user in playerlist:
                        # print(user)
                        if not user.streamWriterObject.is_closing():
                                damage_packet = FSNETCMD_GETDAMAGE.encode(user.aircraft.id,
                                                                1, 1,
                                                                user.aircraft.id,
                                                                100, 11,0, True)

                                user.streamWriterObject.write(damage_packet)

                asyncio.create_task(send_to_all(playerlist))

                message_to_client.put_nowait(message("Succesful stop"))
                return True

        message_to_client.put_nowait(message("Usage : /admin <password> [start|stop]"))
        return False

######################################################################################


    def spawn(self, full_message, player, message_to_client, message_to_server):
        message_to_server.put_nowait(FSNETCMD_REQUESTAIAIRPLANE_REMELIA(b"").encode(
                with_size=True,
                aircraft_name="[BLUE]UCAV",
                ai_username=f"Sakuya Izayoi",
                start_pos_name="NORTH10000_01",
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
        elif len(player.alias) >= 16:
            player.streamWriterObject.write(message("Please pick a username shorter than 16 characters and rejoin!"))
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

    def on_prepare_simulation(self, packet, player, message_to_client, message_to_server):
        # packet is sent after login process is complete,
        async def send_intro():
            await asyncio.sleep(1)
            message_to_client.put_nowait(message("\nWelcome to 6th Edition of YSFlight Red vs Blue!"))
            message_to_client.put_nowait(message("The server is currently in open beta. Please report any bugs"))
            message_to_client.put_nowait(message("Use IFF 1 if you're on blue or IFF 4 if you're on red\nThe G-Limiter is set at +/- 14 G's"))
            message_to_client.put_nowait(message("\nUse /g command to send message to global chat\nBy default you are in team-only chat"))
            message_to_client.put_nowait(message("\nHosted from London, UK\n"))
        asyncio.create_task(send_intro())
        return True

    def on_chat(self, packet, player, message_to_client, message_to_server):
        # print(FSNETCMD_TEXTMESSAGE(packet).message)
        if FSNETCMD_TEXTMESSAGE(packet).message.startswith("/"):
            return False

        async def send_to_red(packet):
            for player in self.red:
                try:
                    if player.streamWriterObject and not player.streamWriterObject.is_closing():
                        player.streamWriterObject.write(send(packet))
                except Exception as e:
                    logging.error(e)

        async def send_to_blue(packet):
            for player in self.blue:
                try:
                    if player.streamWriterObject and not player.streamWriterObject.is_closing():
                        player.streamWriterObject.write(send(packet))
                except Exception as e:
                    logging.error(e)

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
            message_to_server.put_nowait(message("[GLOBAL]" + player.alias + ":" + " ".join(args[1::])))
        return False

    def on_join_request(self, packet, player, message_to_client, message_to_server):
        if not self.game_running:
            message_to_client.put_nowait(FSNETCMD_REJECTJOINREQ.encode(with_size=True))
            message_to_client.put_nowait(message("Match hasn't started yet.\nPlease wait for admins to start the game"))
            return False
        data = FSNETCMD_JOINREQUEST(packet)
        # print(data.start_pos)
        try:
            if data.start_pos.startswith("AI"):
                message_to_client.put_nowait(message("You are not allowed to use AI start positions"))
                message_to_client.put_nowait(FSNETCMD_REJECTJOINREQ.encode(with_size=True))
                return False
        except Exception as e:
            logging.error(e)

        if player in self.red:
            if "red" in data.aircraft.lower():
                if player.iff == 3:
                    return True
                else:
                    err ="You are on RED team, use IFF 4\nPress 4 on keyboard"
            else:
                err = "You are on RED team, please use a RED aircraft"

        else:
            if "blue" in data.aircraft.lower():
                if player.iff == 0:
                    return True
                else:
                    err ="You are on BLUE team, use IFF 1\nPress 1 on keyboard"
            else:
                err = "You are on BLUE team, please use a BLUE aircraft"

        message_to_client.put_nowait(message(err))
        message_to_client.put_nowait(FSNETCMD_REJECTJOINREQ.encode(with_size=True))
        return False


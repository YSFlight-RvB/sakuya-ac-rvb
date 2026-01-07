"""
Kill Counter Plugin for Sakuya AC
"""

ENABLED = False
from lib.PacketManager.packets import FSNETCMD_GETDAMAGE, FSNETCMD_ADDOBJECT, FSNETCMD_UNJOIN
from lib.PacketManager.packets import FSNETCMD_REMOVEGROUND
from lib import YSchat

class Plugin:
    def __init__(self):
        self.plugin_manager = None
        self.ground_objects = {}
        self.flying_players = {}
        self.assists = {}

    def register(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.plugin_manager.register_hook('on_get_damage', self.on_damage)
        self.plugin_manager.register_hook('on_add_object_server', self.on_add_object)
        self.plugin_manager.register_hook('on_unjoin', self.on_unjoin)
        self.plugin_manager.register_hook('on_remove_ground_server', self.remove_ground)

    def on_add_object(self, data, player, message_to_client, message_to_server):
        decode = FSNETCMD_ADDOBJECT(data)
        if decode.object_id == -1:
            return True  # Skip invalid IDs

        if decode.object_type == 1:
            # This is a ground object
            self.ground_objects[decode.object_id] = [decode.object_id, decode.iff]
        else:
            # Check is the add object packet is for the new player or not
            if decode.pilot == player.alias:
                self.flying_players[decode.object_id] = [player, 0]
                print(f"New player tracked: ID {decode.object_id} -> {player.username}")
        return True

    def on_damage(self, data, player, message_to_client, message_to_server):
        decode = FSNETCMD_GETDAMAGE(data)
        if decode.victim_id in self.ground_objects:
                # YSFlight is very incosistent, for ADD_OBJECT object type == 0 is a aircraft player
                # however, for GET_DAMAGE object type == 0 is a ground object
                if (player.iff) == self.ground_objects[decode.victim_id][1]:
                    # This is a friendly fire
                    # TODO : Deduct points
                    pass
                else:
                    self.add_asist(decode.victim_id, decode.attacker_id)
        else:
            #print("here!")
            #for f in self.flying_players:
            #    print(self.flying_players[f][0].aircraft.id , self.flying_players[f][0].username)
            attacker_name = self.flying_players[decode.attacker_id][0].username
            victim_name = self.flying_players[decode.victim_id][0].username
            attacker_iff = self.flying_players[decode.attacker_id][0].iff
            victim_iff = self.flying_players[decode.victim_id][0].iff
            if victim_iff != attacker_iff:
                self.add_asist(decode.victim_id, decode.attacker_id)
                print("Unfriendly player damagd!")
            else:
                print("friendly player damaged!!")
                # deduct points
                pass

        return True

    def on_unjoin(self, data, player, message_to_client, message_to_server):
        # A player aircraft gets killed
        decode = FSNETCMD_UNJOIN(data)
        if decode.object_id in self.assists:
            print("killers : " ,  self.assists[decode.object_id][0])
            self.assists.pop(decode.object_id)
        if decode.object_id in self.flying_players:
            self.flying_players.pop(decode.object_id)
        return True

    def remove_ground(self, data, player, message_to_client, message_to_server):
        # A ground object gets killed
        decode = FSNETCMD_REMOVEGROUND(data)
        print(self.assists)
        if decode.object_id in self.assists:
            print("killers : " ,  self.assists[decode.object_id][0])
            self.assists.pop(decode.object_id)
        print(decode.object_id, self.ground_objects[decode.object_id][1])
        self.ground_objects.pop(decode.object_id)
        return True

    def add_asist(self, victim_id, attacker_id):
        if victim_id not in self.assists:
            self.assists[victim_id] = [[attacker_id], attacker_id]
        else:
            if attacker_id not in self.assists[victim_id][0]:
                self.assists[victim_id][0].append(attacker_id) # Store all killers
            self.assists[victim_id][1] = attacker_id        # Last kill

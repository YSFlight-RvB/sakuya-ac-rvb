"""
Enables moderation of words in chat to make it safe for children
"""

from lib.PacketManager.packets import FSNETCMD_TEXTMESSAGE
import re

# To disable moderation completely disable this, set ENABLED = False
# To allow some profanity, set ABOVE_13 = True

ENABLED = True
ABOVE_13 = False

class Plugin:
    def __init__(self):
        self.plugin_manager = None
        if ABOVE_13:
            # Moderate less for teens/adults - only severe language and unsafe links
            moderation_string = r'\b(b[i!]tch|cunt|whore|slut|bastard|nude|naked|porn|penis|vagina|boobs|dick|hate|murder|die|n[i!]gg?(er|a|as|ers)|f[a@]gg?ot?|kike|chink|retard|racist|racism|rape|rapist|molest|https?:\/\/\S+|www\.\S+)\b'
        else:
            # Stricter moderation for children
            moderation_string = (
                r'\b(f[u\*]ck(?:er|ing)?|sh[i!]t(?:ty|head)?|b[i!]tch(?:es|y)?|cunt|'
                r'ass(?:hole|wipe|hat)?|whore|slut(?:ty)?|damn(?:it)?|hell|piss(?:ed)?|'
                r'bastard|nude|naked|sex(?:ual)?|porn(?:ography)?|penis|vagina|boobs?|'
                r'tits?|titties|dick|cock|pussy|boner|horny|jerk(?:\s*off)?|'
                r'masturbat(?:e|ion)|cum(?:ming)?|hate|kill|murder|die|stupid|idiot|'
                r'dumb(?:ass)?|moron|n[i!]gg?(?:er|a|as|ers)|f[a@]gg?ot?|kike|chink|spic|'
                r'wetback|retard(?:ed)?|racist|racism|nazi|rape(?:d|s)?|rapist|'
                r'molest(?:er|ed)?|pedophile|bl[o0][w0]job|handjob|wtf|stfu|gtfo|lmfao|'
                r'https?:\/\/\S+|www\.\S+|1989|ccp|tiananmen\s*square|tiananmen|'
                r'tian\s*an\s*men|tian\s*men|tian\s*anmen|tian\s*an\s*men\s*square|'
                r'taiwan|taiwan\s*province|taiwan\s*island|chinese\s*communist\s*party|'
                r'winnie\s*the\s*pooh|winnie\s*pooh|xi\s*jinping|xjp|tank\s*man|tankman|'
                r'6\s*4|six\s*four|june\s*4th|june\s*4|64\s*incident|64\s*event|'
                r'6\s*4\s*event|6\s*4\s*incident|june\s*4th\s*incident|june\s*4th\s*event|'
                r'chinese\s*government|chinese\s*regime|chinese\s*authorities|'
                r'chinese\s*state|chinese\s*leadership|chinese\s*party|chinese\s*army|pla|'
                r'people\s*liberation\s*army|chinese\s*military|chinese\s*police|'
                r'chinese\s*security|chinese\s*censorship|chinese\s*firewall|'
                r'great\s*firewall|gfw|chinese\s*propaganda|chinese\s*media|'
                r'chinese\s*news)\b'
            )

        self.filter_regex = re.compile(moderation_string, re.IGNORECASE)

    def register(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.plugin_manager.register_hook('on_chat', self.on_chat)

    @staticmethod
    def censor_match_dynamic_length(match_obj):
        """
        This function is called by re.sub for each match.
        It returns a string of '#' characters matching the length of the found word.
        """
        matched_word = match_obj.group(0)  # Get the actual text that was matched
        return '#' * len(matched_word)

    def on_chat(self, data, player, message_to_client, message_to_server):
        decode = FSNETCMD_TEXTMESSAGE(data)
        msg = decode.raw_message

        # Check if the message contains filtered content
        censored_text = self.filter_regex.sub(self.censor_match_dynamic_length, msg)

        if censored_text != msg:
            # Create a new message with censored content
            message = FSNETCMD_TEXTMESSAGE.encode(censored_text, with_size=True)
            message_to_server.put_nowait(message)
            return False
        return True

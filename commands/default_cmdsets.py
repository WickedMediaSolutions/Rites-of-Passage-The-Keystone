"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # Phase 16 — Player gameplay commands
        #
        from commands.command import (
            CmdScore, CmdInventory, CmdEquipment,
            CmdEquip, CmdUnequip,
            CmdAttack, CmdUse,
            CmdQuest, CmdCurrency,
            CmdShop, CmdBuy, CmdSell,
            # Phase 19 — Socials / Guild / Sect / PvP
            CmdSocial, CmdGuild, CmdSect, CmdPvP,
            CmdTalk, CmdReply,
        )
        self.add(CmdScore())
        self.add(CmdInventory())
        self.add(CmdEquipment())
        self.add(CmdEquip())
        self.add(CmdUnequip())
        self.add(CmdAttack())
        self.add(CmdUse())
        self.add(CmdQuest())
        self.add(CmdCurrency())
        self.add(CmdShop())
        self.add(CmdBuy())
        self.add(CmdSell())
        #
        # Phase 19 — Socials / Guild / Sect / PvP
        #
        self.add(CmdSocial())
        self.add(CmdGuild())
        self.add(CmdSect())
        self.add(CmdPvP())
        self.add(CmdTalk())
        self.add(CmdReply())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # Post-Phase-20 — Professional WHO list (overloads Evennia default)
        #
        from commands.command import CmdWho
        self.add(CmdWho())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #

"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from world.data.enums import PvPMode
from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    _PVP_MODE_ATTR = "rop_pvp_mode"

    @property
    def room_id(self) -> str | None:
        """
        Return the stable world_room_id for this room, or None.

        This is set by the Silvermere builder (build_silvermere.py)
        and used by the world-integration layer for spawn placement.
        """
        return self.attributes.get("world_room_id")

    @property
    def pvp_mode(self) -> PvPMode:
        """
        Return the PvP mode for this room.

        Defaults to PvPMode.SAFE.  Builders set this via
        ``room.pvp_mode = PvPMode.CONTESTED`` (or any other
        PvPMode value).
        """
        raw = self.attributes.get(self._PVP_MODE_ATTR)
        if raw is None:
            return PvPMode.SAFE
        if isinstance(raw, PvPMode):
            return raw
        try:
            return PvPMode(raw)
        except ValueError:
            return PvPMode.SAFE

    @pvp_mode.setter
    def pvp_mode(self, value: PvPMode) -> None:
        """Set the PvP mode for this room."""
        if not isinstance(value, PvPMode):
            raise TypeError(f"pvp_mode must be a PvPMode, got {type(value).__name__}")
        self.attributes.add(self._PVP_MODE_ATTR, value)

    def at_object_receive(self, obj, source_location, move_type="move", **kwargs):
        """Called when another object enters this room.

        When a player enters the room, every world NPC in the room is
        given a chance to start mob combat via try_start_mob_combat.
        """
        super().at_object_receive(obj, source_location, move_type=move_type, **kwargs)

        # Ignore entering world NPCs — only players trigger the scan.
        if obj.attributes.get("world_npc"):
            return

        # Ignore objects with no account (non-player objects).
        if not obj.account:
            return

        from world.world_integration import try_start_mob_combat

        for other in self.contents:
            if not other.attributes.get("world_npc"):
                continue
            spawn_id = other.attributes.get("world_spawn_id")
            if spawn_id is not None:
                try_start_mob_combat(other, spawn_id)

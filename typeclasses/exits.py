"""
Rites of Passage Exit typeclass.
"""

from evennia.objects.objects import DefaultExit
from .objects import ObjectParent


DIRECTION_ALIASES = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "northeast": "ne",
    "northwest": "nw",
    "southeast": "se",
    "southwest": "sw",
    "up": "u",
    "down": "d",
}


class Exit(ObjectParent, DefaultExit):
    """
    ROP Exit.

    Standard directional exits automatically receive their normal
    movement abbreviation as a real Evennia object alias.
    """

    def at_object_creation(self):
        super().at_object_creation()

        abbreviation = DIRECTION_ALIASES.get(self.key.strip().lower())
        if abbreviation and abbreviation not in self.aliases.all():
            self.aliases.add(abbreviation)

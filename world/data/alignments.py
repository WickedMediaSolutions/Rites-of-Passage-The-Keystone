ALIGNMENT_REGISTRY = {}


def register_alignment(alignment_id, name, description=""):
    """Create or update an alignment entry in the registry.

    When the alignment_id already exists, only name and description are
    overwritten — any unrelated existing fields are preserved.
    """
    entry = ALIGNMENT_REGISTRY.setdefault(
        alignment_id,
        {"id": alignment_id},
    )
    entry["name"] = name
    entry["description"] = description


def get_alignment(alignment_id):
    """Return the alignment dict for *alignment_id*, or None."""
    return ALIGNMENT_REGISTRY.get(alignment_id)


def alignment_exists(alignment_id):
    """Return True if *alignment_id* is already registered."""
    return alignment_id in ALIGNMENT_REGISTRY
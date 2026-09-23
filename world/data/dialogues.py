# ---------------------------------------------------------------------------
# Dialogue Registry
# ---------------------------------------------------------------------------

from world.data.quests import accept_quest, complete_quest

DIALOGUE_REGISTRY: dict[str, dict] = {}


def register_dialogue(
    dialogue_id: str,
    name: str,
    description: str = "",
    start_node_id: str | None = None,
    nodes: list[dict] | None = None,
) -> dict:
    """Create or update a dialogue entry in DIALOGUE_REGISTRY.

    *nodes* defaults to a fresh empty list when ``None`` is passed.
    Any unrelated existing fields on the entry are preserved when updating.
    Returns the stored dict.
    """
    if nodes is None:
        nodes = []

    existing = DIALOGUE_REGISTRY.get(dialogue_id, {})
    DIALOGUE_REGISTRY[dialogue_id] = {
        **existing,
        "dialogue_id": dialogue_id,
        "name": name,
        "description": description,
        "start_node_id": start_node_id,
        "nodes": nodes,
    }
    return DIALOGUE_REGISTRY[dialogue_id]


def get_dialogue(dialogue_id: str) -> dict | None:
    """Return the dialogue definition for *dialogue_id*, or None."""
    return DIALOGUE_REGISTRY.get(dialogue_id)


def dialogue_exists(dialogue_id: str) -> bool:
    """Return True if *dialogue_id* is a known dialogue definition."""
    return dialogue_id in DIALOGUE_REGISTRY

def get_dialogue_node(dialogue_id: str, node_id: str) -> dict | None:
    """Return the node dict with matching ``node["id"]``, or None if missing."""
    dialogue = get_dialogue(dialogue_id)
    if dialogue is None:
        return None
    for node in dialogue.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def start_dialogue(dialogue_id: str) -> dict | None:
    """Resolve the dialogue's start node and return it, or None if missing."""
    dialogue = get_dialogue(dialogue_id)
    if dialogue is None:
        return None
    start_node_id = dialogue.get("start_node_id")
    if start_node_id is None:
        return None
    return get_dialogue_node(dialogue_id, start_node_id)


def choose_response(
    dialogue_id: str,
    node_id: str,
    response_index: int,
    cd=None,
) -> tuple[dict | None, dict | None]:
    """Return ``(response_dict, next_node_or_none)`` for the selected response.

    If *response_index* is out of range or the current node is missing the
    call returns ``(None, None)``.  When the chosen response carries a
    ``nextNodeId`` the matching node is resolved and returned as the second
    tuple element.

    If *cd* (CharacterData) is provided, the function will also process any
    ``startsQuestId`` or ``completesQuestId`` fields on the response by
    calling the corresponding quest service functions.  Quest failures do
    **not** block dialogue navigation.
    """
    current_node = get_dialogue_node(dialogue_id, node_id)
    if current_node is None:
        return (None, None)

    responses = current_node.get("responses", [])
    if not (0 <= response_index < len(responses)):
        return (None, None)

    response = responses[response_index]

    # ------------------------------------------------------------------
    # Quest hooks (fire-and-forget — never block navigation)
    # ------------------------------------------------------------------
    if cd is not None:
        quest_id: str

        quest_id = response.get("startsQuestId", "")
        if quest_id:
            accept_quest(cd, quest_id)

        quest_id = response.get("completesQuestId", "")
        if quest_id:
            complete_quest(cd, quest_id)

    next_node = None
    if response.get("nextNodeId") is not None:
        next_node = get_dialogue_node(dialogue_id, response["nextNodeId"])

    return (response, next_node)
"""
Maps every card in the 47-card deck to a unique integer 0-46 and back.
Bitmask representation: bit i is set iff card with id i is in the hand.
"""
from backend.game.cards import Card
from backend.game.deck import build_deck


def build_card_map() -> tuple[dict[Card, int], dict[int, Card]]:
    """
    Returns (card_to_id, id_to_card) using the canonical deck order from build_deck().
    IDs are assigned 0-46 in the order cards appear in build_deck().
    """
    deck = build_deck()
    card_to_id: dict[Card, int] = {}
    id_to_card: dict[int, Card] = {}
    for i, card in enumerate(deck):
        card_to_id[card] = i
        id_to_card[i] = card
    return card_to_id, id_to_card


# Module-level singletons built at import time
CARD_TO_ID, ID_TO_CARD = build_card_map()


def hand_to_mask(cards: list[Card]) -> int:
    """Convert a list of cards to a bitmask integer."""
    mask = 0
    for card in cards:
        mask |= (1 << CARD_TO_ID[card])
    return mask


def mask_to_cards(mask: int, id_to_card: dict[int, Card] = None) -> list[Card]:
    """Convert a bitmask integer back to a list of cards."""
    if id_to_card is None:
        id_to_card = ID_TO_CARD
    cards = []
    while mask:
        lsb = mask & (-mask)          # isolate lowest set bit
        bit_pos = lsb.bit_length() - 1
        cards.append(id_to_card[bit_pos])
        mask ^= lsb
    return cards

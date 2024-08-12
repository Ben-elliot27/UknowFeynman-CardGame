import sys


import random
from collections import Counter

class Particle:
    def __init__(self, name, charge, has_mass, particle_type):
        self.name = name
        self.charge = charge
        self.has_mass = has_mass
        self.particle_type = particle_type


particles = {
    "bosons": [
        Particle("photon", 0, False, "boson"),
        Particle("w", 1, True, "boson"),
        Particle("g", 0, True, "boson"),
        Particle("H", 0, True, "boson")
    ],
    "leptons": [
        Particle("e", 1, True, "lepton"),
        Particle("m", 1, True, "lepton"),
        Particle("tau", 1, True, "lepton"),
        Particle("ve", 0, False, "lepton"),
        Particle("vu", 0, False, "lepton"),
        Particle("vt", 0, False, "lepton")
    ],
    "quarks": [
        Particle("u", 2 / 3, True, "quark"),
        Particle("d", - 1 / 3, True, "quark"),
        Particle("c", 2 / 3, True, "quark"),
        Particle("s", - 1 / 3, True, "quark"),
        Particle("t", 2 / 3, True, "quark"),
        Particle("b", - 1 / 3, True, "quark")
    ],
    "special cards": [
        Particle("skip", -20, False, "special"),
        Particle("reverse", -20, False, "special"),
        Particle("flip", -20, False, "special"),
        Particle("change", -20, False, "special"),
        Particle("null", -20, False, "special"),
    ]
}

# GLOBAL - dynamic use
regular_cards = ['e', 'm', 'tau', 've', 'vu', 'vt', 'u', 'd', 'c', 's', 't',
                 'b']  # Regular cards that have no special action
bosons = ['w', 'photon', 'g', 'H']

allowed_hadrons = [['u', 'u', 'd'], ['u', 'd', 'd']]

opposite_colors = {
    'red': 'pink',
    'pink': 'red',
    'blue': 'purple',
    'purple': 'blue',
    'yellow': 'orange',
    'orange': 'yellow',
    'green': 'cyan',
    'cyan': 'green'
}


class CardAction:
    def execute(self, game_state, player: str, card: dict):
        """
        Execute action for certain card
        :param game_state: game object
        :param player: current or relevant player for action to happen on
        :param card: Other card dependent on action
        :return:
        """
        pass


class FlipAction(CardAction):
    def execute(self, game_state, player, card):
        game_state.is_flipped = not game_state.is_flipped
        side = game_state.get_side()
        new_discard = game_state.draw_safe_cards(side)
        game_state.discard_pile.extend(new_discard)
        game_state.current_card = new_discard[0]
        game_state.bottom_card = new_discard[1]


class ReverseAction(CardAction):
    def execute(self, game_state, player, card):
        game_state.direction *= -1


class SkipAction(CardAction):
    def execute(self, game_state, player, card):
        game_state.current_player_index = (game_state.current_player_index + game_state.direction) % len(
            game_state.players)


class DrawAction(CardAction):
    def __init__(self, draw_count):
        self.draw_count = draw_count

    def execute(self, game_state, player, card):
        out = game_state.draw_cards(self.draw_count, player)
        game_state.current_player_index = (game_state.current_player_index + game_state.direction) % len(
            game_state.players)
        return out


class WildAction(CardAction):
    def __init__(self, part_type):
        self.H = part_type == 'H'

    def execute(self, game_state, player, card):
        if self.H:
            game_state.draw_until_valid_play()
    def change_color(self, game_state):
        game_state.change_color()


card_actions = {
    'flip': FlipAction(),
    'reverse': ReverseAction(),
    'skip': SkipAction(),
    'w': DrawAction(1),
    'photon': DrawAction(2),
    'g': DrawAction(4),
    'H': WildAction('H'),
    'change': WildAction('change')
}


def play_card(game_state, player, cards, socketio, sid):
    side = game_state.get_side()
    if len(cards) == 1:
        card = cards[0]
    elif check_multi_card(cards, side, game_state.current_card, game_state.bottom_card):
        # Handle the playing of multiple cards
        # Logic of person picking up
        if game_state.current_card[side]['value'] == 'g':
            prev_player = (game_state.current_player_index - game_state.direction) % len(game_state.players)
            card_actions['g'].execute(game_state, prev_player, {})
            game_state.is_flipped = not game_state.is_flipped

        game_state.current_player_index = (game_state.current_player_index + game_state.direction) % len(
            game_state.players)
        game_state.discard_pile.extend(cards)
        game_state.bottom_card = cards[-2]
        game_state.current_card = cards[-1]  # Could turn this into a hadron card - need to implement making other person pick up
        remove_cards_from_hand(game_state, player, cards)
        return True
    else:
        return False
    if is_valid_play(game_state, card, socketio, sid):
        action = card_actions.get(card[side]['value'])
        if action:
            if card[side]['value'] in ['flip', 'reverse', 'skip']:
                action.execute(game_state, player, card)
            if card[side]['color'] == 'wild':
                action.change_color(game_state)
                game_state.discard_pile.append(card)
                game_state.bottom_card = game_state.current_card
                game_state.current_card = card
                game_state.hands[player].remove(card)
                return True

        # # Handle special cases if current card has actions
        # current_action = card_actions.get(game_state.current_card[side]['value'])
        # if current_action:
        #     current_action.execute(game_state, player, game_state.current_card)
        #     game_state.current_player_index = (game_state.current_player_index + game_state.direction) % len(
        #         game_state.players)

        game_state.current_player_index = (game_state.current_player_index + game_state.direction) % len(
            game_state.players)
        game_state.discard_pile.append(card)
        game_state.bottom_card = game_state.current_card
        game_state.current_card = card
        game_state.hands[player].remove(card)
        return True


    return False


def remove_cards_from_hand(game_state, player, cards):
    # Count the occurrences of each card to remove
    cards_to_remove = Counter(map(str, cards))

    # Create a new hand and count the cards to be kept
    new_hand = []
    for card in game_state.hands[player]:
        card_str = str(card)
        if cards_to_remove[card_str] > 0:
            cards_to_remove[card_str] -= 1
        else:
            new_hand.append(card)

    game_state.hands[player] = new_hand
def check_multi_card(cards, side, current_card, bottom_card):
    # Check the playing of multiple cards
    if len(cards) > 3:
        # Currently no rules implemented for playing more than 3 cards at a time
        return False
    elif current_card[side]['value'] == 'g':
        return (
            cards[0][side]['value'] == 'flip' and
            cards[0][side]['color'] == current_card[side]['color'] and
            cards[1][side]['color'] == opposite_colors.get(cards[0][side]['color']) and
            cards[1][side]['value'] == bottom_card[side]['value']
        )
    else:
        values = [card[side]['value'] for card in cards]
        return any_combination_of(values, allowed_hadrons)

def any_combination_of(values, combinations):
    # Convert the input list to a Counter
    input_counter = Counter(values)

    # Iterate over each sublist in the comparison list
    for sublist in combinations:
        # Convert the sublist to a Counter
        sublist_counter = Counter(sublist)
        # Check if input Counter matches the sublist Counter
        if input_counter == sublist_counter:
            return True
    # If no match is found
    return False


def is_valid_play(game_state, card, socketio, sid):
    side = game_state.get_side()
    current_color = game_state.current_card[side]['color']
    current_value = game_state.current_card[side]['value']
    played_color = card[side]['color']
    played_value = card[side]['value']

    expr = current_color == played_color or current_value == played_value or played_color == 'wild'
    if not expr:
        socketio.emit('error', {'message': 'Colors not matching or particle type not the same'}, to=sid)
        return False

    bottom_value = game_state.bottom_card[side]['value']
    bottom_particle = find_particle(bottom_value)
    current_particle = find_particle(current_value)
    played_particle = find_particle(played_value)

    if current_particle.particle_type == "boson":
        if played_particle.particle_type == "boson" or played_particle.particle_type != bottom_particle.particle_type:
            socketio.emit('error', {'message': "Current particle is a boson and played card doesn't match bottom card family"}, to=sid)
            return False
        return check_boson_play(bottom_particle, played_particle, current_particle, socketio, sid)

    if played_value == 'H':
        if current_particle.has_mass:
            return True
        else:
            socketio.emit('error', {'message': 'Can only play a Higgs on a particle with mass'}, to=sid)
            return False

    if played_value == "photon":
        if current_particle.charge > 0:
            return True
        else:
            socketio.emit('error', {'message': 'Can only play a photon on a particle with non-zero charge'}, to=sid)
            return False

    if played_value == "g":
        if current_particle.particle_type == "quark":
            return True
        else:
            socketio.emit('error', {'message': 'Can only play a gluon on a quark'}, to=sid)
            return False

    if played_value == "w":
        if current_particle.particle_type != "special":
            return True
        else:
            socketio.emit('error', {'message': 'Cannot play a W boson on special cards'}, to=sid)
            return False
    return True


def find_particle(value):
    for particle_list in particles.values():
        for particle in particle_list:
            if particle.name == value:
                return particle
    return None


def check_boson_play(bottom_particle, played_particle, current_particle, socketio, sid):
    if (bottom_particle.charge * 3 + current_particle.charge * 3 == played_particle.charge * 3 or
            bottom_particle.charge * 3 - current_particle.charge * 3 == played_particle.charge * 3):
        if current_particle.name == 'w':
            if played_particle.name != bottom_particle.name:
                return True
            else:
                socketio.emit("error", {"message": "W bosons need to change the particle type"})
                return False
        if current_particle.name == 'H':
            socketio.emit("error", {"message": "Cannot play on Higgs, press the deck to draw cards"})
            return False
        if played_particle.name == bottom_particle.name:
            return True
        else:
            socketio.emit("error", {"message": "Particle needs to be the same as the bottom particle for the interaction"})
            return False
    socketio.emit("error", {"message": "Charge conservation not met"})
    return False


def create_deck():
    """
    Handles creating of the deck and logic
    :return: deck: [cards]
    """
    colors = ['red', 'green', 'blue', 'yellow']
    back_colors = ['pink', 'cyan', 'orange', 'purple']
    values = ['e', 'm', 'tau', 've', 'vu', 'vt', 'u', 'd', 'c', 's', 't', 'b', 'skip', 'reverse', 'w', 'photon', 'g',
              'flip']
    back_values = values.copy()
    wild_cards = ['H', 'change']
    wild_color = 'wild'

    deck = []

    # Create normal cards
    for color in colors:
        for value in values:
            back_color = random.choice(back_colors)
            back_value = random.choice(back_values)
            deck.append({
                'front': {'color': color, 'value': value},
                'back': {'color': back_color, 'value': back_value}
            })

    # Add wild cards on the opposite side of non-wild cards
    # Adding 4 'H' cards on the back side and 4 'change' cards on the front side
    # CHANGE BELOW NUMBER TO CHANGE NUM OF WILDS
    for card in deck[:4]:  # Select first 4 cards for wild cards placement
        # For each of the first 4 cards, create new wild cards
        deck.append({
            'front': {'color': card['front']['color'], 'value': card['front']['value']},
            'back': {'color': wild_color, 'value': wild_cards[0]}
        })
        deck.append({
            'front': {'color': wild_color, 'value': wild_cards[1]},
            'back': {'color': card['back']['color'], 'value': card['back']['value']}
        })

    random.shuffle(deck)
    return deck


def decay_press_logic(game, d_pressed: bool, socketio):
    sys.stdout.flush()
    if not d_pressed:
        game.draw_cards(2, game.player_on_uno)
        game.player_on_uno = None
        socketio.emit("update_game_state", {'game': game.to_dict(), 'hands': game.hands, 'player': game.player_on_uno},
                      room=game.id)


def change_current_card_color(game_state, color):
    side = game_state.get_side()
    game_state.current_card[side]['color'] = color

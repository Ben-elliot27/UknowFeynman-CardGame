import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

games = {}  # Dictionary to store game states

class Game:
    def __init__(self, id, players):
        self.id = id
        self.players = players
        self.is_flipped = False
        self.deck = self.create_deck()
        self.discard_pile = [self.draw_card(), self.draw_card()]  # Start with a card in the discard pile
        self.direction = 1
        self.current_card = self.discard_pile[-1]  # Current card is the top of discard pile
        self.bottom_card = self.discard_pile[-2]
        self.current_player_index = 0
        self.hands = {player: self.draw_cards(7) for player in players}

    def create_deck(self):
        colors = ['red', 'green', 'blue', 'yellow']
        back_colors = ['pink', 'cyan', 'orange', 'purple']
        values = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'skip', 'reverse', 'draw2', 'flip']
        back_values = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'skip', 'reverse', 'draw2', 'flip']
        deck = []
        for color in colors:
            for value in values:
                back_color = random.choice(back_colors)
                back_value = random.choice(back_values)
                deck.append({'front': {'color': color, 'value': value},
                             'back': {'color': back_color, 'value': back_value}})
        random.shuffle(deck)
        return deck

    def draw_card(self):
        return self.deck.pop()

    def draw_cards(self, count):
        return [self.draw_card_from_deck()[0] for _ in range(count)]

    def play_card(self, player, card):
        if self.is_valid_play(card):
            self.discard_pile.append(card)
            self.bottom_card = self.current_card
            self.current_card = card
            self.hands[player].remove(card)
            if self.is_flipped:
                side = 'back'
            else:
                side = 'front'

            if card[side]['value'] == 'flip':
                self.is_flipped = not self.is_flipped

            elif card[side]['value'] == 'reverse':
                self.direction *= -1
            elif card[side]['value'] == 'skip':
                self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
            elif card[side]['value'] == 'draw2':
                next_player = self.players[(self.current_player_index + self.direction) % len(self.players)]
                self.hands[next_player].extend(self.draw_cards(2))
            elif card[side]['value'] == 'draw4':
                next_player = self.players[(self.current_player_index + self.direction) % len(self.players)]
                self.hands[next_player].extend(self.draw_cards(4))
            self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
            return True
        return False

    def is_valid_play(self, card):
        if self.is_flipped:
            current_color = self.current_card['back']['color']
            current_value = self.current_card['back']['value']
            return (current_color == card['back']['color'] or current_value == card['back']['value'] or card['back']['value'] == 'flip')
        else:
            current_color = self.current_card['front']['color']
            current_value = self.current_card['front']['value']
            return (current_color == card['front']['color'] or current_value == card['front']['value'] or card['front']['value'] == 'flip')

    def draw_card_from_deck(self):
        if self.deck:
            drawn_card = self.draw_card()
            return (drawn_card, False)
        else:
            # Reshuffle discard pile into deck except for the top card
            top_card = self.discard_pile.pop()
            random.shuffle(self.discard_pile)
            self.deck = self.discard_pile
            self.discard_pile = [top_card, self.draw_card()]
            return (self.draw_card_from_deck()[0], True)


    def to_dict(self):
        return {
            'id': self.id,
            'players': self.players,
            'deck': self.deck,
            'discard_pile': self.discard_pile,
            'direction': self.direction,
            'current_card': self.current_card,
            'current_player_index': self.current_player_index,
            'hands': self.hands,
            'is_flipped': self.is_flipped,
            'bottom_card': self.bottom_card
        }


@app.route('/')
def index():
    return render_template("index.html")

@socketio.on('create_game')
def handle_create_game(data):
    player_name = data['player_name']
    game_id = str(len(games) + 1)
    game = Game(game_id, [player_name])
    games[game_id] = game
    join_room(game_id)
    emit('game_created', {'game_id': game_id, 'player_name': player_name, 'hands': game.hands[player_name]}, room=game_id)
    emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands[player_name]}, room=game_id)


@socketio.on('join_game')
def handle_join_game(data):
    player_name = data['player_name']
    game_id = data['game_id']
    game = games.get(game_id)
    if game:
        game.players.append(player_name)
        game.hands[player_name] = game.draw_cards(7)
        join_room(game_id)
        emit('game_joined', {'game_id': game_id, 'player_name': player_name, 'hands': game.hands[player_name]}, room=game_id)
        emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands[player_name]}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})

@socketio.on('play_card')
def handle_play_card(data):
    game_id = data['game_id']
    player_name = data['player_name']
    card = data['card']
    game = games.get(game_id)
    if game and game.play_card(player_name, card):
        emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands[player_name]}, room=game_id)
    else:
        emit('error', {'message': 'Invalid play'})

@socketio.on('draw_card')
def handle_draw_card(data):
    game_id = data['game_id']
    player_name = data['player_name']
    game = games.get(game_id)
    if game:
        drawn_card, reshuffle = game.draw_card_from_deck()
        if reshuffle:
            emit('shuffle_the_deck', {}, room=game_id)
        game.hands[player_name].append(drawn_card)
        emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands[player_name]}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})


@socketio.on('request_hand')
def handle_request_hand(data):
    player_name = data['player_name']
    is_flipped = data['is_flipped']

    # Find the game ID that the player is part of
    game_id = next((game_id for game_id, game in games.items() if player_name in game.players), None)
    if game_id is None:
        emit('error', {'message': 'Game not found'})
        return

    game = games[game_id]
    hands = game.hands[player_name]

    # Emit the updated hand to the requesting client only
    emit('update_hand', {'hands': hands, 'is_flipped': is_flipped}, room=request.sid)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
# CURRENT
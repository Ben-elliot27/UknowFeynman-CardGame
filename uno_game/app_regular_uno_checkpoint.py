import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template
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
        self.deck = self.create_deck()
        self.discard_pile = [self.draw_card()]  # Start with a card in the discard pile
        self.direction = 1
        self.current_card = self.discard_pile[-1]  # Current card is the top of discard pile
        self.current_player_index = 0
        self.hands = {player: self.draw_cards(7) for player in players}

    def create_deck(self):
        colors = ['red', 'green', 'blue', 'yellow']
        values = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'skip', 'reverse', 'draw2']
        deck = [{'color': color, 'value': value} for color in colors for value in values]
        deck.extend([{'color': 'wild', 'value': 'wild'}, {'color': 'wild', 'value': 'draw4'}] * 4)
        random.shuffle(deck)
        return deck

    def draw_card(self):
        return self.deck.pop()

    def draw_cards(self, count):
        return [self.draw_card() for _ in range(count)]

    def play_card(self, player, card):
        if self.is_valid_play(card):
            self.discard_pile.append(card)
            self.current_card = card
            self.hands[player].remove(card)
            if card['value'] == 'reverse':
                self.direction *= -1
            elif card['value'] == 'skip':
                self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
            elif card['value'] == 'draw2':
                next_player = self.players[(self.current_player_index + self.direction) % len(self.players)]
                self.hands[next_player].extend(self.draw_cards(2))
            elif card['value'] == 'draw4':
                next_player = self.players[(self.current_player_index + self.direction) % len(self.players)]
                self.hands[next_player].extend(self.draw_cards(4))
            self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
            return True
        return False

    def is_valid_play(self, card):
        return (self.current_card is None or
                card['color'] == self.current_card['color'] or
                card['value'] == self.current_card['value'] or
                card['color'] == 'wild')

    def draw_card_from_deck(self):
        if self.deck:
            return self.draw_card()
        else:
            # Reshuffle discard pile into deck except for the top card
            top_card = self.discard_pile.pop()
            random.shuffle(self.discard_pile)
            self.deck = self.discard_pile
            self.discard_pile = [top_card]
            return self.draw_card()

    def to_dict(self):
        return {
            'id': self.id,
            'players': self.players,
            'deck': self.deck,
            'discard_pile': self.discard_pile,
            'direction': self.direction,
            'current_card': self.current_card,
            'current_player_index': self.current_player_index,
            'hands': self.hands
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
        emit('update_game_state', {'game': game.to_dict()}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})

@socketio.on('play_card')
def handle_play_card(data):
    game_id = data['game_id']
    player_name = data['player_name']
    card = data['card']
    game = games.get(game_id)
    if game and game.play_card(player_name, card):
        emit('card_played', {'game': game.to_dict()}, room=game_id)
    else:
        emit('error', {'message': 'Invalid play'})

@socketio.on('draw_card')
def handle_draw_card(data):
    game_id = data['game_id']
    player_name = data['player_name']
    game = games.get(game_id)
    if game:
        drawn_card = game.draw_card_from_deck()
        game.hands[player_name].append(drawn_card)
        emit('update_game_state', {'game': game.to_dict()}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

import eventlet
eventlet.monkey_patch()
import time
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import random
import GameLogic, Admin_Controlls
import sys
from questionEvalsSite import questionEvals
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

games = {}  # Dictionary to store game states

adminPword = "6aSymmetryInPhysics"

class Game:
    def __init__(self, idx, players):
        self.id = idx
        self.players = players
        self.player_ids = {}
        self.is_flipped = False
        self.deck = GameLogic.create_deck()
        self.discard_pile = self.draw_safe_cards(side='front')  # Start with a card in the discard pile
        self.direction = 1
        self.current_card = self.discard_pile[-1]  # Current card is the top of discard pile
        self.bottom_card = self.discard_pile[-2]
        self.current_player_index = 0
        self.hands = {player: self.draw_cards(7, None) for player in players}
        self.player_on_uno = None
        self.time_of_last_action = time.time()

    def draw_safe_cards(self, side):
        trial1 = self.draw_card()
        trial2 = self.draw_card()
        while trial1[side]['value'] not in GameLogic.regular_cards:
            self.deck.extend([trial1])  # Put cards back in deck
            random.shuffle(self.deck)
            trial1 = self.draw_card()
        cur_col = trial1[side]['color']
        cur_val = trial1[side]['value']
        while (trial2[side]['color'] != cur_col or trial2['front']['value'] == cur_val or
               trial2[side]['value'] not in GameLogic.regular_cards):
            self.deck.extend([trial2])  # Put cards back in deck
            random.shuffle(self.deck)
            trial2 = self.draw_card()
        return [trial1, trial2]

    def draw_card(self):
        return self.deck.pop()

    def draw_cards(self, count: int, player: str | None):
        self.time_of_last_action = time.time()
        cards = []
        for _ in range(count):
            out, reshuffle = self.draw_card_from_deck()
            cards.append(out)
            if reshuffle:
                socketio.emit('shuffle_the_deck', {}, room=self.id)
        if player:
            self.hands[player].extend(cards)
        return cards

    def play_card(self, player, cards, sid):
        self.time_of_last_action = time.time()
        # Play a card - now a list of card(s)
        successful_play = GameLogic.play_card(self, player, cards, socketio, sid)
        if successful_play:
            player = self.players[self.current_player_index]
            player_prev = self.players[(self.current_player_index - self.direction) % len(
                self.players)]
            if len(self.hands[player_prev]) == 1:
                self.player_on_uno = player_prev
                socketio.emit('show_uno_challenge_button', {'player_on_one_card': player_prev}, room=self.id)
            elif len(self.hands[player]) == 0:
                self.reset(self.id, self.players)
                socketio.emit('update_game_state', {'game': self.to_dict(), 'hands': self.hands, 'player': player}, room=self.id)
        return successful_play

    def reset(self, id, players=None):
        if players == None:
            players = self.players  # If no players given reset with the same players
        socketio.emit("shuffle_the_deck", {}, to=self.id)
        self.time_of_last_action = time.time()
        self.id = id
        self.players = players
        self.is_flipped = False
        self.deck = GameLogic.create_deck()
        self.discard_pile = self.draw_safe_cards(side='front')  # Start with a card in the discard pile
        self.direction = 1
        self.current_card = self.discard_pile[-1]  # Current card is the top of discard pile
        self.bottom_card = self.discard_pile[-2]
        self.current_player_index = 0
        self.hands = {player: self.draw_cards(7, None) for player in players}
        self.player_on_uno = None
        for plyr, plyr_id in self.player_ids.items():
            socketio.emit('update_game_state', {'game': self.to_dict(), 'hands': self.hands, 'player': plyr},
                          to=plyr_id)

    def draw_card_from_deck(self):
        if self.deck:
            drawn_card = self.draw_card()
            try:
                if self.players[self.current_player_index] == self.player_on_uno:
                    self.player_on_uno = None
            except AttributeError:
                pass

            return drawn_card, False
        else:
            # Reshuffle discard pile into deck except for the top card
            top_card = self.discard_pile.pop()
            random.shuffle(self.discard_pile)
            self.deck = self.discard_pile
            self.discard_pile = [top_card, self.draw_card()]
            return self.draw_card_from_deck()[0], True

    def change_color(self):
        socketio.emit('show_color_change_button', {'isFlipped': self.is_flipped,
                                                   'player_to_choose': self.players[self.current_player_index]}, room=self.id)

    def draw_until_valid_play(self):
        # Function to draw until valid play
        side = self.get_side()

        # When H played apply to current player when Higgs was last card and couldn't be played
        player = self.players[self.current_player_index]

        new_card = self.draw_cards(1, player)[0]
        while new_card[side]['color'] != self.current_card[side]['color']:
            time.sleep(0.6)
            new_card = self.draw_cards(1, player)[0]
            socketio.emit('update_game_state', {'game': self.to_dict(), 'hands': self.hands, 'player': player}, room=self.id)


    def get_side(self):
        # Function to get current side
        return 'back' if self.is_flipped else 'front'

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
            'bottom_card': self.bottom_card,
            'player_on_uno': self.player_on_uno,
            'player_ids': self.player_ids,
            'time_of_last_action': self.time_of_last_action
        }

def get_valid_gameId(gameId):
    gameIdTrial = gameId
    existing_gameIds = set(games.keys())
    i = 0
    while gameIdTrial in existing_gameIds:
        gameIdTrial = f'{gameId}_{i}'
        i += 1
    return gameIdTrial


def get_player_id_game(data: dict):
    player_name: str = data['player_name']
    game_id: int = data['game_id']
    game: Game = games.get(game_id)
    return player_name, game_id, game

@app.route('/')
def index():
    return render_template("index.html")

@app.route(f'/admin_controlls_{adminPword}')
def admin_page():
    Admin_Controlls.main(games, socketio)
    return render_template('adminPage.html')

@app.route(f'/qa')
def qa_rank_page():
    questionEvals.main(socketio)
    return render_template('questionEvaluator.html')

@socketio.on('create_game')
def handle_create_game(data):
    player_name = data['player_name']
    if data['gameId'] == '':
        # No game data given
        game_id = str(len(games) + 1)
    else:
        game_id = get_valid_gameId(data['gameId'])
    game = Game(game_id, [player_name])
    games[game_id] = game
    join_room(game_id)
    game.player_ids[player_name] = request.sid
    emit('game_created', {'game_id': game_id, 'player_name': player_name, 'hands': game.hands[player_name]},
         room=game_id, broadcast=True)
    emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name},
         room=game_id)


@socketio.on('join_game')
def handle_join_game(data):
    player_name, game_id, game = get_player_id_game(data)
    if game:
        if player_name not in game.players:
            game.players.append(player_name)
            game.hands[player_name] = game.draw_cards(7, None)
        join_room(game_id)
        game.player_ids[player_name] = request.sid

        emit('game_joined', {'game_id': game_id, 'player_name': player_name, 'hands': game.hands[player_name]})
        emit('show_opp_hands', {'all_players': game.players, 'hands': game.hands, 'is_flipped': game.is_flipped}, room=game_id)
        emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})


@socketio.on('play_card')
def handle_play_card(data):
    sys.stdout.flush()
    player_name, game_id, game = get_player_id_game(data)

    if game:
        if player_name != game.players[game.current_player_index]:
            emit('error', {'message': 'Not your turn'})
            return
        cards = data['card']
        if game.play_card(player_name, cards,request.sid):
            emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})


@socketio.on('draw_card')
def handle_draw_card(data):
    sys.stdout.flush()  # Gather threads so doesn't get run twice
    player_name, game_id, game = get_player_id_game(data)
    if game:
        side = game.get_side()
        if player_name != game.players[game.current_player_index]:
            emit('error', {'message': 'Not your turn'})
            return
        if game.current_card[side]['value'] in GameLogic.bosons:
            # Handle special cases if current card is a boson
            current_action = GameLogic.card_actions.get(game.current_card[side]['value'])
            res = current_action.execute(game, game.players[game.current_player_index], game.current_card)
            game.current_card[side]['value'] = 'null'
        else:
            game.draw_cards(1, player_name)
            game.current_player_index = (game.current_player_index + game.direction) % len(
            game.players)
        emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name}, room=game_id)
    else:
        emit('error', {'message': 'Game not found'})


@socketio.on('request_hand')
def handle_request_hand(data):
    player_name = data['player_name']
    is_flipped = data['is_flipped']
    game_id = data['game_id']

    # Find the game ID that the player is part of
    if game_id is None:
        emit('error', {'message': 'Game not found'})
        return

    game: Game = games[game_id]
    hands = game.hands[player_name]

    # Emit the updated hand to the requesting client only
    emit('update_hand', {'hands': hands, 'is_flipped': is_flipped, 'player': player_name})


@socketio.on('leave')
def on_leave(data):
    player_name, game_id, game = get_player_id_game(data)
    try:
        if game.players[game.current_player_index] == player_name:
            game.current_player_index = (game.current_player_index + game.direction) % (len(game.players) - 1)
        else:
            game.current_player_index = game.current_player_index % (len(game.players) - 1)
    except ZeroDivisionError:
        game.current_player_index = 0
        # Zero div error caught in leaving due to player lengths
    try:
        game.players.remove(player_name)
        del game.player_ids[player_name]
        game.deck.extend(game.hands[player_name])
        random.shuffle(game.deck)
        emit('shuffle_the_deck', {}, room=game_id)
        del game.hands[player_name]
        leave_room(game_id)
        emit('game_left', {'other_players': game.players})
    except ValueError:
        del games[game_id]
        # Game left before initialised so just delete game

    if player_name and game_id and game:
        if len(game.players) <= 0:
            # If only 1 player left, close the room
            del games[game_id]
        else:
            send(player_name + ' has left the room.', room=game_id)
            emit('show_opp_hands', {'all_players': game.players, 'hands': game.hands, 'is_flipped': game.is_flipped}, room=game_id)
            emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name},
                 room=game_id)


@socketio.on('decay_called')
def decay_btn_press(data):
    player_name, game_id, game = get_player_id_game(data)
    d_press = data['decay_pressed']  # bool: decay pressed first or not
    emit("turn_off_uno_buttons", {}, room=game_id)
    if game:
        GameLogic.decay_press_logic(game, d_press, socketio)
    else:
        emit('error', {'message': 'Game not found'})


@socketio.on('change_color_pressed')
def chng_col_press(data):
    player_name, game_id, game = get_player_id_game(data)
    color = data['chosen_color']
    if game.is_flipped:
        match color:
            case 'red': color = 'pink'
            case 'yellow': color = 'orange'
            case 'green': color = 'cyan'
            case 'blue': color = 'purple'
    GameLogic.change_current_card_color(game, color)
    game.current_player_index = (game.current_player_index + game.direction) % len(
        game.players)  # Change to next player
    emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name},
         room=game_id)


def remove_inactive_games(inactivity_timeout=2700):
    """

    :param inactivity_timeout: X seconds
    :return:
    """
    while True:
        current_time = time.time()
        inactive_games = [game for game_id, game in games.items() if current_time - game.time_of_last_action > inactivity_timeout]
        for game in inactive_games:
            for plyr_id in game.player_ids.values():
                socketio.emit('game_left', {'other_players': game.players}, to=plyr_id)
                socketio.emit("error", {"message": "Session closed due to inactivity"}, to=plyr_id)
            del games[game.id]

        eventlet.sleep(60*3)  # Check every 60 seconds


if __name__ == '__main__':
    eventlet.spawn_n(remove_inactive_games)
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)  # In production this needs to change

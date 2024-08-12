"""
A script to handle admin controls when creating a game to show different game data etc
"""
import time

from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import random

response_received = False

def main(games, socketio):


    @socketio.on('connect')
    def handle_connect():
        emit('update_games', {game_id: game.to_dict() for game_id, game in games.items()})

    @socketio.on('view_game')
    def handle_view_game(data):
        game_id = data['game_id']
        game = games.get(game_id)
        if game:
            emit('view_game_details', {'game': game.to_dict(), 'hands': game.hands})
        else:
            emit('error', {'message': 'Game not found'})

    @socketio.on('add_card')
    def handle_add_card(data):
        game_id = data['game_id']
        player = data['player']
        card = data['card']
        game = games.get(game_id)
        if game and player in game.hands:
            game.hands[player].append(card)
            emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands}, room=game_id)  # FIX

    @socketio.on('remove_cards')
    def handle_remove_card(data):
        game_id = data['game_id']
        player = data['player']
        cards = data['cards']
        game = games.get(game_id)
        if game and player in game.hands:
            for card in cards:
                card = eval(card)
                if card in game.hands[player]:
                    game.hands[player].remove(card)
                    game.deck.extend(card)
                    emit("error", {"message": "Admin removed a card"}, to=game.player_ids[player])
                    emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player},
                            room=game_id)
                else:
                    print("wrong card format")

    @socketio.on('delete_game')
    def handle_delete_game(data):
        game_id = data['game_id']
        game = games.get(game_id)
        for plyr, sid in game.player_ids.copy().items():
            emit("get_response", {"function": "force_kick"}, to=sid)
            emit("error", {"message": "Kicked by Admin"}, to=sid)
            force_kick_not_connected(game_id, plyr)
            emit("force_player_leave", {}, to=sid)
            time.sleep(0.6)

    @socketio.on('kick_player')
    def handle_kick_player(data):
        game_id = data['game_id']
        player = data['player']
        game = games.get(game_id)
        if game and player in game.hands:
            to_kick = game.player_ids.get(player)
            emit("get_response", {"function": "force_kick"}, to=to_kick)
            emit("error", {"message": "Kicked by Admin"}, to=to_kick)
            force_kick_not_connected(game_id, player)
            emit("force_player_leave", {}, to=to_kick)


    @socketio.on("force_kick")
    def handle_force_kick(data):
        # A response has been recieved
        global response_received
        response_received = True

    @socketio.on("reset_game")
    def reset_game(data):
        game = games.get(data['game_id'])
        game.reset(data['game_id'])


    def force_kick_not_connected(game_id, player):
        time.sleep(0.5)  # Wait Xs to see if we have a response TODO: If try to kick 2 clients at once this could break -- Also need to reload after this event
        global response_received
        response_receivedlocal = response_received
        response_received = False
        if not response_receivedlocal:
            # need to manually kick player
            delete_not_connected({"game_id": game_id, "player_name": player})

    def delete_not_connected(data):
        """
        :param data: {'game_id': _, 'player_name': _}
        :return:
        """
        player_name: str = data['player_name']
        game_id: int = data['game_id']
        game = games.get(game_id)
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
            socketio.emit('shuffle_the_deck', {}, room=game_id)
            del game.hands[player_name]
            leave_room(game_id)
            socketio.emit('game_left', {'other_players': game.players})
        except ValueError:
            del games[game_id]
            # Game left before initialised so just delete game

        if player_name and game_id and game:
            if len(game.players) <= 0:
                # If only 1 player left, close the room
                del games[game_id]
            else:
                send(player_name + ' has left the room.', room=game_id)
                socketio.emit('show_opp_hands', {'all_players': game.players}, room=game_id)
                socketio.emit('update_game_state', {'game': game.to_dict(), 'hands': game.hands, 'player': player_name},
                     room=game_id)



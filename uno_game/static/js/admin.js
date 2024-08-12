const socket = io();
let selectedCards = []; // Array to hold selected cards

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('update_games', (games) => {
    const gamesDiv = document.getElementById('games');

    gamesDiv.innerHTML = '';
    for (const [gameId, game] of Object.entries(games)) {
        var d = new Date(0);
        d.setUTCSeconds(game.time_of_last_action);
        const gameDiv = document.createElement('div');
        gameDiv.classList.add('game');
        gameDiv.setAttribute('data-id', game.id);
        gameDiv.innerHTML = `
            <strong>Game ID: ${game.id}</strong>
            <label>Last Game Action Time: ${d}</label>
            <div class="game-buttons">
                <button onclick="viewGame('${game.id}')">View</button>
                <button onclick="deleteGame('${game.id}')">Delete</button>
            </div>
        `;
        gamesDiv.appendChild(gameDiv);
    }
});

socket.on('game_deleted', (data) => {
    const gameId = data.game_id;
    const gameDiv = document.querySelector(`.game[data-id="${gameId}"]`);
    if (gameDiv) {
        gameDiv.remove();
    }
});

socket.on('view_game_details', (data) => {
    const game = data.game;
    const hands = data.hands;
    const side = game.is_flipped ? 'back' : 'front'
    const gameDetailsDiv = document.getElementById('gameDetails');
    gameDetailsDiv.innerHTML = `
        <h2>Game ID: ${game.id}</h2>
        <img class="card" src="/static/uno_cards/${game.current_card[side].color}_${game.current_card[side].value}.png" alt="${game.current_card[side].color} ${game.current_card[side].value}">
        <img class="card" src="/static/uno_cards/${game.bottom_card[side].color}_${game.bottom_card[side].value}.png" alt="${game.bottom_card[side].color} ${game.bottom_card[side].value}">
   
        <div class="players">
            ${game.players.map(player => `
                <div class="player">
                    <div class="player-name">${player}</div>
                    <div class="card-container">
                        ${hands[player].map((card, index) => `
                            <div style="margin-right: 10px"
                                 data-card_dict=
                                 "{'front': {'color': '${card.front.color}', 'value': '${card.front.value}'}, 'back': {'color': '${card.back.color}', 'value': '${card.back.value}'}}"
                                 onclick="toggleCardSelection(this)">
                                <img class="card" src="/static/uno_cards/${card.front.color}_${card.front.value}.png" alt="${card.front.color} ${card.front.value}">
                                <img class="card" src="/static/uno_cards/${card.back.color}_${card.back.value}.png" alt="${card.back.color} ${card.back.value}">
                           
                            </div>
                        `).join('')}
                    </div>
                    <div class="button-group">
                        <button onclick="addCard('${game.id}', '${player}')">Add Card</button>
                        <button onclick="removeSelectedCards('${game.id}', '${player}')">Remove Selected Cards</button>
                        <button onclick="kickPlayer('${game.id}', '${player}')">Kick Player</button>
                        <button onclick="resetGame('${game.id}')">Restart Game</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
});

function addCard(gameId, player) {
    const frontColor = prompt("Enter the front color of the card:");
    const frontValue = prompt("Enter the front value of the card:");
    const backColor = prompt("Enter the back color of the card:");
    const backValue = prompt("Enter the back value of the card:");
    if (frontColor && frontValue && backColor && backValue) {
        const card = {
            front: { color: frontColor, value: frontValue },
            back: { color: backColor, value: backValue }
        };
        socket.emit('add_card', { game_id: gameId, player: player, card: card });
    }
}

document.getElementById('addCardForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const frontColor = document.getElementById('frontColor').value;
    const frontValue = document.getElementById('frontValue').value;
    const backColor = document.getElementById('backColor').value;
    const backValue = document.getElementById('backValue').value;
    const gameId = document.getElementById('gameId').value;
    const player = document.getElementById('playerName').value;

    if (frontColor && frontValue && backColor && backValue && gameId && player) {
        const card = {
            front: { color: frontColor, value: frontValue },
            back: { color: backColor, value: backValue }
        };


        socket.emit('add_card', { game_id: gameId, player: player, card: card });

        // Optionally, clear the form after submission
        document.getElementById('addCardForm').reset();
    } else {
        alert('Please fill out all fields.');
    }
});

function toggleCardSelection(cardElement) {
    if (cardElement.classList.contains('selected')) {
        // Remove from selected cards
        cardElement.classList.remove('selected');
        selectedCards = selectedCards.filter(el => el !== cardElement);
    } else {
        // Add to selected cards
        cardElement.classList.add('selected');
        selectedCards.push(cardElement);
    }
}

function removeSelectedCards(gameId, player) {
    // Convert selected card elements to card data
    const selectedCards2 = selectedCards.map(cardElement => {
        return cardElement.dataset.card_dict;
    });

    // Send all selected cards for removal
    socket.emit('remove_cards', { game_id: gameId, player: player, cards: selectedCards2 });

    // Clear selectedCardElements array
    selectedCards.forEach(cardElement => cardElement.classList.remove('selected'));
    selectedCards = [];
}

function kickPlayer(gameId, player) {
    socket.emit('kick_player', { game_id: gameId, player: player });
}
function resetGame(gameId){
    socket.emit('reset_game', {game_id: gameId})
}
function viewGame(gameId) {
    socket.emit('view_game', { game_id: gameId });
}

function deleteGame(gameId) {
    socket.emit('delete_game', { game_id: gameId });
}
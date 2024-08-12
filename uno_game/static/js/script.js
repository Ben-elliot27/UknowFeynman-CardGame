const socket = io();  // Port server is listening on

const opponentHands = [];

//[left, top, angle]
const positions= [
    [[0, 10, 0]],
    [[-300, 0, -10],[300, 100, 10]],
    [[-350, 0, -10], [0, 10, 0], [360, 120, 10]]
]

let multiPlayFlag = false;

let multiPlayBuffer = []

function createGame() {
    const playerName = prompt("Enter your name:", "player 1");
    if (playerName !== null) {
        const gameId = document.getElementById("gameId").value;
        socket.emit('create_game', {player_name: playerName, 'gameId': gameId});
    }
}

function joinGame() {
    const playerName = prompt("Enter your name:", "player 2");
    if (playerName !== null) {
        const gameId = document.getElementById("gameId").value;
        socket.emit('join_game', { game_id: gameId, player_name: playerName });
    }
}

function leaveGame() {
    const playerName = document.getElementById('playerNameHidden').value;
    const gameId = document.getElementById("gameIdHidden").value;
    socket.emit('leave', {game_id: gameId, player_name: playerName});
}


function showGameScreen(gameId, playerName, hands) {
    document.getElementById('menu').style.display = 'none';
    document.getElementById('gameArea').style.display = 'block';
    document.getElementById('gameInfo').innerText = `Game ID: ${gameId} - Player: ${playerName}`;
    document.getElementById('gameIdHidden').value = gameId;
    document.getElementById('playerNameHidden').value = playerName;
    updatePlayerHand(hands, false, playerName);
    shuffleDeck();
}
function hideGameScreen() {
    document.getElementById('menu').style.display = 'block';
    document.getElementById('gameArea').style.display = 'none';
    document.getElementById('gameInfo').innerText = '';
    document.getElementById('gameIdHidden').value = null;
    document.getElementById('playerNameHidden').value = null;
}
function addOpponentHand(playerName) {
    const container = document.getElementById('opponentHandsContainer');
    const newHand = document.createElement('div');
    newHand.className = 'opponentHand';
    newHand.innerText = `${playerName}`;
    newHand.id = `${playerName}_hand`;
    opponentHands.push(newHand);
    container.insertBefore(newHand, container.firstChild);

    positionOpponentHands();
}
function removeOpponentHand(playerName) {
    const index = opponentHands.findIndex(hand => hand.innerText === playerName);
    if (index !== -1) {
        const container = document.getElementById('opponentHandsContainer');
        container.removeChild(opponentHands[index]);
        opponentHands.splice(index, 1);

        positionOpponentHands();
    }
}

function positionOpponentHands() {
    opponentHands.forEach((hand, index) => {
        const pos = positions[opponentHands.length - 1][index]

        hand.style.left = `${pos[0]}px`;
        hand.style.top = `${pos[1]}px`;
        hand.style.transform = `rotate(${pos[2]}deg)`;
    });
}


function addCardsToPlayer(playerName, player_hand, isFlipped) {
    // player_hand: hands[player]
    const player_Name = document.getElementById('playerNameHidden').value;
    if (playerName !==player_Name){
        const playerHand = document.getElementById(`${playerName}_hand`);
        if (!playerHand) {
            console.error(`Player hand with ID ${playerName} not found.`);
            return;
        }

        // Clear existing cards (if any)
        playerHand.innerHTML = '';
        player_hand.forEach(card => {
            const cardImg = document.createElement('img');

            // Determine which side of the card to display based on game state
            const side = isFlipped ? 'front' : 'back';  // Flipped round for back of cards

            cardImg.src = `/static/uno_cards/${card[side].color}_${card[side].value}.png`;
            cardImg.alt = `${card[side].color} ${card[side].value}`;
            cardImg.classList.add("opponentCard")

            playerHand.appendChild(cardImg);
        });
        const lbl = document.createElement('label');
        lbl.innerText = playerName;
        lbl.classList.add("oppLabel")
        playerHand.appendChild(lbl);
    }
}

// Function to show the player's hand with the appropriate side
function updatePlayerHand(hands, isFlipped = false, player='error') {
    const playerName = document.getElementById('playerNameHidden').value;
    if (playerName !== player){
        return
    }
    const playerHandDiv = document.getElementById('playerHand');
    playerHandDiv.innerHTML = '';

    hands.forEach(card => {
        const cardDiv = document.createElement('div');
        cardDiv.classList.add('card');
        const cardImg = document.createElement('img');

        // Determine which side of the card to display based on game state
        const side = isFlipped ? 'back' : 'front';

        cardImg.src = `/static/uno_cards/${card[side].color}_${card[side].value}.png`;
        cardImg.alt = `${card[side].color} ${card[side].value}`;
        cardDiv.id =  `${card[side].color}_${card[side].value}_${playerName}_${Math.random()}`;

        cardImg.onclick = () => playCard(card, cardDiv.id);
        cardDiv.appendChild(cardImg);
        playerHandDiv.appendChild(cardDiv);
    });
}

// Function to toggle the backside view of the player's cards
function toggleBackside() {
    const flipButton = document.getElementById('flipButton');
    const isFlipped = flipButton.innerHTML.includes('See Matter');

    flipButton.innerHTML = isFlipped
                ? '<span class="flip-symbol">🔄</span> See Anti-Matter'
                : '<span class="flip-symbol">🔄</span> See Matter';

    const playerName = document.getElementById('playerNameHidden').value;
    const gameId = document.getElementById("gameIdHidden").value;


    socket.emit('request_hand', { player_name: playerName, is_flipped: !isFlipped, game_id: gameId});
}

function playCard(card, id) {
    const gameId = document.getElementById('gameIdHidden').value;
    const playerName = document.getElementById('playerNameHidden').value;
    if (multiPlayFlag) {
        // add selected cards to a list and make them all hovered
        const selected_card = document.getElementById(id);
        if (!multiPlayBuffer.includes(card)) {
            multiPlayBuffer.push(card);
            setResetStyles(true, selected_card);
            if (multiPlayBuffer.length > 1) {
                socket.emit('play_card', {game_id: gameId, player_name: playerName, card: multiPlayBuffer});
            } else {
                return
            }
        } else {
            setResetStyles(false)
            multiPlayBuffer = multiPlayBuffer.filter(card => card !== selected_card);
        }
    } else {
        multiPlayBuffer = [card]
    }

    socket.emit('play_card', { game_id: gameId, player_name: playerName, card: multiPlayBuffer });



}

function drawCard() {
    const gameId = document.getElementById('gameIdHidden').value;
    const playerName = document.getElementById('playerNameHidden').value;
    socket.emit('draw_card', { game_id: gameId, player_name: playerName });
}

function updateGameState(card, bot_card, isFlipped, hands, player, currentPlayer=player) {
    const side = isFlipped ? 'back' : 'front';
    const currentCardDiv = document.getElementById('discardPile');
    multiPlayBuffer = [];
    if (card && bot_card) {
        currentCardDiv.innerHTML = `
            <img src="/static/uno_cards/${card[side].color}_${card[side].value}.png" alt="${card[side].color} ${card[side].value}">
            <img src="/static/uno_cards/${bot_card[side].color}_${bot_card[side].value}.png" alt="${bot_card[side].color} ${bot_card[side].value}">
        `;
    } else {
        currentCardDiv.innerHTML = '';
    }
    disableEnableButton("multiplay", true)  // Automatically disable multiplay button if there is some game update
    const playerName = document.getElementById('playerNameHidden').value;
    const plyrHand = document.getElementById("playerHand");

    if (playerName === player) {
        updatePlayerHand(hands[playerName], isFlipped, player);
    }
    else {
        addCardsToPlayer(player, hands[player], isFlipped)
    }

    if (currentPlayer === playerName) {
        const cardImages = plyrHand.querySelectorAll("img");  // Assuming card images are <img> elements
        cardImages.forEach(img => {
            img.style.borderRadius = "14%";
            img.style.boxShadow = "0 0 10px gold, 0 0 5px gold inset"; });
        disableEnableButton("multiplay", false);
    }
    else {
        plyrHand.style.boxShadow = "none";
        const oppHand = document.getElementById(`${currentPlayer}_hand`);
        // Add style to the cards that are a child of this class
        const cardImages = oppHand.querySelectorAll("img"); // Assuming card images are <img> elements
        cardImages.forEach(img => img.classList.add("current-player-highlight"));
    }
}

function toggleInstructions() {
    const instructionsDiv = document.getElementById('instructions');
    instructionsDiv.classList.toggle('hidden');
}

function shuffleDeck() {
    const drawPile = document.getElementById('drawPile');
    const cards = drawPile.getElementsByTagName('img');

    // Add the 'shuffling-left' or 'shuffling-right' class to each card to trigger the animation
    for (let i = 0; i < cards.length; i++) {
        if (i % 2 === 0) {
            cards[i].classList.add('shuffling-left');
        } else {
            cards[i].classList.add('shuffling-right');
        }
    }

    // Remove the 'shuffling-left' and 'shuffling-right' classes after the animation completes (0.5s)
    setTimeout(() => {
        for (let i = 0; i < cards.length; i++) {
            cards[i].classList.remove('shuffling-left', 'shuffling-right');
        }
    }, 500);
}
function decayPressed(){
    // First disable both buttons
    disableEnableButton("decayButton", true)
    // then tell backend to check if uno was correctly called
    const gameId = document.getElementById('gameIdHidden').value;
    const playerName = document.getElementById('playerNameHidden').value;
    socket.emit('decay_called', { game_id: gameId, player_name: playerName, decay_pressed: true });
}
function challengePressed(){
    disableEnableButton("challengeButton", true)
    const gameId = document.getElementById('gameIdHidden').value;
    const playerName = document.getElementById('playerNameHidden').value;
    socket.emit('decay_called', { game_id: gameId, player_name: playerName, decay_pressed: false });
}
function turn_off_uno_buttons(){
    disableEnableButton("challengeButton", true)
    disableEnableButton("decayButton", true)
}
function disableEnableButton(buttonId, disabled_bool) {
    // console.log(`button ID: ${buttonId}`)
    var button = document.getElementById(buttonId);
    // console.log(`button found: ${button}`)

    if (button) {
        button.disabled = disabled_bool;
        button.style.display = disabled_bool ? 'none' : 'inline-block';
    }
}
function handleDownToOneCard(data){
    const playerOnOneCard = data.player_on_one_card
    const current_player = document.getElementById('playerNameHidden').value;

    if (playerOnOneCard === current_player) {
        // Show decay Button and hide it after 4s
        disableEnableButton("decayButton", false);
        // setTimeout(function() {
        // disableEnableButton("decayButton", true);
        // }, 4000);
    }
    else {
        // Show challenge Button after 2s hide it after 6s total
        setTimeout(function() {
        disableEnableButton("challengeButton", false);
        }, 1000);
        // setTimeout(function() {
        // disableEnableButton("challengeButton", true);
        // }, 6000);
    }
}

// ---------- CHOOSING COLOR FUNCTIONALITY ----------
function chooseColor(color) {
    const colorChangeButton = document.getElementById('colorChangeButton');
    colorChangeButton.classList.add('selected-' + color);
    setTimeout(() => {
        colorChangeButton.classList.remove('selected-' + color);
        // disable all buttons again - after animation played
        disableEnableButton('redBtn', true)
        disableEnableButton('blueBtn', true)
        disableEnableButton('greenBtn', true)
        disableEnableButton('yellowBtn', true)
    }, 1000); // Duration of the animation
    // broadcast that color was picked & spawn new card
    const gameId = document.getElementById('gameIdHidden').value;
    const playerName = document.getElementById('playerNameHidden').value;
    socket.emit('change_color_pressed', { game_id: gameId, player_name: playerName, chosen_color: color})
}
function setColorButtons(isFlipped, player) {
    if (isFlipped) {
        document.getElementById('redBtn').style.backgroundColor = '#f55ced';
        document.getElementById('blueBtn').style.backgroundColor = '#6927cb';
        document.getElementById('greenBtn').style.backgroundColor = '#2effe5';
        document.getElementById('yellowBtn').style.backgroundColor = '#ff9900';
    }
    else {
        document.getElementById('redBtn').style.backgroundColor = '#ff4d4d';
        document.getElementById('blueBtn').style.backgroundColor = '#4d4dff';
        document.getElementById('greenBtn').style.backgroundColor = '#4dff4d';
        document.getElementById('yellowBtn').style.backgroundColor = '#ffff4d';
    }
    console.log("setting color buttons")

    const playerName = document.getElementById('playerNameHidden').value;
    if (playerName === player) {
        console.log("setting color buttons2")
        disableEnableButton('redBtn', false)
        disableEnableButton('blueBtn', false)
        disableEnableButton('greenBtn', false)
        disableEnableButton('yellowBtn', false)
    }
}

function multiPlayPressed(){
    const mult_but = document.getElementById("multiplay")

    if (mult_but.innerText === "Multi-Play") {
        mult_but.style.backgroundColor = "#8ce73e";
        mult_but.innerText = "Selected";
        multiPlayFlag = true;
    }
    else {
        mult_but.style.backgroundColor = "#ff0000";
        mult_but.innerText = "Multi-Play";
        multiPlayFlag = false;
        multiPlayBuffer = []
        setResetStyles(false)
    }
}

function setResetStyles(isSetting, selected_card=null){
    if (isSetting){
        selected_card.style.transform = "translateY(-30px)";
        selected_card.style.margin = "0";
        const cardImages = selected_card.querySelectorAll("img");
        cardImages.forEach(img => {
            img.style.boxShadow = "0 0 10px rgba(63,253,36,0.8), 0 0 5px rgba(63,253,36,0.8) inset"; img.classList.add("no-hover-effect")});
    }
    else {
        const plyrHand = document.getElementById("playerHand");
        const cardDivs = plyrHand.querySelectorAll("div"); // Assuming cards are <div> elements
        cardDivs.forEach(div => {div.style.transform = "none"; div.style.margin = "-7.5px"});
        const cardImages = plyrHand.querySelectorAll("img"); // Assuming card images are <img> elements
        cardImages.forEach(img => {
            img.style.boxShadow = "0 0 10px gold, 0 0 5px gold inset"; img.classList.remove("no-hover-effect"); });
    }


}

function startTutorial() {
    alert("Feature not yet implemented")
}

// Socket events to handle initial game setup
socket.on('game_created', (data) => {
    alert(`Game created with ID: ${data.game_id}`);
    showGameScreen(data.game_id, data.player_name, data.hands);
});

socket.on('game_joined', (data) => {
    alert(`Joined game with ID: ${data.game_id}`);
    showGameScreen(data.game_id, data.player_name, data.hands);
    for (let plyr in data.other_players) {
        addOpponentHand(plyr);
    }
});
socket.on('game_left', (data) => {
    for (let plyr in data.other_players) {
        removeOpponentHand(plyr);
    }
    hideGameScreen();

});

socket.on('show_opp_hands', (data) => {
    const thisPlayer = document.getElementById('playerNameHidden').value;
    const opponents = data.all_players.filter(player => player !== thisPlayer);

    // Add new opponent hands
    opponents.forEach(plyr => {
        if (!opponentHands.some(hand => hand.innerText === plyr)) {
            addOpponentHand(plyr);
            addCardsToPlayer(plyr, data.hands[plyr], data.is_flipped)
        }
    });

    // Remove opponent hands that are no longer in the game
    opponentHands.slice().forEach(hand => {
        if (!opponents.includes(hand.innerText)) {
            removeOpponentHand(hand.innerText);
        }
    });

});

socket.on('update_game_state', (data) => {
    updateGameState(data.game.current_card, data.game.bottom_card, data.game.is_flipped, data.hands, data.player, data.game.players[data.game.current_player_index]);
});

socket.on('error', (data) => {
    alert(data.message);
});

// Socket event to update the hand when requested
socket.on('update_hand', (data) => {
    updatePlayerHand(data.hands, data.is_flipped, data.player);
});

socket.on('shuffle_the_deck', (data) => {
    shuffleDeck()
});

socket.on('show_uno_challenge_button', (data) => {
    handleDownToOneCard(data)
});
socket.on('show_color_change_button', (data) => {
    setColorButtons(data.isFlipped, data.player_to_choose)
    }
);
socket.on("Multi-Play possible", (data) => {
    disableEnableButton("multiplay", false)
    }
);
socket.on("turn_off_uno_buttons", (data) => {
    turn_off_uno_buttons();
    }
);
socket.on("force_player_leave", () =>{
    leaveGame();
});

socket.on('get_response', (data) => {
    console.log(data.function);
    socket.emit(data.function.toString(), {});
});


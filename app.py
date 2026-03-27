from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from config import Config
from db import get_db_connection
from auth import auth_bp
from datetime import datetime
import eventlet
import json

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(auth_bp)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

# --- SOCKET EVENTS ---
@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    join_room(room)
    if room not in rooms:
        rooms[room] = {
            'board': [''] * 225, 
            'turn': 'X',
            'players': {}
        }

    room_data = rooms[room]
    sid = request.sid

    # Gán người chơi X hoặc O
    if 'X' not in room_data['players'].values():
        player = 'X'
    elif 'O' not in room_data['players'].values():
        player = 'O'
    else:
        emit('error', {'message': 'Phòng đã đủ người'})
        return

    room_data['players'][sid] = player
    emit('joined', {
        'player': player,
        'turn': room_data['turn'],
        'board': room_data['board']
    }, room=sid)


@socketio.on('make_move')
def handle_make_move(data):
    room = data['room']
    index = data['index']
    player = data['player']

    if room not in rooms:
        return

    room_data = rooms[room]
    if room_data['board'][index] == '' and player == room_data['turn']:
        room_data['board'][index] = player
        room_data['turn'] = 'O' if player == 'X' else 'X'

        emit('update_board', {
            'index': index,
            'player': player,
            'turn': room_data['turn']
        }, room=room)
        if check_win(room_data['board'], index, player):
            save_online_result(player, room_data['board'])

@socketio.on('reset_board')
def handle_reset_board(data):
    room = data['room']
    if room in rooms:
        rooms[room]['board'] = [''] * 225
        rooms[room]['turn'] = 'X'
        emit('reset_board', room=room)


@socketio.on('disconnect')
def handle_disconnect():
    for room, room_data in list(rooms.items()):
        if request.sid in room_data['players']:
            del room_data['players'][request.sid]
            if not room_data['players']:
                del rooms[room]
            break

# --- ROUTES ---
@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('auth.login'))

@app.route('/choose_mode')
def choose_mode():
    username = session.get('username')
    return render_template('choose_mode.html', username=username)

@app.route('/play_two_players')
def play_two_players():
    return render_template('play_two_players.html')

@app.route('/play_vs_computer')
def play_vs_computer():
    return render_template('play_vs_computer.html')

@app.route('/play_online')
def play_online():
    return render_template('play_online.html', username=session.get('username', 'Khách'))

@app.route('/start_two_players', methods=['POST'])
def start_two_players():
    player_choice = request.form.get('player_choice')
    session['player_choice'] = player_choice
    return render_template('board_two_players.html', player=player_choice)

@app.route('/save_match_result', methods=['POST'])
def save_match_result():
    data = request.get_json()
    username = session.get('username', 'Khách')
    mode = data.get('mode', 'Chơi 2 người')
    player = data.get('player', 'X')
    result = data.get('result', 'Hòa')
    board_json = json.dumps(data.get('board', []))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO match_history (username, mode, player, result, board)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, mode, player, result, board_json))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Kết quả đã được lưu"})
    except Exception as e:
        print("Lỗi khi lưu kết quả:", e)
        return jsonify({"status": "error", "message": str(e)})

@app.route('/history')
def history():
    username = session.get('username', 'Khách')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, mode, player, result, board, created_at 
        FROM match_history 
        WHERE username = %s
        ORDER BY created_at DESC
    """, (username,))
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('history.html', username=username, matches=matches)

def check_win(board, index, player):
    row = index // 15
    col = index % 15
    board2d = [board[i*15:(i+1)*15] for i in range(15)]

    def count_dir(r, c, dr, dc):
        cnt = 0
        rr, cc = r, c
        while 0 <= rr < 15 and 0 <= cc < 15 and board2d[rr][cc] == player:
            cnt += 1
            rr += dr
            cc += dc
        rr, cc = r - dr, c - dc
        while 0 <= rr < 15 and 0 <= cc < 15 and board2d[rr][cc] == player:
            cnt += 1
            rr -= dr
            cc -= dc
        return cnt >= 5

    dirs = [(0,1),(1,0),(1,1),(1,-1)]
    return any(count_dir(row,col,dr,dc) for dr, dc in dirs)

def save_online_result(player, board):
    username = session.get('username', 'Khách')
    mode = "Chơi online"
    result = "Thắng" if player == 'X' else "Thua"
    board_json = json.dumps(board)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO match_history (username, mode, player, result, board)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, mode, player, result, board_json))
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Kết quả online đã lưu")
    except Exception as e:
        print("❌ Lỗi lưu kết quả online:", e)

if __name__ == "__main__":
    eventlet.monkey_patch()
    socketio.run(app, debug=True)

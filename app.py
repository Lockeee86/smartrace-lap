from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import time
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Globale Variablen
race_data = {}
track_data = {}
connected_clients = 0

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/webhook', methods=['POST'])
def receive_race_data():
    global race_data
    try:
        data = request.json
        race_data = data
        race_data['timestamp'] = datetime.now().isoformat()
        
        # An alle Clients senden
        socketio.emit('race_update', race_data)
        
        print(f"Race data received: {json.dumps(data, indent=2)}")
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error processing race data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/webhook/track', methods=['POST'])
def receive_track_data():
    global track_data
    try:
        data = request.json
        track_data = data
        track_data['timestamp'] = datetime.now().isoformat()
        
        # An alle Clients senden
        socketio.emit('track_update', track_data)
        
        print(f"Track data received: {json.dumps(data, indent=2)}")
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error processing track data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/live-data')
def get_live_data():
    return jsonify({
        'race_data': race_data,
        'track_data': track_data,
        'connected_clients': connected_clients
    })

@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients += 1
    emit('connected', {'data': 'Connected to SmartRace Dashboard'})
    
    # Aktuelle Daten senden
    if race_data:
        emit('race_update', race_data)
    if track_data:
        emit('track_update', track_data)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients
    connected_clients = max(0, connected_clients - 1)

if __name__ == '__main__':
    print("🏁 SmartRace Dashboard starting...")
    print("📡 Webhooks available:")
    print("   Race Data: /webhook")
    print("   Track Data: /webhook/track")
    print("🌐 Dashboard: http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

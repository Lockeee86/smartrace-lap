from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import datetime
import json

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smartrace-dashboard-secret-key'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

print("🏁 SmartRace Dashboard starting...")
print("📡 Webhooks available:")
print("   Race Data: /webhook")
print("   Track Data: /webhook/track")

# Global data storage
race_data = {
    'race_status': {
        'mode': 'Practice',
        'time': 0,
        'is_running': False,
        'start_time': None
    },
    'drivers': {},
    'session_info': {
        'session_type': 'Practice',
        'total_time': 0,
        'total_laps': 0
    }
}

track_data = {
    'track_data': {
        'name': 'Unknown Track',
        'length': 0,
        'sectors': [],
        'coordinates': [],
        'layout': ''
    }
}

lap_history = {}

# Routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/track')
def track():
    return render_template('track.html')

# API Routes
@app.route('/api/race-data')
def api_race_data():
    return jsonify(race_data)

@app.route('/api/track-data')
def api_track_data():
    return jsonify(track_data)

@app.route('/api/lap-history')
def api_lap_history():
    return jsonify(lap_history)

@app.route('/api/lap-history/<driver_id>')
def api_driver_lap_history(driver_id):
    return jsonify(lap_history.get(driver_id, []))

# Webhook endpoints
@app.route('/webhook', methods=['POST'])
def race_webhook():
    try:
        data = request.get_json()
        if data:
            print(f"🏁 Race webhook received: {json.dumps(data, indent=2)}")
            update_race_data(data)
            
            # Emit to all connected clients
            socketio.emit('race_update', race_data)
            
            return jsonify({'status': 'success', 'message': 'Race data updated'})
        else:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
    except Exception as e:
        print(f"❌ Race webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook/track', methods=['POST'])
def track_webhook():
    try:
        data = request.get_json()
        if data:
            print(f"🗺️ Track webhook received: {json.dumps(data, indent=2)}")
            update_track_data(data)
            
            # Emit to all connected clients
            socketio.emit('track_update', track_data)
            
            return jsonify({'status': 'success', 'message': 'Track data updated'})
        else:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
    except Exception as e:
        print(f"❌ Track webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Data processing functions
def update_race_data(data):
    global race_data, lap_history
    
    # Update race status
    if 'raceStatus' in data or 'race_status' in data:
        status = data.get('raceStatus', data.get('race_status', {}))
        
        if 'mode' in status:
            race_data['race_status']['mode'] = status['mode']
        if 'time' in status:
            race_data['race_status']['time'] = status['time']
        if 'isRunning' in status:
            race_data['race_status']['is_running'] = status['isRunning']
        elif 'is_running' in status:
            race_data['race_status']['is_running'] = status['is_running']
        if 'startTime' in status:
            race_data['race_status']['start_time'] = status['startTime']
        elif 'start_time' in status:
            race_data['race_status']['start_time'] = status['start_time']
    
    # Update session info
    if 'sessionInfo' in data or 'session_info' in data:
        session = data.get('sessionInfo', data.get('session_info', {}))
        
        if 'sessionType' in session:
            race_data['session_info']['session_type'] = session['sessionType']
        elif 'session_type' in session:
            race_data['session_info']['session_type'] = session['session_type']
        if 'totalTime' in session:
            race_data['session_info']['total_time'] = session['totalTime']
        elif 'total_time' in session:
            race_data['session_info']['total_time'] = session['total_time']
        if 'totalLaps' in session:
            race_data['session_info']['total_laps'] = session['totalLaps']
        elif 'total_laps' in session:
            race_data['session_info']['total_laps'] = session['total_laps']
    
    # Update drivers data
    if 'drivers' in data:
        for driver_id, driver_info in data['drivers'].items():
            # Initialize driver if not exists
            if driver_id not in race_data['drivers']:
                race_data['drivers'][driver_id] = {
                    'id': driver_id,
                    'name': f'Driver {driver_id}',
                    'position': 0,
                    'laps': 0,
                    'last_lap_time': None,
                    'best_lap_time': None,
                    'total_time': 0,
                    'sector_times': [],
                    'is_active': True
                }
            
            # Initialize lap history if not exists
            if driver_id not in lap_history:
                lap_history[driver_id] = []
            
            # Update driver info
            driver = race_data['drivers'][driver_id]
            
            if 'name' in driver_info:
                driver['name'] = driver_info['name']
            
            if 'laps' in driver_info:
                driver['laps'] = driver_info['laps']
            
            if 'bestLapTime' in driver_info:
                driver['best_lap_time'] = driver_info['bestLapTime']
            elif 'best_lap_time' in driver_info:
                driver['best_lap_time'] = driver_info['best_lap_time']
            
            if 'lastLapTime' in driver_info:
                old_lap_time = driver['last_lap_time']
                driver['last_lap_time'] = driver_info['lastLapTime']
                
                # If lap time changed, add to history
                if old_lap_time != driver['last_lap_time'] and driver['last_lap_time']:
                    lap_history[driver_id].append({
                        'lap_time': driver['last_lap_time'],
                        'lap_number': driver['laps'],
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    
                    # Keep only last 50 laps in history
                    if len(lap_history[driver_id]) > 50:
                        lap_history[driver_id] = lap_history[driver_id][-50:]
            elif 'last_lap_time' in driver_info:
                old_lap_time = driver['last_lap_time']
                driver['last_lap_time'] = driver_info['last_lap_time']
                
                if old_lap_time != driver['last_lap_time'] and driver['last_lap_time']:
                    lap_history[driver_id].append({
                        'lap_time': driver['last_lap_time'],
                        'lap_number': driver['laps'],
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    
                    if len(lap_history[driver_id]) > 50:
                        lap_history[driver_id] = lap_history[driver_id][-50:]
            
            if 'position' in driver_info:
                driver['position'] = driver_info['position']
            
            if 'totalTime' in driver_info:
                driver['total_time'] = driver_info['totalTime']
            elif 'total_time' in driver_info:
                driver['total_time'] = driver_info['total_time']
            
            if 'sectorTimes' in driver_info:
                driver['sector_times'] = driver_info['sectorTimes']
            elif 'sector_times' in driver_info:
                driver['sector_times'] = driver_info['sector_times']

def update_track_data(data):
    global track_data
    
    if 'name' in data:
        track_data['track_data']['name'] = data['name']
    if 'length' in data:
        track_data['track_data']['length'] = data['length']
    if 'sectors' in data:
        track_data['track_data']['sectors'] = data['sectors']
    if 'coordinates' in data:
        track_data['track_data']['coordinates'] = data['coordinates']
    if 'layout' in data:
        track_data['track_data']['layout'] = data['layout']

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print(f"🔌 Client connected: {request.sid}")
    emit('race_update', race_data)
    emit('track_update', track_data)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid}")

@socketio.on('request_data')
def handle_request_data():
    print(f"📊 Data requested by client: {request.sid}")
    emit('race_update', race_data)
    emit('track_update', track_data)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('dashboard.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🌐 Dashboard: http://localhost:5000")
    print("🚀 Starting server...")
    try:
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5000, 
            debug=True, 
            allow_unsafe_werkzeug=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"❌ Server start error: {e}")
        raise

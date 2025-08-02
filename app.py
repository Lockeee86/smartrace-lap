from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import datetime
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smartrace-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global data storage
race_data = {
    'drivers': {},
    'race_time': 0,
    'total_laps': 0,
    'race_mode': 'Practice',
    'track_name': 'Unknown Track',
    'is_race_active': False,
    'start_time': None
}

track_data = {
    'track_data': {
        'name': 'Default Track',
        'length': 1000,
        'sectors': [],
        'coordinates': [],
        'layout': 'Oval'
    }
}

lap_history = defaultdict(list)  # Store lap history per driver

print("🏁 SmartRace Dashboard starting...")
print("📡 Webhooks available:")
print("   Race Data: /webhook")
print("   Track Data: /webhook/track")

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/track')
def track():
    return render_template('track.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get current race data"""
    return jsonify({
        'race_data': race_data,
        'track_data': track_data,
        'lap_history': dict(lap_history)
    })

# Webhook endpoints
@app.route('/webhook', methods=['POST'])
def webhook_race_data():
    """Handle race data from SmartRace"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
        
        print(f"📊 Received race data: {json.dumps(data, indent=2)}")
        
        # Update race data
        update_race_data(data)
        
        # Broadcast to all connected clients
        socketio.emit('race_update', race_data)
        
        return jsonify({'status': 'success', 'message': 'Race data updated'})
        
    except Exception as e:
        print(f"❌ Error processing race data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook/track', methods=['POST'])
def webhook_track_data():
    """Handle track data from SmartRace"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
        
        print(f"🗺️ Received track data: {json.dumps(data, indent=2)}")
        
        # Update track data
        update_track_data(data)
        
        # Broadcast to all connected clients
        socketio.emit('track_update', track_data)
        
        return jsonify({'status': 'success', 'message': 'Track data updated'})
        
    except Exception as e:
        print(f"❌ Error processing track data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def update_race_data(data):
    """Update global race data from webhook"""
    global race_data, lap_history
    
    # Update basic race info
    if 'raceTime' in data:
        race_data['race_time'] = data['raceTime']
    
    if 'totalLaps' in data:
        race_data['total_laps'] = data['totalLaps']
    
    if 'raceMode' in data:
        race_data['race_mode'] = data['raceMode']
    
    if 'trackName' in data:
        race_data['track_name'] = data['trackName']
    
    if 'isRaceActive' in data:
        race_data['is_race_active'] = data['isRaceActive']
        if data['isRaceActive'] and not race_data['start_time']:
            race_data['start_time'] = datetime.datetime.now().isoformat()
    
    # Update driver data
    if 'drivers' in data:
        for driver_id, driver_info in data['drivers'].items():
            if driver_id not in race_data['drivers']:
                race_data['drivers'][driver_id] = {
                    'id': driver_id,
                    'name': driver_info.get('name', f'Driver {driver_id}'),
                    'laps': 0,
                    'best_lap_time': None,
                    'last_lap_time': None,
                    'position': None,
                    'total_time': 0,
                    'sector_times': [],
                    'is_active': True
                }
            
            # Update driver info
            driver = race_data['drivers'][driver_id]
            
            if 'name' in driver_info:
                driver['name'] = driver_info['name']
            
            if 'laps' in driver_info:
                driver['laps'] = driver_info['laps']
            
            if 'bestLapTime' in driver_info:
                driver['best_lap_time'] = driver_info['bestLapTime']
            
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
            
            if 'position' in driver_info:
                driver['position'] = driver_info['position']
            
            if 'totalTime' in driver_info:
                driver['total_time'] = driver_info['totalTime']
            
            if 'sectorTimes' in driver_info:
                driver['sector_times'] = driver_info['sectorTimes']

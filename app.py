from flask import Flask, render_template, request, jsonify, make_response
from flask_socketio import SocketIO, emit
import datetime
import json
import csv
import io

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smartrace-dashboard-secret-key'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global data storage
race_data = {
    'session_info': {
        'session_type': 'Practice',
        'total_time': '00:00:00',
        'total_laps': 0,
        'current_lap': 0,
        'session_status': 'Waiting',
        'flag_status': 'Green'
    },
    'drivers': {}
}

track_data = {
    'track_data': {
        'name': 'Unknown Track',
        'length': 0,
        'sectors': 3,
        'layout': None
    }
}

lap_history = {}

# Main routes
@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html', 
                         race_data=race_data, 
                         track_data=track_data)

@app.route('/analysis')
def analysis():
    """Analysis view with detailed statistics"""
    return render_template('analysis.html', 
                         race_data=race_data, 
                         lap_history=lap_history)

@app.route('/track')
def track():
    """Track visualization view"""
    return render_template('track.html', 
                         track_data=track_data, 
                         race_data=race_data)

# API routes
@app.route('/api/race-data')
def get_race_data():
    """Get current race data"""
    return jsonify(race_data)

@app.route('/api/track-data')
def get_track_data():
    """Get track data"""
    return jsonify(track_data)

@app.route('/api/lap-history')
def get_lap_history():
    """Get lap history for all drivers"""
    return jsonify(lap_history)

# CSV Export Routes
@app.route('/export/race-data')
def export_race_data():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Driver ID', 'Driver Name', 'Position', 'Best Lap Time', 'Last Lap Time', 'Total Laps', 'Gap', 'Status'])
    
    # Sort drivers by position
    drivers_sorted = sorted(race_data['drivers'].items(), 
                          key=lambda x: x[1].get('position', 999))
    
    # Data rows
    for driver_id, driver in drivers_sorted:
        writer.writerow([
            driver_id,
            driver.get('name', f'Driver {driver_id}'),
            driver.get('position', '-'),
            driver.get('best_lap_time', '-'),
            driver.get('last_lap_time', '-'),
            driver.get('laps_completed', 0),
            driver.get('gap', '-'),
            driver.get('status', 'Unknown')
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=race_data_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

@app.route('/export/lap-history')
def export_lap_history():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Driver ID', 'Driver Name', 'Lap Number', 'Lap Time', 'Sector 1', 'Sector 2', 'Sector 3', 'Timestamp'])
    
    # Data rows
    for driver_id, laps in lap_history.items():
        driver_name = race_data['drivers'].get(driver_id, {}).get('name', f'Driver {driver_id}')
        
        for lap_num, lap in enumerate(laps, 1):
            writer.writerow([
                driver_id,
                driver_name,
                lap_num,
                lap.get('lap_time', '-'),
                lap.get('sector_1', '-'),
                lap.get('sector_2', '-'),
                lap.get('sector_3', '-'),
                lap.get('timestamp', '-')
            ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=lap_history_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

@app.route('/export/session-summary')
def export_session_summary():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Session Info
    writer.writerow(['SESSION SUMMARY'])
    writer.writerow(['Session Type', race_data['session_info']['session_type']])
    writer.writerow(['Total Time', race_data['session_info']['total_time']])
    writer.writerow(['Total Laps', race_data['session_info']['total_laps']])
    writer.writerow(['Track Name', track_data['track_data']['name']])
    writer.writerow(['Track Length', track_data['track_data']['length']])
    writer.writerow(['Export Time', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])  # Empty row
    
    # Driver Summary
    writer.writerow(['DRIVER RESULTS'])
    writer.writerow(['Position', 'Driver Name', 'Best Lap', 'Total Laps', 'Average Lap Time', 'Gap'])
    
    drivers_sorted = sorted(race_data['drivers'].items(), 
                          key=lambda x: x[1].get('position', 999))
    
    for driver_id, driver in drivers_sorted:
        # Calculate average lap time if lap history exists
        avg_time = '-'
        if driver_id in lap_history and lap_history[driver_id]:
            times = [lap.get('lap_time', 0) for lap in lap_history[driver_id] if lap.get('lap_time')]
            if times:
                avg_time = sum(times) / len(times)
        
        writer.writerow([
            driver.get('position', '-'),
            driver.get('name', f'Driver {driver_id}'),
            driver.get('best_lap_time', '-'),
            driver.get('laps_completed', 0),
            f"{avg_time:.3f}" if isinstance(avg_time, float) else avg_time,
            driver.get('gap', '-')
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=session_summary_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

# Webhook endpoints
@app.route('/webhook', methods=['POST'])
def handle_race_webhook():
    """Handle SmartRace race data webhooks"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        print(f"📊 Received race data: {json.dumps(data, indent=2)}")
        
        # Update race data based on received webhook
        update_race_data(data)
        
        # Emit to all connected clients
        socketio.emit('race_update', race_data)
        
        return jsonify({'status': 'success', 'message': 'Data received'}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/track', methods=['POST'])
def handle_track_webhook():
    """Handle SmartRace track data webhooks"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No track data received'}), 400
        
        print(f"🏁 Received track data: {json.dumps(data, indent=2)}")
        
        # Update track data
        update_track_data(data)
        
        # Emit to all connected clients
        socketio.emit('track_update', track_data)
        
        return jsonify({'status': 'success', 'message': 'Track data received'}), 200
        
    except Exception as e:
        print(f"❌ Track webhook error: {e}")
        return jsonify({'error': str(e)}), 500

# Data processing functions
def update_race_data(webhook_data):
    """Update race data from webhook"""
    global race_data, lap_history
    
    try:
        # Update session info if present
        if 'session' in webhook_data:
            session = webhook_data['session']
            race_data['session_info'].update({
                'session_type': session.get('type', race_data['session_info']['session_type']),
                'total_time': session.get('total_time', race_data['session_info']['total_time']),
                'total_laps': session.get('total_laps', race_data['session_info']['total_laps']),
                'current_lap': session.get('current_lap', race_data['session_info']['current_lap']),
                'session_status': session.get('status', race_data['session_info']['session_status']),
                'flag_status': session.get('flag', race_data['session_info']['flag_status'])
            })
        
        # Update drivers if present
        if 'drivers' in webhook_data:
            for driver_data in webhook_data['drivers']:
                driver_id = str(driver_data.get('id', driver_data.get('driver_id', 'unknown')))
                
                # Initialize driver if not exists
                if driver_id not in race_data['drivers']:
                    race_data['drivers'][driver_id] = {
                        'name': f'Driver {driver_id}',
                        'position': 999,
                        'laps_completed': 0,
                        'best_lap_time': None,
                        'last_lap_time': None,
                        'gap': '-',
                        'status': 'Unknown'
                    }
                
                # Update driver data
                driver = race_data['drivers'][driver_id]
                driver.update({
                    'name': driver_data.get('name', driver.get('name')),
                    'position': driver_data.get('position', driver.get('position')),
                    'laps_completed': driver_data.get('laps', driver.get('laps_completed')),
                    'best_lap_time': driver_data.get('best_lap', driver.get('best_lap_time')),
                    'last_lap_time': driver_data.get('last_lap', driver.get('last_lap_time')),
                    'gap': driver_data.get('gap', driver.get('gap')),
                    'status': driver_data.get('status', driver.get('status'))
                })
                
                # Update lap history if lap data present
                if 'lap_time' in driver_data:
                    if driver_id not in lap_history:
                        lap_history[driver_id] = []
                    
                    lap_entry = {
                        'lap_time': driver_data['lap_time'],
                        'sector_1': driver_data.get('sector_1'),
                        'sector_2': driver_data.get('sector_2'),
                        'sector_3': driver_data.get('sector_3'),
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                    
                    lap_history[driver_id].append(lap_entry)
        
        # Handle direct lap data
        elif 'lap_data' in webhook_data:
            for lap_data in webhook_data['lap_data']:
                driver_id = str(lap_data.get('driver_id', 'unknown'))
                
                if driver_id not in lap_history:
                    lap_history[driver_id] = []
                
                lap_entry = {
                    'lap_time': lap_data.get('lap_time'),
                    'sector_1': lap_data.get('sector_1'),
                    'sector_2': lap_data.get('sector_2'),
                    'sector_3': lap_data.get('sector_3'),
                    'timestamp': datetime.datetime.now().isoformat()
                }
                
                lap_history[driver_id].append(lap_entry)
        
        print(f"✅ Race data updated: {len(race_data['drivers'])} drivers")
        
    except Exception as e:
        print(f"❌ Error updating race data: {e}")

def update_track_data(webhook_data):
    """Update track data from webhook"""
    global track_data
    
    try:
        if 'track' in webhook_data:
            track = webhook_data['track']
            track_data['track_data'].update({
                'name': track.get('name', track_data['track_data']['name']),
                'length': track.get('length', track_data['track_data']['length']),
                'sectors': track.get('sectors', track_data['track_data']['sectors']),
                'layout': track.get('layout', track_data['track_data']['layout'])
            })
        
        print(f"✅ Track data updated: {track_data['track_data']['name']}")
        
    except Exception as e:
        print(f"❌ Error updating track data: {e}")

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"🔌 Client connected: {request.sid}")
    
    # Send current data to newly connected client
    emit('race_update', race_data)
    emit('track_update', track_data)
    emit('lap_history_update', lap_history)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"🔌 Client disconnected: {request.sid}")

@socketio.on('request_data')
def handle_data_request():
    """Handle data request from client"""
    emit('race_update', race_data)
    emit('track_update', track_data)
    emit('lap_history_update', lap_history)

if __name__ == '__main__':
    print("🏁 SmartRace Dashboard starting...")
    print("📡 Webhooks available:")
    print("   Race Data: /webhook")
    print("   Track Data: /webhook/track")
    print("📊 CSV Exports available:")
    print("   Race Data: /export/race-data")
    print("   Lap History: /export/lap-history") 
    print("   Session Summary: /export/session-summary")
    print("🌐 Dashboard: http://localhost:5000")
    
    try:
        print("🚀 Starting server...")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Server start error: {e}")
        raise

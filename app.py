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

# Dynamische Auto-Datenbank - wird von SmartRace befüllt
car_database = {}

def register_car_from_smartrace(car_data):
    """Registriert ein Auto aus SmartRace car_data Format"""
    car_id = str(car_data.get('id', 'unknown'))
    
    if car_id not in car_database:
        # Standard-Farben wenn keine RGB-Farbe übertragen wird
        default_colors = ['#FF8C00', '#DC143C', '#00D2BE', '#1E41FF', '#FFD700', '#0066CC', '#8B0000', '#32CD32', '#9932CC', '#FF69B4']
        
        # RGB zu Hex konvertieren falls nötig
        color = car_data.get('color', '')
        hex_color = default_colors[len(car_database) % len(default_colors)]  # Fallback
        
        if color and color.startswith('rgb('):
            # RGB zu Hex konvertieren
            try:
                rgb_values = color.replace('rgb(', '').replace(')', '').split(',')
                r, g, b = [int(x.strip()) for x in rgb_values]
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
            except:
                pass
        elif color.startswith('#'):
            hex_color = color
        
        # Auto-Kategorie aus Herstellerdaten ableiten
        manufacturer = car_data.get('manufacturer', 'Unknown').lower()
        car_class = 'Slot Car'  # Standard für SmartRace
        
        if 'formula' in car_data.get('name', '').lower():
            car_class = 'Formula'
        elif 'gt' in car_data.get('name', '').lower():
            car_class = 'GT'
        elif 'rally' in car_data.get('name', '').lower():
            car_class = 'Rally'
        elif 'touring' in car_data.get('name', '').lower():
            car_class = 'Touring'
        
        car_database[car_id] = {
            'name': car_data.get('name', f'Car {car_id}'),
            'color': hex_color,
            'class': car_class,
            'manufacturer': car_data.get('manufacturer', 'Unknown'),
            'scale': car_data.get('scale', ''),
            'digital_analog': car_data.get('digital_analog', ''),
            'active': car_data.get('active', 'no'),
            'decoder_type': car_data.get('decoder_type', ''),
            'magnets': car_data.get('magnets', ''),
            'tyres': car_data.get('tyres', ''),
            'sound': car_data.get('sound', ''),
            'image': car_data.get('image', ''),
            'logo': car_data.get('logo', ''),
            'comment': car_data.get('comment', ''),
            'tags': car_data.get('tags', '[]'),
            'laps': car_data.get('laps', 0),
            'fuel': car_data.get('fuel', ''),
            'brakes': car_data.get('brakes', ''),
            'speed': car_data.get('speed', ''),
            'changed_on': car_data.get('changed_on', ''),
            'interval': car_data.get('interval', 0),
            'interval_counter': car_data.get('interval_counter', 0)
        }
        
        print(f"🚗 SmartRace car registered: ID {car_id} - {car_database[car_id]['name']} ({car_database[car_id]['manufacturer']})")
        
        # Emit update to all clients
        socketio.emit('car_database_update', car_database)
        
        return car_id

def get_car_info(car_id):
    """Holt Auto-Info oder erstellt Fallback"""
    if car_id in car_database:
        return car_database[car_id]
    
    # Fallback Auto info
    return {
        'name': f'Car {car_id}',
        'color': '#666666',
        'class': 'Unknown',
        'manufacturer': 'Unknown',
        'scale': '',
        'active': 'unknown'
    }

# Main routes (unchanged)
@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html', 
                         race_data=race_data, 
                         track_data=track_data,
                         car_database=car_database)

@app.route('/analysis')
def analysis():
    """Analysis view with detailed statistics"""
    return render_template('analysis.html', 
                         race_data=race_data, 
                         lap_history=lap_history,
                         car_database=car_database)

@app.route('/track')
def track():
    """Track visualization view"""
    return render_template('track.html', 
                         track_data=track_data, 
                         race_data=race_data,
                         car_database=car_database)

# API routes (unchanged)
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

@app.route('/api/car-database')
def get_car_database():
    """Get car database"""
    return jsonify(car_database)

# Webhook endpoints für SmartRace - KORRIGIERT
@app.route('/webhook/race-data', methods=['POST'])
def webhook_race_data():
    """Receive race data from SmartRace with car_data processing"""
    try:
        data = request.get_json()
        if data:
            print(f"📡 Received SmartRace data: {json.dumps(data, indent=2)}")
            
            # Update session_info
            if 'session_info' in data:
                race_data['session_info'].update(data['session_info'])
            
            # Process drivers mit car_data
            if 'drivers' in data:
                for driver_id, driver_data in data['drivers'].items():
                    # SmartRace car_data verarbeiten
                    if 'car_data' in driver_data and driver_data['car_data']:
                        car_id = register_car_from_smartrace(driver_data['car_data'])
                        driver_data['car_id'] = car_id
                    
                race_data['drivers'].update(data['drivers'])
            
            # Separate car_data Verarbeitung (falls direkt übertragen)
            if 'car_data' in data and data['car_data']:
                register_car_from_smartrace(data['car_data'])
            
            # Multiple cars processing (falls als Array übertragen)
            if 'cars' in data and isinstance(data['cars'], list):
                for car_info in data['cars']:
                    register_car_from_smartrace(car_info)
            elif 'cars' in data and isinstance(data['cars'], dict):
                for car_id, car_info in data['cars'].items():
                    register_car_from_smartrace(car_info)
            
            # Emit updates
            socketio.emit('race_update', race_data)
            
        return jsonify({'status': 'success', 'message': 'SmartRace data processed', 'cars_registered': len(car_database)})
    except Exception as e:
        print(f"❌ Error processing SmartRace data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/webhook/car-data', methods=['POST'])
def webhook_car_data():
    """Receive individual car data from SmartRace"""
    try:
        data = request.get_json()
        if data:
            print(f"🚗 Received SmartRace car data: {json.dumps(data, indent=2)}")
            
            # Register single car from SmartRace format
            if 'car_data' in data:
                register_car_from_smartrace(data['car_data'])
            elif 'id' in data and 'name' in data:
                # Direct car object
                register_car_from_smartrace(data)
            
            return jsonify({'status': 'success', 'message': 'SmartRace car registered', 'cars_total': len(car_database)})
    except Exception as e:
        print(f"❌ Error processing SmartRace car data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/webhook/lap-data', methods=['POST'])
def webhook_lap_data():
    """Receive individual lap data from SmartRace"""
    try:
        data = request.get_json()
        if data:
            driver_id = data.get('driver_id')
            if driver_id:
                if driver_id not in lap_history:
                    lap_history[driver_id] = []
                
                # Car data aus lap data verarbeiten
                if 'car_data' in data and data['car_data']:
                    car_id = register_car_from_smartrace(data['car_data'])
                    data['car_id'] = car_id
                
                lap_data = {
                    'lap_number': data.get('lap_number'),
                    'lap_time': data.get('lap_time'),
                    'sector_1': data.get('sector_1'),
                    'sector_2': data.get('sector_2'),
                    'sector_3': data.get('sector_3'),
                    'timestamp': data.get('timestamp', datetime.datetime.now().isoformat()),
                    'car_id': data.get('car_id')
                }
                
                lap_history[driver_id].append(lap_data)
                
                # Keep only last 50 laps per driver
                if len(lap_history[driver_id]) > 50:
                    lap_history[driver_id] = lap_history[driver_id][-50:]
            
            socketio.emit('lap_update', {'driver_id': driver_id, 'lap_data': data})
        
        return jsonify({'status': 'success', 'message': 'SmartRace lap data processed'})
    except Exception as e:
        print(f"❌ Error processing SmartRace lap data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/webhook/track-data', methods=['POST'])
def webhook_track_data():
    """Receive track data from SmartRace"""
    try:
        data = request.get_json()
        if data:
            track_data.update(data)
            socketio.emit('track_update', track_data)
        
        return jsonify({'status': 'success', 'message': 'Track data updated'})
    except Exception as e:
        print(f"❌ Error processing track data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

# CSV Export Routes mit SmartRace Daten
@app.route('/export/race-data')
def export_race_data():
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Driver_ID', 'Driver_Name', 'Car_ID', 'Car_Name', 'Car_Manufacturer', 'Car_Scale', 'Car_Class', 'Position', 'Laps', 'Best_Time', 'Last_Time', 'Gap', 'Status'])
    
    for driver_id, driver in race_data['drivers'].items():
        car_id = driver.get('car_id', 'unknown')
        car_info = get_car_info(car_id)
        
        writer.writerow([
            driver_id,
            driver.get('name', f'Driver {driver_id}'),
            car_id,
            car_info['name'],
            car_info['manufacturer'],
            car_info['scale'],
            car_info['class'],
            driver.get('position', ''),
            driver.get('laps_completed', 0),
            driver.get('best_lap_time', ''),
            driver.get('last_lap_time', ''),
            driver.get('gap', ''),
            driver.get('status', 'Unknown')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=smartrace_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@app.route('/export/lap-history')
def export_lap_history():
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Driver_ID', 'Driver_Name', 'Car_Name', 'Car_Manufacturer', 'Lap_Number', 'Lap_Time', 'Sector_1', 'Sector_2', 'Sector_3', 'Timestamp'])
    
    for driver_id, laps in lap_history.items():
        driver_name = race_data['drivers'].get(driver_id, {}).get('name', f'Driver {driver_id}')
        car_id = race_data['drivers'].get(driver_id, {}).get('car_id', 'unknown')
        car_info = get_car_info(car_id)
        
        for lap in laps:
            writer.writerow([
                driver_id,
                driver_name,
                car_info['name'],
                car_info['manufacturer'],
                lap.get('lap_number', ''),
                lap.get('lap_time', ''),
                lap.get('sector_1', ''),
                lap.get('sector_2', ''),
                lap.get('sector_3', ''),
                lap.get('timestamp', '')
            ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=smartrace_laps_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@app.route('/export/session-summary')
def export_session_summary():
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Metric', 'Value'])
    
    writer.writerow(['Session Type', race_data['session_info']['session_type']])
    writer.writerow(['Total Time', race_data['session_info']['total_time']])
    writer.writerow(['Total Laps', race_data['session_info']['total_laps']])
    writer.writerow(['Session Status', race_data['session_info']['session_status']])
    writer.writerow(['Cars Registered', len(car_database)])
    writer.writerow([''])
    
    writer.writerow(['Driver Summary', ''])
    writer.writerow(['Driver', 'Car', 'Manufacturer', 'Scale', 'Best Lap', 'Total Laps', 'Position'])
    
    for driver_id, driver in race_data['drivers'].items():
        car_id = driver.get('car_id', 'unknown')
        car_info = get_car_info(car_id)
        
        writer.writerow([
            driver.get('name', f'Driver {driver_id}'),
            car_info['name'],
            car_info['manufacturer'],
            car_info['scale'],
            driver.get('best_lap_time', ''),
            driver.get('laps_completed', 0),
            driver.get('position', '')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=smartrace_summary_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

# Test route mit echtem SmartRace Format
@app.route('/test/generate-smartrace-data')
def generate_smartrace_test_data():
    """Generate test data in real SmartRace format"""
    import random
    
    # Reset databases
    global car_database
    car_database = {}
    
    # Test data im echten SmartRace Format
    test_smartrace_data = {
        "session_info": {
            "session_type": "Race",
            "session_status": "Running",
            "total_time": "00:15:23",
            "current_lap": 16,
            "flag_status": "Green"
        },
        "drivers": {
            "driver_1": {
                "name": "Max Verstappen",
                "position": 1,
                "laps_completed": 15,
                "best_lap_time": "1:23.456",
                "last_lap_time": "1:24.123",
                "gap": "Leader",
                "status": "Running",
                "car_data": {
                    "color": "rgb(30, 65, 255)",
                    "brakes": "Carbon",
                    "active": "yes",
                    "tags": "[]",
                    "decoder_type": "Carrera (default)",
                    "image": "cdvfile://localhost/persistent/redbull.jpg",
                    "laps": 15,
                    "fuel": "98%",
                    "speed": "High",
                    "tyres": "Soft",
                    "digital_analog": "digital",
                    "name": "Red Bull RB19",
                    "manufacturer": "Red Bull Racing",
                    "id": 1,
                    "interval_counter": 0,
                    "scale": "1:32",
                    "magnets": "no",
                    "logo": "redbull.png",
                    "changed_on": None,
                    "interval": 0,
                    "sound": "V6 Turbo",
                    "comment": "Championship winning car"
                }
            },
            "driver_2": {
                "name": "Lewis Hamilton",
                "position": 2,
                "laps_completed": 15,
                "best_lap_time": "1:23.789",
                "last_lap_time": "1:24.456",
                "gap": "+2.345",
                "status": "Running",
                "car_data": {
                    "color": "rgb(0, 210, 190)",
                    "brakes": "Brembo",
                    "active": "yes",
                    "tags": "[]",
                    "decoder_type": "Carrera (default)",
                    "image": "cdvfile://localhost/persistent/mercedes.jpg",
                    "laps": 15,
                    "fuel": "95%",
                    "speed": "High",
                    "tyres": "Medium",
                    "digital_analog": "digital",
                    "name": "Mercedes W14",
                    "manufacturer": "Mercedes-AMG",
                    "id": 2,
                    "interval_counter": 0,
                    "scale": "1:32",
                    "magnets": "no",
                    "logo": "mercedes.png",
                    "changed_on": None,
                    "interval": 0,
                    "sound": "V6 Hybrid",
                    "comment": "Silver Arrow"
                }
            },
            "driver_3": {
                "name": "Charles Leclerc",
                "position": 3,
                "laps_completed": 14,
                "best_lap_time": "1:23.901",
                "last_lap_time": "1:25.123",
                "gap": "+1 Lap",
                "status": "Running",
                "car_data": {
                    "color": "rgb(220, 20, 60)",
                    "brakes": "Brembo",
                    "active": "yes",
                    "tags": "[]",
                    "decoder_type": "Carrera (default)",
                    "image": "cdvfile://localhost/persistent/ferrari.jpg",
                    "laps": 14,
                    "fuel": "92%",
                    "speed": "High",
                    "tyres": "Hard",
                    "digital_analog": "digital",
                    "name": "Ferrari SF-23",
                    "manufacturer": "Scuderia Ferrari",
                    "id": 3,
                    "interval_counter": 0,
                    "scale": "1:32",
                    "magnets": "no",
                    "logo": "ferrari.png",
                    "changed_on": None,
                    "interval": 0,
                    "sound": "V6 Turbo",
                    "comment": "Prancing Horse"
                }
            },
            "driver_4": {
                "name": "Stuttgart Racing",
                "position": 4,
                "laps_completed": 14,
                "best_lap_time": "1:24.234",
                "last_lap_time": "1:24.567",
                "gap": "+5.678",
                "status": "Running",
                "car_data": {
                    "color": "rgb(176, 243, 0)",
                    "brakes": None,
                    "active": "yes",
                    "tags": "[]",
                    "decoder_type": "Carrera (default)",
                    "image": "cdvfile://localhost/persistent/1684000048302.jpg",
                    "laps": 14,
                    "fuel": None,
                    "speed": None,
                    "tyres": "Ortmann",
                    "digital_analog": "digital",
                    "name": "Porsche 911 RSR Grello (911)",
                    "manufacturer": "Carrera",
                    "id": 40,
                    "interval_counter": 0,
                    "scale": "1:24",
                    "magnets": "yes",
                    "logo": "porsche.png",
                    "changed_on": None,
                    "interval": 0,
                    "sound": "-",
                    "comment": ""
                }
            }
        }
    }
    
    # Process test data through webhook
    webhook_race_data_result = webhook_race_data()
    request.get_json = lambda: test_smartrace_data
    
    # Update race data
    race_data['session_info'].update(test_smartrace_data['session_info'])
    
    for driver_id, driver_data in test_smartrace_data['drivers'].items():
        if 'car_data' in driver_data:
            car_id = register_car_from_smartrace(driver_data['car_data'])
            driver_data['car_id'] = car_id
    
    race_data['drivers'].update(test_smartrace_data['drivers'])
    
    # Generate test lap history
    for driver_id, driver_data in test_smartrace_data['drivers'].items():
        lap_history[driver_id] = []
        for lap in range(1, driver_data['laps_completed'] + 1):
            base_time = 83.0 + random.uniform(-2, 3)
            lap_time = f"1:{base_time:.3f}"
            
            lap_history[driver_id].append({
                'lap_number': lap,
                'lap_time': lap_time,
                'sector_1': f"{random.uniform(25, 30):.3f}",
                'sector_2': f"{random.uniform(28, 32):.3f}",
                'sector_3': f"{random.uniform(25, 29):.3f}",
                'timestamp': datetime.datetime.now().isoformat(),
                'car_id': driver_data.get('car_id')
            })
    
    socketio.emit('race_update', race_data)
    socketio.emit('car_database_update', car_database)
    
    return jsonify({
        'status': 'success', 
        'message': 'SmartRace test data generated', 
        'drivers': len(test_smartrace_data['drivers']),
        'cars': len(car_database),
        'format': 'SmartRace compatible'
    })

# WebSocket event handlers
@socketio.on('connect')
def on_connect():
    print(f"🔌 Client connected: {request.sid}")
    emit('race_update', race_data)
    emit('track_update', track_data)
    emit('car_database_update', car_database)

@socketio.on('disconnect')
def on_disconnect():
    print(f"🔌 Client disconnected: {request.sid}")

if __name__ == '__main__':
    print("🏁 SmartRace Dashboard starting...")
    print("📡 SmartRace Webhooks available:")
    print("   POST /webhook/race-data - Race data with car_data")
    print("   POST /webhook/car-data - Individual car registration")
    print("   POST /webhook/track-data - Track data updates") 
    print("   POST /webhook/lap-data - Individual lap data with car_data")
    print("🧪 SmartRace test data: GET /test/generate-smartrace-data")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

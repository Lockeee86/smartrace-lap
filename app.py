from flask import Flask, render_template, request, jsonify, make_response, flash, redirect, url_for
from flask_socketio import SocketIO, emit
import datetime
import json
import csv
import io
import os
from dotenv import load_dotenv
import dropbox
from dropbox.exceptions import ApiError, AuthError
import threading
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smartrace-dashboard-secret-key'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Dropbox configuration
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
DROPBOX_FOLDER = os.getenv('DROPBOX_FOLDER', '/SmartRace_Data')
DROPBOX_ENABLED = os.getenv('DROPBOX_ENABLED', 'false').lower() == 'true'

# Initialize Dropbox client
dbx = None
if DROPBOX_ENABLED and DROPBOX_ACCESS_TOKEN:
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        dbx.users_get_current_account()
        print("✅ Dropbox connection established")
    except AuthError:
        print("❌ Dropbox authentication failed")
        dbx = None
    except Exception as e:
        print(f"❌ Dropbox initialization error: {e}")
        dbx = None

# Global data storage
race_data = {
    'session_info': {
        'session_type': 'Practice',
        'total_time': '00:00:00',
        'total_laps': 0,
        'current_lap': 0,
        'session_status': 'Waiting',
        'flag_status': 'Green',
        'session_start': None,
        'session_name': f'SmartRace_Session_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
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
car_database = {}

# Dropbox helper functions
def upload_to_dropbox(file_content, filename, folder=None):
    """Upload file content to Dropbox"""
    if not dbx:
        return False, "Dropbox not configured"
    
    try:
        dropbox_path = f"{DROPBOX_FOLDER}/{folder}" if folder else DROPBOX_FOLDER
        full_path = f"{dropbox_path}/{filename}"
        
        # Create folder if it doesn't exist
        try:
            dbx.files_get_metadata(dropbox_path)
        except:
            try:
                dbx.files_create_folder_v2(dropbox_path)
            except:
                pass  # Folder might already exist
        
        # Upload file
        dbx.files_upload(
            file_content.encode('utf-8') if isinstance(file_content, str) else file_content,
            full_path,
            mode=dropbox.files.WriteMode('overwrite'),
            autorename=True
        )
        
        return True, f"Successfully uploaded to {full_path}"
    
    except ApiError as e:
        return False, f"Dropbox API error: {e}"
    except Exception as e:
        return False, f"Upload error: {e}"

def get_session_folder_name():
    """Generate folder name for current session"""
    session_name = race_data['session_info'].get('session_name', 'Unknown_Session')
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"{date_str}_{session_name}"

def auto_backup_session():
    """Automatically backup current session data"""
    if not DROPBOX_ENABLED or not dbx:
        return
    
    try:
        folder_name = get_session_folder_name()
        
        # Export race results
        csv_content = generate_race_results_csv()
        success, msg = upload_to_dropbox(csv_content, "race_results.csv", folder_name)
        
        if success:
            print(f"✅ Auto-backup: Race results uploaded")
        
        # Export lap history
        lap_csv_content = generate_lap_history_csv()
        success, msg = upload_to_dropbox(lap_csv_content, "lap_history.csv", folder_name)
        
        if success:
            print(f"✅ Auto-backup: Lap history uploaded")
        
        # Export session info as JSON
        session_json = json.dumps({
            'race_data': race_data,
            'track_data': track_data,
            'car_database': car_database,
            'export_timestamp': datetime.datetime.now().isoformat()
        }, indent=2)
        
        success, msg = upload_to_dropbox(session_json, "session_data.json", folder_name)
        
        if success:
            print(f"✅ Auto-backup: Session data uploaded")
            
    except Exception as e:
        print(f"❌ Auto-backup failed: {e}")

# Modified CSV generation functions
def generate_race_results_csv():
    """Generate race results CSV with car information"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers with car information
    headers = [
        'Position', 'Driver Name', 'Car Name', 'Car Manufacturer', 
        'Car Scale', 'Car Class', 'Car Color', 'Digital/Analog',
        'Laps Completed', 'Best Lap Time', 'Last Lap Time', 
        'Total Time', 'Gap', 'Status', 'Export Time'
    ]
    writer.writerow(headers)
    
    # Sort drivers by position
    sorted_drivers = sorted(
        race_data['drivers'].items(),
        key=lambda x: int(x[1].get('position', 999))
    )
    
    export_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for driver_id, driver in sorted_drivers:
        car_info = car_database.get(driver.get('car_id'), {})
        
        row = [
            driver.get('position', '-'),
            driver.get('name', f'Driver {driver_id}'),
            car_info.get('name', 'Unknown Car'),
            car_info.get('manufacturer', 'Unknown'),
            car_info.get('scale', '-'),
            get_car_class_from_smartrace(car_info),
            car_info.get('color', '#666666'),
            car_info.get('digital_analog', 'unknown'),
            driver.get('laps_completed', 0),
            driver.get('best_lap_time', '-'),
            driver.get('last_lap_time', '-'),
            driver.get('total_time', '-'),
            driver.get('gap', '-'),
            driver.get('status', 'Unknown'),
            export_time
        ]
        writer.writerow(row)
    
    return output.getvalue()

def generate_lap_history_csv():
    """Generate lap history CSV with car information"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    headers = [
        'Driver ID', 'Driver Name', 'Car Name', 'Car Manufacturer',
        'Lap Number', 'Lap Time', 'Sector 1', 'Sector 2', 'Sector 3',
        'Timestamp', 'Session'
    ]
    writer.writerow(headers)
    
    session_name = race_data['session_info'].get('session_name', 'Unknown Session')
    
    for driver_id, laps in lap_history.items():
        driver_info = race_data['drivers'].get(driver_id, {})
        car_info = car_database.get(driver_info.get('car_id'), {})
        
        for lap in laps:
            row = [
                driver_id,
                driver_info.get('name', f'Driver {driver_id}'),
                car_info.get('name', 'Unknown Car'),
                car_info.get('manufacturer', 'Unknown'),
                lap.get('lap_number', '-'),
                lap.get('lap_time', '-'),
                lap.get('sector_1', '-'),
                lap.get('sector_2', '-'),
                lap.get('sector_3', '-'),
                lap.get('timestamp', datetime.datetime.now().isoformat()),
                session_name
            ]
            writer.writerow(row)
    
    return output.getvalue()

# Existing functions (register_car_from_smartrace, etc.) bleiben unverändert...
def register_car_from_smartrace(car_data):
    """Registriert ein Auto aus SmartRace car_data Format"""
    car_id = str(car_data.get('id', 'unknown'))
    
    if car_id not in car_database:
        default_colors = ['#FF8C00', '#DC143C', '#00D2BE', '#1E41FF', '#FFD700', '#0066CC', '#8B0000', '#32CD32', '#9932CC', '#FF69B4']
        
        color = car_data.get('color', '')
        hex_color = default_colors[len(car_database) % len(default_colors)]
        
        if color and color.startswith('rgb('):
            try:
                rgb_values = color.replace('rgb(', '').replace(')', '').split(',')
                r, g, b = [int(x.strip()) for x in rgb_values]
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
            except:
                pass
        elif color.startswith('#'):
            hex_color = color
        
        car_database[car_id] = {
            'name': car_data.get('name', f'Car {car_id}'),
            'color': hex_color,
            'manufacturer': car_data.get('manufacturer', 'Unknown'),
            'scale': car_data.get('scale', '1:32'),
            'digital_analog': car_data.get('digital_analog', 'digital'),
            'magnets': car_data.get('magnets', 'unknown'),
            'tyres': car_data.get('tyres', 'unknown'),
            'decoder_type': car_data.get('decoder_type', 'unknown'),
            'logo': car_data.get('logo', ''),
            'comment': car_data.get('comment', ''),
            'smartrace_data': car_data
        }
        
        print(f"✅ Registered SmartRace car: {car_database[car_id]['name']}")

def get_car_class_from_smartrace(car_info):
    """Extract car class from SmartRace data"""
    name = car_info.get('name', '').lower()
    manufacturer = car_info.get('manufacturer', '').lower()
    
    if 'formula' in name or 'f1' in name:
        return 'Formula'
    elif any(term in name for term in ['gt', 'gte', 'gtc']):
        return 'GT'
    elif 'rally' in name:
        return 'Rally'
    elif 'nascar' in name:
        return 'NASCAR'
    elif 'le mans' in name or 'lmp' in name:
        return 'Endurance'
    elif manufacturer in ['carrera', 'scalextric', 'ninco']:
        return 'Slot Car'
    else:
        return 'Sports Car'

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html', 
                         race_data=race_data, 
                         track_data=track_data,
                         dropbox_enabled=DROPBOX_ENABLED,
                         dropbox_connected=dbx is not None)

@app.route('/settings')
def settings():
    return render_template('settings.html',
                         dropbox_enabled=DROPBOX_ENABLED,
                         dropbox_connected=dbx is not None,
                         dropbox_folder=DROPBOX_FOLDER)

@app.route('/api/dropbox/status')
def dropbox_status():
    """Get Dropbox connection status"""
    if not DROPBOX_ENABLED:
        return jsonify({'enabled': False, 'connected': False, 'message': 'Dropbox integration disabled'})
    
    if not dbx:
        return jsonify({'enabled': True, 'connected': False, 'message': 'Dropbox not connected'})
    
    try:
        account = dbx.users_get_current_account()
        return jsonify({
            'enabled': True,
            'connected': True,
            'account_name': account.name.display_name,
            'email': account.email,
            'folder': DROPBOX_FOLDER,
            'message': 'Connected successfully'
        })
    except Exception as e:
        return jsonify({'enabled': True, 'connected': False, 'message': f'Connection error: {e}'})

@app.route('/api/export/dropbox')
def export_to_dropbox():
    """Export current session to Dropbox"""
    if not DROPBOX_ENABLED or not dbx:
        return jsonify({'success': False, 'message': 'Dropbox not available'})
    
    try:
        folder_name = get_session_folder_name()
        results = []
        
        # Export race results
        csv_content = generate_race_results_csv()
        success, msg = upload_to_dropbox(csv_content, "race_results.csv", folder_name)
        results.append({'file': 'race_results.csv', 'success': success, 'message': msg})
        
        # Export lap history
        lap_csv_content = generate_lap_history_csv()
        success, msg = upload_to_dropbox(lap_csv_content, "lap_history.csv", folder_name)
        results.append({'file': 'lap_history.csv', 'success': success, 'message': msg})
        
        # Export session data
        session_json = json.dumps({
            'race_data': race_data,
            'track_data': track_data,
            'car_database': car_database,
            'export_timestamp': datetime.datetime.now().isoformat()
        }, indent=2)
        
        success, msg = upload_to_dropbox(session_json, "session_data.json", folder_name)
        results.append({'file': 'session_data.json', 'success': success, 'message': msg})
        
        successful_uploads = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': successful_uploads > 0,
            'message': f'Successfully uploaded {successful_uploads}/{len(results)} files to Dropbox/{folder_name}',
            'results': results,
            'folder': f"{DROPBOX_FOLDER}/{folder_name}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Export failed: {e}'})

# Existing routes remain the same...
@app.route('/api/race-data')
def get_race_data():
    return jsonify(race_data)

@app.route('/api/track-data')
def get_track_data():
    return jsonify(track_data)

@app.route('/api/lap-history')
def get_lap_history():
    return jsonify(lap_history)

@app.route('/api/car-database')
def get_car_database():
    return jsonify(car_database)

# Track management route
@app.route('/track')
def track():
    """Track management page"""
    return render_template('track.html')

@app.route('/api/track-info')
def track_info():
    """Get track information"""
    return jsonify({
        'track_name': 'Nürburgring GP',
        'length': 5148,
        'sectors': 3,
        'layout': 'road_course'
    })

# Analysis route  
@app.route('/analysis')
def analysis():
    """Analysis page"""
    return render_template('analysis.html')

@app.route('/api/analysis-data')
def analysis_data():
    """Get analysis data"""
    return jsonify({
        'sessions': [],
        'statistics': {},
        'charts': []
    })


@app.route('/smartrace', methods=['POST'])
def handle_smartrace_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Register car if present
        if 'car_data' in data:
            register_car_from_smartrace(data['car_data'])
            socketio.emit('car_database_update', car_database)
        
        # Handle driver data
        if 'driver_data' in data:
            driver_data = data['driver_data']
            driver_id = str(driver_data.get('id', 'unknown'))
            
            race_data['drivers'][driver_id] = {
                'name': driver_data.get('name', f'Driver {driver_id}'),
                'car_id': str(data.get('car_data', {}).get('id', 'unknown')),
                'position': driver_data.get('position'),
                'laps_completed': driver_data.get('laps', 0),
                'best_lap_time': driver_data.get('best_time'),
                'last_lap_time': driver_data.get('last_time'),
                'total_time': driver_data.get('total_time'),
                'gap': driver_data.get('gap'),
                'status': driver_data.get('status', 'Running')
            }
        
        # Handle lap data
        if 'lap_data' in data:
            lap_data = data['lap_data']
            driver_id = str(data.get('driver_data', {}).get('id', 'unknown'))
            
            if driver_id not in lap_history:
                lap_history[driver_id] = []
            
            lap_info = {
                'lap_number': lap_data.get('lap_number'),
                'lap_time': lap_data.get('lap_time'),
                'sector_1': lap_data.get('sector_1'),
                'sector_2': lap_data.get('sector_2'),
                'sector_3': lap_data.get('sector_3'),
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            lap_history[driver_id].append(lap_info)
            
            if len(lap_history[driver_id]) > 100:
                lap_history[driver_id] = lap_history[driver_id][-100:]
            
            socketio.emit('lap_update', {
                'driver_id': driver_id,
                'lap_data': lap_info
            })
        
        # Handle session data
        if 'session_data' in data:
            session_data = data['session_data']
            race_data['session_info'].update({
                'session_type': session_data.get('type', race_data['session_info']['session_type']),
                'total_time': session_data.get('total_time', race_data['session_info']['total_time']),
                'current_lap': session_data.get('current_lap', race_data['session_info']['current_lap']),
                'session_status': session_data.get('status', race_data['session_info']['session_status']),
                'flag_status': session_data.get('flag_status', race_data['session_info']['flag_status'])
            })
        
        socketio.emit('race_update', race_data)
        
        return jsonify({'success': True, 'message': 'Data processed successfully'})
        
    except Exception as e:
        print(f"Error processing SmartRace data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/csv/race-results')
def export_race_results():
    csv_data = generate_race_results_csv()
    
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename=smartrace_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Type"] = "text/csv"
    
    return response

@app.route('/export/csv/lap-history')
def export_lap_history():
    csv_data = generate_lap_history_csv()
    
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename=smartrace_laphistory_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Type"] = "text/csv"
    
    return response

# Auto-backup thread
def start_auto_backup():
    """Start automatic backup thread"""
    if not DROPBOX_ENABLED or not dbx:
        return
    
    interval = int(os.getenv('AUTO_UPLOAD_INTERVAL', 300))  # 5 minutes default
    
    def backup_loop():
        while True:
            time.sleep(interval)
            if race_data['session_info']['session_status'] in ['Running', 'Finished']:
                auto_backup_session()
    
    backup_thread = threading.Thread(target=backup_loop, daemon=True)
    backup_thread.start()
    print(f"✅ Auto-backup started (interval: {interval}s)")

if __name__ == '__main__':
    print("🏁 SmartRace Dashboard with Dropbox Integration")
    print(f"📁 Dropbox: {'✅ Enabled' if DROPBOX_ENABLED else '❌ Disabled'}")
    if DROPBOX_ENABLED:
        print(f"📂 Dropbox folder: {DROPBOX_FOLDER}")
    
    # Production-ready server start
    socketio.run(app, 
                host='0.0.0.0', 
                port=5000, 
                debug=False,  # Debug auf False für Production
                allow_unsafe_werkzeug=True)  # Für Development erlauben

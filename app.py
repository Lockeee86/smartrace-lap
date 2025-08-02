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
            'lap_history': lap_history,
            'car_database': car_database,
            'export_timestamp': datetime.datetime.now().isoformat()
        }, indent=2)
        
        success, msg = upload_to_dropbox(session_json, "session_data.json", folder_name)
        
        if success:
            print(f"✅ Auto-backup: Session data uploaded")
    
    except Exception as e:
        print(f"❌ Auto-backup failed: {e}")

def generate_race_results_csv():
    """Generate CSV content for race results"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Position', 'Driver ID', 'Driver Name', 'Car Number', 
        'Total Time', 'Best Lap', 'Total Laps', 'Gap', 'Status'
    ])
    
    # Sort drivers by position or best lap
    sorted_drivers = sorted(
        race_data['drivers'].items(), 
        key=lambda x: x[1].get('position', 999)
    )
    
    for driver_id, driver_data in sorted_drivers:
        writer.writerow([
            driver_data.get('position', 'N/A'),
            driver_id,
            driver_data.get('name', 'Unknown'),
            driver_data.get('car_number', 'N/A'),
            driver_data.get('total_time', '00:00:00'),
            driver_data.get('best_lap', '00:00:00'),
            driver_data.get('total_laps', 0),
            driver_data.get('gap', '0.000'),
            driver_data.get('status', 'Running')
        ])
    
    return output.getvalue()

def generate_lap_history_csv():
    """Generate CSV content for lap history"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Driver ID', 'Lap Number', 'Lap Time', 'Sector 1', 
        'Sector 2', 'Sector 3', 'Timestamp'
    ])
    
    # Write lap data
    for driver_id, laps in lap_history.items():
        for lap in laps:
            writer.writerow([
                driver_id,
                lap.get('lap_number', 'N/A'),
                lap.get('lap_time', '00:00:00'),
                lap.get('sector_1', '00:00:00'),
                lap.get('sector_2', '00:00:00'),
                lap.get('sector_3', '00:00:00'),
                lap.get('timestamp', '')
            ])
    
    return output.getvalue()

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    try:
        return render_template('index.html', 
                             dropbox_enabled=DROPBOX_ENABLED,
                             total_drivers=len(race_data['drivers']))
    except Exception as e:
        print(f"ERROR in index route: {e}")
        return jsonify({"error": f"Homepage error: {e}"}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "server": "SmartRace Dashboard",
            "dropbox_enabled": DROPBOX_ENABLED,
            "total_drivers": len(race_data['drivers'])
        })
    except Exception as e:
        print(f"ERROR in health_check: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/race-data')
def get_race_data():
    """Get race data - KORRIGIERT"""
    try:
        return jsonify(race_data)
    except Exception as e:
        print(f"ERROR in get_race_data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/track-data')
def get_track_data():
    """Get track data - KORRIGIERT"""
    try:
        return jsonify(track_data)
    except Exception as e:
        print(f"ERROR in get_track_data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/lap-history')
def get_lap_history():
    """Get lap history - KORRIGIERT"""
    try:
        return jsonify(lap_history)
    except Exception as e:
        print(f"ERROR in get_lap_history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/car-database')
def get_car_database():
    """Get car database - KORRIGIERT"""
    try:
        return jsonify(car_database)
    except Exception as e:
        print(f"ERROR in get_car_database: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/track-info')
def track_info():
    """Get track information - KORRIGIERT"""
    try:
        return jsonify({
            'track_name': 'Nürburgring GP',
            'length': 5148,
            'sectors': 3,
            'layout': 'road_course'
        })
    except Exception as e:
        print(f"ERROR in track_info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis-data')
def analysis_data():
    """Get analysis data - KORRIGIERT"""
    try:
        return jsonify({
            'sessions': [],
            'statistics': {},
            'charts': []
        })
    except Exception as e:
        print(f"ERROR in analysis_data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dropbox/status')
def dropbox_status():
    """Get Dropbox connection status - KORRIGIERT"""
    try:
        if not DROPBOX_ENABLED:
            return jsonify({'enabled': False, 'connected': False, 'message': 'Dropbox integration disabled'})
        
        if not dbx:
            return jsonify({'enabled': True, 'connected': False, 'message': 'Dropbox not connected'})
        
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
        print(f"ERROR in dropbox_status: {e}")
        return jsonify({'enabled': True, 'connected': False, 'message': f'Connection error: {e}'}), 500

@app.route('/api/dropbox/upload', methods=['POST'])
def manual_upload():
    """Manual upload to Dropbox"""
    try:
        if not DROPBOX_ENABLED or not dbx:
            return jsonify({'success': False, 'message': 'Dropbox not available'}), 400
        
        folder_name = get_session_folder_name()
        
        # Upload race results
        csv_content = generate_race_results_csv()
        success, msg = upload_to_dropbox(csv_content, "race_results.csv", folder_name)
        
        if not success:
            return jsonify({'success': False, 'message': msg}), 500
        
        # Upload lap history
        lap_csv_content = generate_lap_history_csv()
        success, msg = upload_to_dropbox(lap_csv_content, "lap_history.csv", folder_name)
        
        if not success:
            return jsonify({'success': False, 'message': msg}), 500
        
        return jsonify({
            'success': True, 
            'message': f'Files uploaded to {folder_name}',
            'folder': folder_name
        })
        
    except Exception as e:
        print(f"ERROR in manual_upload: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/smartrace', methods=['POST'])
def receive_smartrace_data():
    """Receive data from SmartRace"""
    try:
        data = request.get_json()
        print(f"📥 Received SmartRace data: {json.dumps(data, indent=2)}")
        
        # Handle driver data
        if 'driver_data' in data:
            driver_data = data['driver_data']
            driver_id = str(driver_data.get('id', 'unknown'))
            
            race_data['drivers'][driver_id] = {
                'name': driver_data.get('name', f'Driver {driver_id}'),
                'car_number': driver_data.get('car_number'),
                'position': driver_data.get('position'),
                'best_lap': driver_data.get('best_lap'),
                'last_lap': driver_data.get('last_lap'),
                'total_laps': driver_data.get('total_laps'),
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
    """Export race results as CSV"""
    try:
        csv_data = generate_race_results_csv()
        
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = f"attachment; filename=smartrace_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-Type"] = "text/csv"
        
        return response
    except Exception as e:
        print(f"ERROR in export_race_results: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/csv/lap-history')
def export_lap_history():
    """Export lap history as CSV"""
    try:
        csv_data = generate_lap_history_csv()
        
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = f"attachment; filename=smartrace_laphistory_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-Type"] = "text/csv"
        
        return response
    except Exception as e:
        print(f"ERROR in export_lap_history: {e}")
        return jsonify({'error': str(e)}), 500

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("🔌 Client connected")
    emit('race_update', race_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print("🔌 Client disconnected")

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

# Main
if __name__ == '__main__':
    print("🏁 SmartRace Dashboard with Dropbox Integration")
    print(f"📁 Dropbox: {'✅ Enabled' if DROPBOX_ENABLED else '❌ Disabled'}")
    if DROPBOX_ENABLED:
        print(f"📂 Dropbox folder: {DROPBOX_FOLDER}")
        # Start auto-backup thread
        start_auto_backup()
    
    # Production-ready server start
    try:
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=5000, 
                    debug=False,  # Debug auf False für Production
                    use_reloader=False,  # Verhindert doppelte Starts
                    allow_unsafe_werkzeug=True)  # Für Development erlauben
    except Exception as e:
        print(f"❌ Server start failed: {e}")

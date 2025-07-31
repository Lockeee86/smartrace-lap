from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime
from database import RaceDatabase

app = Flask(__name__)
db = RaceDatabase()

# Health check endpoint für Docker
@app.route('/health', methods=['GET'])
def health_check():
    """Health check für Docker"""
    try:
        db_info = db.get_database_info()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'total_laps': db_info['total_laps'],
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/', methods=['GET'])
def dashboard():
    """Hauptseite mit Dashboard"""
    return render_template('dashboard.html')

@app.route('/webhook', methods=['POST'])
def receive_race_data():
    """Empfange POST-Daten von SmartRace App"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Keine Daten empfangen'}), 400
        
        print(f"Empfangen: {data['event_type']} um {datetime.fromtimestamp(data['time']/1000)}")
        
        # Nur lap_update Events verarbeiten
        if data['event_type'] == 'ui.lap_update':
            db.insert_lap_update(data)
            print(f"Runde gespeichert: {data['event_data']['driver_data']['name']} - Runde {data['event_data']['lap']} - Zeit: {data['event_data']['laptime']}")
        
        return jsonify({'status': 'success', 'message': 'Daten empfangen und gespeichert'}), 200
    
    except Exception as e:
        print(f"Fehler beim Verarbeiten der Daten: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/latest-laps', methods=['GET'])
def get_latest_laps():
    """API Endpoint für neueste Runden"""
    limit = request.args.get('limit', 20, type=int)
    laps = db.get_latest_laps(limit)
    return jsonify(laps)

@app.route('/api/driver-stats', methods=['GET'])
def get_driver_stats():
    """API Endpoint für Fahrerstatistiken"""
    driver_name = request.args.get('driver')
    stats = db.get_driver_stats(driver_name)
    return jsonify(stats)

@app.route('/api/live-data', methods=['GET'])
def get_live_data():
    """API Endpoint für Live-Daten"""
    recent_laps = db.get_latest_laps(10)
    driver_stats = db.get_driver_stats()
    db_info = db.get_database_info()
    
    return jsonify({
        'recent_laps': recent_laps,
        'driver_stats': driver_stats,
        'database_info': db_info,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/database-info', methods=['GET'])
def get_database_info():
    """API Endpoint für Datenbank-Informationen"""
    return jsonify(db.get_database_info())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"SmartRace Server startet auf Port {port}")
    print(f"Debug Modus: {debug}")
    print(f"Datenbank Pfad: {os.environ.get('DATABASE_PATH', '/app/data/smartrace.db')}")
    
    # Für Docker - lausche auf allen Interfaces
    app.run(host='0.0.0.0', port=port, debug=debug)

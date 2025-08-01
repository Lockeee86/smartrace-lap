from flask import Flask, request, jsonify, render_template
from database import RaceDatabase
import json
from datetime import datetime

app = Flask(__name__)
db = RaceDatabase()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Keine Daten erhalten'}), 400
        
        if data.get('event_type') == 'ui.lap_update':
            db.insert_lap_update(data)
            return jsonify({'status': 'success'}), 200
        
        return jsonify({'status': 'ignored', 'reason': 'Event type not supported'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-data')
def live_data():
    try:
        stats = db.get_driver_stats()
        recent = db.get_recent_laps(20)
        db_info = db.get_database_info()
        
        last_update = "Keine Daten"
        if recent:
            last_update = recent[0]['datetime']
        
        return jsonify({
            'driver_stats': stats,
            'recent_laps': recent,
            'database_info': db_info,
            'last_update': last_update
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Neue Analyse-Endpoints
@app.route('/api/analysis/overview')
def analysis_overview():
    try:
        data = db.get_analysis_overview()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/driver/<int:driver_id>')
def driver_analysis(driver_id):
    try:
        data = db.get_driver_analysis(driver_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/session-comparison')
def session_comparison():
    try:
        data = db.get_session_comparison()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/sector-performance')
def sector_performance():
    try:
        data = db.get_sector_performance()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/consistency')
def consistency_analysis():
    try:
        data = db.get_consistency_analysis()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/car-performance')
def car_performance():
    try:
        data = db.get_car_performance_analysis()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/lap-progression/<int:driver_id>')
def lap_progression(driver_id):
    try:
        data = db.get_lap_progression(driver_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

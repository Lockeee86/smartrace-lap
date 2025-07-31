from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartrace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class LapData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Integer)
    event_type = db.Column(db.String(50))
    controller_id = db.Column(db.String(20))
    lap = db.Column(db.Integer)
    laptime = db.Column(db.String(20))
    laptime_raw = db.Column(db.Integer)
    sector_1 = db.Column(db.String(20))
    sector_2 = db.Column(db.String(20))
    sector_3 = db.Column(db.String(20))
    lap_pb = db.Column(db.Boolean)
    driver_id = db.Column(db.Integer)
    driver_name = db.Column(db.String(100))
    car_id = db.Column(db.Integer)
    car_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/api/lap-update', methods=['POST'])
def lap_update():
    data = request.json
    event_data = data['event_data']
    driver_data = event_data['driver_data']
    car_data = event_data['car_data']

    lap = LapData(
        timestamp=data['time'],
        event_type=data['event_type'],
        controller_id=event_data['controller_id'],
        lap=event_data['lap'],
        laptime=event_data['laptime'],
        laptime_raw=event_data['laptime_raw'],
        sector_1=event_data['sector_1'],
        sector_2=event_data['sector_2'],
        sector_3=event_data['sector_3'],
        lap_pb=event_data['lap_pb'],
        driver_id=driver_data['id'],
        driver_name=driver_data['name'],
        car_id=car_data['id'],
        car_name=car_data['name']
    )

    db.session.add(lap)
    db.session.commit()

    return jsonify({"status": "success"}), 200

@app.route('/')
def index():
    # Rendert das Template aus dem templates-Ordner
    return render_template('index.html')

@app.route('/api/laps')
def get_laps():
    laps = LapData.query.order_by(LapData.timestamp.desc()).limit(50).all()
    return jsonify([{
        'timestamp': lap.timestamp,
        'driver_name': lap.driver_name,
        'car_name': lap.car_name,
        'lap': lap.lap,
        'laptime': lap.laptime,
        'lap_pb': lap.lap_pb
    } for lap in laps])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)

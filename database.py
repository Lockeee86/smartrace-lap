import sqlite3
import json
import os
from datetime import datetime

class RaceDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.environ.get('DATABASE_PATH', '/app/data/smartrace.db')
        
        self.db_path = db_path
        
        # Erstelle Verzeichnis falls es nicht existiert
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.init_database()
    
    def init_database(self):
        """Erstelle die Datenbanktabellen falls sie nicht existieren"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabelle für Rundendaten
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lap_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                datetime TEXT,
                controller_id TEXT,
                lap INTEGER,
                laptime TEXT,
                laptime_raw INTEGER,
                sector_1 TEXT,
                sector_1_pb BOOLEAN,
                sector_2 TEXT,
                sector_2_pb BOOLEAN,
                sector_3 TEXT,
                sector_3_pb BOOLEAN,
                lap_pb BOOLEAN,
                driver_id INTEGER,
                driver_name TEXT,
                car_id INTEGER,
                car_name TEXT,
                car_manufacturer TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index für bessere Performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_driver_name ON lap_updates(driver_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON lap_updates(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        print(f"Datenbank initialisiert: {self.db_path}")
    
    def insert_lap_update(self, data):
        """Speichere Rundendaten in der Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        event_data = data['event_data']
        
        # Konvertiere Unix-Timestamp zu lesbarem Datum
        dt = datetime.fromtimestamp(data['time'] / 1000)
        
        cursor.execute('''
            INSERT INTO lap_updates (
                timestamp, datetime, controller_id, lap, laptime, laptime_raw,
                sector_1, sector_1_pb, sector_2, sector_2_pb, sector_3, sector_3_pb,
                lap_pb, driver_id, driver_name, car_id, car_name, car_manufacturer, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['time'],
            dt.strftime('%Y-%m-%d %H:%M:%S'),
            event_data['controller_id'],
            event_data['lap'],
            event_data['laptime'],
            event_data['laptime_raw'],
            event_data['sector_1'],
            event_data['sector_1_pb'],
            event_data['sector_2'],
            event_data['sector_2_pb'],
            event_data['sector_3'],
            event_data['sector_3_pb'],
            event_data['lap_pb'],
            event_data['driver_data']['id'],
            event_data['driver_data']['name'],
            event_data['car_data']['id'],
            event_data['car_data']['name'],
            event_data['car_data']['manufacturer'],
            json.dumps(data)
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_laps(self, limit=20):
        """Hole die neuesten Rundendaten"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM lap_updates 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def get_driver_stats(self, driver_name=None):
        """Hole Fahrerstatistiken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if driver_name:
            cursor.execute('''
                SELECT driver_name, COUNT(*) as total_laps, 
                       MIN(laptime_raw) as best_time,
                       AVG(laptime_raw) as avg_time,
                       MAX(timestamp) as last_lap_time
                FROM lap_updates 
                WHERE driver_name = ?
                GROUP BY driver_name
            ''', (driver_name,))
        else:
            cursor.execute('''
                SELECT driver_name, COUNT(*) as total_laps, 
                       MIN(laptime_raw) as best_time,
                       AVG(laptime_raw) as avg_time,
                       MAX(timestamp) as last_lap_time
                FROM lap_updates 
                GROUP BY driver_name
                ORDER BY best_time ASC
            ''')
        
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def get_database_info(self):
        """Hole Informationen über die Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total_laps FROM lap_updates')
        total_laps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT driver_name) as unique_drivers FROM lap_updates')
        unique_drivers = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(timestamp) as first_lap, MAX(timestamp) as last_lap FROM lap_updates')
        result = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_laps': total_laps,
            'unique_drivers': unique_drivers,
            'first_lap': result[0],
            'last_lap': result[1],
            'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        }

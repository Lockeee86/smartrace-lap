import sqlite3
import json
import os
from datetime import datetime
import statistics

class RaceDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.environ.get('DATABASE_PATH', '/app/data/smartrace.db')
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Erstelle die Datenbanktabellen falls sie nicht existieren"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                raw_data TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def insert_lap_update(self, data):
        """Speichere Rundendaten in der Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        event_data = data.get('event_data', {})
        driver_data = event_data.get('driver_data', {})
        car_data = event_data.get('car_data', {})
        
        cursor.execute('''
            INSERT INTO lap_updates (
                timestamp, datetime, controller_id, lap, laptime, laptime_raw,
                sector_1, sector_1_pb, sector_2, sector_2_pb, sector_3, sector_3_pb,
                lap_pb, driver_id, driver_name, car_id, car_name, car_manufacturer, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('time'),
            datetime.fromtimestamp(data.get('time', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            event_data.get('controller_id'),
            event_data.get('lap'),
            event_data.get('laptime'),
            event_data.get('laptime_raw'),
            event_data.get('sector_1'),
            event_data.get('sector_1_pb', False),
            event_data.get('sector_2'),
            event_data.get('sector_2_pb', False),
            event_data.get('sector_3'),
            event_data.get('sector_3_pb', False),
            event_data.get('lap_pb', False),
            driver_data.get('id'),
            driver_data.get('name'),
            car_data.get('id'),
            car_data.get('name'),
            car_data.get('manufacturer'),
            json.dumps(data)
        ))
        
        conn.commit()
        conn.close()
    
    # Bestehende Funktionen...
    def get_driver_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                driver_name,
                COUNT(*) as total_laps,
                MIN(laptime_raw) as best_time,
                AVG(laptime_raw) as avg_time
            FROM lap_updates 
            WHERE laptime_raw IS NOT NULL AND laptime_raw > 0
            GROUP BY driver_name
            ORDER BY best_time ASC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'driver_name': row[0],
                'total_laps': row[1],
                'best_time': row[2],
                'avg_time': row[3]
            })
        
        conn.close()
        return results
    
    def get_recent_laps(self, limit=20):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM lap_updates 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def get_database_info(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM lap_updates')
        total_laps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT driver_name) FROM lap_updates')
        unique_drivers = cursor.fetchone()[0]
        
        try:
            database_size = os.path.getsize(self.db_path)
        except:
            database_size = 0
        
        conn.close()
        
        return {
            'total_laps': total_laps,
            'unique_drivers': unique_drivers,
            'database_size': database_size
        }
    
    # Neue Analyse-Funktionen
    def get_analysis_overview(self):
        """Umfassende Übersicht für die Analyse"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Gesamtstatistiken
        cursor.execute('''
            SELECT 
                COUNT(*) as total_laps,
                COUNT(DISTINCT driver_name) as total_drivers,
                COUNT(DISTINCT car_name) as total_cars,
                MIN(laptime_raw) as fastest_lap,
                AVG(laptime_raw) as average_lap,
                COUNT(CASE WHEN lap_pb = 1 THEN 1 END) as total_pbs
            FROM lap_updates 
            WHERE laptime_raw IS NOT NULL AND laptime_raw > 0
        ''')
        overview = cursor.fetchone()
        
        # Top 5 Fahrer nach Bestzeit
        cursor.execute('''
            SELECT 
                driver_name,
                MIN(laptime_raw) as best_time,
                COUNT(*) as laps
            FROM lap_updates 
            WHERE laptime_raw IS NOT NULL AND laptime_raw > 0
            GROUP BY driver_name
            ORDER BY best_time ASC
            LIMIT 5
        ''')
        top_drivers = cursor.fetchall()
        
        # Aktivität über Zeit (letzte 7 Tage)
        cursor.execute('''
            SELECT 
                DATE(datetime) as date,
                COUNT(*) as laps
            FROM lap_updates 
            WHERE datetime >= datetime('now', '-7 days')
            GROUP BY DATE(datetime)
            ORDER BY date
        ''')
        daily_activity = cursor.fetchall()
        
        # Sektor-Performance
        cursor.execute('''
            SELECT 
                AVG(CAST(substr(sector_1, 3) AS REAL) * 1000) as avg_sector1,
                AVG(CAST(substr(sector_2, 3) AS REAL) * 1000) as avg_sector2,
                AVG(CAST(substr(sector_3, 3) AS REAL) * 1000) as avg_sector3
            FROM lap_updates 
            WHERE sector_1 LIKE '0:%' AND sector_2 LIKE '0:%' AND sector_3 LIKE '0:%'
        ''')
        sector_avg = cursor.fetchone()
        
        conn.close()
        
        return {
            'overview': {
                'total_laps': overview[0],
                'total_drivers': overview[1],
                'total_cars': overview[2],
                'fastest_lap': overview[3],
                'average_lap': overview[4],
                'total_pbs': overview[5]
            },
            'top_drivers': [{'name': row[0], 'best_time': row[1], 'laps': row[2]} for row in top_drivers],
            'daily_activity': [{'date': row[0], 'laps': row[1]} for row in daily_activity],
            'sector_performance': {
                'sector_1': sector_avg[0] if sector_avg[0] else 0,
                'sector_2': sector_avg[1] if sector_avg[1] else 0,
                'sector_3': sector_avg[2] if sector_avg[2] else 0
            }
        }
    
    def get_driver_analysis(self, driver_id=None):
        """Detailanalyse für alle Fahrer oder einen spezifischen Fahrer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        where_clause = ""
        params = ()
        if driver_id:
            where_clause = "WHERE driver_id = ?"
            params = (driver_id,)
        
        cursor.execute(f'''
            SELECT 
                driver_name,
                driver_id,
                COUNT(*) as total_laps,
                MIN(laptime_raw) as best_time,
                MAX(laptime_raw) as worst_time,
                AVG(laptime_raw) as avg_time,
                COUNT(CASE WHEN lap_pb = 1 THEN 1 END) as personal_bests
            FROM lap_updates 
            {where_clause}
            AND laptime_raw IS NOT NULL AND laptime_raw > 0
            GROUP BY driver_name, driver_id
            ORDER BY best_time ASC
        ''', params)
        
        results = []
        for row in cursor.fetchall():
            # Berechne Konsistenz (Standardabweichung)
            cursor.execute('''
                SELECT laptime_raw FROM lap_updates 
                WHERE driver_id = ? AND laptime_raw IS NOT NULL AND laptime_raw > 0
            ''', (row[1],))
            lap_times = [r[0] for r in cursor.fetchall()]
            
            consistency = 0
            if len(lap_times) > 1:
                consistency = statistics.stdev(lap_times)
            
            results.append({
                'driver_name': row[0],
                'driver_id': row[1],
                'total_laps': row[2],
                'best_time': row[3],
                'worst_time': row[4],
                'avg_time': row[5],
                'personal_bests': row[6],
                'consistency': consistency,
                'improvement': row[4] - row[3] if row[3] and row[4] else 0
            })
        
        conn.close()
        return results
    
    def get_consistency_analysis(self):
        """Analyse der Fahrkonsistenz"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT driver_name, driver_id 
            FROM lap_updates 
            WHERE laptime_raw IS NOT NULL AND laptime_raw > 0
        ''')
        drivers = cursor.fetchall()
        
        results = []
        for driver_name, driver_id in drivers:
            cursor.execute('''
                SELECT laptime_raw 
                FROM lap_updates 
                WHERE driver_id = ? AND laptime_raw IS NOT NULL AND laptime_raw > 0
                ORDER BY timestamp
            ''', (driver_id,))
            
            lap_times = [row[0] for row in cursor.fetchall()]
            
            if len(lap_times) >= 3:
                avg_time = statistics.mean(lap_times)
                consistency = statistics.stdev(lap_times)
                consistency_percent = (consistency / avg_time) * 100
                
                # Berechne Verbesserungstrend (erste vs. letzte 5 Runden)
                first_5 = lap_times[:5]
                last_5 = lap_times[-5:]
                trend = statistics.mean(first_5) - statistics.mean(last_5) if len(first_5) >= 3 and len(last_5) >= 3 else 0
                
                results.append({
                    'driver_name': driver_name,
                    'driver_id': driver_id,
                    'avg_time': avg_time,
                    'consistency_ms': consistency,
                    'consistency_percent': consistency_percent,
                    'trend': trend,
                    'total_laps': len(lap_times)
                })
        
        conn.close()
        return sorted(results, key=lambda x: x['consistency_percent'])
    
    def get_sector_performance(self):
        """Analyse der Sektorzeiten"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                driver_name,
                AVG(CASE 
                    WHEN sector_1 LIKE '0:%' THEN CAST(substr(sector_1, 3) AS REAL) * 1000
                    ELSE NULL 
                END) as avg_s1,
                AVG(CASE 
                    WHEN sector_2 LIKE '0:%' THEN CAST(substr(sector_2, 3) AS REAL) * 1000
                    ELSE NULL 
                END) as avg_s2,
                AVG(CASE 
                    WHEN sector_3 LIKE '0:%' THEN CAST(substr(sector_3, 3) AS REAL) * 1000
                    ELSE NULL 
                END) as avg_s3,
                MIN(CASE 
                    WHEN sector_1 LIKE '0:%' THEN CAST(substr(sector_1, 3) AS REAL) * 1000
                    ELSE NULL 
                END) as best_s1,
                MIN(CASE 
                    WHEN sector_2 LIKE '0:%' THEN CAST(substr(sector_2, 3) AS REAL) * 1000
                    ELSE NULL 
                END) as best_s2,
                MIN(CASE 
                    WHEN sector_3 LIKE '0:%' THEN CAST(substr(sector_3, 3) AS REAL) * 1000
                    ELSE NULL 
                END) as best_s3
            FROM lap_updates 
            WHERE sector_1 LIKE '0:%' AND sector_2 LIKE '0:%' AND sector_3 LIKE '0:%'
            GROUP BY driver_name
        ''')
        
        results = []
        for row in cursor.fetchall():
            if all(x is not None for x in row[1:]):
                results.append({
                    'driver_name': row[0],
                    'avg_sector_1': row[1],
                    'avg_sector_2': row[2],
                    'avg_sector_3': row[3],
                    'best_sector_1': row[4],
                    'best_sector_2': row[5],
                    'best_sector_3': row[6]
                })
        
        conn.close()
        return results
    
    def get_car_performance_analysis(self):
        """Analyse der Fahrzeugleistung"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                car_name,
                car_manufacturer,
                COUNT(*) as total_laps,
                MIN(laptime_raw) as best_time,
                AVG(laptime_raw) as avg_time,
                COUNT(DISTINCT driver_name) as drivers_used
            FROM lap_updates 
            WHERE laptime_raw IS NOT NULL AND laptime_raw > 0
                AND car_name IS NOT NULL
            GROUP BY car_name, car_manufacturer
            ORDER BY best_time ASC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'car_name': row[0],
                'manufacturer': row[1],
                'total_laps': row[2],
                'best_time': row[3],
                'avg_time': row[4],
                'drivers_used': row[5]
            })
        
        conn.close()
        return results
    
    def get_lap_progression(self, driver_id):
        """Rundenfortschritt für einen Fahrer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                lap,
                laptime_raw,
                lap_pb,
                datetime
            FROM lap_updates 
            WHERE driver_id = ? AND laptime_raw IS NOT NULL AND laptime_raw > 0
            ORDER BY timestamp
        ''', (driver_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'lap': row[0],
                'laptime': row[1],
                'lap_pb': row[2],
                'datetime': row[3]
            })
        
        conn.close()
        return results

    def get_session_comparison(self):
        """Vergleiche verschiedene Sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                DATE(datetime) as session_date,
                COUNT(*) as total_laps,
                COUNT(DISTINCT driver_name) as drivers,
                MIN(laptime_raw) as fastest_lap,
                AVG(laptime_raw) as avg_lap
            FROM lap_updates 
            WHERE laptime_raw IS NOT NULL AND laptime_raw > 0
            GROUP BY DATE(datetime)
            ORDER BY session_date DESC
            LIMIT 10
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'date': row[0],
                'total_laps': row[1],
                'drivers': row[2],
                'fastest_lap': row[3],
                'avg_lap': row[4]
            })
        
        conn.close()
        return results

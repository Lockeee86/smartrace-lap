// SmartRace Dashboard Manager - Clean Version
(function() {
    'use strict';
    
    // Avoid duplicate initialization
    if (window.smartraceDashboard) {
        console.log('⚠️ Dashboard already initialized, skipping...');
        return;
    }

    class SmartRaceDashboard {
        constructor() {
            this.socket = null;
            this.lapHistory = {};
            this.carDatabase = {};
            this.showTop6Only = false;
            this.isInitialized = false;
        }

        async init() {
            if (this.isInitialized) {
                console.log('⚠️ Dashboard already initialized');
                return;
            }

            console.log('🏁 Initializing SmartRace Dashboard...');
            
            try {
                await this.loadCarDatabase();
                this.initWebSocket();
                this.setupEventListeners();
                this.startPeriodicUpdates();
                this.isInitialized = true;
                console.log('✅ SmartRace Dashboard initialized successfully');
            } catch (error) {
                console.error('❌ Dashboard initialization failed:', error);
            }
        }

        async loadCarDatabase() {
            try {
                console.log('🔄 Loading car database...');
                const response = await fetch('/api/car-database');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                this.carDatabase = await response.json();
                console.log('✅ Car database loaded:', Object.keys(this.carDatabase).length, 'cars');
            } catch (error) {
                console.error('❌ Failed to load car database:', error);
                this.carDatabase = {};
            }
        }

        initWebSocket() {
            console.log('🔌 Initializing WebSocket connection...');
            
            this.socket = io({
                transports: ['websocket', 'polling'],
                timeout: 20000,
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: 5
            });

            this.socket.on('connect', () => {
                console.log('✅ WebSocket connected');
                this.updateConnectionStatus(true);
            });

            this.socket.on('disconnect', (reason) => {
                console.log('❌ WebSocket disconnected:', reason);
                this.updateConnectionStatus(false);
            });

            this.socket.on('connect_error', (error) => {
                console.error('❌ WebSocket connection error:', error);
                this.updateConnectionStatus(false);
            });

            this.socket.on('race_update', (data) => {
                console.log('📊 Race data received:', data);
                if (data && data.drivers) {
                    this.updateDriversTable(data.drivers);
                }
                if (data && data.session_info) {
                    this.updateSessionInfo(data.session_info);
                }
            });

            this.socket.on('lap_update', (lapData) => {
                console.log('⏱️ Lap data received:', lapData);
                this.addLapToHistory(lapData);
                this.updateLaptimeMonitor();
            });

            this.socket.on('car_database_update', (carData) => {
                console.log('🚗 Car database update:', carData);
                this.carDatabase = { ...this.carDatabase, ...carData };
            });
        }

        updateConnectionStatus(connected) {
            const statusElement = document.getElementById('connection-status');
            if (statusElement) {
                statusElement.innerHTML = connected ? 
                    '<span class="badge bg-success">🟢 Connected</span>' : 
                    '<span class="badge bg-danger">🔴 Disconnected</span>';
            }
        }

        updateDriversTable(drivers) {
            console.log('🔄 Updating drivers table with:', drivers);
            
            const tbody = document.querySelector('#drivers-table tbody');
            if (!tbody) {
                console.warn('⚠️ Drivers table tbody not found');
                return;
            }

            if (!drivers || Object.keys(drivers).length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No driver data available</td></tr>';
                return;
            }

            // Sort drivers by position
            const sortedDrivers = Object.entries(drivers)
                .sort(([,a], [,b]) => (a.position || 999) - (b.position || 999));

            // Apply Top 6 filter if enabled
            const displayDrivers = this.showTop6Only ? 
                sortedDrivers.slice(0, 6) : sortedDrivers;

            tbody.innerHTML = displayDrivers.map(([driverId, driver]) => {
                const carInfo = this.carDatabase[driver.car_id] || {};
                const positionBadge = this.getPositionBadge(driver.position);
                const carColor = carInfo.color || '#6c757d';

                return `
                    <tr>
                        <td class="text-center">${positionBadge}</td>
                        <td>
                            <div class="d-flex align-items-center">
                                <div class="car-color me-2" 
                                     style="width: 20px; height: 20px; background: ${carColor}; border-radius: 3px; border: 1px solid #ccc;"></div>
                                <div>
                                    <strong>${driver.driver_name || `Driver ${driverId}`}</strong><br>
                                    <small class="text-muted">${carInfo.name || 'Unknown Car'}</small>
                                </div>
                            </div>
                        </td>
                        <td class="text-center"><span class="badge bg-primary">${driver.laps || 0}</span></td>
                        <td class="fw-bold text-center">${this.formatTime(driver.last_lap_time)}</td>
                        <td class="text-success fw-bold text-center">${this.formatTime(driver.best_lap_time)}</td>
                        <td class="text-center">${this.formatTime(driver.total_time)}</td>
                        <td class="text-muted text-center">${driver.gap_to_leader ? '+' + this.formatTime(driver.gap_to_leader) : '-'}</td>
                    </tr>
                `;
            }).join('');

            console.log('✅ Drivers table updated with', displayDrivers.length, 'entries');
        }

        updateSessionInfo(sessionInfo) {
            console.log('🔄 Updating session info:', sessionInfo);
            
            const updates = {
                'session-name': sessionInfo.session_name || 'No Active Session',
                'session-type': sessionInfo.session_type || 'Practice',
                'track-name': sessionInfo.track_name || 'Unknown Track',
                'session-time': this.formatTime(sessionInfo.total_time),
                'session-status': sessionInfo.session_status || 'Stopped'
            };

            Object.entries(updates).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            });
        }

        getPositionBadge(position) {
            const badges = {
                1: '🥇 1st',
                2: '🥈 2nd', 
                3: '🥉 3rd'
            };
            return badges[position] || `#${position || '?'}`;
        }

        formatTime(seconds) {
            if (!seconds && seconds !== 0) return '-';
            
            const mins = Math.floor(Math.abs(seconds) / 60);
            const secs = Math.abs(seconds) % 60;
            const sign = seconds < 0 ? '-' : '';
            
            if (mins > 0) {
                return `${sign}${mins}:${secs.toFixed(3).padStart(6, '0')}`;
            }
            return `${sign}${secs.toFixed(3)}s`;
        }

        addLapToHistory(lapData) {
            const driverId = lapData.driver_id || lapData.car_id;
            if (!this.lapHistory[driverId]) {
                this.lapHistory[driverId] = [];
            }
            
            this.lapHistory[driverId].push({
                lap: lapData.lap_number || this.lapHistory[driverId].length + 1,
                time: lapData.lap_time,
                timestamp: lapData.timestamp || new Date().toISOString()
            });

            // Keep only last 20 laps per driver
            if (this.lapHistory[driverId].length > 20) {
                this.lapHistory[driverId] = this.lapHistory[driverId].slice(-20);
            }
        }

        updateLaptimeMonitor() {
            const container = document.getElementById('laptime-monitor');
            if (!container) return;

            const recentLaps = this.getRecentLaps(8);
            
            if (recentLaps.length === 0) {
                container.innerHTML = '<div class="text-center text-muted p-3">No recent lap data</div>';
                return;
            }

            container.innerHTML = recentLaps.map(lap => {
                const carInfo = this.carDatabase[lap.car_id] || {};
                const carColor = carInfo.color || '#6c757d';
                
                return `
                    <div class="lap-entry d-flex justify-content-between align-items-center p-2 mb-2 bg-light rounded border">
                        <div class="d-flex align-items-center">
                            <div class="car-color me-2" 
                                 style="width: 16px; height: 16px; background: ${carColor}; border-radius: 2px; border: 1px solid #ccc;"></div>
                            <div>
                                <strong>${lap.driver_name || `Driver ${lap.car_id}`}</strong>
                                <small class="text-muted ms-2">Lap ${lap.lap}</small>
                            </div>
                        </div>
                        <div class="fw-bold text-primary">${this.formatTime(lap.time)}</div>
                    </div>
                `;
            }).join('');
        }

        getRecentLaps(count = 8) {
            const allLaps = [];
            
            Object.entries(this.lapHistory).forEach(([driverId, laps]) => {
                laps.forEach(lap => {
                    allLaps.push({
                        ...lap,
                        driver_id: driverId,
                        car_id: driverId,
                        timestamp_sort: new Date(lap.timestamp).getTime()
                    });
                });
            });

            return allLaps
                .sort((a, b) => b.timestamp_sort - a.timestamp_sort)
                .slice(0, count);
        }

        setupEventListeners() {
            // Top 6 toggle button
            const toggleButton = document.getElementById('toggle-top6');
            if (toggleButton) {
                toggleButton.addEventListener('click', () => this.toggleTop6());
            }

            // Periodic Dropbox status check
            setInterval(() => this.checkDropboxStatus(), 30000);
            this.checkDropboxStatus(); // Initial check
        }

        toggleTop6() {
            this.showTop6Only = !this.showTop6Only;
            const button = document.getElementById('toggle-top6');
            if (button) {
                button.textContent = this.showTop6Only ? 'Show All Drivers' : 'Show Top 6 Only';
                button.className = this.showTop6Only ? 
                    'btn btn-outline-primary btn-sm' : 
                    'btn btn-primary btn-sm';
            }
            
            // Re-fetch and update data
            this.fetchCurrentData();
        }

        async fetchCurrentData() {
            try {
                const response = await fetch('/api/session-info');
                const data = await response.json();
                if (data.drivers) {
                    this.updateDriversTable(data.drivers);
                }
                if (data.session_info) {
                    this.updateSessionInfo(data.session_info);
                }
            } catch (error) {
                console.error('❌ Failed to fetch current data:', error);
            }
        }

        async checkDropboxStatus() {
            try {
                const response = await fetch('/api/dropbox-status');
                const data = await response.json();
                const statusElement = document.getElementById('dropbox-status');
                if (statusElement) {
                    statusElement.innerHTML = data.connected ? 
                        '<span class="badge bg-success">☁️ Connected</span>' : 
                        '<span class="badge bg-warning">☁️ Disconnected</span>';
                }
            } catch (error) {
                console.error('❌ Dropbox status check failed:', error);
            }
        }

        startPeriodicUpdates() {
            // Update laptime monitor every 10 seconds
            setInterval(() => {
                if (document.getElementById('laptime-monitor')) {
                    this.updateLaptimeMonitor();
                }
            }, 10000);

            // Fetch fresh data every 30 seconds
            setInterval(() => {
                this.fetchCurrentData();
            }, 30000);
        }
    }

    // Global functions for buttons
    window.exportToCSV = function(type) {
        console.log('📁 Exporting', type, 'to CSV...');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
        const filename = `smartrace_${type}_${timestamp}.csv`;
        
        fetch(`/api/export/${type}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showNotification(`✅ ${type} exported successfully!`, 'success');
            })
            .catch(error => {
                console.error('❌ Export failed:', error);
                showNotification(`❌ Export failed: ${error.message}`, 'danger');
            });
    };

    window.uploadToDropbox = function() {
        console.log('☁️ Uploading to Dropbox...');
        showNotification('☁️ Uploading to Dropbox...', 'info');
        
        fetch('/api/upload-to-dropbox', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('✅ Successfully uploaded to Dropbox!', 'success');
                } else {
                    showNotification(`❌ Upload failed: ${data.error}`, 'danger');
                }
            })
            .catch(error => {
                console.error('❌ Dropbox upload failed:', error);
                showNotification(`❌ Upload failed: ${error.message}`, 'danger');
            });
    };

    window.showNotification = function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    };

    // Initialize dashboard when page loads
    document.addEventListener('DOMContentLoaded', function() {
        // Only initialize if we're on dashboard page
        if (document.getElementById('drivers-table') || 
            document.getElementById('laptime-monitor') ||
            document.querySelector('.dashboard-content')) {
            
            console.log('🏁 Starting SmartRace Dashboard initialization...');
            window.smartraceDashboard = new SmartRaceDashboard();
            window.smartraceDashboard.init();
        } else {
            console.log('📄 Not on dashboard page, skipping initialization');
        }
    });

})();

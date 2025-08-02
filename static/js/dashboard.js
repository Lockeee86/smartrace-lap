// Dashboard WebSocket and UI Management
class DashboardManager {
    constructor() {
        this.socket = null;
        this.lapHistory = {};
        this.carDatabase = {};
        this.showTop6Only = false;
        this.init();
    }

    async init() {
        await this.loadCarDatabase();
        this.initWebSocket();
        this.updateLaptimeMonitor();
        this.startPeriodicUpdate();
    }

    async loadCarDatabase() {
        try {
            const response = await fetch('/api/car-database');
            this.carDatabase = await response.json();
            console.log('🚗 SmartRace car database loaded:', this.carDatabase);
        } catch (error) {
            console.error('Failed to load car database:', error);
        }
    }

    initWebSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('🔌 Connected to SmartRace server');
            document.getElementById('connection-status').innerHTML = 
                '<span class="badge bg-success">Connected</span>';
        });

        this.socket.on('disconnect', () => {
            console.log('🔌 Disconnected from SmartRace server');
            document.getElementById('connection-status').innerHTML = 
                '<span class="badge bg-danger">Disconnected</span>';
        });

        this.socket.on('race_update', (data) => {
            console.log('📊 SmartRace data update received');
            this.updateDriversTable(data.drivers || {});
            this.updateSessionInfo(data.session_info || {});
        });

        this.socket.on('car_database_update', (carData) => {
            console.log('🚗 SmartRace car database update:', carData);
            this.carDatabase = { ...this.carDatabase, ...carData };
        });

        this.socket.on('lap_update', (lapData) => {
            console.log('⏱️ SmartRace lap update received:', lapData);
            this.addLapToHistory(lapData);
            this.updateLaptimeMonitor();
        });

        this.socket.on('dropbox_status', (status) => {
            this.updateDropboxStatus(status);
        });
    }

    updateDriversTable(drivers) {
        const tbody = document.querySelector('#drivers-table tbody');
        if (!tbody) return;

        // Sort by position
        const sortedDrivers = Object.entries(drivers).sort(([,a], [,b]) => {
            return (a.position || 999) - (b.position || 999);
        });

        // Filter if Top 6 only
        const displayDrivers = this.showTop6Only ? 
            sortedDrivers.slice(0, 6) : sortedDrivers;

        tbody.innerHTML = displayDrivers.map(([driverId, driver]) => {
            const carInfo = this.carDatabase[driver.car_id] || {};
            const positionBadge = this.getPositionBadge(driver.position);
            const carColor = carInfo.color || '#6c757d';

            return `
                <tr>
                    <td>${positionBadge}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="car-color me-2" style="width: 20px; height: 20px; background: ${carColor}; border-radius: 3px;"></div>
                            <div>
                                <strong>${driver.driver_name || `Driver ${driverId}`}</strong><br>
                                <small class="text-muted">${carInfo.name || 'Unknown Car'}</small>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge bg-primary">${driver.laps || 0}</span></td>
                    <td class="fw-bold">${this.formatTime(driver.last_lap_time)}</td>
                    <td class="text-success fw-bold">${this.formatTime(driver.best_lap_time)}</td>
                    <td>${this.formatTime(driver.total_time)}</td>
                    <td class="text-muted">${driver.gap_to_leader ? '+' + this.formatTime(driver.gap_to_leader) : '-'}</td>
                </tr>
            `;
        }).join('');
    }

    updateSessionInfo(sessionInfo) {
        const elements = {
            'session-name': sessionInfo.session_name || 'No Session',
            'session-type': sessionInfo.session_type || 'Practice',
            'track-name': sessionInfo.track_name || 'Unknown Track',
            'session-time': this.formatTime(sessionInfo.total_time),
            'session-status': sessionInfo.session_status || 'Stopped'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    addLapToHistory(lapData) {
        const driverId = lapData.driver_id || lapData.car_id;
        if (!this.lapHistory[driverId]) {
            this.lapHistory[driverId] = [];
        }
        
        this.lapHistory[driverId].push({
            lap: lapData.lap_number || this.lapHistory[driverId].length + 1,
            time: lapData.lap_time,
            timestamp: lapData.timestamp || new Date().toISOString(),
            sectors: lapData.sector_times || []
        });

        // Keep only last 50 laps per driver
        if (this.lapHistory[driverId].length > 50) {
            this.lapHistory[driverId] = this.lapHistory[driverId].slice(-50);
        }
    }

    updateLaptimeMonitor() {
        const container = document.getElementById('laptime-monitor');
        if (!container) return;

        const recentLaps = this.getRecentLaps(10);
        
        container.innerHTML = recentLaps.length ? recentLaps.map(lap => {
            const carInfo = this.carDatabase[lap.car_id] || {};
            const carColor = carInfo.color || '#6c757d';
            
            return `
                <div class="lap-entry d-flex justify-content-between align-items-center p-2 mb-2 bg-light rounded">
                    <div class="d-flex align-items-center">
                        <div class="car-color me-2" style="width: 16px; height: 16px; background: ${carColor}; border-radius: 2px;"></div>
                        <div>
                            <strong>${lap.driver_name}</strong>
                            <small class="text-muted ms-2">Lap ${lap.lap}</small>
                        </div>
                    </div>
                    <div class="fw-bold ${lap.is_best ? 'text-success' : ''}">${this.formatTime(lap.time)}</div>
                </div>
            `;
        }).join('') : '<p class="text-muted text-center">No recent laps</p>';
    }

    getRecentLaps(count = 10) {
        const allLaps = [];
        
        Object.entries(this.lapHistory).forEach(([driverId, laps]) => {
            const carInfo = this.carDatabase[driverId] || {};
            laps.forEach(lap => {
                allLaps.push({
                    ...lap,
                    driver_id: driverId,
                    driver_name: `Driver ${driverId}`,
                    car_id: driverId,
                    timestamp_sort: new Date(lap.timestamp).getTime()
                });
            });
        });

        return allLaps
            .sort((a, b) => b.timestamp_sort - a.timestamp_sort)
            .slice(0, count);
    }

    getPositionBadge(position) {
        const badges = {
            1: '🥇',
            2: '🥈', 
            3: '🥉'
        };
        return badges[position] || `#${position || '?'}`;
    }

    formatTime(seconds) {
        if (!seconds && seconds !== 0) return '-';
        
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(3);
        
        return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : `${secs}s`;
    }

    updateDropboxStatus(status) {
        const statusElement = document.getElementById('dropbox-status');
        if (statusElement) {
            statusElement.innerHTML = status.connected ? 
                '<span class="badge bg-success">☁️ Connected</span>' : 
                '<span class="badge bg-warning">☁️ Disconnected</span>';
        }
    }

    async updateLaptimeMonitor() {
        try {
            const response = await fetch('/api/recent-laps');
            const data = await response.json();
            
            const container = document.getElementById('laptime-monitor');
            if (!container) return;

            if (data.laps && data.laps.length > 0) {
                container.innerHTML = data.laps.map(lap => {
                    const carInfo = this.carDatabase[lap.car_id] || {};
                    const carColor = carInfo.color || '#6c757d';
                    
                    return `
                        <div class="lap-entry d-flex justify-content-between align-items-center p-2 mb-2 bg-light rounded">
                            <div class="d-flex align-items-center">
                                <div class="car-color me-2" style="width: 16px; height: 16px; background: ${carColor}; border-radius: 2px;"></div>
                                <div>
                                    <strong>${lap.driver_name || `Driver ${lap.car_id}`}</strong>
                                    <small class="text-muted ms-2">Lap ${lap.lap_number || '?'}</small>
                                </div>
                            </div>
                            <div class="fw-bold">${this.formatTime(lap.lap_time)}</div>
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = '<p class="text-muted text-center">No recent laps available</p>';
            }
        } catch (error) {
            console.error('Failed to update laptime monitor:', error);
        }
    }

    startPeriodicUpdate() {
        setInterval(() => {
            if (document.getElementById('laptime-monitor')) {
                this.updateLaptimeMonitor();
            }
        }, 5000);
    }

    toggleTop6() {
        this.showTop6Only = !this.showTop6Only;
        const button = document.getElementById('toggle-top6');
        if (button) {
            button.textContent = this.showTop6Only ? 'Show All' : 'Top 6 Only';
            button.className = this.showTop6Only ? 
                'btn btn-outline-primary btn-sm' : 
                'btn btn-primary btn-sm';
        }
        
        // Re-render table with current data
        fetch('/api/session-info')
            .then(r => r.json())
            .then(data => this.updateDriversTable(data.drivers || {}));
    }
}

// Global functions for buttons
function exportToCSV(type) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `smartrace_${type}_${timestamp}.csv`;
    
    fetch(`/api/export/${type}`)
        .then(response => response.blob())
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
            console.error('Export failed:', error);
            showNotification(`❌ Export failed: ${error.message}`, 'danger');
        });
}

function uploadToDropbox() {
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
            console.error('Dropbox upload failed:', error);
            showNotification(`❌ Upload failed: ${error.message}`, 'danger');
        });
}

function checkDropboxStatus() {
    fetch('/api/dropbox-status')
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('dropbox-status');
            if (statusElement) {
                statusElement.innerHTML = data.connected ? 
                    '<span class="badge bg-success">☁️ Connected</span>' : 
                    '<span class="badge bg-warning">☁️ Disconnected</span>';
            }
        })
        .catch(error => {
            console.error('Dropbox status check failed:', error);
        });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Initialize dashboard only if we're on the dashboard page
let dashboard = null;

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on dashboard page
    if (document.getElementById('drivers-table') || document.getElementById('laptime-monitor')) {
        console.log('🏁 Initializing SmartRace Dashboard...');
        dashboard = new DashboardManager();
        
        // Setup toggle button
        const toggleButton = document.getElementById('toggle-top6');
        if (toggleButton) {
            toggleButton.addEventListener('click', () => dashboard.toggleTop6());
        }
        
        // Check Dropbox status periodically
        if (typeof checkDropboxStatus === 'function') {
            checkDropboxStatus();
            setInterval(checkDropboxStatus, 30000);
        }
        
        console.log('✅ SmartRace Dashboard initialized!');
    } else {
        console.log('📄 Not on dashboard page, skipping dashboard initialization');
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && dashboard) {
        console.log('👁️ Page became visible, refreshing data...');
        dashboard.updateLaptimeMonitor();
    }
});

// Handle window focus
window.addEventListener('focus', function() {
    if (dashboard) {
        console.log('🔍 Window focused, refreshing data...');
        dashboard.updateLaptimeMonitor();
    }
});

// Error handling for WebSocket
window.addEventListener('error', function(event) {
    console.error('💥 Global error:', event.error);
    if (typeof showNotification === 'function') {
        showNotification(`❌ Error: ${event.error.message}`, 'danger');
    }
});

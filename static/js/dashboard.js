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
            this.carDatabase = carData;
            this.refreshAllDisplays();
        });

        this.socket.on('lap_update', (data) => {
            console.log('⏱️ SmartRace lap update received');
            this.handleLapUpdate(data);
        });
    }

    refreshAllDisplays() {
        this.updateLaptimeMonitor();
        const driversTableBody = document.querySelector('#drivers-standings tbody');
        if (driversTableBody && window.currentRaceData) {
            this.updateDriversTable(window.currentRaceData.drivers || {});
        }
    }

    handleLapUpdate(data) {
        const driverId = data.driver_id;
        if (!this.lapHistory[driverId]) {
            this.lapHistory[driverId] = [];
        }

        this.lapHistory[driverId].push(data.lap_data);
        
        // Keep only last 50 laps per driver
        if (this.lapHistory[driverId].length > 50) {
            this.lapHistory[driverId] = this.lapHistory[driverId].slice(-50);
        }

        this.updateLaptimeMonitor();
    }

    updateSessionInfo(sessionInfo) {
        if (sessionInfo.total_time) {
            const element = document.getElementById('session-time');
            if (element) element.textContent = sessionInfo.total_time;
        }

        if (sessionInfo.current_lap) {
            const element = document.getElementById('current-lap');
            if (element) element.textContent = sessionInfo.current_lap;
        }

        if (sessionInfo.flag_status) {
            const element = document.getElementById('flag-status');
            if (element) {
                element.textContent = sessionInfo.flag_status;
                element.className = `badge bg-${this.getFlagColor(sessionInfo.flag_status)}`;
            }
        }
    }

    getFlagColor(flagStatus) {
        switch (flagStatus?.toLowerCase()) {
            case 'green': return 'success';
            case 'yellow': return 'warning';
            case 'red': return 'danger';
            case 'checkered': return 'dark';
            default: return 'secondary';
        }
    }

    updateDriversTable(drivers) {
        window.currentRaceData = { drivers };
        const tbody = document.querySelector('#drivers-standings tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        const sortedDrivers = Object.entries(drivers).sort((a, b) => {
            const posA = parseInt(a[1].position) || 999;
            const posB = parseInt(b[1].position) || 999;
            return posA - posB;
        });

        sortedDrivers.forEach(([driverId, driver]) => {
            const row = this.createDriverRow(driverId, driver);
            tbody.appendChild(row);
        });
    }

    createDriverRow(driverId, driver) {
        const row = document.createElement('tr');
        row.id = `driver-row-${driverId}`;

        const positionBadge = this.createPositionBadge(driver.position);
        const carInfo = this.carDatabase[driver.car_id] || {
            name: 'Unknown Car', 
            color: '#666666', 
            class: 'Unknown',
            manufacturer: 'Unknown',
            scale: ''
        };
        
        row.innerHTML = `
            <td class="text-center">${positionBadge}</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="car-color-indicator" 
                         style="background-color: ${carInfo.color}; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px;"></div>
                    <div>
                        <strong>${driver.name}</strong>
                        <br>
                        <small class="text-muted">${carInfo.name}</small>
                    </div>
                </div>
            </td>
            <td>
                <span class="badge bg-info">${carInfo.manufacturer}</span>
                <br>
                <small class="text-muted">${carInfo.scale}</small>
            </td>
            <td class="text-center">${driver.laps_completed || 0}</td>
            <td class="text-center font-monospace">
                <span class="${driver.best_lap_time ? 'text-success fw-bold' : 'text-muted'}">
                    ${driver.best_lap_time || '-'}
                </span>
            </td>
            <td class="text-center font-monospace">
                <span class="${driver.last_lap_time ? 'text-primary' : 'text-muted'}">
                    ${driver.last_lap_time || '-'}
                </span>
            </td>
            <td class="text-center font-monospace">${driver.total_time || '-'}</td>
            <td class="text-center">
                <span class="${driver.gap ? 'text-warning' : 'text-muted'}">
                    ${driver.gap || '-'}
                </span>
            </td>
            <td class="text-center">
                <span class="badge bg-${this.getStatusColor(driver.status)}">
                    ${driver.status || 'Unknown'}
                </span>
            </td>
        `;

        return row;
    }

    createPositionBadge(position) {
        if (!position) return '<span class="badge bg-secondary">-</span>';
        
        let badgeClass = 'bg-primary';
        if (position == 1) badgeClass = 'bg-warning text-dark';
        else if (position == 2) badgeClass = 'bg-secondary';
        else if (position == 3) badgeClass = 'bg-success';
        
        return `<span class="badge ${badgeClass}">${position}</span>`;
    }

    getStatusColor(status) {
        switch (status?.toLowerCase()) {
            case 'running': return 'success';
            case 'finished': return 'primary';
            case 'dnf': return 'danger';
            case 'dns': return 'secondary';
            default: return 'info';
        }
    }

    async updateLaptimeMonitor() {
        try {
            const response = await fetch('/api/lap-history');
            const lapHistory = await response.json();
            
            const tbody = document.querySelector('#laptime-monitor tbody');
            if (!tbody) return;

            tbody.innerHTML = '';

            // Flatten all laps and sort by timestamp
            const allLaps = [];
            Object.entries(lapHistory).forEach(([driverId, laps]) => {
                laps.forEach(lap => {
                    allLaps.push({
                        driverId,
                        ...lap
                    });
                });
            });

            // Sort by timestamp (newest first)
            allLaps.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            // Show only top entries based on filter
            const maxEntries = this.showTop6Only ? 6 : 50;
            const recentLaps = allLaps.slice(0, maxEntries);

            recentLaps.forEach(lap => {
                const row = this.createLaptimeRow(lap);
                tbody.appendChild(row);
            });

        } catch (error) {
            console.error('Failed to update laptime monitor:', error);
        }
    }

    createLaptimeRow(lap) {
        const row = document.createElement('tr');
        const driverId = lap.driverId;
        
        // Get driver and car info
        const driverData = window.currentRaceData?.drivers?.[driverId] || {};
        const driverName = driverData.name || `Driver ${driverId}`;
        const carInfo = this.carDatabase[driverData.car_id] || {
            name: 'Unknown Car',
            color: '#666666',
            manufacturer: 'Unknown'
        };

        // Format timestamp
        const timestamp = new Date(lap.timestamp);
        const timeStr = timestamp.toLocaleTimeString('de-DE');

        // Calculate average sector time
        const sectors = [lap.sector_1, lap.sector_2, lap.sector_3].filter(s => s && s !== '-');
        let avgTime = '-';
        if (sectors.length > 0) {
            const totalMs = sectors.reduce((sum, sector) => {
                const ms = this.timeToMs(sector);
                return sum + (ms || 0);
            }, 0);
            avgTime = this.msToTime(totalMs / sectors.length);
        }

        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="car-color-indicator me-2" 
                         style="background-color: ${carInfo.color}; width: 10px; height: 10px; border-radius: 50%;"></div>
                    <div>
                        <strong>${driverName}</strong>
                        <br>
                        <small class="text-muted">${carInfo.name}</small>
                    </div>
                </div>
            </td>
            <td class="text-center">
                <span class="badge bg-secondary">${lap.lap_number || '-'}</span>
            </td>
            <td class="text-center font-monospace">
                <span class="text-success fw-bold">${lap.lap_time || '-'}</span>
            </td>
            <td class="text-center font-monospace text-info">${lap.sector_1 || '-'}</td>
            <td class="text-center font-monospace text-info">${lap.sector_2 || '-'}</td>
            <td class="text-center font-monospace text-info">${lap.sector_3 || '-'}</td>
            <td class="text-center text-info">${avgTime}</td>
            <td class="text-center">
                <small class="text-muted">${timeStr}</small>
            </td>
        `;

        return row;
    }

    timeToMs(timeStr) {
        if (!timeStr || timeStr === '-') return null;
        
        try {
            const parts = timeStr.split(':');
            if (parts.length === 3) {
                const [minutes, seconds, milliseconds] = parts;
                return (parseInt(minutes) * 60 * 1000) + 
                       (parseInt(seconds) * 1000) + 
                       parseInt(milliseconds);
            } else if (parts.length === 2) {
                const [seconds, milliseconds] = parts;
                return (parseInt(seconds) * 1000) + parseInt(milliseconds);
            }
        } catch (e) {
            return null;
        }
        return null;
    }

    msToTime(ms) {
        if (!ms) return '-';
        
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        const milliseconds = Math.floor(ms % 1000);
        
        if (minutes > 0) {
            return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
        } else {
            return `${seconds}.${milliseconds.toString().padStart(3, '0')}`;
        }
    }

    startPeriodicUpdate() {
        // Update laptime monitor every 5 seconds
        setInterval(() => {
            this.updateLaptimeMonitor();
        }, 5000);
    }
}

// Filter functions
function showAllDrivers() {
    dashboard.showTop6Only = false;
    dashboard.updateLaptimeMonitor();
    
    // Update button states
    document.getElementById('btn-show-all').classList.add('active');
    document.getElementById('btn-show-top6').classList.remove('active');
}

function showTop6Only() {
    dashboard.showTop6Only = true;
    dashboard.updateLaptimeMonitor();
    
    // Update button states
    document.getElementById('btn-show-top6').classList.add('active');
    document.getElementById('btn-show-all').classList.remove('active');
}

// Export functions
async function exportRaceResults() {
    const btn = document.getElementById('btn-export-results');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exporting...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/export/csv/race-results');
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `smartrace_results_${new Date().toISOString().slice(0, 19).replace(/[:]/g, '-')}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('✅ Race results exported successfully!', 'success');
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        showNotification(`❌ Export failed: ${error.message}`, 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function exportLapHistory() {
    const btn = document.getElementById('btn-export-laps');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exporting...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/export/csv/lap-history');
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `smartrace_laphistory_${new Date().toISOString().slice(0, 19).replace(/[:]/g, '-')}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('✅ Lap history exported successfully!', 'success');
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        showNotification(`❌ Export failed: ${error.message}`, 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Dropbox functions
async function exportToDropbox() {
    const btn = document.getElementById('btn-dropbox-export');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/export/dropbox');
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Successfully uploaded to Dropbox!', 'success');
            updateDropboxInfo(result);
        } else {
            showNotification(`❌ Upload failed: ${result.message}`, 'danger');
        }
    } catch (error) {
        showNotification(`❌ Upload error: ${error.message}`, 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function checkDropboxStatus() {
    try {
        const response = await fetch('/api/dropbox/status');
        const status = await response.json();
        
        updateDropboxStatusBadge(status);
        updateDropboxInfo(status);
        
        if (status.connected) {
            showNotification(`✅ ${status.message}`, 'success');
        } else {
            showNotification(`⚠️ ${status.message}`, 'warning');
        }
    } catch (error) {
        showNotification(`❌ Status check failed: ${error.message}`, 'danger');
    }
}

function updateDropboxStatusBadge(status) {
    const badge = document.getElementById('dropbox-status-badge');
    if (!badge) return;
    
    if (status.connected) {
        badge.innerHTML = '<span class="badge bg-success">Dropbox Connected</span>';
    } else {
        badge.innerHTML = '<span class="badge bg-secondary">Dropbox Offline</span>';
    }
}

function updateDropboxInfo(info) {
    const infoDiv = document.getElementById('dropbox-info');
    if (!infoDiv) return;
    
    if (info.connected && info.account_name) {
        infoDiv.innerHTML = `
            <div class="alert alert-success alert-sm">
                <strong>Account:</strong> ${info.account_name}<br>
                <strong>Email:</strong> ${info.email}<br>
                <strong>Folder:</strong> ${info.folder}
            </div>
        `;
    } else if (info.results) {
        const successCount = info.results.filter(r => r.success).length;
        const totalCount = info.results.length;
        
        let resultHtml = `
            <div class="alert alert-info alert-sm">
                <strong>Upload Results:</strong> ${successCount}/${totalCount} files<br>
                <strong>Folder:</strong> ${info.folder}<br><br>
                <strong>Files:</strong><br>
        `;
        
        info.results.forEach(result => {
            const icon = result.success ? '✅' : '❌';
            resultHtml += `${icon} ${result.file}<br>`;
        });
        
        resultHtml += '</div>';
        infoDiv.innerHTML = resultHtml;
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Utility functions
function refreshData() {
    location.reload();
}

function clearAllData() {
    if (confirm('Are you sure you want to clear all race data? This action cannot be undone.')) {
        localStorage.clear();
        sessionStorage.clear();
        location.reload();
    }
}

// Initialize dashboard when DOM is ready
let dashboard;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🏁 Initializing SmartRace Dashboard...');
    dashboard = new DashboardManager();
    
    // Auto-check Dropbox status after 2 seconds
    setTimeout(() => {
        if (typeof checkDropboxStatus === 'function') {
            checkDropboxStatus();
        }
    }, 2000);
    
    console.log('✅ SmartRace Dashboard initialized!');
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
    showNotification(`❌ Error: ${event.error.message}`, 'danger');
});

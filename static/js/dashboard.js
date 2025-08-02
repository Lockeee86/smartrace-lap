// Dashboard WebSocket and UI Management
class DashboardManager {
    constructor() {
        this.socket = null;
        this.lapHistory = {};
        this.showTop6Only = false;
        this.init();
    }

    init() {
        this.initWebSocket();
        this.updateLaptimeMonitor();
        this.startPeriodicUpdate();
    }

    initWebSocket() {
        // Initialize WebSocket connection
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('✅ Connected to SmartRace Dashboard');
            this.updateConnectionStatus('connected');
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Disconnected from SmartRace Dashboard');
            this.updateConnectionStatus('disconnected');
        });

        this.socket.on('race_update', (data) => {
            console.log('📊 Race data updated:', data);
            this.handleRaceUpdate(data);
        });

        this.socket.on('track_update', (data) => {
            console.log('🏁 Track data updated:', data);
            this.handleTrackUpdate(data);
        });
    }

    handleRaceUpdate(data) {
        // Update session info
        if (data.session_info) {
            this.updateSessionInfo(data.session_info);
        }

        // Update drivers and lap times
        if (data.drivers) {
            this.updateDriversTable(data.drivers);
        }

        // Update laptime monitor
        this.updateLaptimeMonitor();
    }

    updateSessionInfo(sessionInfo) {
        const elements = {
            'session-time': sessionInfo.total_time,
            'current-lap': sessionInfo.current_lap,
            'flag-status': sessionInfo.flag_status
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined) {
                element.textContent = value;
            }
        });
    }

    updateDriversTable(drivers) {
        // Sort drivers by position
        const sortedDrivers = Object.entries(drivers).sort((a, b) => {
            return (a[1].position || 999) - (b[1].position || 999);
        });

        const tbody = document.querySelector('#driver-standings tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        sortedDrivers.forEach(([driverId, driver]) => {
            const row = this.createDriverRow(driverId, driver);
            tbody.appendChild(row);
        });
    }

    createDriverRow(driverId, driver) {
        const row = document.createElement('tr');
        row.id = `driver-row-${driverId}`;

        const positionBadge = this.createPositionBadge(driver.position);
        
        row.innerHTML = `
            <td>${positionBadge}</td>
            <td><strong>${driver.name || `Driver ${driverId}`}</strong></td>
            <td>${driver.laps_completed || 0}</td>
            <td class="text-warning">${driver.best_lap_time || '-'}</td>
            <td>${driver.last_lap_time || '-'}</td>
            <td>${driver.gap || '-'}</td>
            <td><span class="badge bg-success">${driver.status || 'Unknown'}</span></td>
        `;

        return row;
    }

    createPositionBadge(position) {
        if (position === 1) {
            return `<span class="badge bg-warning text-dark">${position}</span>`;
        } else if (position <= 3) {
            return `<span class="badge bg-success">${position}</span>`;
        } else {
            return `<span class="badge bg-primary">${position}</span>`;
        }
    }

    async updateLaptimeMonitor() {
        try {
            // Fetch current lap history
            const response = await fetch('/api/lap-history');
            const lapHistory = await response.json();
            
            // Fetch current race data  
            const raceResponse = await fetch('/api/race-data');
            const raceData = await raceResponse.json();

            this.lapHistory = lapHistory;
            this.renderLaptimeMonitor(raceData.drivers, lapHistory);
        } catch (error) {
            console.error('Failed to update laptime monitor:', error);
        }
    }

    renderLaptimeMonitor(drivers, lapHistory) {
        const tbody = document.getElementById('laptime-rows');
        if (!tbody) return;

        // Sort drivers by position
        const sortedDrivers = Object.entries(drivers).sort((a, b) => {
            return (a[1].position || 999) - (b[1].position || 999);
        });

        // Show only top 6 if filter is active
        const driversToShow = this.showTop6Only ? sortedDrivers.slice(0, 6) : sortedDrivers;

        tbody.innerHTML = '';

        driversToShow.forEach(([driverId, driver]) => {
            const row = this.createLaptimeRow(driverId, driver, lapHistory[driverId] || []);
            tbody.appendChild(row);
        });
    }

    createLaptimeRow(driverId, driver, driverLaps) {
        const row = document.createElement('tr');
        
        // Get last 10 laps
        const last10Laps = driverLaps.slice(-10);
        const lapCells = [];
        
        // Fill lap time cells (L-9 to Current)
        for (let i = 9; i >= 0; i--) {
            const lapIndex = last10Laps.length - 1 - i;
            const lap = lapIndex >= 0 ? last10Laps[lapIndex] : null;
            
            let lapTime = '-';
            let cellClass = 'text-center text-muted';
            
            if (lap && lap.lap_time) {
                lapTime = lap.lap_time;
                
                // Color coding for lap times
                if (lap.lap_time === driver.best_lap_time) {
                    cellClass = 'text-center text-success fw-bold'; // Best lap
                } else {
                    cellClass = 'text-center';
                }
            }
            
            const isCurrentLap = i === 0 && lap;
            if (isCurrentLap) {
                cellClass += ' bg-warning bg-opacity-25';
            }
            
            lapCells.push(`<td class="${cellClass}">${lapTime}</td>`);
        }

        // Calculate average lap time
        const validLaps = driverLaps.filter(lap => lap.lap_time && lap.lap_time !== '-');
        const avgTime = validLaps.length > 0 ? 
            (validLaps.reduce((sum, lap) => sum + parseFloat(lap.lap_time || 0), 0) / validLaps.length).toFixed(3) : 
            '-';

        row.innerHTML = `
            <td class="fw-bold">
                <span class="badge bg-primary me-1">${driver.position || '-'}</span>
                ${driver.name || `Driver ${driverId}`}
            </td>
            ${lapCells.join('')}
            <td class="text-center text-success fw-bold">${driver.best_lap_time || '-'}</td>
            <td class="text-center text-info">${avgTime}</td>
        `;

        return row;
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;

        const statusConfig = {
            connected: { class: 'bg-success', text: 'Connected' },
            disconnected: { class: 'bg-danger', text: 'Disconnected' },
            connecting: { class: 'bg-warning', text: 'Connecting...' }
        };

        const config = statusConfig[status] || statusConfig.connecting;
        statusElement.className = `badge ${config.class} me-2`;
        statusElement.textContent = config.text;
    }

    startPeriodicUpdate() {
        // Update laptime monitor every 5 seconds
        setInterval(() => {
            this.updateLaptimeMonitor();
        }, 5000);
    }
}

// Global functions for button controls
function showAllDrivers() {
    dashboard.showTop6Only = false;
    dashboard.updateLaptimeMonitor();
    
    // Update button states
    document.querySelectorAll('.btn-group .btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
}

function showTop6Drivers() {
    dashboard.showTop6Only = true;
    dashboard.updateLaptimeMonitor();
    
    // Update button states  
    document.querySelectorAll('.btn-group .btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DashboardManager();
});

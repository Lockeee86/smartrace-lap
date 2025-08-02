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
            if (element) element.textContent = sessionInfo.flag_status;
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
            <td>${positionBadge}</td>
            <td>
                <div class="d-flex align-items-center">
                    <div>
                        <div class="fw-bold">${driver.name || `Driver ${driverId}`}</div>
                        <small style="color: ${carInfo.color}; font-weight: bold;">
                            🏎️ ${carInfo.name}
                            <span class="text-muted">(${carInfo.manufacturer} ${carInfo.scale})</span>
                        </small>
                        <div class="mt-1">
                            <span class="badge" style="background-color: ${carInfo.color}20; color: ${carInfo.color}; border: 1px solid ${carInfo.color};">
                                ${carInfo.class}
                            </span>
                            ${carInfo.digital_analog === 'digital' ? '<span class="badge bg-info ms-1">Digital</span>' : ''}
                            ${carInfo.magnets === 'yes' ? '<span class="badge bg-warning ms-1">Magnets</span>' : ''}
                        </div>
                    </div>
                </div>
            </td>
            <td class="text-center">${driver.laps_completed || 0}</td>
            <td class="text-center text-success fw-bold">${driver.best_lap_time || '-'}</td>
            <td class="text-center">${driver.last_lap_time || '-'}</td>
            <td class="text-center">${driver.gap || '-'}</td>
            <td>
                <span class="badge ${this.getStatusBadgeClass(driver.status)}">
                    ${driver.status || 'Unknown'}
                </span>
            </td>
        `;

        return row;
    }

    createPositionBadge(position) {
        if (!position) return '<span class="badge bg-secondary">-</span>';
        
        const pos = parseInt(position);
        let badgeClass = 'bg-primary';
        
        if (pos === 1) badgeClass = 'bg-warning';
        else if (pos === 2) badgeClass = 'bg-secondary';
        else if (pos === 3) badgeClass = 'bg-success';
        
        return `<span class="badge ${badgeClass}">${position}</span>`;
    }

    getStatusBadgeClass(status) {
        switch(status?.toLowerCase()) {
            case 'running': return 'bg-success';
            case 'finished': return 'bg-primary';
            case 'dnf': return 'bg-danger';
            case 'dns': return 'bg-secondary';
            default: return 'bg-info';
        }
    }

    async updateLaptimeMonitor() {
        try {
            const [raceResponse, historyResponse] = await Promise.all([
                fetch('/api/race-data'),
                fetch('/api/lap-history')
            ]);
            
            const raceData = await raceResponse.json();
            const lapHistory = await historyResponse.json();
            
            this.lapHistory = lapHistory;
            this.renderLaptimeMonitor(raceData.drivers || {});
        } catch (error) {
            console.error('Failed to update laptime monitor:', error);
        }
    }

    renderLaptimeMonitor(drivers) {
        const tbody = document.querySelector('#laptime-monitor tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        let driverEntries = Object.entries(drivers);
        
        if (this.showTop6Only) {
            driverEntries = driverEntries.sort((a, b) => {
                const posA = parseInt(a[1].position) || 999;
                const posB = parseInt(b[1].position) || 999;
                return posA - posB;
            }).slice(0, 6);
        }

        driverEntries.forEach(([driverId, driver]) => {
            const row = this.createLaptimeRow(driverId, driver);
            tbody.appendChild(row);
        });
    }

    createLaptimeRow(driverId, driver) {
        const row = document.createElement('tr');
        const driverLaps = this.lapHistory[driverId] || [];
        
        const carInfo = this.carDatabase[driver.car_id] || {
            name: 'Unknown Car',
            color: '#666666',
            manufacturer: 'Unknown',
            scale: '',
            class: 'Unknown'
        };

        const last10Laps = driverLaps.slice(-10);
        const lapCells = [];

        for (let i = 9; i >= 0; i--) {
            const lapIndex = last10Laps.length - 1 - i;
            const lap = lapIndex >= 0 ? last10Laps[lapIndex] : null;

            let lapTime = '-';
            let cellClass = 'text-center text-muted';

            if (lap && lap.lap_time) {
                lapTime = lap.lap_time;

                if (lap.lap_time === driver.best_lap_time) {
                    cellClass = 'text-center text-success fw-bold';
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

        const validLaps = driverLaps.filter(lap => lap.lap_time && lap.lap_time !== '-');
        const avgTime = validLaps.length > 0 ? 
            (validLaps.reduce((sum, lap) => sum + parseFloat(lap.lap_time || 0), 0) / validLaps.length).toFixed(3) : 
            '-';

        row.innerHTML = `
            <td class="fw-bold" style="min-width: 200px;">
                <div class="d-flex align-items-center">
                    <span class="badge bg-primary me-2">${driver.position || '-'}</span>
                    <div class="flex-grow-1">
                        <div class="mb-1">${driver.name || `Driver ${driverId}`}</div>
                        <div class="d-flex flex-wrap align-items-center gap-1">
                            <small style="color: ${carInfo.color}; font-weight: bold; font-size: 0.75rem;">
                                🏎️ ${carInfo.name}
                            </small>
                        </div>
                        <div class="d-flex flex-wrap align-items-center gap-1 mt-1">
                            <span class="badge" style="background-color: ${carInfo.color}20; color: ${carInfo.color}; border: 1px solid ${carInfo.color}; font-size: 0.6rem;">
                                ${carInfo.manufacturer} ${carInfo.scale}
                            </span>
                            ${carInfo.class !== 'Unknown' ? `<span class="badge bg-secondary" style="font-size: 0.6rem;">${carInfo.class}</span>` : ''}
                        </div>
                    </div>
                </div>
            </td>
            ${lapCells.join('')}
            <td class="text-center text-success fw-bold">${driver.best_lap_time || '-'}</td>
            <td class="text-center text-info">${avgTime}</td>
        `;

        return row;
    }

    startPeriodicUpdate() {
        setInterval(() => {
            this.updateLaptimeMonitor();
        }, 5000);
    }
}

// Filter functions
function showAllDrivers() {
    dashboard.showTop6Only = false;
    dashboard.updateLaptimeMonitor();
    
    document.getElementById('btn-all-drivers').classList.add('active');
    document.getElementById('btn-top6-drivers').classList.remove('active');
}

function showTop6Drivers() {
    dashboard.showTop6Only = true;
    dashboard.updateLaptimeMonitor();
    
    document.getElementById('btn-top6-drivers').classList.add('active');
    document.getElementById('btn-all-drivers').classList.remove('active');
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new DashboardManager();
    
    console.log('🏁 SmartRace Dashboard initialized with car support');
});

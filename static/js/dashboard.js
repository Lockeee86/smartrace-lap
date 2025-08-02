// Global variables
let socket;
let raceData = {};
let trackData = {};
let lapTimesChart, driverComparisonChart, sectorChart;
let isConnected = false;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Dashboard initializing...');
    initializeSocket();
    initializeCharts();
    updateConnectionStatus(false);
});

// Socket.IO Connection
function initializeSocket() {
    try {
        socket = io();
        
        socket.on('connect', function() {
            console.log('✅ Socket.IO connected');
            isConnected = true;
            updateConnectionStatus(true);
            socket.emit('request_data');
        });
        
        socket.on('disconnect', function() {
            console.log('❌ Socket.IO disconnected');
            isConnected = false;
            updateConnectionStatus(false);
        });
        
        socket.on('race_update', function(data) {
            console.log('🏁 Race data received:', data);
            raceData = data;
            updateDashboard();
        });
        
        socket.on('track_update', function(data) {
            console.log('🗺️ Track data received:', data);  
            trackData = data;
            updateTrackDisplay();
        });
        
        socket.on('connect_error', function(error) {
            console.error('❌ Socket.IO connection error:', error);
            isConnected = false;
            updateConnectionStatus(false);
        });
        
    } catch (error) {
        console.error('❌ Socket initialization error:', error);
    }
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connectionStatus');
    if (indicator) {
        if (connected) {
            indicator.innerHTML = '<i class="bi bi-wifi text-success"></i> Connected';
            indicator.className = 'status-online';
        } else {
            indicator.innerHTML = '<i class="bi bi-wifi-off text-danger"></i> Disconnected';
            indicator.className = 'status-offline';
        }
    }
}

// Update dashboard with race data
function updateDashboard() {
    if (!raceData) return;
    
    // Update race status cards
    if (raceData.race_status) {
        updateElement('raceTime', formatTime(raceData.race_status.time || 0));
        updateElement('raceMode', raceData.race_status.mode || 'Practice');
    }
    
    if (raceData.session_info) {
        updateElement('totalLaps', raceData.session_info.total_laps || 0);
    }
    
    // Update drivers count
    const driversCount = Object.keys(raceData.drivers || {}).length;
    updateElement('driversCount', driversCount);
    
    // Update drivers table
    updateDriversTable();
    
    // Update charts
    updateCharts();
}

// Update drivers table
function updateDriversTable() {
    const tableBody = document.getElementById('driversTableBody');
    if (!tableBody || !raceData.drivers) return;
    
    // Convert drivers object to array and sort by position
    const driversArray = Object.values(raceData.drivers).sort((a, b) => {
        return (a.position || 999) - (b.position || 999);
    });
    
    let html = '';
    driversArray.forEach(driver => {
        const positionClass = getPositionClass(driver.position);
        const lastLap = formatLapTime(driver.last_lap_time);
        const bestLap = formatLapTime(driver.best_lap_time);
        
        html += `
            <tr>
                <td><span class="badge ${positionClass}">${driver.position || '-'}</span></td>
                <td>${driver.name || `Driver ${driver.id}`}</td>
                <td>${driver.laps || 0}</td>
                <td class="lap-time">${lastLap}</td>
                <td class="lap-time">${bestLap}</td>
                <td>${formatTime(driver.total_time || 0)}</td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

// Update track display
function updateTrackDisplay() {
    if (!trackData || !trackData.track_data) return;
    
    // Update track info
    updateElement('trackName', trackData.track_data.name || 'Unknown Track');
    updateElement('trackLength', `${(trackData.track_data.length || 0).toFixed(2)} m`);
    
    // Update track SVG if we have layout data
    const trackSvg = document.getElementById('trackLayout');
    if (trackSvg && trackData.track_data.layout) {
        trackSvg.innerHTML = trackData.track_data.layout;
    } else if (trackSvg) {
        // Default track layout
        trackSvg.innerHTML = createDefaultTrackSVG();
    }
}

// Create default track SVG
function createDefaultTrackSVG() {
    return `
        <svg viewBox="0 0 400 200" style="width: 100%; height: 200px;">
            <path d="M50 100 Q50 50, 100 50 L300 50 Q350 50, 350 100 Q350 150, 300 150 L100 150 Q50 150, 50 100 Z" 
                  class="track-path" fill="none" stroke="#666" stroke-width="4"/>
            <path d="M50 100 Q50 40, 100 40 L300 40 Q360 40, 360 100 Q360 160, 300 160 L100 160 Q50 160, 50 100 Z" 
                  class="track-border" fill="none" stroke="#444" stroke-width="1" stroke-dasharray="3,3"/>
            <line x1="45" y1="95" x2="55" y2="105" stroke="#00ff00" stroke-width="3"/>
            <text x="20" y="90" fill="#fff" font-size="12">S/F</text>
        </svg>
    `;
}

// Initialize charts
function initializeCharts() {
    // Only initialize if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.warn('⚠️ Chart.js not loaded - charts disabled');
        return;
    }
    
    try {
        // Lap times chart
        const lapTimesCtx = document.getElementById('lapTimesChart');
        if (lapTimesCtx) {
            lapTimesChart = new Chart(lapTimesCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: getChartOptions('Lap Times (seconds)')
            });
        }
        
        // Driver comparison chart
        const comparisonCtx = document.getElementById('driverComparisonChart');
        if (comparisonCtx) {
            driverComparisonChart = new Chart(comparisonCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Best Lap Time',
                        data: [],
                        backgroundColor: 'rgba(13, 202, 240, 0.7)',
                        borderColor: 'rgba(13, 202, 240, 1)',
                        borderWidth: 1
                    }]
                },
                options: getChartOptions('Lap Time (seconds)')
            });
        }
        
    } catch (error) {
        console.error('❌ Chart initialization error:', error);
    }
}

// Get common chart options
function getChartOptions(yAxisLabel) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                ticks: { color: '#fff' },
                grid: { color: '#333' }
            },
            y: {
                ticks: { color: '#fff' },
                grid: { color: '#333' },
                title: {
                    display: true,
                    text: yAxisLabel,
                    color: '#fff'
                }
            }
        },
        plugins: {
            legend: {
                labels: { color: '#fff' }
            }
        }
    };
}

// Update charts with current data
function updateCharts() {
    if (!raceData.drivers) return;
    
    // Update driver comparison chart
    if (driverComparisonChart) {
        const drivers = Object.values(raceData.drivers);
        const labels = drivers.map(d => d.name || `Driver ${d.id}`);
        const times = drivers.map(d => d.best_lap_time ? parseFloat(d.best_lap_time) : 0);
        
        driverComparisonChart.data.labels = labels;
        driverComparisonChart.data.datasets[0].data = times;
        driverComparisonChart.update('none');
    }
}

// Utility functions
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element && element.textContent !== value.toString()) {
        element.textContent = value;
        element.classList.add('lap-time-update');
        setTimeout(() => element.classList.remove('lap-time-update'), 2000);
    }
}

function formatTime(seconds) {
    if (!seconds || seconds === 0) return '00:00.000';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

function formatLapTime(time) {
    if (!time) return '-';
    
    if (typeof time === 'string' && time.includes(':')) {
        return time;
    }
    
    if (typeof time === 'number') {
        return formatTime(time);
    }
    
    return time.toString();
}

function getPositionClass(position) {
    if (position === 1) return 'badge bg-warning position-1';
    if (position === 2) return 'badge bg-secondary position-2';  
    if (position === 3) return 'badge bg-warning position-3';
    return 'badge bg-primary';
}

// Auto-refresh data every 5 seconds if socket disconnected
setInterval(() => {
    if (!isConnected && socket) {
        console.log('🔄 Attempting to reconnect...');
        socket.connect();
    }
}, 5000);

console.log('✅ Dashboard JavaScript loaded');

// Global variables
let socket;
let raceData = {};
let trackData = {};
let lapTimesChart, driverComparisonChart;

// Initialize Socket.IO connection
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeCharts();
});

function initializeSocket() {
    socket = io();
    
    // Connection events
    socket.on('connect', function() {
        updateConnectionStatus(true);
        console.log('🔌 Connected to server');
    });
    
    socket.on('disconnect', function() {
        updateConnectionStatus(false);
        console.log('❌ Disconnected from server');
    });
    
    // Race data events
    socket.on('race_update', function(data) {
        console.log('🏁 Race update received:', data);
        raceData = data;
        updateDashboard(data);
    });
    
    socket.on('track_update', function(data) {
        console.log('🗺️ Track update received:', data);
        trackData = data;
        updateTrack(data);
    });
    
    // Request initial data
    socket.emit('request_data');
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connectionStatus');
    const textElement = document.getElementById('connectionText');
    
    if (statusElement && textElement) {
        if (connected) {
            statusElement.className = 'bi bi-circle-fill text-success me-1';
            textElement.textContent = 'Verbunden';
        } else {
            statusElement.className = 'bi bi-circle-fill text-danger me-1';
            textElement.textContent = 'Getrennt';
        }
    }
}

function initializeDashboard() {
    // Request initial data when dashboard loads
    if (socket && socket.connected) {
        socket.emit('request_data');
    }
}

function updateDashboard(data) {
    updateRaceStatus(data);
    updateLeaderboard(data);
    updateLapTimes(data);
    updateAnalysis(data);
}

function updateRaceStatus(data) {
    // Race time
    const raceTimeElement = document.getElementById('raceTime');
    if (raceTimeElement && data.race_time) {
        raceTimeElement.textContent = formatTime(data.race_time);
    }
    
    // Total laps
    const totalLapsElement = document.getElementById('totalLaps');
    if (totalLapsElement && data.total_laps !== undefined) {
        totalLapsElement.textContent = data.total_laps || '0';
    }
    
    // Race mode
    const raceModeElement = document.getElementById('raceMode');
    if (raceModeElement && data.race_mode) {
        raceModeElement.textContent = data.race_mode;
    }
    
    // Track name
    const trackNameElement = document.getElementById('trackName');
    if (trackNameElement && data.track_name) {
        trackNameElement.textContent = data.track_name;
    }
}

function updateLeaderboard(data) {
    const leaderboardElement = document.getElementById('leaderboard');
    if (!leaderboardElement || !data.drivers) return;
    
    // Sort drivers by position or best lap time
    const sortedDrivers = Object.entries(data.drivers)
        .map(([id, driver]) => ({ id, ...driver }))
        .sort((a, b) => {
            if (a.position && b.position) {
                return a.position - b.position;
            }
            if (a.best_lap_time && b.best_lap_time) {
                return a.best_lap_time - b.best_lap_time;
            }
            return (b.laps || 0) - (a.laps || 0);
        });
    
    let leaderboardHTML = '';
    
    if (sortedDrivers.length === 0) {
        leaderboardHTML = `
            <div class="text-center text-muted py-5">
                <i class="bi bi-hourglass-split fs-1"></i>
                <p class="mt-2">Warten auf Race-Daten...</p>
            </div>
        `;
    } else {
        sortedDrivers.forEach((driver, index) => {
            const position = index + 1;
            const positionClass = position <= 3 ? `position-${position}` : '';
            const positionIcon = position === 1 ? '🥇' : position === 2 ? '🥈' : position === 3 ? '🥉' : `${position}.`;
            
            leaderboardHTML += `
                <div class="leaderboard-item ${positionClass} p-3 mb-2 rounded-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <span class="fs-5 me-3 fw-bold" style="min-width: 40px;">${positionIcon}</span>
                            <div>
                                <div class="fw-bold text-light">${driver.name || `Driver ${driver.id}`}</div>
                                <small class="text-muted">${driver.laps || 0} Runden</small>
                            </div>
                        </div>
                        <div class="text-end">
                            <div class="fw-bold text-info">
                                ${driver.best_lap_time ? formatTime(driver.best_lap_time) : '--:--.---'}
                            </div>
                            <small class="text-muted">
                                ${driver.last_lap_time ? formatTime(driver.last_lap_time) : 'Keine Zeit'}
                            </small>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    leaderboardElement.innerHTML = leaderboardHTML;
}

function updateLapTimes(data) {
    const lapTimesContainer = document.getElementById('lapTimesContainer');
    if (!lapTimesContainer || !data.drivers) return;
    
    const drivers = Object.entries(data.drivers).map(([id, driver]) => ({ id, ...driver }));
    
    if (drivers.length === 0) {
        lapTimesContainer.innerHTML = `
            <div class="col-12 text-center text-muted py-3">
                <i class="bi bi-clock-history fs-1"></i>
                <p class="mt-2">Keine Rundenzeiten verfügbar</p>
            </div>
        `;
        return;
    }
    
    // Find best lap time for comparison
    const allLapTimes = drivers
        .map(d => d.last_lap_time)
        .filter(t => t && t > 0);
    const bestLapTime = allLapTimes.length > 0 ? Math.min(...allLapTimes) : null;
    
    let lapTimesHTML = '';
    
    drivers.forEach(driver => {
        if (!driver.last_lap_time) return;
        
        let cardClass = 'lap-time-card';
        let badgeClass = 'bg-secondary';
        let badgeText = 'Current';
        
        // Determine card style based on performance
        if (bestLapTime && driver.last_lap_time === bestLapTime) {
            cardClass += ' lap-time-best';
            badgeClass = 'bg-success';
            badgeText = 'Best Lap';
        } else if (driver.best_lap_time && driver.last_lap_time === driver.best_lap_time) {
            cardClass += ' lap-time-personal';
            badgeClass = 'bg-primary';
            badgeText = 'Personal Best';
        } else if (bestLapTime && driver.last_lap_time > bestLapTime * 1.05) {
            cardClass += ' lap-time-slow';
            badgeClass = 'bg-warning';
            badgeText = 'Slow';
        }
        
        const gapText = bestLapTime && driver.last_lap_time !== bestLapTime 
            ? `+${formatTime(driver.last_lap_time - bestLapTime)}` 
            : 'Best';
        
        lapTimesHTML += `
            <div class="col-lg-3 col-md-4 col-sm-6">
                <div class="card bg-dark ${cardClass}">
                    <div class="card-body text-center">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-title text-light mb-0">${driver.name || `Driver ${driver.id}`}</h6>
                            <span class="badge ${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="h4 text-info mb-1">${formatTime(driver.last_lap_time)}</div>
                        <div class="text-muted small">
                            Gap: <span class="text-${gapText === 'Best' ? 'success' : 'warning'}">${gapText}</span>
                        </div>
                        <div class="text-muted small mt-1">
                            Lap ${driver.laps || 0}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    lapTimesContainer.innerHTML = lapTimesHTML;
}

function updateTrack(data) {
    updateTrackSVG('trackSvg', data, { width: 800, height: 400 });
    updateTrackSVG('trackDetailSvg', data, { width: 1000, height: 600 });
    updateTrackInfo(data);
}

function updateTrackSVG(svgId, data, dimensions) {
    const svg = document.getElementById(svgId);
    if (!svg || !data.track_data) return;
    
    const trackData = data.track_data;
    const { width, height } = dimensions;
    
    // Clear existing content
    svg.innerHTML = '';
    
    try {
        // Create track path from coordinates
        if (trackData.coordinates && trackData.coordinates.length > 0) {
            const coords = trackData.coordinates;
            
            // Find bounds of track
            const minX = Math.min(...coords.map(c => c.x));
            const maxX = Math.max(...coords.map(c => c.x));
            const minY = Math.min(...coords.map(c => c.y));
            const maxY = Math.max(...coords.map(c => c.y));
            
            // Calculate scale and offset
            const trackWidth = maxX - minX;
            const trackHeight = maxY - minY;
            const scale = Math.min((width - 100) / trackWidth, (height - 100) / trackHeight);
            const offsetX = (width - trackWidth * scale) / 2 - minX * scale;
            const offsetY = (height - trackHeight * scale) / 2 - minY * scale;
            
            // Create path string
            let pathString = `M ${coords[0].x * scale + offsetX} ${coords[0].y * scale + offsetY}`;
            for (let i = 1; i < coords.length; i++) {
                pathString += ` L ${coords[i].x * scale + offsetX} ${coords[i].y * scale + offsetY}`;
            }
            pathString += ' Z'; // Close path
            
            // Add track path
            const trackPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            trackPath.setAttribute('d', pathString);
            trackPath.setAttribute('class', 'track-path');
            trackPath.setAttribute('fill', 'none');
            trackPath.setAttribute('stroke', '#ffffff');
            trackPath.setAttribute('stroke-width', svgId === 'trackDetailSvg' ? '12' : '8');
            svg.appendChild(trackPath);
            
            // Add track borders
            const borderPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            borderPath.setAttribute('d', pathString);
            borderPath.setAttribute('class', 'track-border');
            svg.appendChild(borderPath);
            
            // Add start/finish line
            if (coords.length > 1) {
                const startLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                startLine.setAttribute('x1', coords[0].x * scale + offsetX - 10);
                startLine.setAttribute('y1', coords[0].y * scale + offsetY - 10);
                startLine.setAttribute('x2', coords[0].x * scale + offsetX + 10);
                startLine.setAttribute('y2', coords[0].y * scale + offsetY + 10);
                startLine.setAttribute('class', 'start-finish');
                svg.appendChild(startLine);
                
                // Add start/finish text
                const startText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                startText.setAttribute('x', coords[0].x * scale + offsetX);
                startText.setAttribute('y', coords[0].y * scale + offsetY - 20);
                startText.setAttribute('text-anchor', 'middle');
                startText.setAttribute('fill', '#198754');
                startText.setAttribute('font-size', '12');
                startText.setAttribute('font-weight', 'bold');
                startText.textContent = 'START/FINISH';
                svg.appendChild(startText);
            }
            
            // Add sectors if available
            if (trackData.sectors && trackData.sectors.length > 0) {
                trackData.sectors.forEach((sector, index) => {
                    if (sector.position && sector.position < coords.length) {
                        const coord = coords[sector.position];
                        const sectorLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        sectorLine.setAttribute('x1', coord.x * scale + offsetX - 8);
                        sectorLine.setAttribute('y1', coord.y * scale + offsetY - 8);
                        sectorLine.setAttribute('x2', coord.x * scale + offsetX + 8);
                        sectorLine.setAttribute('y2', coord.y * scale + offsetY + 8);
                        sectorLine.setAttribute('class', 'sector-line');
                        svg.appendChild(sectorLine);
                        
                        // Add sector text
                        const sectorText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        sectorText.setAttribute('x', coord.x * scale + offsetX);
                        sectorText.setAttribute('y', coord.y * scale + offsetY - 15);
                        sectorText.setAttribute('text-anchor', 'middle');
                        sectorText.setAttribute('fill', '#ffc107');
                        sectorText.setAttribute('font-size', '10');
                        sectorText.textContent = `S${index + 1}`;
                        svg.appendChild(sectorText);
                    }
                });
            }
            
        } else {
            // Fallback: Simple oval track
            const centerX = width / 2;
            const centerY = height / 2;
            const radiusX = (width - 100) / 2;
            const radiusY = (height - 100) / 2;
            
            const track = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
            track.setAttribute('cx', centerX);
            track.setAttribute('cy', centerY);
            track.setAttribute('rx', radiusX);
            track.setAttribute('ry', radiusY);
            track.setAttribute('class', 'track-path');
            svg.appendChild(track);
            
            // Start/finish line
            const startLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            startLine.setAttribute('x1', centerX + radiusX - 10);
            startLine.setAttribute('y1', centerY - 10);
            startLine.setAttribute('x2', centerX + radiusX + 10);
            startLine.setAttribute('y2', centerY + 10);
            startLine.setAttribute('stroke', '#198754');
            startLine.setAttribute('stroke-width', '4');
            svg.appendChild(startLine);
        }
        
    } catch (error) {
        console.error('Error rendering track:', error);
        
        // Error fallback
        const errorText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        errorText.setAttribute('x', width / 2);
        errorText.setAttribute('y', height / 2);
        errorText.setAttribute('text-anchor', 'middle');
        errorText.setAttribute('fill', '#dc3545');
        errorText.setAttribute('font-size', '16');
        errorText.textContent = 'Fehler beim Laden des Tracks';
        svg.appendChild(errorText);
    }
}

function updateTrackInfo(data) {
    if (!data.track_data) return;
    
    const trackData = data.track_data;
    
    // Update track info elements
    const elements = {
        'trackInfoName': trackData.name || 'Unbekannt',
        'trackLength': trackData.length ? `${trackData.length} m` : '--- m',
        'sectorCount': trackData.sectors ? trackData.sectors.length : '---',
        'trackLayout': trackData.layout || 'Standard'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

function updateAnalysis(data) {
    updateAnalysisStats(data);
    updateAnalysisCharts(data);
}

function updateAnalysisStats(data) {
    if (!data.drivers) return;
    
    const drivers = Object.values(data.drivers);
    const allLapTimes = drivers
        .map(d => d.best_lap_time)
        .filter(t => t && t > 0);
    
    // Best lap time
    const bestLapElement = document.getElementById('bestLapTime');
    const bestDriverElement = document.getElementById('bestLapDriver');
    if (allLapTimes.length > 0) {
        const bestTime = Math.min(...allLapTimes);
        const bestDriver = drivers.find(d => d.best_lap_time === bestTime);
        
        if (bestLapElement) bestLapElement.textContent = formatTime(bestTime);
        if (bestDriverElement) bestDriverElement.textContent = bestDriver?.name || 'Unbekannt';
    }
    
    // Average lap time
    const avgLapElement = document.getElementById('avgLapTime');
    if (avgLapElement && allLapTimes.length > 0) {
        const avgTime = allLapTimes.reduce((a, b) => a + b, 0) / allLapTimes.length;
        avgLapElement.textContent = formatTime(avgTime);
    }
    
    // Total rounds
    const totalRoundsElement = document.getElementById('totalRounds');
    if (totalRoundsElement) {
        const totalRounds = drivers.reduce((sum, d) => sum + (d.laps || 0), 0);
        totalRoundsElement.textContent = totalRounds;
    }
    
    // Active drivers
    const activeDriversElement = document.getElementById('activeDrivers');
    if (activeDriversElement) {
        const activeCount = drivers.filter(d => d.laps && d.laps > 0).length;
        activeDriversElement.textContent = activeCount;
    }
}

function initializeCharts() {
    // Only initialize if elements exist (on analysis page)
    const lapTimesCtx = document.getElementById('lapTimesChart');
    const driverComparisonCtx = document.getElementById('driverComparisonChart');
    
    if (lapTimesCtx) {
        lapTimesChart = new Chart(lapTimesCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#fff' }
                    }
                },
                scales: {
                    x: { 
                        ticks: { color: '#fff' },
                        grid: { color: '#444' }
                    },
                    y: { 
                        ticks: { 
                            color: '#fff',
                            callback: function(value) {
                                return formatTime(value);
                            }
                        },
                        grid: { color: '#444' }
                    }
                }
            }
        });
    }
    
    if (driverComparisonCtx) {
        driverComparisonChart = new Chart(driverComparisonCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Beste Rundenzeit',
                    data: [],
                    backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dda0dd', '#98d8c8']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#fff' }
                    }
                },
                scales: {
                    x: { 
                        ticks: { color: '#fff' },
                        grid: { color: '#444' }
                    },
                    y: { 
                        ticks: { 
                            color: '#fff',
                            callback: function(value) {
                                return formatTime(value);
                            }
                        },
                        grid: { color: '#444' }
                    }
                }
            }
        });
    }
}

function updateAnalysisCharts(data) {
    if (!data.drivers) return;
    
    const drivers = Object.entries(data.drivers).map(([id, driver]) => ({ id, ...driver }));
    
    // Update driver comparison chart
    if (driverComparisonChart) {
        const driverNames = drivers.map(d => d.name || `Driver ${d.id}`);
        const bestTimes = drivers.map(d => d.best_lap_time || 0);
        
        driverComparisonChart.data.labels = driverNames;
        driverComparisonChart.data.datasets[0].data = bestTimes;
        driverComparisonChart.update();
    }
    
    // Update lap times chart (simplified version)
    if (lapTimesChart) {
        // This would need more complex data structure for historical lap times
        // For now, show current lap times
        const driverNames = drivers.map(d => d.name || `Driver ${d.id}`);
        const datasets = drivers.map((driver, index) => ({
            label: driver.name || `Driver ${driver.id}`,
            data: driver.lap_history || [driver.last_lap_time || 0],
            borderColor: [
                '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', 
                '#ffeaa7', '#dda0dd', '#98d8c8'
            ][index % 7],
            backgroundColor: 'transparent',
            tension: 0.4
        }));
        
        lapTimesChart.data.labels = ['Current'];
        lapTimesChart.data.datasets = datasets;
        lapTimesChart.update();
    }
}

// Utility functions
function formatTime(milliseconds) {
    if (!milliseconds || milliseconds <= 0) {
        return '--:--.---';
    }
    
    const totalSeconds = milliseconds / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);
    const ms = Math.floor((milliseconds % 1000));
    
    return `${minutes}:${seconds.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

function formatTimeShort(milliseconds) {
    if (!milliseconds || milliseconds <= 0) {
        return '---';
    }
    
    const totalSeconds = milliseconds / 1000;
    const seconds = Math.floor(totalSeconds);
    const ms = Math.floor(milliseconds % 1000);
    
    return `${seconds}.${ms.toString().padStart(3, '0')}`;
}

// Export functions for global access
window.smartRace = {
    updateDashboard,
    updateTrack,
    formatTime,
    formatTimeShort,
    socket
};


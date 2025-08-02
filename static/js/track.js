// Track Management (separate from dashboard)
class TrackManager {
    constructor() {
        this.currentTrack = null;
        this.trackData = {};
        this.init();
    }

    init() {
        console.log('🏁 Track Manager initialized');
        this.loadTrackData();
    }

    async loadTrackData() {
        try {
            const response = await fetch('/api/track-info');
            this.trackData = await response.json();
            this.updateTrackDisplay();
        } catch (error) {
            console.error('Failed to load track data:', error);
        }
    }

    updateTrackDisplay() {
        // Track specific UI updates
        console.log('Track data loaded:', this.trackData);
    }
}

// Initialize only on track page
let trackManager = null;

document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.track-content')) {
        console.log('🏁 Initializing Track Manager...');
        trackManager = new TrackManager();
    }
});

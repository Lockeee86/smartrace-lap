// Analysis Management (separate from dashboard)
class AnalysisManager {
    constructor() {
        this.analysisData = {};
        this.charts = {};
        this.init();
    }

    init() {
        console.log('📊 Analysis Manager initialized');
        this.loadAnalysisData();
    }

    async loadAnalysisData() {
        try {
            const response = await fetch('/api/analysis-data');
            this.analysisData = await response.json();
            this.updateAnalysisDisplay();
        } catch (error) {
            console.error('Failed to load analysis data:', error);
        }
    }

    updateAnalysisDisplay() {
        // Analysis specific UI updates
        console.log('Analysis data loaded:', this.analysisData);
    }
}

// Initialize only on analysis page
let analysisManager = null;

document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.analysis-content')) {
        console.log('📊 Initializing Analysis Manager...');
        analysisManager = new AnalysisManager();
    }
});

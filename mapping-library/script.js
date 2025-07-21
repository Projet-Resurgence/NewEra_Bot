class InteractiveMap {
    constructor() {
        this.canvas = document.getElementById('mapCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.tooltip = document.getElementById('tooltip');
        this.colorPicker = document.getElementById('colorPicker');
        this.mapSelector = document.getElementById('mapSelector');

        this.currentMap = 'countries';
        this.availableMaps = new Map();
        this.mapImage = null;
        this.borderCanvas = null;
        this.borderCtx = null;
        this.countiesConfig = null;
        this.colorToCountyMap = new Map();
        this.selectedCounties = new Set();
        this.countyColors = new Map();

        // Performance optimizations
        this.cachedOriginalImageData = null;
        this.cachedBorders = null;

        this.init();
    }

    async init() {
        try {
            await this.discoverMaps();
            await this.loadCurrentMap();
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize map:', error);
            this.showError('Failed to load map. Please check if the image and config files exist.');
        }
    }

    async discoverMaps() {
        // Try to discover available maps by attempting to load common ones
        const potentialMaps = ['countries', 'regions'];

        for (const mapName of potentialMaps) {
            try {
                const configResponse = await fetch(`map_${mapName}_config.txt`);
                const imageResponse = await fetch(`maps_images/map_${mapName}.png`);

                if (configResponse.ok && imageResponse.ok) {
                    this.availableMaps.set(mapName, {
                        configFile: `map_${mapName}_config.txt`,
                        imageFile: `maps_images/map_${mapName}.png`,
                        label: this.capitalize(mapName) + ' Map'
                    });
                }
            } catch (error) {
                console.log(`Map ${mapName} not available:`, error.message);
            }
        }

        this.updateMapSelector();
    }

    updateMapSelector() {
        this.mapSelector.innerHTML = '';

        for (const [mapName, mapData] of this.availableMaps) {
            const option = document.createElement('option');
            option.value = mapName;
            option.textContent = mapData.label;
            option.selected = mapName === this.currentMap;
            this.mapSelector.appendChild(option);
        }
    }

    async loadCurrentMap() {
        const mapData = this.availableMaps.get(this.currentMap);
        if (!mapData) {
            throw new Error(`Map '${this.currentMap}' not found`);
        }

        this.showLoading();

        try {
            await this.loadConfig(mapData.configFile);
            await this.loadMapImage(mapData.imageFile);
            this.createBorderOverlay();
            this.renderLegend();
            this.setupCanvas();
            this.hideLoading();
        } catch (error) {
            this.hideLoading();
            throw error;
        }
    }

    async loadConfig(configFile) {
        try {
            const response = await fetch(configFile);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const configText = await response.text();
            this.countiesConfig = JSON.parse(configText);

            // Build color to county mapping
            this.colorToCountyMap.clear();
            let countyId = 1;

            for (const [color, group] of Object.entries(this.countiesConfig.groups)) {
                const countyData = {
                    id: countyId++,
                    label: group.label,
                    originalColor: color,
                    currentColor: '#ffffff', // Start with white
                    paths: group.paths
                };

                this.colorToCountyMap.set(color, countyData);
            }

            console.log(`Loaded ${this.colorToCountyMap.size} counties from ${configFile}`);
        } catch (error) {
            throw new Error(`Failed to load config from ${configFile}: ${error.message}`);
        }
    }

    async loadMapImage(imageFile) {
        return new Promise((resolve, reject) => {
            this.mapImage = new Image();
            this.mapImage.onload = () => {
                resolve();
            };
            this.mapImage.onerror = () => {
                reject(new Error(`Failed to load image: ${imageFile}`));
            };
            this.mapImage.src = imageFile;
        });
    }

    createBorderOverlay() {
        // Simplified - we'll draw borders directly in drawMap
        console.log('Border overlay creation simplified - drawing borders directly');
    }

    setupCanvas() {
        if (!this.mapImage) return;

        // Set canvas size to match image
        this.canvas.width = this.mapImage.width;
        this.canvas.height = this.mapImage.height;

        // Cache the original image data for fast access
        this.cacheOriginalImageData();

        // Pre-calculate borders once
        this.calculateBorders();

        this.drawMap();
    }

    cacheOriginalImageData() {
        // Create a temporary canvas to get the original image data
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = this.mapImage.width;
        tempCanvas.height = this.mapImage.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(this.mapImage, 0, 0);

        this.cachedOriginalImageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
    }

    calculateBorders() {
        // Pre-calculate border pixels for much faster rendering
        if (!this.cachedOriginalImageData) return;

        const data = this.cachedOriginalImageData.data;
        const width = this.canvas.width;
        const height = this.canvas.height;

        this.cachedBorders = new Set();

        // Simple edge detection - much faster than before
        for (let y = 0; y < height - 1; y++) {
            for (let x = 0; x < width - 1; x++) {
                const idx = (y * width + x) * 4;
                const rightIdx = (y * width + (x + 1)) * 4;
                const downIdx = ((y + 1) * width + x) * 4;

                const currentColor = `${data[idx]},${data[idx + 1]},${data[idx + 2]}`;
                const rightColor = `${data[rightIdx]},${data[rightIdx + 1]},${data[rightIdx + 2]}`;
                const downColor = `${data[downIdx]},${data[downIdx + 1]},${data[downIdx + 2]}`;

                // Store border pixels
                if (currentColor !== rightColor) {
                    this.cachedBorders.add(`${x + 1},${y}`);
                    this.cachedBorders.add(`${x + 1},${y + 1}`);
                }
                if (currentColor !== downColor) {
                    this.cachedBorders.add(`${x},${y + 1}`);
                    this.cachedBorders.add(`${x + 1},${y + 1}`);
                }
            }
        }
    }

    drawMap() {
        // Clear canvas with white background
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Fast rendering using cached data
        this.drawColoredCounties();
        this.drawCachedBorders();
    }

    drawColoredCounties() {
        if (!this.cachedOriginalImageData || this.countyColors.size === 0) return;

        // Get current canvas image data
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        const originalData = this.cachedOriginalImageData.data;

        // Process each colored county
        for (const [countyId, fillColor] of this.countyColors) {
            const county = Array.from(this.colorToCountyMap.values()).find(c => c.id === countyId);
            if (!county) continue;

            const originalRGB = this.hexToRgb(county.originalColor);
            const fillRGB = this.hexToRgb(fillColor);

            if (!originalRGB || !fillRGB) continue;

            // Fast pixel replacement using cached original data
            for (let i = 0; i < originalData.length; i += 4) {
                const r = originalData[i];
                const g = originalData[i + 1];
                const b = originalData[i + 2];

                // If this pixel matches the original county color, fill it
                if (r === originalRGB.r && g === originalRGB.g && b === originalRGB.b) {
                    data[i] = fillRGB.r;
                    data[i + 1] = fillRGB.g;
                    data[i + 2] = fillRGB.b;
                    data[i + 3] = 255; // Make sure it's opaque
                }
            }
        }

        // Apply all changes at once - much faster than multiple putImageData calls
        this.ctx.putImageData(imageData, 0, 0);
    }

    drawCachedBorders() {
        if (!this.cachedBorders) return;

        this.ctx.fillStyle = '#000000';

        // Draw all border pixels at once
        for (const borderPixel of this.cachedBorders) {
            const [x, y] = borderPixel.split(',').map(Number);
            this.ctx.fillRect(x, y, 1, 1);
        }
    }

    // Removed old slow methods - drawSimpleBorders and fillCountyArea
    // New fast methods are drawColoredCounties and drawCachedBorders

    setupEventListeners() {
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleCanvasMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => this.hideTooltip());

        document.getElementById('clearSelection').addEventListener('click', () => this.clearSelection());
        document.getElementById('resetAll').addEventListener('click', () => this.resetAll());

        // Color picker now only affects new selections, not existing ones
        this.mapSelector.addEventListener('change', (e) => this.changeMap(e.target.value));
    }

    async changeMap(newMapName) {
        if (newMapName === this.currentMap) return;

        this.currentMap = newMapName;
        this.selectedCounties.clear();
        this.countyColors.clear();

        // Clear caches when changing maps
        this.cachedOriginalImageData = null;
        this.cachedBorders = null;

        try {
            await this.loadCurrentMap();
            this.updateUI();
        } catch (error) {
            console.error('Failed to change map:', error);
            this.showError(`Failed to load ${newMapName} map: ${error.message}`);
        }
    }

    getCanvasCoordinates(e) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        return {
            x: Math.floor((e.clientX - rect.left) * scaleX),
            y: Math.floor((e.clientY - rect.top) * scaleY)
        };
    }

    getPixelColor(x, y) {
        // Use cached original image data for much faster access
        if (!this.cachedOriginalImageData) return '#ffffff';

        const data = this.cachedOriginalImageData.data;
        const index = (y * this.canvas.width + x) * 4;

        if (index >= data.length || index < 0) return '#ffffff';

        const r = data[index].toString(16).padStart(2, '0');
        const g = data[index + 1].toString(16).padStart(2, '0');
        const b = data[index + 2].toString(16).padStart(2, '0');

        return `#${r}${g}${b}`;
    }

    handleCanvasClick(e) {
        const coords = this.getCanvasCoordinates(e);
        const clickedColor = this.getPixelColor(coords.x, coords.y);

        const county = this.colorToCountyMap.get(clickedColor);
        if (county) {
            this.toggleCountySelection(county);
        } else {
            console.log('Clicked on background or unrecognized area:', clickedColor);
        }
    }

    handleCanvasMouseMove(e) {
        const coords = this.getCanvasCoordinates(e);
        const hoveredColor = this.getPixelColor(coords.x, coords.y);

        const county = this.colorToCountyMap.get(hoveredColor);
        if (county) {
            this.showTooltip(e, `County ${county.id}: ${county.label}`);
        } else {
            this.hideTooltip();
        }
    }

    toggleCountySelection(county) {
        if (this.selectedCounties.has(county.id)) {
            this.selectedCounties.delete(county.id);
            this.countyColors.delete(county.id);
        } else {
            this.selectedCounties.add(county.id);
            // Automatically apply the current color picker color
            const currentColor = this.colorPicker.value;
            this.countyColors.set(county.id, currentColor);
        }

        this.drawMap();
        this.updateUI();
    }

    clearSelection() {
        this.selectedCounties.clear();
        this.drawMap();
        this.updateUI();
    }

    resetAll() {
        this.selectedCounties.clear();
        this.countyColors.clear();
        this.drawMap();
        this.updateUI();
    }

    updateUI() {
        this.updateSelectedCountiesList();
        this.updateCountyCount();
        this.updateLegend();
    }

    updateSelectedCountiesList() {
        const list = document.getElementById('selectedCounties');
        list.innerHTML = '';

        for (const countyId of this.selectedCounties) {
            const county = Array.from(this.colorToCountyMap.values()).find(c => c.id === countyId);
            if (county) {
                const li = document.createElement('li');
                const customColor = this.countyColors.get(countyId) || '#ffffff';

                li.innerHTML = `
                    <span>County ${county.id}: ${county.label}</span>
                    <div class="county-color-indicator" style="background-color: ${customColor}"></div>
                `;
                list.appendChild(li);
            }
        }
    }

    updateCountyCount() {
        const count = this.selectedCounties.size;
        document.getElementById('countyCount').textContent =
            `${count} county${count !== 1 ? 'ies' : ''} selected`;
    }

    renderLegend() {
        const legendContent = document.getElementById('legendContent');
        legendContent.innerHTML = '';

        // Only show counties that have been colored
        const coloredCounties = [];
        for (const [color, county] of this.colorToCountyMap) {
            if (this.countyColors.has(county.id)) {
                coloredCounties.push([color, county]);
            }
        }

        // If no counties are colored, show a message
        if (coloredCounties.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'empty-legend';
            emptyMessage.textContent = 'No counties colored yet. Click on the map to select and color counties.';
            emptyMessage.style.cssText = 'text-align: center; padding: 20px; color: #7f8c8d; font-style: italic;';
            legendContent.appendChild(emptyMessage);
            return;
        }

        // Show only colored counties
        for (const [color, county] of coloredCounties) {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.dataset.countyId = county.id;

            const customColor = this.countyColors.get(county.id);

            item.innerHTML = `
                <div class="legend-color" style="background-color: ${customColor}; border: 2px solid #000;"></div>
                <span class="legend-label">County ${county.id}: ${county.label}</span>
            `;

            item.addEventListener('click', () => {
                this.toggleCountySelection(county);
            });

            legendContent.appendChild(item);
        }
    }

    updateLegend() {
        // Re-render the entire legend since we only show colored counties
        this.renderLegend();

        // Update selection indicators
        const legendItems = document.querySelectorAll('.legend-item');
        legendItems.forEach(item => {
            const countyId = parseInt(item.dataset.countyId);

            if (this.selectedCounties.has(countyId)) {
                item.classList.add('selected-county');
            } else {
                item.classList.remove('selected-county');
            }
        });
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    showLoading() {
        const mapContainer = document.querySelector('.map-container');
        let loading = mapContainer.querySelector('.loading');
        if (!loading) {
            loading = document.createElement('div');
            loading.className = 'loading';
            loading.innerHTML = '🗺️ Loading map...';
            mapContainer.appendChild(loading);
        }
        this.canvas.style.display = 'none';
    }

    hideLoading() {
        const loading = document.querySelector('.loading');
        if (loading) {
            loading.remove();
        }
        this.canvas.style.display = 'block';
    }

    showTooltip(e, text) {
        this.tooltip.textContent = text;
        this.tooltip.style.left = e.pageX + 10 + 'px';
        this.tooltip.style.top = e.pageY - 10 + 'px';
        this.tooltip.style.opacity = '1';
    }

    hideTooltip() {
        this.tooltip.style.opacity = '0';
    }

    showError(message) {
        const container = document.querySelector('.container');
        const existingError = container.querySelector('.error');
        if (existingError) {
            existingError.remove();
        }

        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = message;
        container.insertBefore(errorDiv, container.firstChild);

        // Auto-remove error after 10 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 10000);
    }
}

// Initialize the map when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new InteractiveMap();
});

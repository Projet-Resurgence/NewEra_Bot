# 🗺️ Interactive County Map

A high-performance web interface for colorable county maps with multi-map support.

## ✨ Features

- 🎨 **Interactive County Coloring**: Click counties to paint them with your chosen colors
- 🗺️ **Multi-Map Support**: Automatically discovers and supports multiple map configurations
- � **Individual Color Memory**: Each county maintains its color independently
- � **Responsive Design**: Works on desktop and mobile devices
- �️ **Clean UI**: White backgrounds with black borders for clear visualization
- 📊 **Dynamic Legend**: Shows only colored counties with their names

## � Quick Start

### Development Mode
```bash
# Simple development server
python3 server.py

# Or use the development script
./start-dev.sh
```

### Production Mode
```bash
# Install dependencies
pip3 install -r requirements.txt

# Start production server
./start-production.sh

# Or manually with Gunicorn
gunicorn -c gunicorn.conf.py wsgi:application
```

## 📦 Installation

1. **Clone or download** the project files
2. **Install Python dependencies** (optional for development):
   ```bash
   pip3 install -r requirements.txt
   ```
3. **Add your maps** to the `maps_images/` directory
4. **Create configuration files** for each map
5. **Start the server** using one of the methods above

## 🗂️ File Structure

```
mapping-library/
├── index.html              # Main web interface
├── script.js               # Interactive map logic
├── styles.css              # Responsive styling
├── server.py               # Enhanced development server
├── wsgi.py                 # WSGI application for production
├── gunicorn.conf.py        # Gunicorn configuration
├── requirements.txt        # Python dependencies
├── start-dev.sh           # Development startup script
├── start-production.sh    # Production startup script
├── maps_images/           # Map image files
│   └── map_countries.png  # Example map
└── map_countries_config.txt # Example map configuration
```

## 🗺️ Adding New Maps

1. **Add your map image** to `maps_images/` with the naming pattern `map_<name>.png`
2. **Create a configuration file** named `map_<name>_config.txt` with county definitions:

```json
{
  "counties": {
    "#FF0000": {
      "id": "county1",
      "name": "County Name 1"
    },
    "#00FF00": {
      "id": "county2", 
      "name": "County Name 2"
    }
  }
}
```

The system will automatically discover and load your new maps!

### Visual Design
- **White Background**: All areas start as clean white/virgin land
- **Black Borders**: Thin black lines clearly define county boundaries
- **Custom Coloring**: Selected areas can be painted with any chosen color
- **Clean Interface**: Focus on the map content without visual clutter

### Multiple Map Support
- **Automatic Discovery**: System automatically finds available maps
- **Naming Convention**: Maps follow the pattern `map_*.png` with `map_*_config.txt`
- **Easy Extension**: Add new maps by following the naming pattern
- **Seamless Switching**: Change between maps without page reload

### County Detection
- Each region filled with a specific color (like `#d90104`) represents one county
- Counties are automatically assigned incremental IDs (County 1, County 2, etc.)
- Mouse hover shows county information
- Click to select/deselect counties

### Color System
- Original map colors define county boundaries
- Selected counties can be recolored with custom colors
- The color picker allows you to choose any color
- Changes are applied to all selected counties at once

## Quick Start

1. **Start the Server**:
   ```bash
   python3 server.py
   ```

2. **Open Your Browser**:
   Navigate to `http://localhost:8000`

3. **Interact with the Map**:
   - Select a map from the dropdown (Countries Map, Regions Map, etc.)
   - Click on counties to select them (they remain white until colored)
   - Choose a color from the color picker
   - Selected counties will be painted with the chosen color
   - Use the legend to see all available counties

## Controls

### Map Selection
- **Map Dropdown**: Choose between available maps (countries, regions, etc.)
- **Auto-Discovery**: System automatically finds maps following the naming pattern

### Color Controls
- **Color Picker**: Select the color to apply to selected counties
- **Clear Selection**: Deselect all currently selected counties
- **Reset All**: Clear all selections and restore original colors

### Selection Info
- **Selected Counties List**: Shows currently selected counties with their colors
- **County Count**: Displays the number of selected counties

### Legend
- **Interactive Legend**: Click on legend items to select/deselect counties
- **Visual Indicators**: Shows current colors for each county
- **Auto-updating**: Reflects changes in real-time

## File Structure

```
mapping-library/
├── index.html              # Main HTML interface
├── styles.css              # Styling and responsive design
├── script.js               # JavaScript functionality
├── server.py               # Local development server
├── map_countries_config.txt # Countries configuration data
├── map_regions_config.txt   # Regions configuration data (example)
├── maps_images/
│   ├── map_countries.png   # Countries map image
│   └── map_regions.png     # Regions map image (example)
└── README.md              # This file
```

## Adding New Maps

To add a new map, simply follow the naming convention:

1. **Add Image**: Place your map image as `maps_images/map_[name].png`
2. **Add Config**: Create a configuration file as `map_[name]_config.txt`
3. **Restart**: Refresh the page to see the new map in the dropdown

**Example for a "districts" map:**
- Image: `maps_images/map_districts.png`
- Config: `map_districts_config.txt`
- Will appear as: "Districts Map" in the dropdown

## Configuration Format

The `map_countries_config.txt` follows this structure:

```json
{
  "groups": {
    "#d90104": {
      "label": "American Samoa",
      "paths": ["Western_AS", "Eastern_AS", ...]
    },
    "#addfb9": {
      "label": "Afghanistan", 
      "paths": ["Badakhshan_AF", "Takhar_AF", ...]
    }
  }
}
```

- **Color keys** (like `#d90104`): Hex colors that identify county regions
- **Labels**: Human-readable names for counties
- **Paths**: Internal region identifiers (currently for display in config)

## Browser Compatibility

- ✅ Chrome/Chromium 60+
- ✅ Firefox 55+
- ✅ Safari 12+
- ✅ Edge 79+

## Troubleshooting

### Map Not Loading
- Ensure `maps_images/map_countries.png` exists
- Check browser console for errors
- Verify the server is running

### Counties Not Clickable
- Confirm `map_countries_config.txt` is properly formatted JSON
- Check that colors in the config match colors in the image exactly
- Use developer tools to inspect pixel colors

### Server Issues
- Default port is 8000; the script will try alternatives if busy
- Make sure Python 3 is installed
- Check firewall settings if accessing from other devices

## Future Enhancements

As mentioned, county names will be changed from auto-increment IDs to more meaningful names in future versions. The current system provides a solid foundation that can be easily extended with:

- Custom county naming
- Data import/export
- Statistical analysis
- Advanced coloring schemes
- Multiple map support

## Development

The interface is built with vanilla HTML/CSS/JavaScript for maximum compatibility and easy customization. The modular design allows for easy extension and modification.

### Key Components

- **InteractiveMap class**: Main application logic
- **Canvas-based rendering**: Direct pixel manipulation for fast county detection
- **Event-driven architecture**: Responsive to user interactions
- **Color mapping system**: Efficient county identification and recoloring

## ⚡ Performance Features

### Development Server (`server.py`)
- 🧵 **Multi-threaded**: Handles multiple requests concurrently
- 🔒 **Security**: Path traversal protection
- 📝 **Enhanced Logging**: Timestamped request logs
- 🌐 **CORS Support**: Full cross-origin resource sharing
- 🔄 **Auto Port Detection**: Tries alternative ports if main port is busy

### Production Server (`wsgi.py` + Gunicorn)
- 🚀 **WSGI Compatible**: Works with any WSGI server
- 👥 **Multi-worker**: Scales with CPU cores
- 🔄 **Auto-restart**: Workers restart after handling requests
- 📊 **Performance Monitoring**: Request timing and logging
- 🛡️ **Production Ready**: Proper error handling and security

## 🔧 Server Options

### Development
```bash
python3 server.py           # Basic multi-threaded server on port 8000
```

### Production with Gunicorn
```bash
# Basic production server
gunicorn wsgi:application

# High-performance configuration
gunicorn --bind 0.0.0.0:8000 --workers 4 --worker-class sync wsgi:application

# With configuration file
gunicorn -c gunicorn.conf.py wsgi:application

# Advanced with gevent workers (install gevent first)
gunicorn --worker-class gevent --workers 1 --worker-connections 1000 wsgi:application
```

### Custom Configuration
Edit `gunicorn.conf.py` to customize:
- Worker count and type
- Binding address and port
- Logging configuration
- Performance tuning
- SSL/HTTPS settings

## 📈 Performance Tips

1. **Use Gunicorn for production** - Much faster than development server
2. **Tune worker count** - Start with `(CPU cores × 2) + 1`
3. **Enable preloading** - Reduces memory usage with multiple workers
4. **Use reverse proxy** - Nginx or Apache in front of Gunicorn
5. **Enable gzip compression** - At reverse proxy level

## 🔍 Monitoring

### Server Status
```bash
# Check if server is running
curl -I http://localhost:8000

# Check server response time
time curl http://localhost:8000
```

### Gunicorn Process Management
```bash
# Reload workers gracefully
kill -HUP $(pgrep -f "gunicorn.*wsgi:application")

# Stop server gracefully
kill -TERM $(pgrep -f "gunicorn.*wsgi:application")
```

## 🛠️ Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)
```

**Maps Not Loading**
- Check file naming: `map_<name>.png` and `map_<name>_config.txt`
- Verify JSON syntax in config files
- Check browser console for errors

**Performance Issues**
- Increase Gunicorn workers: `--workers 8`
- Use gevent workers: `--worker-class gevent`
- Add reverse proxy with caching

## 🔗 URLs

- **Development**: http://localhost:8000
- **Production**: Configurable (default: http://localhost:8000)
- **Health Check**: GET / (returns main interface)

## 📄 License

This project is provided as-is for educational and development purposes.

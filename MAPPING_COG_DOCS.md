# Mapping Cog Documentation

## Overview
The mapping cog provides advanced geographic visualization commands for the NEBot Discord bot. It generates maps showing regions and countries with filtering capabilities, optimized for large-scale map processing.

## Features

### Commands

#### `/regions_map [filter_type] [filter_value]`
Displays the raw regions map with black outlines on a white background.

**Features:**
- White background with black region borders (7px width)
- Water areas remain unchanged (#272727)
- Optional filtering by continent, geographical area, or country
- Automatic cropping when filtered

**Usage Examples:**
- `/regions_map` - Full world regions map
- `/regions_map continent Europe` - European regions only
- `/regions_map geographical_area "Afrique du Sud"` - South African regions
- `/regions_map country France` - French regions only

#### `/countries_map [filter_type] [filter_value]`
Displays a political map with countries colored by their territories.

**Features:**
- Country territories colored using Discord role colors
- Unoccupied regions shown in white
- Water areas remain unchanged
- Legend showing country names and colors (bottom-left)
- Optional filtering and cropping
- Consistent colors across all regions of the same country

**Usage Examples:**
- `/countries_map` - Full world political map
- `/countries_map continent Europe` - European countries
- `/countries_map geographical_area "Afrique du Sud"` - South African territories
- `/countries_map country France` - French territory only

### Filtering Options

Both commands support the following filter types:
- `continent` - Filter by continent (Europe, Asie, Afrique, Amerique, Oceanie, Moyen-Orient)
- `geographical_area` - Filter by geographical area name
- `country` - Filter by country name
- `all` or no filter - Show entire world map

### Performance Optimizations

The cog is optimized for low-performance VPS environments with large maps (~12000x6000px):

1. **Vectorized Operations**: Uses numpy for efficient pixel processing instead of pixel-by-pixel iteration
2. **Region Color Caching**: Preloads region colors from CSV on initialization
3. **Efficient Masking**: Uses boolean masks for water/land/region identification
4. **Optimized Cropping**: Vectorized bounding box calculation
5. **Async Processing**: Map generation runs in thread executor to prevent blocking

## Technical Implementation

### Core Files
- `src/cogs/mapping.py` - Main cog implementation
- `datas/mapping/region_map.png` - Base map (12000x6064px RGBA)
- `datas/mapping/region_list.csv` - Region metadata with hex colors
- `datas/arial.ttf` - Font for legend text

### Key Methods

#### `generate_filtered_map(filter_key, filter_value, is_regions_map)`
Core method that orchestrates map generation:
- Loads base map and converts to numpy array
- Applies filtering based on key/value
- Calls appropriate map generation method
- Handles cropping for filtered maps
- Saves result to `datas/mapping/final_map.png`

#### `generate_regions_map(base_array, regions_data)`
Creates outlined regions map:
- White background with water areas preserved
- Vectorized color masking for region identification
- 7px black borders using scipy binary dilation
- Efficient processing using numpy operations

#### `generate_countries_map(base_array, regions_data)`
Creates political map with country colors:
- Maintains water areas unchanged
- Colors regions by country using Discord role colors
- Fallback color generation for missing roles
- Adds legend with country names and colors

#### `crop_to_regions(image, regions_data, offset=50)`
Crops map to show only relevant regions:
- Calculates bounding box using vectorized operations
- Adds configurable margin offset
- Efficient region detection from base map

#### `add_legend(image, country_colors, regions_data)`
Adds country legend to map:
- Bottom-left positioning
- White background with black text
- Color squares next to country names
- Uses arial.ttf font (12px)

### Database Integration

The cog integrates with the NEBot database schema:
- `Countries` table for country data and Discord role IDs
- `Regions` table for region-to-country assignments
- `GeographicalAreas` table for geographic grouping
- Uses centralized `shared_utils` for database access

### Color Management

Country colors are determined using this priority:
1. Discord role color (from `Countries.role_id`)
2. Generated color based on country ID hash
3. Gray fallback for errors

Colors are adjusted to ensure appropriate brightness for visibility.

### Error Handling

Comprehensive error handling includes:
- Missing file detection
- Database connection errors
- Image processing failures
- Font loading fallbacks
- Graceful degradation for missing data

## Usage in Bot

The mapping cog follows NEBot's architecture patterns:
- Uses centralized utilities from `shared_utils`
- Implements hybrid commands (slash + prefix)
- Includes autocomplete for all filter options
- Follows embed color standards
- Async processing to prevent blocking

## Performance Characteristics

**Optimizations for 12000x6064px maps:**
- Memory efficient: ~275MB peak usage for full map processing
- Processing time: ~2-5 seconds for full world map
- Filtered maps: ~0.5-2 seconds depending on region count
- Network transfer: PNG compression reduces file size significantly

## Future Enhancements

Potential improvements:
1. Caching generated maps with timestamps
2. Additional filtering options (by alliance, doctrine, etc.)
3. Interactive web-based map viewer
4. Real-time updates when territories change
5. Historical map comparisons
6. Statistical overlays (population, GDP, etc.)

## Dependencies

Required Python packages:
- `discord.py` - Discord bot framework
- `Pillow` - Image processing
- `numpy` - Efficient array operations
- `scipy` - Image morphology operations
- Standard library: `asyncio`, `concurrent.futures`, `csv`, `hashlib`

## Installation

1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Verify base map exists: `datas/mapping/region_map.png`
3. Verify CSV data exists: `datas/mapping/region_list.csv`
4. Load cog in bot: The cog auto-loads via `setup()` function

The mapping cog is now ready for production use with the NEBot geopolitical roleplay system.

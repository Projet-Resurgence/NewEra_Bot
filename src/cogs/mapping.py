import discord
from discord.ext import commands
from discord import app_commands
from shared_utils import get_db, get_discord_utils, ERROR_COLOR_INT, ALL_COLOR_INT
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import Optional, Dict, Tuple, List
import os
import asyncio
import concurrent.futures
import json
import time
import hashlib
import csv
import pytz
import uuid
import gc
import traceback
from datetime import datetime, timedelta
from scipy.ndimage import binary_dilation
from skimage.segmentation import find_boundaries
from asyncdb import AsyncDatabase

CROPPING_OFFSET = 10
BORDERS_SIZE = 3


class MappingCog(commands.Cog):
    """Geographic mapping and visualization commands with optimized preprocessing."""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)
        self.async_db = AsyncDatabase()
        self.region_colors_cache = {}
        self.region_masks_cache = {}
        self._load_region_colors()
        self.country_colors = {}
        
        # Thread pool executor for CPU-intensive tasks
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, 
            thread_name_prefix="mapping_thread"
        )
        
        try:
            print("[MappingCog] Loading base image...")
            self.base_img = Image.open("datas/mapping/region_map.png").convert("RGBA")
            print(f"[MappingCog] Base image loaded: {self.base_img.size}")
            
            print("[MappingCog] Converting to NumPy array...")
            self.base_array = np.array(self.base_img)
            print(f"[MappingCog] Base array created: {self.base_array.shape}, dtype: {self.base_array.dtype}")
            
            # Estimate memory usage
            memory_mb = (self.base_array.nbytes / (1024 * 1024))
            print(f"[MappingCog] Base array memory usage: {memory_mb:.2f} MB")
            
            if memory_mb > 500:  # Warning if base image is larger than 500MB
                print(f"[MappingCog] ⚠️ WARNING: Large base image detected ({memory_mb:.2f} MB)")
                print("[MappingCog] Consider reducing image size to prevent memory issues")
                
        except Exception as e:
            print(f"[MappingCog] ❌ Error loading base image: {e}")
            # Create a minimal fallback array to prevent crashes
            self.base_img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
            self.base_array = np.array(self.base_img)
            print("[MappingCog] Created fallback base image")

    def cog_unload(self):
        """Clean up resources when the cog is unloaded."""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
                print("[MappingCog] Thread pool executor shut down")
        except Exception as e:
            print(f"[MappingCog] Error during cleanup: {e}")

    def _load_region_colors(self):
        """Load region colors from CSV for optimization."""
        try:
            csv_path = "datas/mapping/region_list.csv"
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hex_color = row["Code couleur HEX"].strip()
                    # Convert hex to RGB tuple
                    if not hex_color.startswith("#"):
                        hex_color = "#" + hex_color
                    rgb = self.hex_to_rgb(hex_color)

                    self.region_colors_cache[rgb] = {
                        "country": row["Pays/Region"],
                        "continent": row["Continent"],
                        "name": row["Nom region"],
                        "hex": hex_color,
                    }
        except Exception as e:
            print(f"Error loading region colors: {e}")

    def _find_region_mask_threaded(self, local_base_array: np.ndarray, region_rgb: tuple) -> np.ndarray:
        """Thread-safe function to find region mask using np.all()."""
        region_color_array = np.array(region_rgb)
        return np.all(local_base_array[:, :, :3] == region_color_array, axis=2)

    def _create_water_mask_threaded(self, local_base_array: np.ndarray) -> np.ndarray:
        """Thread-safe function to create water mask."""
        water_color = np.array([39, 39, 39])
        return (np.all(local_base_array[:, :, :3] == water_color, axis=2)) | (local_base_array[:, :, 3] == 0)

    def _build_label_map_threaded(self, local_base_array: np.ndarray, relevant_colors: list) -> np.ndarray:
        """Thread-safe function to build label map for boundary detection."""
        height, width = local_base_array.shape[:2]
        label_map = np.zeros((height, width), dtype=np.int32)
        for idx, color in enumerate(relevant_colors, start=1):
            mask = np.all(local_base_array[:, :, :3] == np.array(color), axis=2)
            label_map[mask] = idx
        return label_map

    def _colorize_region_threaded(self, local_base_array: np.ndarray, result_array: np.ndarray, 
                                  region_rgb: tuple, country_color: tuple) -> int:
        """Thread-safe function to colorize a single region."""
        region_color_array = np.array(region_rgb)
        region_mask = np.all(local_base_array[:, :, :3] == region_color_array, axis=2)
        pixel_count = np.sum(region_mask)
        if pixel_count > 0:
            result_array[region_mask, :3] = country_color
        return pixel_count

    def _crop_calculation_threaded(self, local_base_array: np.ndarray, relevant_colors: list) -> tuple:
        """Thread-safe function to calculate crop boundaries."""
        height, width = local_base_array.shape[:2]
        region_mask = np.zeros((height, width), dtype=bool)
        
        for color in relevant_colors:
            color_mask = np.all(local_base_array[:, :, :3] == np.array(color), axis=2)
            region_mask |= color_mask
        
        if not np.any(region_mask):
            return None
        
        y_coords, x_coords = np.where(region_mask)
        return (x_coords.min(), x_coords.max(), y_coords.min(), y_coords.max())

    async def generate_filtered_map_async(
        self,
        filter_key: str,
        filter_value: Optional[str] = None,
        is_regions_map: bool = False,
    ) -> str:
        """Async wrapper for generate_filtered_map to prevent blocking."""
        # Use async database operations to avoid cursor conflicts
        return await self._generate_filtered_map_async_safe(filter_key, filter_value, is_regions_map)

    async def _generate_filtered_map_async_safe(
        self,
        filter_key: str,
        filter_value: Optional[str] = None,
        is_regions_map: bool = False,
    ) -> str:
        """Fully async map generation to avoid database cursor conflicts."""
        local_base_array = None
        local_base_img = None
        result_img = None
        
        try:
            thread_id = str(uuid.uuid4())[:8]
            
            print(f"[Mapping-{thread_id}] Starting async map generation for {filter_key}={filter_value}")
            
            # Make a copy of the base array for this thread with explicit memory management
            try:
                local_base_array = self.base_array.copy()
                print(f"[Mapping-{thread_id}] Created local base array copy")
            except MemoryError as e:
                print(f"[Mapping-{thread_id}] Memory error copying base array: {e}")
                gc.collect()
                return ""
            
            # Create a local base image for this thread
            local_base_img = Image.fromarray(local_base_array)
            
            # Get regions data for filtering using ASYNC database to avoid cursor conflicts
            country_colors = {}
            try:
                regions_data = await self.async_db.get_regions_data_async(filter_key, filter_value)
                print(f"[Mapping-{thread_id}] Retrieved {len(regions_data)} regions via async database")
            except Exception as e:
                print(f"[Mapping-{thread_id}] Error getting regions data via async DB: {e}")
                return ""
                
            if regions_data == [] and filter_key != "All":
                print(f"[Mapping-{thread_id}] No regions data available for mapping.")
                return ""

            if is_regions_map:
                # For regions map: outline regions with black borders on white background
                result_img = await self._generate_regions_map_local(regions_data, local_base_array)
            else:
                # For countries map: colorize by country and add legend
                result_img = await self._generate_countries_map_local(regions_data, local_base_array, country_colors, is_all=(filter_key == "All"))
                if result_img is None:
                    print(f"[Mapping-{thread_id}] No regions data available for mapping.")
                    return ""

            # Crop if not showing all
            if filter_key != "All" and filter_value:
                result_img = await self._crop_to_regions_local(result_img, regions_data, local_base_array)

            if not is_regions_map:
                result_img = await self._add_legend_local(result_img, regions_data, country_colors)

            # Save result with unique filename to avoid conflicts
            timestamp = int(time.time() * 1000)
            output_path = f"datas/mapping/final_map_{thread_id}_{timestamp}.png"
            result_img.save(output_path)
            
            print(f"[Mapping-{thread_id}] Completed async map generation, saved to {output_path}")
            return output_path

        except Exception as e:
            print(f"[Mapping-{thread_id}] Error generating map: {e}")
            traceback.print_exc()
            return ""
        
        finally:
            # Explicit cleanup to prevent memory leaks
            try:
                if local_base_array is not None:
                    del local_base_array
                if local_base_img is not None:
                    del local_base_img  
                if result_img is not None:
                    del result_img
                gc.collect()
                print(f"[Mapping-{thread_id}] Memory cleanup completed")
            except Exception as cleanup_error:
                print(f"[Mapping-{thread_id}] Error during cleanup: {cleanup_error}")

    async def _generate_regions_map_local(self, regions_data: List[dict], local_base_array: np.ndarray) -> Image.Image:
        """Generate a white map with black region outlines using local array copy with threading."""
        print("[Mapping] Starting _generate_regions_map_local...", flush=True)
        height, width = local_base_array.shape[:2]
        result_array = np.ones((height, width, 3), dtype=np.uint8) * 255  # white background

        # Create water mask using thread executor
        loop = asyncio.get_event_loop()
        water_mask = await loop.run_in_executor(
            self.executor,
            self._create_water_mask_threaded,
            local_base_array
        )
        
        # Apply water color
        water_color = np.array([39, 39, 39])
        result_array[water_mask] = water_color
        print("[Mapping] Water mask applied.", flush=True)

        # Determine relevant colors
        if not regions_data:
            relevant_colors = list(self.region_colors_cache.keys())
            print(f"[Mapping] No filter: {len(relevant_colors)} regions from CSV.", flush=True)
        else:
            relevant_colors = []
            for region in regions_data:
                hex_color = region.get("region_color_hex", "")
                if hex_color:
                    if not hex_color.startswith("#"):
                        hex_color = "#" + hex_color
                    relevant_colors.append(self.hex_to_rgb(hex_color))
            print(f"[Mapping] Filter: {len(relevant_colors)} regions from DB.", flush=True)

        if relevant_colors:
            # Build label map using thread executor
            label_map = await loop.run_in_executor(
                self.executor,
                self._build_label_map_threaded,
                local_base_array,
                relevant_colors
            )

            # Extract boundaries using thread executor
            border_mask = await loop.run_in_executor(
                self.executor,
                find_boundaries,
                label_map,
                "outer"
            )

            # Apply borders in black
            result_array[border_mask] = [0, 0, 0]
            print(f"[Mapping] Applied {np.sum(border_mask)} border pixels.", flush=True)

        print("[Mapping] Finished _generate_regions_map_local.", flush=True)
        return Image.fromarray(result_array)

    async def _generate_countries_map_local(self, regions_data: List[dict], local_base_array: np.ndarray, 
                                     country_colors: dict, is_all: bool) -> Image.Image:
        """Generate a map colored by countries using local array copy with proper threading."""
        print("[Mapping] Starting _generate_countries_map_local...", flush=True)
        height, width = local_base_array.shape[:2]
        result_array = local_base_array.copy()

        unoccupied_color = np.array([255, 255, 255])  # White for unoccupied

        # If no regions_data (All filter), we need to get all regions from database
        if is_all:
            print("[Mapping] No regions data provided, querying all regions from database...", flush=True)
            regions_data = await self.get_all_regions_async()
            print(f"[Mapping] Retrieved {len(regions_data)} regions from database", flush=True)

        if not regions_data:
            print("[Mapping] No regions data available for mapping.", flush=True)
            return Image.new("RGB", (width, height), color=(255, 255, 255))

        # Build country color mapping and region-to-country mapping
        region_to_country = {}
        countries_in_map = set()

        # First pass: collect all countries and their colors
        for idx, region in enumerate(regions_data):
            country_id = region.get("country_id")
            if country_id:
                countries_in_map.add(country_id)
                if country_id not in country_colors:
                    country_colors[country_id] = await self.get_country_color(country_id)
                    print(f"[Mapping] Country {country_id} gets color {country_colors[country_id]}")
            
            # Yield control every 20 regions to prevent blocking
            if idx % 20 == 0:
                await asyncio.sleep(0)

        print(f"[Mapping] Found {len(country_colors)} countries with colors")

        # Second pass: map each region to its country
        for idx, region in enumerate(regions_data):
            hex_color = region.get("region_color_hex", "")
            if hex_color:
                if not hex_color.startswith("#"):
                    hex_color = "#" + hex_color
                region_rgb = self.hex_to_rgb(hex_color)
                country_id = region.get("country_id")
                region_to_country[region_rgb] = country_id

            # Yield control every 20 regions
            if idx % 20 == 0:
                await asyncio.sleep(0)
                print(f"[Mapping] Mapped {idx+1}/{len(regions_data)} regions...", flush=True)

        print(f"[Mapping] Mapped {len(region_to_country)} regions to countries")

        # Create water mask using thread executor
        print("[Mapping] Creating water mask...")
        loop = asyncio.get_event_loop()
        water_mask = await loop.run_in_executor(
            self.executor, 
            self._create_water_mask_threaded, 
            local_base_array
        )

        # Process regions in parallel chunks using thread executor
        total_regions = len(region_to_country)
        chunk_size = 10  # Process 10 regions at a time
        region_items = list(region_to_country.items())
        
        print(f"[Mapping] Processing {total_regions} regions in chunks of {chunk_size}...")
        
        # Create tasks for each chunk
        chunk_tasks = []
        for chunk_start in range(0, total_regions, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_regions)
            chunk_items = region_items[chunk_start:chunk_end]
            
            # Process each chunk in executor
            task = loop.run_in_executor(
                self.executor,
                self._process_region_chunk_threaded,
                local_base_array,
                result_array,
                chunk_items,
                country_colors,
                unoccupied_color
            )
            chunk_tasks.append(task)
        
        # Wait for all chunks to complete
        chunk_results = await asyncio.gather(*chunk_tasks)
        total_pixels_processed = sum(chunk_results)
        print(f"[Mapping] Processed {total_pixels_processed} total pixels across all regions")

        # Handle any remaining non-water areas as unoccupied using executor
        print("[Mapping] Processing unoccupied areas...")
        await loop.run_in_executor(
            self.executor,
            self._process_unoccupied_areas_threaded,
            local_base_array,
            result_array,
            water_mask,
            list(region_to_country.keys()),
            unoccupied_color
        )

        # Convert back to PIL Image
        result_img = Image.fromarray(result_array)
        print("[Mapping] Finished _generate_countries_map_local.", flush=True)
        return result_img

    def _process_region_chunk_threaded(self, local_base_array: np.ndarray, result_array: np.ndarray,
                                     chunk_items: list, country_colors: dict, unoccupied_color: np.ndarray) -> int:
        """Thread-safe function to process a chunk of regions."""
        total_pixels = 0
        for region_rgb, country_id in chunk_items:
            pixel_count = self._colorize_region_threaded(
                local_base_array, 
                result_array, 
                region_rgb, 
                country_colors.get(country_id, unoccupied_color)
            )
            total_pixels += pixel_count
        return total_pixels

    def _process_unoccupied_areas_threaded(self, local_base_array: np.ndarray, result_array: np.ndarray,
                                         water_mask: np.ndarray, region_rgbs: list, unoccupied_color: np.ndarray):
        """Thread-safe function to process unoccupied areas."""
        height, width = local_base_array.shape[:2]
        non_water_mask = ~water_mask
        processed_mask = np.zeros((height, width), dtype=bool)

        # Build processed mask from all regions
        for region_rgb in region_rgbs:
            region_color_array = np.array(region_rgb)
            region_mask = np.all(local_base_array[:, :, :3] == region_color_array, axis=2)
            processed_mask |= region_mask

        # Color unprocessed areas
        unprocessed_mask = non_water_mask & ~processed_mask
        unprocessed_count = np.sum(unprocessed_mask)
        if unprocessed_count > 0:
            result_array[unprocessed_mask, :3] = unoccupied_color
            print(f"[Mapping] Set {unprocessed_count} unprocessed pixels to white")

    async def _crop_to_regions_local(self, image: Image.Image, regions_data: List[dict], 
                              local_base_array: np.ndarray, offset: int = 50) -> Image.Image:
        """Crop the image to show only the relevant regions using local array copy with threading."""
        print("[Mapping] Starting _crop_to_regions_local...", flush=True)
        if not regions_data:
            print("[Mapping] No regions data, skipping crop.", flush=True)
            return image

        relevant_colors = []
        for idx, region in enumerate(regions_data):
            hex_color = region.get("region_color_hex", "")
            if hex_color:
                if not hex_color.startswith("#"):
                    hex_color = "#" + hex_color
                rgb = self.hex_to_rgb(hex_color)
                relevant_colors.append(rgb)
            if idx % 20 == 0:
                print(f"[Mapping] Processed {idx+1}/{len(regions_data)} regions for cropping...", flush=True)

        if not relevant_colors:
            print("[Mapping] No relevant colors, skipping crop.", flush=True)
            return image

        # Calculate crop boundaries using thread executor
        loop = asyncio.get_event_loop()
        crop_bounds = await loop.run_in_executor(
            self.executor,
            self._crop_calculation_threaded,
            local_base_array,
            relevant_colors
        )

        if crop_bounds is None:
            print("[Mapping] No region mask found, skipping crop.", flush=True)
            return image

        min_x, max_x, min_y, max_y = crop_bounds
        width, height = local_base_array.shape[1], local_base_array.shape[0]

        min_x = max(0, min_x - offset)
        max_x = min(width, max_x + offset)
        min_y = max(0, min_y - offset)
        max_y = min(height, max_y + offset)

        print(f"[Mapping] Cropping image to box: ({min_x}, {min_y}, {max_x}, {max_y})", flush=True)
        print("[Mapping] Finished _crop_to_regions_local.", flush=True)
        return image.crop((min_x, min_y, max_x, max_y))

    async def _add_legend_local(self, image: Image.Image, regions_data: list, country_colors: dict) -> Image.Image:
        """Add a dynamic legend by extending the canvas on the left side."""
        print("[Mapping] Starting dynamic _add_legend_local...", flush=True)
        try:
            if not regions_data:
                regions_data = await self.get_all_regions_async()
                
            # Collect unique countries
            country_names = {}
            for idx, region in enumerate(regions_data):
                country_id = region.get("country_id")
                country_name = region.get("country_name")
                if country_id and country_name and country_id in country_colors:
                    country_names[country_id] = country_name
                    
                # Yield control every 20 regions to prevent blocking
                if idx % 20 == 0:
                    await asyncio.sleep(0)
                    print(f"[Mapping] Processed {idx+1}/{len(regions_data)} regions for legend...", flush=True)

            if not country_names:
                print("[Mapping] No country names found, skipping legend.", flush=True)
                return image

            # Calculate scale factor based on image size
            image_width, image_height = image.size
            reference_size = 400
            scale_factor = min(image_width, image_height) / reference_size
            scale_factor = max(0.5, min(scale_factor, 2.0))  # Clamp between 0.5x and 2x

            print(
                f"[Mapping] Image size: {image_width}x{image_height}, scale factor: {scale_factor:.2f}",
                flush=True,
            )

            # Calculate dynamic font size based on number of countries
            num_countries = len(country_names)
            if num_countries <= 20:
                base_font_size = 14
            elif num_countries <= 50:
                base_font_size = 12
            elif num_countries <= 100:
                base_font_size = 10
            else:
                base_font_size = 8
                
            font_size = max(6, int(base_font_size * scale_factor))

            try:
                font = ImageFont.truetype("datas/arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Calculate text dimensions for all countries
            draw_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            legend_items = []
            max_text_width = 0

            for country_id, country_name in country_names.items():
                bbox = draw_temp.textbbox((0, 0), country_name, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                max_text_width = max(max_text_width, text_width)
                legend_items.append((country_id, country_name, text_width, text_height))

            # Sort countries alphabetically for consistent display
            legend_items.sort(key=lambda x: x[1])

            # Calculate layout parameters
            color_square_size = max(6, int(10 * scale_factor))
            padding = max(2, int(4 * scale_factor))
            item_height = max(color_square_size, max([item[3] for item in legend_items])) + padding
            
            # Calculate optimal number of columns
            available_height = image_height - (2 * padding)
            max_items_per_column = max(1, available_height // item_height)
            num_columns = max(1, (len(legend_items) + max_items_per_column - 1) // max_items_per_column)
            
            # Limit columns to prevent legend from being too wide
            max_columns = max(1, min(4, num_countries // 10))
            num_columns = min(num_columns, max_columns)
            
            items_per_column = (len(legend_items) + num_columns - 1) // num_columns
            
            print(f"[Mapping] Legend layout: {num_countries} countries, {num_columns} columns, {items_per_column} items per column")

            # Calculate legend dimensions
            column_width = color_square_size + padding + max_text_width + padding
            legend_width = (column_width * num_columns) + padding
            legend_height = min(available_height, items_per_column * item_height + padding)

            # Create extended canvas
            new_width = image_width + legend_width
            new_height = image_height
            extended_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
            
            # Paste original map on the right side
            extended_img.paste(image, (legend_width, 0))
            
            # Draw legend on the left side
            legend_draw = ImageDraw.Draw(extended_img)
            
            # Draw background for legend area
            legend_draw.rectangle([0, 0, legend_width, new_height], fill=(240, 240, 240), outline=(200, 200, 200))
            
            # Draw legend items
            for idx, (country_id, country_name, text_width, text_height) in enumerate(legend_items):
                column = idx // items_per_column
                row = idx % items_per_column
                
                if column >= num_columns:
                    continue
                    
                x_base = column * column_width + padding
                y_pos = row * item_height + padding
                
                # Skip if this would go beyond image bounds
                if y_pos + item_height > legend_height:
                    continue
                
                color = country_colors[country_id]
                
                # Draw color square
                legend_draw.rectangle(
                    [x_base, y_pos, x_base + color_square_size, y_pos + color_square_size],
                    fill=tuple(color),
                    outline=(0, 0, 0)
                )
                
                # Draw country name
                text_x = x_base + color_square_size + padding
                text_y = y_pos + (color_square_size - text_height) // 2
                legend_draw.text(
                    (text_x, text_y),
                    country_name,
                    fill=(0, 0, 0),
                    font=font
                )
                
                if idx % 20 == 0:
                    print(f"[Mapping] Drew legend item {idx+1}/{len(legend_items)}...", flush=True)

            print(f"[Mapping] Dynamic legend created: {legend_width}x{legend_height}, extended canvas: {new_width}x{new_height}")
            print("[Mapping] Finished dynamic _add_legend_local.", flush=True)
            return extended_img

        except Exception as e:
            print(f"Error adding dynamic legend: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return image

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb: tuple) -> str:
        """Convert RGB tuple to hex string."""
        return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

    async def get_country_color(self, country_id: int) -> Tuple[int, int, int]:
        """Get a consistent color for a country based on its Discord role."""
        try:
            country_data = await self.async_db.get_country_datas_async(str(country_id))
            if not country_data:
                return (128, 128, 128)  # Gray fallback

            role_id = country_data.get("role_id")
            if not role_id:
                return (128, 128, 128)  # Gray fallback

            # Try to get the Discord role color
            for guild in self.bot.guilds:
                role = guild.get_role(int(role_id))
                if role and role.color.value != 0:  # Not default color
                    color = role.color
                    print(f"Found color for country {country_id}: {color}")
                    return (color.r, color.g, color.b)

            # Fallback: generate color from country_id
            import hashlib

            hash_obj = hashlib.md5(str(country_id).encode())
            hash_hex = hash_obj.hexdigest()
            r = int(hash_hex[0:2], 16)
            g = int(hash_hex[2:4], 16)
            b = int(hash_hex[4:6], 16)

            # Ensure it's not too dark or too light
            brightness = (r + g + b) / 3
            if brightness < 80:
                r, g, b = min(255, r + 80), min(255, g + 80), min(255, b + 80)
            elif brightness > 200:
                r, g, b = max(0, r - 80), max(0, g - 80), max(0, b - 80)

            return (r, g, b)

        except Exception as e:
            print(f"Error getting country color for {country_id}: {e}")
            return (128, 128, 128)  # Gray fallback
    
    async def get_regions_data_async(
        self, filter_key: str = "All", filter_value: Optional[str] = None
    ) -> list:
        return self.async_db.get_regions_data(filter_key, filter_value)

    def get_regions_data(
        self, filter_key: str = "All", filter_value: Optional[str] = None
    ) -> list:
        """Get regions data with optional filtering."""
        try:
            cursor = self.db.cur

            if filter_key == "All" or not filter_value:
                # For "All" case, we return empty list to trigger CSV-based processing
                # This ensures we get all regions including those not in database
                if filter_key == "All":
                    print(
                        "[Mapping] Filter key is 'All', returning empty list to use CSV colors"
                    )
                    return []

                # If filter_value is None but filter_key is not "All", get all regions
                cursor.execute(
                    """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                """
                )
            elif filter_key == "Continent":
                cursor.execute(
                    """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                    WHERE r.continent = ?
                """,
                    (filter_value,),
                )
            elif filter_key == "GeographicAreas":
                cursor.execute(
                    """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                    WHERE ga.name = ?
                """,
                    (filter_value,),
                )
            elif filter_key == "Countries":
                cursor.execute(
                    """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                    WHERE c.name = ?
                """,
                    (filter_value,),
                )

            result = [dict(row) for row in cursor.fetchall()]
            print(
                f"[Mapping] Database query returned {len(result)} regions for filter {filter_key}={filter_value}"
            )
            return result

        except Exception as e:
            print(f"Error getting regions data: {e}")
            return []

    async def generate_filtered_map(
        self,
        filter_key: str = "All",
        filter_value: Optional[str] = None,
        is_regions_map: bool = False,
    ) -> str:
        """Generate a filtered map based on the key/value and map type."""
        try:
            # Get regions data for filtering
            self.country_colors = {}
            regions_data = await self.async_db.get_regions_data_async(filter_key, filter_value)
            if regions_data == [] and filter_key != "All":
                print("[Mapping] No regions data available for mapping.")
                return ""

            if is_regions_map:
                # For regions map: outline regions with black borders on white background
                result_img = self.generate_regions_map(regions_data)
            else:
                # For countries map: colorize by country and add legend
                result_img = await self.generate_countries_map(regions_data, is_all=(filter_key == "All"))
                if result_img is None:
                    print("[Mapping] No regions data available for mapping.")
                    return ""

            # Crop if not showing all
            if filter_key != "All" and filter_value:
                result_img = self.crop_to_regions(result_img, regions_data)

            if not is_regions_map:
                result_img = await self.add_legend(result_img, regions_data)

            # Save result
            output_path = "datas/mapping/final_map.png"
            result_img.save(output_path)
            return output_path

        except Exception as e:
            print(f"Error generating map: {e}")
            return ""


    def generate_regions_map(self, regions_data: List[dict]) -> Image.Image:
        """Generate a white map with black region outlines (sans overlap)."""
        print("[Mapping] Starting generate_regions_map...", flush=True)
        height, width = self.base_array.shape[:2]
        result_array = np.ones((height, width, 3), dtype=np.uint8) * 255  # fond blanc

        water_color = np.array([39, 39, 39])  # #272727

        # Mask eau (pixels gris foncés ou transparents)
        water_mask = (np.all(self.base_array[:, :, :3] == water_color, axis=2)) | (
            self.base_array[:, :, 3] == 0
        )
        result_array[water_mask] = water_color
        print("[Mapping] Water mask applied.", flush=True)

        # Détermination des couleurs des régions à afficher
        if not regions_data:
            relevant_colors = set(self.region_colors_cache.keys())
            print(f"[Mapping] No filter: {len(relevant_colors)} regions from CSV.", flush=True)
        else:
            relevant_colors = set()
            for region in regions_data:
                hex_color = region.get("region_color_hex", "")
                if hex_color:
                    if not hex_color.startswith("#"):
                        hex_color = "#" + hex_color
                    relevant_colors.add(self.hex_to_rgb(hex_color))
            print(f"[Mapping] Filter: {len(relevant_colors)} regions from DB.", flush=True)

        # Construction d'une carte d'IDs (chaque région = un entier unique)
        label_map = np.zeros((height, width), dtype=np.int32)
        for idx, color in enumerate(relevant_colors, start=1):
            mask = np.all(self.base_array[:, :, :3] == np.array(color), axis=2)
            label_map[mask] = idx

        # Extraction des frontières
        border_mask = find_boundaries(label_map, mode="outer")

        # Application des frontières en noir
        result_array[border_mask] = [0, 0, 0]

        print(f"[Mapping] Applied {np.sum(border_mask)} border pixels.", flush=True)
        print("[Mapping] Finished generate_regions_map.", flush=True)
        return Image.fromarray(result_array)

    async def generate_countries_map(self, regions_data: List[dict], is_all: bool) -> Image.Image:
        """Generate a map colored by countries with legend."""
        print("[Mapping] Starting generate_countries_map...", flush=True)
        height, width = self.base_array.shape[:2]
        result_array = self.base_array.copy()

        water_color = np.array([39, 39, 39])  # #272727
        unoccupied_color = np.array([255, 255, 255])  # White for unoccupied

        # If no regions_data (All filter), we need to get all regions from database
        if is_all:
            print(
                "[Mapping] No regions data provided, querying all regions from database...",
                flush=True,
            )
            regions_data = await self.get_all_regions_async()
            print(
                f"[Mapping] Retrieved {len(regions_data)} regions from database",
                flush=True,
            )

        if not regions_data:
            print("[Mapping] No regions data available for mapping.", flush=True)
            return Image.new("RGB", (width, height), color=(255, 255, 255))

        # Build country color mapping and region-to-country mapping
        region_to_country = {}
        countries_in_map = set()

        # First pass: collect all countries and their colors
        for idx, region in enumerate(regions_data):
            country_id = region.get("country_id")
            if country_id:
                countries_in_map.add(country_id)
                if country_id not in self.country_colors:
                    self.country_colors[country_id] = await self.get_country_color(country_id)
                    print(
                        f"[Mapping] Country {country_id} gets color {self.country_colors[country_id]}"
                    )

        print(f"[Mapping] Found {len(self.country_colors)} countries with colors")

        # Second pass: map each region to its country
        for idx, region in enumerate(regions_data):
            hex_color = region.get("region_color_hex", "")
            if hex_color:
                if not hex_color.startswith("#"):
                    hex_color = "#" + hex_color
                region_rgb = self.hex_to_rgb(hex_color)
                country_id = region.get("country_id")
                region_to_country[region_rgb] = country_id

            if idx % 50 == 0:
                print(
                    f"[Mapping] Mapped {idx+1}/{len(regions_data)} regions...",
                    flush=True,
                )

        print(f"[Mapping] Mapped {len(region_to_country)} regions to countries")

        # Create water mask
        water_mask = (np.all(self.base_array[:, :, :3] == water_color, axis=2)) | (
            self.base_array[:, :, 3] == 0
        )  # Transparent areas

        # Process regions by finding their pixels in the base map and recoloring
        for idx, (region_rgb, country_id) in enumerate(region_to_country.items()):
            region_color_array = np.array(region_rgb)
            # Find pixels that match this region's original color in the BASE map
            region_mask = np.all(
                self.base_array[:, :, :3] == region_color_array, axis=2
            )
            pixel_count = np.sum(region_mask)

            if pixel_count > 0:
                if country_id and country_id in self.country_colors:
                    # Color by country
                    result_array[region_mask, :3] = self.country_colors[country_id]
                    print(
                        f"[Mapping] Colored {pixel_count} pixels for country {country_id}"
                    )
                else:
                    # Unoccupied - white
                    result_array[region_mask, :3] = unoccupied_color
                    print(f"[Mapping] Set {pixel_count} pixels to white (unoccupied)")
            else:
                print(
                    f"[Mapping] Warning: No pixels found for region color {region_rgb}"
                )

            if idx % 20 == 0:
                print(
                    f"[Mapping] Processed {idx+1}/{len(region_to_country)} regions...",
                    flush=True,
                )

        # Handle any remaining non-water areas as unoccupied
        # Find all pixels that are not water and not part of any processed region
        non_water_mask = ~water_mask
        processed_mask = np.zeros((height, width), dtype=bool)

        for region_rgb in region_to_country.keys():
            region_color_array = np.array(region_rgb)
            region_mask = np.all(
                self.base_array[:, :, :3] == region_color_array, axis=2
            )
            processed_mask |= region_mask

        unprocessed_mask = non_water_mask & ~processed_mask
        unprocessed_count = np.sum(unprocessed_mask)
        if unprocessed_count > 0:
            result_array[unprocessed_mask, :3] = unoccupied_color
            print(f"[Mapping] Set {unprocessed_count} unprocessed pixels to white")

        # Convert back to PIL Image
        result_img = Image.fromarray(result_array)

        print("[Mapping] Finished generate_countries_map.", flush=True)
        return result_img

    def crop_to_regions(
        self, image: Image.Image, regions_data: List[dict], offset: int = 50
    ) -> Image.Image:
        """Crop the image to show only the relevant regions with offset margin."""
        print("[Mapping] Starting crop_to_regions...", flush=True)
        if not regions_data:
            print("[Mapping] No regions data, skipping crop.", flush=True)
            return image

        relevant_colors = []
        for idx, region in enumerate(regions_data):
            hex_color = region.get("region_color_hex", "")
            if hex_color:
                if not hex_color.startswith("#"):
                    hex_color = "#" + hex_color
                rgb = self.hex_to_rgb(hex_color)
                relevant_colors.append(np.array(rgb))
            if idx % 20 == 0:
                print(
                    f"[Mapping] Processed {idx+1}/{len(regions_data)} regions for cropping...",
                    flush=True,
                )

        if not relevant_colors:
            print("[Mapping] No relevant colors, skipping crop.", flush=True)
            return image

        height, width = self.base_array.shape[:2]
        region_mask = np.zeros((height, width), dtype=bool)

        for idx, color in enumerate(relevant_colors):
            color_mask = np.all(self.base_array[:, :, :3] == color, axis=2)
            region_mask |= color_mask
            if idx % 10 == 0:
                print(
                    f"[Mapping] Built region mask {idx+1}/{len(relevant_colors)}...",
                    flush=True,
                )

        if not np.any(region_mask):
            print("[Mapping] No region mask found, skipping crop.", flush=True)
            return image

        y_coords, x_coords = np.where(region_mask)

        min_x, max_x = x_coords.min(), x_coords.max()
        min_y, max_y = y_coords.min(), y_coords.max()

        min_x = max(0, min_x - offset)
        max_x = min(width, max_x + offset)
        min_y = max(0, min_y - offset)
        max_y = min(height, max_y + offset)

        print(
            f"[Mapping] Cropping image to box: ({min_x}, {min_y}, {max_x}, {max_y})",
            flush=True,
        )
        print("[Mapping] Finished crop_to_regions.", flush=True)
        return image.crop((min_x, min_y, max_x, max_y))

    def get_all_regions(self):
        try: 
            cursor = self.db.cur
            cursor.execute(
                """
                SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                    r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                    c.name as country_name
                FROM Regions r
                LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                LEFT JOIN Countries c ON r.country_id = c.country_id
            """
            )
            return  [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Mapping] Error fetching regions: {e}", flush=True)
            return []
        
    
    async def get_all_regions_async(self):
        """Get all regions using async database."""
        return await self.async_db.get_all_regions_async()


    async def add_legend(self, image: Image.Image, regions_data: list) -> Image.Image:
        """Add a dynamic legend by extending the canvas on the left side."""
        print("[Mapping] Starting dynamic add_legend...", flush=True)
        try:
            if not regions_data:
                regions_data = await self.get_all_regions_async()
                
            # Collect unique countries
            country_names = {}
            for idx, region in enumerate(regions_data):
                country_id = region.get("country_id")
                country_name = region.get("country_name")
                if country_id and country_name and country_id in self.country_colors:
                    country_names[country_id] = country_name
                if idx % 20 == 0:
                    print(
                        f"[Mapping] Processed {idx+1}/{len(regions_data)} regions for legend...",
                        flush=True,
                    )

            if not country_names:
                print("[Mapping] No country names found, skipping legend.", flush=True)
                return image

            # Calculate scale factor based on image size
            image_width, image_height = image.size
            reference_size = 400
            scale_factor = min(image_width, image_height) / reference_size
            scale_factor = max(0.5, min(scale_factor, 2.0))  # Clamp between 0.5x and 2x

            print(
                f"[Mapping] Image size: {image_width}x{image_height}, scale factor: {scale_factor:.2f}",
                flush=True,
            )

            # Calculate dynamic font size based on number of countries
            num_countries = len(country_names)
            if num_countries <= 20:
                base_font_size = 14
            elif num_countries <= 50:
                base_font_size = 12
            elif num_countries <= 100:
                base_font_size = 10
            else:
                base_font_size = 8
                
            font_size = max(6, int(base_font_size * scale_factor))

            try:
                font = ImageFont.truetype("datas/arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Calculate text dimensions for all countries
            draw_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            legend_items = []
            max_text_width = 0

            for country_id, country_name in country_names.items():
                bbox = draw_temp.textbbox((0, 0), country_name, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                max_text_width = max(max_text_width, text_width)
                legend_items.append((country_id, country_name, text_width, text_height))

            # Sort countries alphabetically for consistent display
            legend_items.sort(key=lambda x: x[1])

            # Calculate layout parameters
            color_square_size = max(6, int(10 * scale_factor))
            padding = max(2, int(4 * scale_factor))
            item_height = max(color_square_size, max([item[3] for item in legend_items])) + padding
            
            # Calculate optimal number of columns
            available_height = image_height - (2 * padding)
            max_items_per_column = max(1, available_height // item_height)
            num_columns = max(1, (len(legend_items) + max_items_per_column - 1) // max_items_per_column)
            
            # Limit columns to prevent legend from being too wide
            max_columns = max(1, min(4, num_countries // 10))
            num_columns = min(num_columns, max_columns)
            
            items_per_column = (len(legend_items) + num_columns - 1) // num_columns
            
            print(f"[Mapping] Legend layout: {num_countries} countries, {num_columns} columns, {items_per_column} items per column")

            # Calculate legend dimensions
            column_width = color_square_size + padding + max_text_width + padding
            legend_width = (column_width * num_columns) + padding
            legend_height = min(available_height, items_per_column * item_height + padding)

            # Create extended canvas
            new_width = image_width + legend_width
            new_height = image_height
            extended_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
            
            # Paste original map on the right side
            extended_img.paste(image, (legend_width, 0))
            
            # Draw legend on the left side
            legend_draw = ImageDraw.Draw(extended_img)
            
            # Draw background for legend area
            legend_draw.rectangle([0, 0, legend_width, new_height], fill=(240, 240, 240), outline=(200, 200, 200))
            
            # Draw legend items
            for idx, (country_id, country_name, text_width, text_height) in enumerate(legend_items):
                column = idx // items_per_column
                row = idx % items_per_column
                
                if column >= num_columns:
                    continue
                    
                x_base = column * column_width + padding
                y_pos = row * item_height + padding
                
                # Skip if this would go beyond image bounds
                if y_pos + item_height > legend_height:
                    continue
                
                color = self.country_colors[country_id]
                
                # Draw color square
                legend_draw.rectangle(
                    [x_base, y_pos, x_base + color_square_size, y_pos + color_square_size],
                    fill=tuple(color),
                    outline=(0, 0, 0)
                )
                
                # Draw country name
                text_x = x_base + color_square_size + padding
                text_y = y_pos + (color_square_size - text_height) // 2
                legend_draw.text(
                    (text_x, text_y),
                    country_name,
                    fill=(0, 0, 0),
                    font=font
                )
                
                if idx % 20 == 0:
                    print(f"[Mapping] Drew legend item {idx+1}/{len(legend_items)}...", flush=True)

            print(f"[Mapping] Dynamic legend created: {legend_width}x{legend_height}, extended canvas: {new_width}x{new_height}")
            print("[Mapping] Finished dynamic add_legend.", flush=True)
            return extended_img

        except Exception as e:
            print(f"Error adding dynamic legend: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return image

    @commands.hybrid_command(
        name="regions_map",
        brief="Display the raw regions map.",
        usage="regions_map [continent|geographical_area|country] [filter_value]",
        description="Display the raw regions map with optional filtering.",
        help="""Display the raw regions map with optional filtering.

        ARGUMENTS:
        - `filter_type` (optional): Type of filter - 'continent', 'geographical_area', or 'country'
        - `filter_value` (optional): Value to filter by

        EXAMPLES:
        - `regions_map` : Display the full world regions map
        - `regions_map continent Europe` : Display only European regions
        - `regions_map geographical_area "Afrique du Sud"` : Display only South African regions
        - `regions_map country France` : Display only French regions
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.describe(
        filter_type="Type of filter to apply", filter_value="Value to filter by"
    )
    async def regions_map(
        self, ctx, filter_type: Optional[str] = None, filter_value: Optional[str] = None
    ):
        """Display the raw regions map with optional filtering."""
        try:
            await ctx.defer()

            # Normalize filter parameters
            if filter_type:
                filter_type = filter_type.lower()
                if filter_type == "continent":
                    filter_key = "Continent"
                elif filter_type == "geographical_area":
                    filter_key = "GeographicAreas"
                elif filter_type == "country":
                    filter_key = "Countries"
                else:
                    filter_key = "All"
            else:
                filter_key = "All"

            # Generate the map
            output_path = await self.generate_filtered_map_async(
                filter_key, filter_value, is_regions_map=True
            )

            if not output_path or not os.path.exists(output_path):
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to generate the regions map.",
                    color=ERROR_COLOR_INT,
                )
                return await ctx.send(embed=embed)

            # Send the map
            embed = discord.Embed(
                title="🗺️ Regions Map",
                description=f"Regions map"
                + (
                    f" filtered by {filter_type}: {filter_value}"
                    if filter_value
                    else ""
                ),
                color=ALL_COLOR_INT,
            )

            file = discord.File(output_path, filename="regions_map.png")
            embed.set_image(url="attachment://regions_map.png")

            await ctx.send(embed=embed, file=file)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while generating the map: {str(e)}",
                color=ERROR_COLOR_INT,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="countries_map",
        brief="Display the countries map with territories colored by country.",
        usage="countries_map [continent|geographical_area|country] [filter_value]",
        description="Display a map showing country territories with consistent colors and legend.",
        help="""Display a map showing country territories with consistent colors and legend.

        FEATURES:
        - Unoccupied regions are shown in white
        - Occupied regions are colored by country
        - Includes a legend showing country names and colors
        - Water areas remain unchanged

        ARGUMENTS:
        - `filter_type` (optional): Type of filter - 'continent', 'geographical_area', or 'country'
        - `filter_value` (optional): Value to filter by

        EXAMPLES:
        - `countries_map` : Display the full world political map
        - `countries_map continent Europe` : Display only European countries
        - `countries_map geographical_area "Afrique du Sud"` : Display only South African regions
        - `countries_map country France` : Display only French territory
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.describe(
        filter_type="Type of filter to apply", filter_value="Value to filter by"
    )
    async def countries_map(
        self, ctx, filter_type: Optional[str] = None, filter_value: Optional[str] = None
    ):
        """Display the countries map with territories colored by country."""
        try:
            await ctx.defer()

            # Normalize filter parameters
            if filter_type:
                filter_type = filter_type.lower()
                if filter_type == "continent":
                    filter_key = "Continent"
                elif filter_type == "geographical_area":
                    filter_key = "GeographicAreas"
                elif filter_type == "country":
                    filter_key = "Countries"
                else:
                    filter_key = "All"
            else:
                filter_key = "All"

            # Generate the map
            output_path = await self.generate_filtered_map_async(
                filter_key, filter_value, is_regions_map=False
            )

            if not output_path or not os.path.exists(output_path):
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to generate the countries map.",
                    color=ERROR_COLOR_INT,
                )
                return await ctx.send(embed=embed)

            # Send the map
            embed = discord.Embed(
                title="🌍 Countries Map",
                description=f"Political map showing country territories"
                + (
                    f" filtered by {filter_type}: {filter_value}"
                    if filter_value
                    else ""
                ),
                color=ALL_COLOR_INT,
            )

            file = discord.File(output_path, filename="countries_map.png")
            embed.set_image(url="attachment://countries_map.png")

            await ctx.send(embed=embed, file=file)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while generating the map: {str(e)}",
                color=ERROR_COLOR_INT,
            )
            await ctx.send(embed=embed)

    async def continent_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        """Autocomplete for continent names."""
        continents = [
            "Europe",
            "Asie",
            "Afrique",
            "Amerique",
            "Oceanie",
            "Moyen-Orient",
        ]
        return [
            app_commands.Choice(name=continent, value=continent)
            for continent in continents
            if current.lower() in continent.lower()
        ]

    async def geographical_area_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        """Autocomplete for geographical area names."""
        try:
            areas = self.db.get_all_geographical_areas()
            return [
                app_commands.Choice(name=area["name"], value=area["name"])
                for area in areas[:25]  # Discord limit
                if current.lower() in area["name"].lower()
            ]
        except:
            return []

    async def country_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        """Autocomplete for country names."""
        try:
            cursor = self.db.cur
            cursor.execute(
                "SELECT name FROM Countries WHERE name LIKE ?", (f"%{current}%",)
            )
            countries = cursor.fetchall()
            return [
                app_commands.Choice(name=country[0], value=country[0])
                for country in countries[:25]  # Discord limit
            ]
        except:
            return []

    # Add autocomplete to commands
    @regions_map.autocomplete("filter_type")
    async def regions_map_filter_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        choices = ["continent", "geographical_area", "country", "all"]
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in choices
            if current.lower() in choice.lower()
        ]

    @regions_map.autocomplete("filter_value")
    async def regions_map_filter_value_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        filter_type = interaction.namespace.filter_type
        if filter_type == "continent":
            return await self.continent_autocomplete(interaction, current)
        elif filter_type == "geographical_area":
            return await self.geographical_area_autocomplete(interaction, current)
        elif filter_type == "country":
            return await self.country_autocomplete(interaction, current)
        return []

    @countries_map.autocomplete("filter_type")
    async def countries_map_filter_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        choices = ["continent", "geographical_area", "country", "all"]
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in choices
            if current.lower() in choice.lower()
        ]

    @countries_map.autocomplete("filter_value")
    async def countries_map_filter_value_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        filter_type = interaction.namespace.filter_type
        if filter_type == "continent":
            return await self.continent_autocomplete(interaction, current)
        elif filter_type == "geographical_area":
            return await self.geographical_area_autocomplete(interaction, current)
        elif filter_type == "country":
            return await self.country_autocomplete(interaction, current)
        return []

    def _cleanup_temp_files(self, file_path: str):
        """Clean up temporary map files."""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"[Mapping] Cleaned up temporary file: {file_path}")
        except Exception as e:
            print(f"[Mapping] Error cleaning up {file_path}: {e}")

    async def generate_all_maps_async(self, map_channel):
        """Generate all continental and world maps in parallel with thread-safe memory management."""
        temp_files = []  # Track temporary files for cleanup
        successful_generations = 0
        total_maps = 0
        
        try:
            print("[Map Update] Starting parallel map generation...")
            
            # Continental data list
            continents = [
                "Europe",
                "Asie", 
                "Afrique",
                "Amerique",
                "Oceanie",
                "Moyen-Orient",
            ]
            
            total_maps = len(continents) + 1  # +1 for world map
            
            print(f"[Map Update] Generating {len(continents)} continental maps and 1 world map in parallel...")
            
            # Create semaphore to limit concurrent map generations and prevent memory overload
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent map generations

            async def generate_continent_with_semaphore(continent):
                """Generate continent map with semaphore control for memory management."""
                async with semaphore:
                    try:
                        print(f"[Map Update] Starting generation for {continent}")
                        
                        # Pre-generation memory check
                        gc.collect()
                        
                        result = await self._generate_continent_map_with_stats_safe(continent)
                        
                        # Force garbage collection after each map generation
                        gc.collect()
                        
                        if result[0] is not None and result[1] is not None:
                            print(f"[Map Update] ✅ Successfully generated {continent} map")
                            return continent, result
                        else:
                            print(f"[Map Update] ❌ Failed to generate {continent} map")
                            return continent, (None, None)
                            
                    except MemoryError as e:
                        print(f"[Map Update] ❌ Memory error generating {continent} map: {e}")
                        gc.collect()
                        return continent, (None, None)
                    except Exception as e:
                        print(f"[Map Update] ❌ Error generating {continent} map: {e}")
                        traceback.print_exc()
                        return continent, (None, None)
            
            async def generate_world_with_semaphore():
                """Generate world map with semaphore control for memory management."""
                async with semaphore:
                    try:
                        print(f"[Map Update] Starting world map generation")
                        
                        # Pre-generation memory check
                        gc.collect()
                        
                        result = await self._generate_world_map_with_stats_safe(continents)
                        
                        # Force garbage collection after world map generation
                        gc.collect()
                        
                        if result[0] is not None and result[1] is not None:
                            print(f"[Map Update] ✅ Successfully generated world map")
                            return "World", result
                        else:
                            print(f"[Map Update] ❌ Failed to generate world map")
                            return "World", (None, None)
                            
                    except MemoryError as e:
                        print(f"[Map Update] ❌ Memory error generating world map: {e}")
                        gc.collect()
                        return "World", (None, None)
                    except Exception as e:
                        print(f"[Map Update] ❌ Error generating world map: {e}")
                        traceback.print_exc()
                        return "World", (None, None)
            
            # Generate all maps in parallel with controlled concurrency
            tasks = []
            
            # Force garbage collection before starting map generation
            gc.collect()
            print(f"[Map Update] Memory cleanup before generation - starting with {len(continents)} continents")
            
            # Add continent tasks with memory monitoring
            for i, continent in enumerate(continents):
                task = generate_continent_with_semaphore(continent)
                tasks.append(task)
                print(f"[Map Update] Added task {i+1}/{len(continents)}: {continent}")
            
            # Add world map task
            world_task = generate_world_with_semaphore()
            tasks.append(world_task)
            print(f"[Map Update] Added world map task")
            
            # Execute all tasks in parallel with controlled concurrency
            print(f"[Map Update] Executing {len(tasks)} map generation tasks in parallel with max 2 concurrent...")
            
            # Add timeout to prevent hanging
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=1200  # 20 minutes timeout
                )
            except asyncio.TimeoutError:
                print("[Map Update] ❌ Map generation timed out after 20 minutes")
                return
            
            # Force garbage collection after all tasks complete
            gc.collect()
            print(f"[Map Update] All tasks completed, memory cleanup performed")
            
            # Process results and collect successful generations
            continent_results = []
            world_result = []
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"[Map Update] ❌ Task failed with exception: {result}")
                    continue
                    
                map_type, (embed, file_path) = result
                
                if embed is not None and file_path is not None and os.path.exists(file_path):
                    successful_generations += 1
                    temp_files.append(file_path)
                    
                    if map_type == "World":
                        world_result = [(embed, file_path)]
                    else:
                        continent_results.append((map_type, (embed, file_path)))
                else:
                    print(f"[Map Update] ⚠️ Failed generation for {map_type}")
                    if map_type != "World":
                        continent_results.append((map_type, (None, None)))
            
            # Final memory cleanup
            gc.collect()
            
            print(f"[Map Update] Generation complete: {successful_generations}/{total_maps} maps successful")
           
            # Clear the channel with error handling
            print(f"[Map Update] Clearing channel {map_channel.name}")
            try:
                async for message in map_channel.history(limit=None):
                    try:
                        await message.delete()
                    except Exception as e:
                        print(f"[Map Update] Error deleting message: {e}")
            except Exception as e:
                print(f"[Map Update] Error during channel clearing: {e}")

            # Send continental maps to Discord
            maps_sent = 0
            for continent, (embed, file_path) in continent_results:
                if embed and file_path and os.path.exists(file_path):
                    try:
                        file = discord.File(file_path, filename=f"{continent}_map.png")
                        embed.set_image(url=f"attachment://{continent}_map.png")
                        await map_channel.send(embed=embed, file=file)
                        maps_sent += 1
                        print(f"[Map Update] ✅ Sent {continent} map to Discord")
                        
                        # Small delay between Discord messages
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"[Map Update] ❌ Error sending {continent} map to Discord: {e}")
                else:
                    print(f"[Map Update] ⚠️ Skipping {continent} - no valid map generated")
            
            # Send world map to Discord
            if world_result:
                embed, file_path = world_result[0]
                if embed and file_path and os.path.exists(file_path):
                    try:
                        file = discord.File(file_path, filename="world_map.png")
                        embed.set_image(url="attachment://world_map.png")
                        await map_channel.send(embed=embed, file=file)
                        maps_sent += 1
                        print("[Map Update] ✅ Sent world map to Discord")
                    except Exception as e:
                        print(f"[Map Update] ❌ Error sending world map to Discord: {e}")
                else:
                    print("[Map Update] ⚠️ Skipping world map - no valid map generated")
            
            print(f"[Map Update] Discord upload complete: {maps_sent}/{successful_generations} maps sent")
                    
        except Exception as e:
            print(f"[Map Update] ❌ Critical error in generate_all_maps_async: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Sending generated maps to /home/ubuntu/Bots/resurgence-web/images with correct names ($continent-map.png)

            # Ensure both continent_results and world_result are lists of (continent, (embed, file_path))
            all_results = continent_results.copy()
            if world_result:
                # world_result is a list of one tuple: [(embed, file_path)]
                embed, file_path = world_result[0]
                all_results.append(("World", (embed, file_path)))
            for continent, (embed, file_path) in all_results:
                if embed and file_path and os.path.exists(file_path):
                    try:
                        new_file_path = f"/home/ubuntu/Bots/resurgence-web/images/{continent.lower()}-map.png"
                        os.rename(file_path, new_file_path)
                        print(f"[Map Update] ✅ Moved {file_path} to {new_file_path}")
                    except Exception as e:
                        print(f"[Map Update] ❌ Error moving {file_path} to {new_file_path}: {e}")

            # Force garbage collection to free memory
            gc.collect()
            print("[Map Update] Memory cleanup completed")

    async def _generate_continent_map_with_stats_safe(self, continent: str):
        """Generate a single continent map with enhanced error handling and memory management."""
        try:
            print(f"[Map Update] Processing continent: {continent}")
            
            # Get continental statistics using async database with retry
            max_retries = 3
            continental_stats = None
            
            for attempt in range(max_retries):
                try:
                    continental_stats = await self.async_db.get_continental_statistics_async(continent)
                    break
                except Exception as e:
                    print(f"[Map Update] Attempt {attempt + 1}/{max_retries} failed for {continent} stats: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(1)
            
            if not continental_stats:
                print(f"[Map Update] No statistics available for {continent}")
                return None, None
            
            # Generate the continental map with retry mechanism
            output_path = None
            for attempt in range(max_retries):
                try:
                    output_path = await self.generate_filtered_map_async(
                        "Continent", continent, is_regions_map=False
                    )
                    if output_path and os.path.exists(output_path):
                        break
                    else:
                        print(f"[Map Update] Attempt {attempt + 1}/{max_retries} - no output for {continent}")
                except Exception as e:
                    print(f"[Map Update] Attempt {attempt + 1}/{max_retries} failed for {continent} map: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(2)
            
            if not output_path or not os.path.exists(output_path):
                print(f"[Map Update] Failed to generate map for {continent} after {max_retries} attempts")
                return None, None
                
            # Create embed with continental statistics
            embed = discord.Embed(
                title=f"🌍 {continent} - Carte Politique",
                color=ALL_COLOR_INT,
            )
            
            # Add statistical fields with safe formatting
            try:
                embed.add_field(
                    name="📊 Statistiques Générales",
                    value=f"🏛️ **Pays total:** {continental_stats.get('total_countries', 0)}\n"
                    f"👤 **Pays joués:** {continental_stats.get('played_countries', 0)}\n"
                    f"🏳️ **Pays libres:** {continental_stats.get('unplayed_countries', 0)}\n"
                    f"📍 **Régions totales:** {continental_stats.get('total_regions', 0)}",
                    inline=True,
                )
                
                embed.add_field(
                    name="🗺️ Contrôle Territorial",
                    value=f"🎯 **Régions contrôlées:** {continental_stats.get('controlled_regions', 0)}\n"
                    f"🆓 **Régions libres:** {continental_stats.get('free_regions', 0)}\n"
                    f"📈 **% contrôlé:** {continental_stats.get('control_percentage', 0):.1f}%\n"
                    f"🔓 **% libre:** {continental_stats.get('free_percentage', 0):.1f}%",
                    inline=True,
                )
                
                embed.add_field(
                    name="⏰ Mise à jour",
                    value=f"📅 **Date:** {datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m/%Y')}\n"
                    f"🕐 **Heure:** <t:{int(datetime.now(pytz.timezone('Europe/Paris')).timestamp())}>",
                    inline=False,
                )
            except Exception as e:
                print(f"[Map Update] Error creating embed for {continent}: {e}")
                # Create minimal embed as fallback
                embed = discord.Embed(
                    title=f"🌍 {continent} - Carte Politique",
                    description="Statistiques temporairement indisponibles",
                    color=ALL_COLOR_INT,
                )
            
            print(f"[Map Update] Successfully processed {continent}")
            return embed, output_path
            
        except Exception as e:
            print(f"[Map Update] Critical error processing continent {continent}: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    async def _generate_continent_map_with_stats(self, continent: str):
        """Generate a single continent map with statistics."""
        try:
            print(f"[Map Update] Processing continent: {continent}")
            
            # Get continental statistics using async database
            continental_stats = await self.async_db.get_continental_statistics_async(continent)
            
            # Generate the continental map
            output_path = await self.generate_filtered_map_async(
                "Continent", continent, is_regions_map=False
            )
            
            if not output_path or not os.path.exists(output_path):
                print(f"[Map Update] Failed to generate map for {continent}")
                return None, None
                
            # Create embed with continental statistics
            embed = discord.Embed(
                title=f"🌍 {continent} - Carte Politique",
                color=ALL_COLOR_INT,
            )
            
            # Add statistical fields
            embed.add_field(
                name="📊 Statistiques Générales",
                value=f"🏛️ **Pays total:** {continental_stats['total_countries']}\n"
                f"👤 **Pays joués:** {continental_stats['played_countries']}\n"
                f"🏳️ **Pays libres:** {continental_stats['unplayed_countries']}\n"
                f"📍 **Régions totales:** {continental_stats['total_regions']}",
                inline=True,
            )
            
            embed.add_field(
                name="🗺️ Contrôle Territorial",
                value=f"🎯 **Régions contrôlées:** {continental_stats['controlled_regions']}\n"
                f"🆓 **Régions libres:** {continental_stats['free_regions']}\n"
                f"📈 **% contrôlé:** {continental_stats['control_percentage']:.1f}%\n"
                f"🔓 **% libre:** {continental_stats['free_percentage']:.1f}%",
                inline=True,
            )
            
            embed.add_field(
                name="⏰ Mise à jour",
                value=f"📅 **Date:** {datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m/%Y')}\n"
                f"🕐 **Heure:** <t:{int(datetime.now(pytz.timezone('Europe/Paris')).timestamp())}>",
                inline=False,
            )
            
            return embed, output_path
            
        except Exception as e:
            print(f"[Map Update] Error processing continent {continent}: {e}")
            raise e

    async def _generate_world_map_with_stats_safe(self, continents: List[str]):
        """Generate world map with enhanced error handling and memory management."""
        try:
            print(f"[Map Update] Processing world map...")
            
            # Get world statistics using async database with retry
            max_retries = 3
            world_stats = None
            
            for attempt in range(max_retries):
                try:
                    world_stats = await self.async_db.get_world_statistics_async()
                    break
                except Exception as e:
                    print(f"[Map Update] Attempt {attempt + 1}/{max_retries} failed for world stats: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(1)
            
            if not world_stats:
                print(f"[Map Update] No world statistics available")
                return None, None
            
            # Generate the world map with retry mechanism
            output_path = None
            for attempt in range(max_retries):
                try:
                    output_path = await self.generate_filtered_map_async(
                        "All", None, is_regions_map=False
                    )
                    if output_path and os.path.exists(output_path):
                        break
                    else:
                        print(f"[Map Update] Attempt {attempt + 1}/{max_retries} - no world map output")
                except Exception as e:
                    print(f"[Map Update] Attempt {attempt + 1}/{max_retries} failed for world map: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(2)
            
            if not output_path or not os.path.exists(output_path):
                print(f"[Map Update] Failed to generate world map after {max_retries} attempts")
                return None, None
                
            # Create embed with world statistics
            embed = discord.Embed(
                title="🌍 Monde - Carte Politique Globale",
                description="Vue d'ensemble de l'état géopolitique mondial",
                color=ALL_COLOR_INT,
            )
            
            # Add statistical fields with safe formatting
            try:
                embed.add_field(
                    name="🌐 Statistiques Mondiales",
                    value=f"🏛️ **Pays total:** {world_stats.get('total_countries', 0)}\n"
                    f"👤 **Pays joués:** {world_stats.get('played_countries', 0)}\n"
                    f"🏳️ **Pays libres:** {world_stats.get('unplayed_countries', 0)}\n"
                    f"📍 **Régions totales:** {world_stats.get('total_regions', 0)}",
                    inline=True,
                )
                
                embed.add_field(
                    name="🗺️ Contrôle Global",
                    value=f"🎯 **Régions contrôlées:** {world_stats.get('controlled_regions', 0)}\n"
                    f"🆓 **Régions libres:** {world_stats.get('free_regions', 0)}\n"
                    f"📈 **% contrôlé:** {world_stats.get('control_percentage', 0):.1f}%\n"
                    f"🔓 **% libre:** {world_stats.get('free_percentage', 0):.1f}%",
                    inline=True,
                )
                
                # Get continent country counts with retry and safe fallback
                continent_counts = []
                for continent in continents:
                    try:
                        count = await self.async_db.get_continent_country_count_async(continent)
                        continent_counts.append(count)
                    except Exception as e:
                        print(f"[Map Update] Error getting count for {continent}: {e}")
                        continent_counts.append(0)
                
                embed.add_field(
                    name="📈 Répartition par Continent",
                    value="\n".join(
                        [
                            f"🌍 **{continent}:** {count} pays"
                            for continent, count in zip(continents, continent_counts)
                        ]
                    ) if continent_counts else "Données indisponibles",
                    inline=False,
                )
                
                embed.add_field(
                    name="⏰ Mise à jour Quotidienne",
                    value=f"📅 **Date:** {datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m/%Y')}\n"
                    f"🕐 **Heure:** <t:{int(datetime.now(pytz.timezone('Europe/Paris')).timestamp())}>\n"
                    f"🔄 **Prochaine:** <t:{int((datetime.now(pytz.timezone('Europe/Paris')).replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp())}>",
                    inline=False,
                )
            except Exception as e:
                print(f"[Map Update] Error creating world embed: {e}")
                # Create minimal embed as fallback
                embed = discord.Embed(
                    title="🌍 Monde - Carte Politique Globale",
                    description="Statistiques temporairement indisponibles",
                    color=ALL_COLOR_INT,
                )
            
            print(f"[Map Update] Successfully processed world map")
            return embed, output_path
            
        except Exception as e:
            print(f"[Map Update] Critical error processing world map: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    async def _generate_world_map_with_stats(self, continents: List[str]):
        """Generate world map with global statistics."""
        try:
            print("[Map Update] Generating world map...")
            
            # Get global statistics using async database
            world_stats = await self.async_db.get_world_statistics_async()
            
            # Generate the world map
            output_path = await self.generate_filtered_map_async(
                "All", None, is_regions_map=False
            )
            
            if not output_path or not os.path.exists(output_path):
                print("[Map Update] Failed to generate world map")
                return None, None
                
            # Create embed with world statistics
            embed = discord.Embed(
                title="🌍 Monde - Carte Politique Globale",
                description="Vue d'ensemble de l'état géopolitique mondial",
                color=ALL_COLOR_INT,
            )
            
            # Add global statistical fields
            embed.add_field(
                name="🌐 Statistiques Mondiales",
                value=f"🏛️ **Pays total:** {world_stats['total_countries']}\n"
                f"👤 **Pays joués:** {world_stats['played_countries']}\n"
                f"🏳️ **Pays libres:** {world_stats['unplayed_countries']}\n"
                f"📍 **Régions totales:** {world_stats['total_regions']}",
                inline=True,
            )
            
            embed.add_field(
                name="🗺️ Contrôle Global",
                value=f"🎯 **Régions contrôlées:** {world_stats['controlled_regions']}\n"
                f"🆓 **Régions libres:** {world_stats['free_regions']}\n"
                f"📈 **% contrôlé:** {world_stats['control_percentage']:.1f}%\n"
                f"🔓 **% libre:** {world_stats['free_percentage']:.1f}%",
                inline=True,
            )
            
            # Get continent country counts in parallel
            continent_count_tasks = [
                self.async_db.get_continent_country_count_async(continent)
                for continent in continents
            ]
            continent_counts = await asyncio.gather(*continent_count_tasks)
            
            embed.add_field(
                name="📈 Répartition par Continent",
                value="\n".join(
                    [
                        f"🌍 **{continent}:** {count} pays"
                        for continent, count in zip(continents, continent_counts)
                    ]
                ),
                inline=False,
            )
            
            embed.add_field(
                name="⏰ Mise à jour Quotidienne",
                value=f"📅 **Date:** {datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m/%Y')}\n"
                f"🕐 **Heure:** <t:{int(datetime.now(pytz.timezone('Europe/Paris')).timestamp())}>\n"
                f"🔄 **Prochaine:** <t:{int((datetime.now(pytz.timezone('Europe/Paris')).replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp())}>",
                inline=False,
            )
            
            return embed, output_path
            
        except Exception as e:
            print(f"[Map Update] Error generating world map: {e}")
            raise e


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(MappingCog(bot))

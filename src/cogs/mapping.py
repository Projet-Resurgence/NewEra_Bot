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
from scipy.ndimage import binary_dilation
from skimage.segmentation import find_boundaries

CROPPING_OFFSET = 10
BORDERS_SIZE = 3


class MappingCog(commands.Cog):
    """Geographic mapping and visualization commands with optimized preprocessing."""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)
        self.region_colors_cache = {}
        self.region_masks_cache = {}
        self._load_region_colors()
        self.country_colors = {}
        self.base_img = Image.open("datas/mapping/region_map.png").convert("RGBA")
        self.base_array = np.array(self.base_img)

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

    async def generate_filtered_map_async(
        self,
        filter_key: str,
        filter_value: Optional[str] = None,
        is_regions_map: bool = False,
    ) -> str:
        """Async wrapper for generate_filtered_map to prevent blocking."""
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor,
                self.generate_filtered_map,
                filter_key,
                filter_value,
                is_regions_map,
            )

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb: tuple) -> str:
        """Convert RGB tuple to hex string."""
        return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

    def get_country_color(self, country_id: int) -> Tuple[int, int, int]:
        """Get a consistent color for a country based on its Discord role."""
        try:
            country_data = self.db.get_country_datas(str(country_id))
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

    def generate_filtered_map(
        self,
        filter_key: str = "All",
        filter_value: Optional[str] = None,
        is_regions_map: bool = False,
    ) -> str:
        """Generate a filtered map based on the key/value and map type."""
        try:
            # Get regions data for filtering
            self.country_colors = {}
            regions_data = self.get_regions_data(filter_key, filter_value)

            if is_regions_map:
                # For regions map: outline regions with black borders on white background
                result_img = self.generate_regions_map(regions_data)
            else:
                # For countries map: colorize by country and add legend
                result_img = self.generate_countries_map(regions_data)

            # Crop if not showing all
            if filter_key != "All" and filter_value:
                result_img = self.crop_to_regions(result_img, regions_data)

            if not is_regions_map:
                result_img = self.add_legend(result_img, regions_data)

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

    # def generate_regions_map(self, regions_data: List[dict]) -> Image.Image:
    #     """Generate a white map with black region outlines."""
    #     print("[Mapping] Starting generate_regions_map...", flush=True)
    #     height, width = self.base_array.shape[:2]
    #     result_array = (
    #         np.ones((height, width, 3), dtype=np.uint8) * 255
    #     )  # White background

    #     water_color = np.array([39, 39, 39])  # #272727

    #     # Create water mask
    #     water_mask = (np.all(self.base_array[:, :, :3] == water_color, axis=2)) | (
    #         self.base_array[:, :, 3] == 0
    #     )  # Transparent areas

    #     # Apply water color to water areas
    #     result_array[water_mask] = water_color
    #     print("[Mapping] Water mask applied.", flush=True)

    #     # For regions map, we need to identify ALL regions to create borders
    #     # If we have a filter, only show borders for those regions
    #     # If no filter, show borders for ALL regions in the CSV (not database)

    #     if not regions_data:  # No filter - use all CSV regions
    #         print(
    #             "[Mapping] No filter specified, using all CSV regions for borders.",
    #             flush=True,
    #         )
    #         relevant_colors = set(self.region_colors_cache.keys())
    #     else:
    #         # Filter specified - get colors from the filtered database data
    #         print(
    #             f"[Mapping] Filter specified, using {len(regions_data)} filtered regions.",
    #             flush=True,
    #         )
    #         relevant_colors = set()
    #         for region in regions_data:
    #             hex_color = region.get("region_color_hex", "")
    #             if hex_color:
    #                 if not hex_color.startswith("#"):
    #                     hex_color = "#" + hex_color
    #                 rgb = self.hex_to_rgb(hex_color)
    #                 relevant_colors.add(rgb)

    #     print(
    #         f"[Mapping] Using {len(relevant_colors)} region colors for borders.",
    #         flush=True,
    #     )

    #     # Create borders for each region individually to avoid merging adjacent regions
    #     combined_border_mask = np.zeros((height, width), dtype=bool)
    #     found_regions = 0
    #     missing_regions = 0

    #     # Use a smaller kernel and create borders more carefully to avoid thickness
    #     kernel = np.ones((3, 3), dtype=bool)  # Smaller 3x3 kernel for thinner borders

    #     for idx, color in enumerate(relevant_colors):
    #         color_array = np.array(color)
    #         region_mask = np.all(self.base_array[:, :, :3] == color_array, axis=2)
    #         pixel_count = np.sum(region_mask)

    #         if pixel_count > 0:
    #             # Create border for this individual region
    #             dilated_mask = binary_dilation(region_mask, structure=kernel)
    #             border_mask = dilated_mask & ~region_mask

    #             # Add this region's border to the combined border mask
    #             combined_border_mask |= border_mask
    #             found_regions += 1

    #             if idx % 50 == 0:  # Less frequent logging
    #                 individual_border_count = np.sum(border_mask)
    #                 print(
    #                     f"[Mapping] Region {color}: {pixel_count} pixels, {individual_border_count} border pixels"
    #                 )
    #         else:
    #             missing_regions += 1
    #             if missing_regions <= 5:  # Only log first few missing regions
    #                 print(
    #                     f"[Mapping] Warning: No pixels found for region color {color}"
    #                 )

    #         if idx % 50 == 0:
    #             print(
    #                 f"[Mapping] Processed {idx+1}/{len(relevant_colors)} region colors...",
    #                 flush=True,
    #             )

    #     print(
    #         f"[Mapping] Successfully found {found_regions}/{len(relevant_colors)} regions in map"
    #     )
    #     print(f"[Mapping] {missing_regions} regions not found in base map")

    #     # Apply all borders at once
    #     if np.any(combined_border_mask):
    #         result_array[combined_border_mask] = [0, 0, 0]  # Black borders
    #         total_border_pixels = np.sum(combined_border_mask)
    #         print(
    #             f"[Mapping] Applied {total_border_pixels} total border pixels for individual regions.",
    #             flush=True,
    #         )
    #     else:
    #         print(
    #             "[Mapping] Warning: No regions found for border creation!", flush=True
    #         )

    #     print("[Mapping] Finished generate_regions_map.", flush=True)
    #     return Image.fromarray(result_array)

    def generate_countries_map(self, regions_data: List[dict]) -> Image.Image:
        """Generate a map colored by countries with legend."""
        print("[Mapping] Starting generate_countries_map...", flush=True)
        height, width = self.base_array.shape[:2]
        result_array = self.base_array.copy()

        water_color = np.array([39, 39, 39])  # #272727
        unoccupied_color = np.array([255, 255, 255])  # White for unoccupied

        # If no regions_data (All filter), we need to get all regions from database
        if not regions_data:
            print(
                "[Mapping] No regions data provided, querying all regions from database...",
                flush=True,
            )
            regions_data = self.get_all_regions()
            print(
                f"[Mapping] Retrieved {len(regions_data)} regions from database",
                flush=True,
            )

        # Build country color mapping and region-to-country mapping
        region_to_country = {}
        countries_in_map = set()

        # First pass: collect all countries and their colors
        for idx, region in enumerate(regions_data):
            country_id = region.get("country_id")
            if country_id:
                countries_in_map.add(country_id)
                if country_id not in self.country_colors:
                    self.country_colors[country_id] = self.get_country_color(country_id)
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

    def add_legend(self, image: Image.Image, regions_data: list) -> Image.Image:
        """Add a legend showing countries and their colors."""
        print("[Mapping] Starting add_legend...", flush=True)
        try:
            if not regions_data:
                regions_data = self.get_all_regions()
            country_names = {}
            for idx, region in enumerate(regions_data):
                country_id = region.get("country_id")
                country_name = region.get("country_name")
                if country_id and country_name and country_id in self.country_colors:
                    country_names[country_id] = country_name
                print(f"[Mapping] Processed region {region['name']} for legend...")
                if idx % 20 == 0:
                    print(
                        f"[Mapping] Processed {idx+1}/{len(regions_data)} regions for legend...",
                        flush=True,
                    )

            if not country_names:
                print("[Mapping] No country names found, skipping legend.", flush=True)
                return image

            # Calculate scale factor based on image size (reference: 400x400)
            image_width, image_height = image.size
            reference_size = 250
            scale_factor = min(image_width, image_height) / reference_size
            scale_factor = max(0.8, min(scale_factor, 5.0))  # Clamp between 0.5x and 3x

            print(
                f"[Mapping] Image size: {image_width}x{image_height}, scale factor: {scale_factor:.2f}",
                flush=True,
            )

            # Scale font and sizes
            base_font_size = 12
            font_size = max(8, int(base_font_size * scale_factor))

            try:
                font = ImageFont.truetype("datas/arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            draw_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            legend_items = []
            max_text_width = 0

            for idx, (country_id, country_name) in enumerate(country_names.items()):
                text = country_name
                bbox = draw_temp.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                max_text_width = max(max_text_width, text_width)
                legend_items.append((country_id, text, text_width, text_height))
                if idx % 10 == 0:
                    print(
                        f"[Mapping] Calculated legend item {idx+1}/{len(country_names)}...",
                        flush=True,
                    )

            # Scale legend elements
            color_square_size = max(8, int(12 * scale_factor))
            padding = max(3, int(5 * scale_factor))
            legend_width = color_square_size + padding + max_text_width + padding * 2
            legend_height = len(legend_items) * (color_square_size + padding) + padding

            legend_img = Image.new(
                "RGBA", (legend_width, legend_height), (255, 255, 255, 200)
            )
            legend_draw = ImageDraw.Draw(legend_img)

            y_offset = padding
            for idx, (country_id, text, text_width, text_height) in enumerate(
                legend_items
            ):
                color = self.country_colors[country_id]
                legend_draw.rectangle(
                    [
                        padding,
                        y_offset,
                        padding + color_square_size,
                        y_offset + color_square_size,
                    ],
                    fill=tuple(color),
                    outline=(0, 0, 0),
                )
                legend_draw.text(
                    (padding + color_square_size + padding, y_offset),
                    text,
                    fill=(0, 0, 0),
                    font=font,
                )
                y_offset += color_square_size + padding
                if idx % 10 == 0:
                    print(
                        f"[Mapping] Drew legend item {idx+1}/{len(legend_items)}...",
                        flush=True,
                    )

            image_width, image_height = image.size
            legend_x = max(5, int(10 * scale_factor))
            legend_y = image_height - legend_height - max(5, int(10 * scale_factor))

            result_img = image.copy()
            result_img.paste(legend_img, (legend_x, legend_y), legend_img)

            print(
                f"[Mapping] Legend positioned at ({legend_x}, {legend_y}) with size {legend_width}x{legend_height}",
                flush=True,
            )
            print("[Mapping] Finished add_legend.", flush=True)
            return result_img

        except Exception as e:
            print(f"Error adding legend: {e}", flush=True)
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


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(MappingCog(bot))

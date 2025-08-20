#!/usr/bin/env python3
"""
Test individual region border generation
"""
import sys

sys.path.append("src")
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation
import csv


def test_individual_borders():
    print("Testing individual region border generation...")

    # Load base map
    base_img = Image.open("datas/mapping/region_map.png").convert("RGBA")
    base_array = np.array(base_img)
    height, width = base_array.shape[:2]

    print(f"Base map size: {width}x{height}")

    # Load first few CSV colors (South African regions)
    csv_colors = []
    with open("datas/mapping/region_list.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= 7:  # Test first 7 South African regions
                break
            hex_color = row["Code couleur HEX"].strip()
            if not hex_color.startswith("#"):
                hex_color = "#" + hex_color
            hex_color = hex_color.lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            csv_colors.append((rgb, row["Nom region"]))

    print(f"Testing individual borders for {len(csv_colors)} regions")

    # Create result image
    result_array = np.ones((height, width, 3), dtype=np.uint8) * 255  # White background

    # Apply water areas
    water_color = np.array([39, 39, 39])
    water_mask = np.all(base_array[:, :, :3] == water_color, axis=2)
    result_array[water_mask] = water_color

    # Create borders for each region individually
    combined_border_mask = np.zeros((height, width), dtype=bool)
    total_region_pixels = 0

    for color, region_name in csv_colors:
        color_array = np.array(color)
        region_mask = np.all(base_array[:, :, :3] == color_array, axis=2)
        pixel_count = np.sum(region_mask)
        total_region_pixels += pixel_count

        if pixel_count > 0:
            # Create border for this individual region
            kernel = np.ones((7, 7), dtype=bool)
            dilated_mask = binary_dilation(region_mask, structure=kernel)
            border_mask = dilated_mask & ~region_mask

            # Add to combined border mask
            combined_border_mask |= border_mask
            border_pixels = np.sum(border_mask)

            print(
                f"Region '{region_name}' {color}: {pixel_count} pixels, {border_pixels} border pixels"
            )
        else:
            print(f"Region '{region_name}' {color}: NOT FOUND")

    # Apply all borders
    result_array[combined_border_mask] = [0, 0, 0]  # Black borders
    total_border_pixels = np.sum(combined_border_mask)

    print(f"\\nTotal region pixels: {total_region_pixels}")
    print(f"Total border pixels: {total_border_pixels}")

    # Save test image
    result_img = Image.fromarray(result_array)
    result_img.save("test_individual_borders.png")
    print("\\nTest image saved as test_individual_borders.png")

    return total_border_pixels > 0


if __name__ == "__main__":
    test_individual_borders()

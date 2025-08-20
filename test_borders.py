#!/usr/bin/env python3
"""
Quick test of the border generation logic
"""
import sys

sys.path.append("src")
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation
import csv


def test_border_logic():
    print("Testing border generation logic...")

    # Load base map
    base_img = Image.open("datas/mapping/region_map.png").convert("RGBA")
    base_array = np.array(base_img)
    height, width = base_array.shape[:2]

    print(f"Base map size: {width}x{height}")

    # Load first few CSV colors
    csv_colors = []
    with open("datas/mapping/region_list.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= 5:  # Just test first 5 regions
                break
            hex_color = row["Code couleur HEX"].strip()
            if not hex_color.startswith("#"):
                hex_color = "#" + hex_color
            hex_color = hex_color.lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            csv_colors.append(rgb)

    print(f"Testing with {len(csv_colors)} sample colors")

    # Create combined region mask
    region_mask = np.zeros((height, width), dtype=bool)
    total_pixels = 0

    for color in csv_colors:
        color_array = np.array(color)
        color_mask = np.all(base_array[:, :, :3] == color_array, axis=2)
        pixel_count = np.sum(color_mask)
        region_mask |= color_mask
        total_pixels += pixel_count
        print(f"Color {color}: {pixel_count} pixels")

    print(f"Total region pixels: {total_pixels}")
    print(f"Combined mask has {np.sum(region_mask)} pixels")

    # Test border creation
    if np.any(region_mask):
        print("Creating borders...")
        kernel = np.ones((7, 7), dtype=bool)
        dilated_mask = binary_dilation(region_mask, structure=kernel)
        border_mask = dilated_mask & ~region_mask

        border_pixel_count = np.sum(border_mask)
        print(f"Border pixels: {border_pixel_count}")

        # Create test output
        result_array = (
            np.ones((height, width, 3), dtype=np.uint8) * 255
        )  # White background

        # Apply water areas
        water_color = np.array([39, 39, 39])
        water_mask = np.all(base_array[:, :, :3] == water_color, axis=2)
        result_array[water_mask] = water_color

        # Apply borders
        result_array[border_mask] = [0, 0, 0]  # Black borders

        # Save test image
        result_img = Image.fromarray(result_array)
        result_img.save("test_borders.png")
        print("Test image saved as test_borders.png")

        return True
    else:
        print("No regions found!")
        return False


if __name__ == "__main__":
    test_border_logic()

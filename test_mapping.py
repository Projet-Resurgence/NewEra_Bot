#!/usr/bin/env python3
"""
Test script for the mapping cog functionality
"""
import sys
import os

sys.path.append("/home/ubuntu/Bots/NEBot/src")

from PIL import Image
import numpy as np


def test_map_exists():
    """Test if the base map exists and is readable"""
    map_path = "/home/ubuntu/Bots/NEBot/datas/mapping/region_map.png"

    if not os.path.exists(map_path):
        print(f"❌ Base map not found at {map_path}")
        return False

    try:
        img = Image.open(map_path)
        print(f"✅ Base map loaded successfully: {img.size} pixels, mode: {img.mode}")

        # Convert to RGBA and check some properties
        img_rgba = img.convert("RGBA")
        img_array = np.array(img_rgba)
        print(f"✅ Image converted to numpy array: {img_array.shape}")

        # Check for water color
        water_color = np.array([39, 39, 39])
        water_pixels = np.all(img_array[:, :, :3] == water_color, axis=2)
        water_count = np.sum(water_pixels)
        print(f"✅ Found {water_count} water pixels with color #272727")

        # Check for transparent pixels
        transparent_pixels = img_array[:, :, 3] == 0
        transparent_count = np.sum(transparent_pixels)
        print(f"✅ Found {transparent_count} transparent pixels")

        return True

    except Exception as e:
        print(f"❌ Error loading base map: {e}")
        return False


def test_csv_data():
    """Test if the CSV data is readable"""
    csv_path = "/home/ubuntu/Bots/NEBot/datas/mapping/region_list.csv"

    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found at {csv_path}")
        return False

    try:
        import csv

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            print(f"✅ CSV loaded successfully with {len(rows)} regions")

            # Show some sample data
            if rows:
                sample = rows[0]
                print(f"✅ Sample row: {sample}")

                # Test hex color conversion
                hex_color = sample["Code couleur HEX"]
                if not hex_color.startswith("#"):
                    hex_color = "#" + hex_color

                # Convert hex to RGB
                hex_color = hex_color.lstrip("#")
                rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
                print(
                    f"✅ Sample color conversion: #{sample['Code couleur HEX']} -> {rgb}"
                )

        return True

    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return False


def test_font():
    """Test if the font file exists"""
    font_path = "/home/ubuntu/Bots/NEBot/datas/arial.ttf"

    if not os.path.exists(font_path):
        print(f"⚠️  Font file not found at {font_path} - will use default font")
        return False

    try:
        from PIL import ImageFont

        font = ImageFont.truetype(font_path, 12)
        print(f"✅ Font loaded successfully")
        return True

    except Exception as e:
        print(f"⚠️  Error loading font: {e} - will use default font")
        return False


def test_output_directory():
    """Test if output directory exists and is writable"""
    output_dir = "/home/ubuntu/Bots/NEBot/datas/mapping"

    if not os.path.exists(output_dir):
        print(f"❌ Output directory not found: {output_dir}")
        return False

    try:
        # Test write permissions
        test_file = os.path.join(output_dir, "test_write.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print(f"✅ Output directory is writable: {output_dir}")
        return True

    except Exception as e:
        print(f"❌ Cannot write to output directory: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing mapping cog dependencies...")
    print("=" * 50)

    tests = [
        ("Base Map", test_map_exists),
        ("CSV Data", test_csv_data),
        ("Font File", test_font),
        ("Output Directory", test_output_directory),
    ]

    passed = 0
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if test_func():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All tests passed! Mapping cog should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")

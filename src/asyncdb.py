"""
Async database module for read-only operations to avoid SQLite cursor conflicts.
Uses aiosqlite for async database operations with WAL mode for concurrent access.
"""

import aiosqlite
import asyncio
from typing import Optional, List, Dict, Any
import os


class AsyncDatabase:
    """Async database class for read-only operations to avoid cursor conflicts."""

    def __init__(self, db_path: str = "datas/rts.db"):
        self.db_path = db_path

    async def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dictionaries."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for concurrent access
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            
            # Enable row factory for dict-like access
            db.row_factory = aiosqlite.Row
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def _execute_scalar(self, query: str, params: tuple = ()) -> Any:
        """Execute a query and return a single scalar value."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for concurrent access
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    # Mapping-related async methods
    async def get_regions_data_async(
        self, filter_key: str = "All", filter_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get regions data with optional filtering - async version."""
        try:
            if filter_key == "All" or not filter_value:
                if filter_key == "All":
                    print("[AsyncDB] Filter key is 'All', returning empty list to use CSV colors")
                    return []

                query = """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                """
                return await self._execute_query(query)

            elif filter_key == "Continent":
                query = """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                    WHERE r.continent = ?
                """
                return await self._execute_query(query, (filter_value,))

            elif filter_key == "GeographicAreas":
                query = """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                    WHERE ga.name = ?
                """
                return await self._execute_query(query, (filter_value,))

            elif filter_key == "Countries":
                query = """
                    SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                           r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                           c.name as country_name
                    FROM Regions r
                    LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                    LEFT JOIN Countries c ON r.country_id = c.country_id
                    WHERE c.name = ?
                """
                return await self._execute_query(query, (filter_value,))

            return []

        except Exception as e:
            print(f"[AsyncDB] Error getting regions data: {e}")
            return []

    async def get_continental_statistics_async(self, continent: str) -> Dict[str, Any]:
        """Get statistics for a specific continent - async version."""
        try:
            # Get all regions in the continent
            total_regions = await self._execute_scalar(
                "SELECT COUNT(*) FROM Regions WHERE continent = ?", (continent,)
            ) or 0

            # Get controlled regions (regions with country_id)
            controlled_regions = await self._execute_scalar(
                "SELECT COUNT(*) FROM Regions WHERE continent = ? AND country_id IS NOT NULL",
                (continent,),
            ) or 0

            # Get free regions
            free_regions = total_regions - controlled_regions

            # Get unique countries in the continent
            played_countries = await self._execute_scalar(
                "SELECT COUNT(DISTINCT country_id) FROM Regions WHERE continent = ? AND country_id IS NOT NULL",
                (continent,),
            ) or 0

            # Get total countries (including those without regions)
            total_countries_result = await self._execute_scalar(
                """SELECT COUNT(DISTINCT c.country_id) 
                   FROM Countries c 
                   LEFT JOIN Regions r ON c.country_id = r.country_id 
                   WHERE r.continent = ? OR r.continent IS NULL""",
                (continent,),
            ) or 0

            total_countries = max(played_countries, total_countries_result)
            unplayed_countries = max(0, total_countries - played_countries)

            # Calculate percentages
            control_percentage = (
                (controlled_regions / total_regions * 100) if total_regions > 0 else 0
            )
            free_percentage = (
                (free_regions / total_regions * 100) if total_regions > 0 else 0
            )

            return {
                "total_regions": total_regions,
                "controlled_regions": controlled_regions,
                "free_regions": free_regions,
                "total_countries": total_countries,
                "played_countries": played_countries,
                "unplayed_countries": unplayed_countries,
                "control_percentage": control_percentage,
                "free_percentage": free_percentage,
            }

        except Exception as e:
            print(f"[AsyncDB] Error getting continental statistics for {continent}: {e}")
            return {
                "total_regions": 0,
                "controlled_regions": 0,
                "free_regions": 0,
                "total_countries": 0,
                "played_countries": 0,
                "unplayed_countries": 0,
                "control_percentage": 0.0,
                "free_percentage": 0.0,
            }

    async def get_world_statistics_async(self) -> Dict[str, Any]:
        """Get global world statistics - async version."""
        try:
            # Get all regions worldwide
            total_regions = await self._execute_scalar("SELECT COUNT(*) FROM Regions") or 0

            # Get controlled regions (regions with country_id)
            controlled_regions = await self._execute_scalar(
                "SELECT COUNT(*) FROM Regions WHERE country_id IS NOT NULL"
            ) or 0

            # Get free regions
            free_regions = total_regions - controlled_regions

            # Get total countries
            total_countries = await self._execute_scalar("SELECT COUNT(*) FROM Countries") or 0

            # Get played countries (countries that have at least one region)
            played_countries = await self._execute_scalar(
                "SELECT COUNT(DISTINCT country_id) FROM Regions WHERE country_id IS NOT NULL"
            ) or 0

            unplayed_countries = total_countries - played_countries

            # Calculate percentages
            control_percentage = (
                (controlled_regions / total_regions * 100) if total_regions > 0 else 0
            )
            free_percentage = (
                (free_regions / total_regions * 100) if total_regions > 0 else 0
            )

            return {
                "total_regions": total_regions,
                "controlled_regions": controlled_regions,
                "free_regions": free_regions,
                "total_countries": total_countries,
                "played_countries": played_countries,
                "unplayed_countries": unplayed_countries,
                "control_percentage": control_percentage,
                "free_percentage": free_percentage,
            }

        except Exception as e:
            print(f"[AsyncDB] Error getting world statistics: {e}")
            return {
                "total_regions": 0,
                "controlled_regions": 0,
                "free_regions": 0,
                "total_countries": 0,
                "played_countries": 0,
                "unplayed_countries": 0,
                "control_percentage": 0.0,
                "free_percentage": 0.0,
            }

    async def get_continent_country_count_async(self, continent: str) -> int:
        """Get the number of countries in a specific continent - async version."""
        try:
            result = await self._execute_scalar(
                "SELECT COUNT(DISTINCT country_id) FROM Regions WHERE continent = ? AND country_id IS NOT NULL",
                (continent,),
            )
            return result or 0
        except Exception as e:
            print(f"[AsyncDB] Error getting country count for {continent}: {e}")
            return 0

    async def get_country_datas_async(self, country_id: str) -> Optional[Dict[str, Any]]:
        """Get country data by ID - async version."""
        try:
            query = """
                SELECT country_id, name, role_id, public_channel_id, secret_channel_id 
                FROM Countries 
                WHERE country_id = ?
            """
            results = await self._execute_query(query, (country_id,))
            return results[0] if results else None
        except Exception as e:
            print(f"[AsyncDB] Error getting country data for {country_id}: {e}")
            return None

    async def get_all_regions_async(self) -> List[Dict[str, Any]]:
        """Get all regions - async version."""
        try:
            query = """
                SELECT r.region_id, r.country_id, r.name, r.region_color_hex, 
                       r.continent, r.geographical_area_id, ga.name as geographical_area_name,
                       c.name as country_name
                FROM Regions r
                LEFT JOIN GeographicalAreas ga ON r.geographical_area_id = ga.geographical_area_id
                LEFT JOIN Countries c ON r.country_id = c.country_id
            """
            return await self._execute_query(query)
        except Exception as e:
            print(f"[AsyncDB] Error getting all regions: {e}")
            return []

    async def get_geographical_areas_async(self) -> List[Dict[str, Any]]:
        """Get all geographical areas - async version."""
        try:
            query = "SELECT geographical_area_id, name FROM GeographicalAreas ORDER BY name"
            return await self._execute_query(query)
        except Exception as e:
            print(f"[AsyncDB] Error getting geographical areas: {e}")
            return []

    async def get_countries_async(self) -> List[Dict[str, Any]]:
        """Get all countries - async version."""
        try:
            query = "SELECT country_id, name FROM Countries ORDER BY name"
            return await self._execute_query(query)
        except Exception as e:
            print(f"[AsyncDB] Error getting countries: {e}")
            return []

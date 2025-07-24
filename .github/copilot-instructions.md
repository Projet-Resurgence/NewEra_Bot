# NEBot AI Coding Agent Instructions

## Project Overview
NEBot is a comprehensive Discord bot for managing post-apocalyptic geopolitical roleplay set in 2045. The bot handles complex multi-country economies, governments, military systems, territory management, and roleplay assistance through AI integration.

## Core Architecture Patterns

### 1. Centralized Utilities System
**Critical**: All cogs use the centralized utilities pattern via `src/shared_utils.py`:

```python
# Always import from shared_utils in cogs
from shared_utils import (
    get_db,
    get_discord_utils,
    CountryEntity,
    CountryConverter,
    ERROR_COLOR_INT,
    MONEY_COLOR_INT,
    P_POINTS_COLOR_INT,
    D_POINTS_COLOR_INT
)

# In cog __init__:
def __init__(self, bot):
    self.bot = bot
    self.db = get_db()
    self.dUtils = get_discord_utils(bot, self.db)
```

**Never** import `db` or `discord_utils` directly. Always use the centralized getter functions.

### 2. Cog System Architecture
All commands are organized into specialized cogs in `src/cogs/`:
- `economy.py` - Financial transactions (7 commands)
- `points.py` - Political/diplomatic points (10 commands)  
- `structures.py` - Building & construction (8 commands)
- `admin_utilities.py` - Administrative tools (12 commands)

**Cog Template** (use this pattern for new cogs):
```python
import discord
from discord.ext import commands
from shared_utils import get_db, get_discord_utils, ERROR_COLOR_INT

class NewCog(commands.Cog):
    """Description of the cog's purpose."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)
    
    @commands.hybrid_command()
    async def example_command(self, ctx):
        """Command description."""
        # Implementation here
        pass

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(NewCog(bot))
```

### 3. Database Integration Patterns

**Database Class**: `src/db.py` contains the `Database` class with SQLite operations.

**Key Schema Tables**:
- `Countries` - Central entity with Discord role/channel integration
- `Governments` - Composite key `(country_id, slot)` for government positions
- `Inventory` - Resource tracking (balance, pol_points, diplo_points, population_capacity)
- `Regions` - Geographic assignments with CASCADE deletes
- `Structures` - Building management with capacity column for production slots
- `Technologies` - Research and development tracking
- `Productions` - Active production assignments with composite key `(Structure_Id, Technology_Id)`

**Database Access Pattern**:
```python
# Get country data
country_data = self.db.get_country_datas(country_id)

# Check resources
has_money = self.db.has_enough_balance(country_id, amount)
has_points = self.db.has_enough_points(country_id, amount, type=1)  # 1=political, 2=diplomatic

# Update resources
self.db.add_balance(country_id, amount)
self.db.add_points(country_id, amount, type=1)

# Production system queries
structure_capacity = self.db.get_structure_capacity(structure_id)
tech_slot_usage = base_slots * (1 + tech_level / 10)  # Technology slot formula
```

### 4. CountryEntity System
Use the centralized `CountryEntity` class for country/player management:

```python
from shared_utils import CountryEntity, CountryConverter

# Command with country parameter
@commands.hybrid_command()
async def command_name(self, ctx, target: CountryConverter):
    country_entity = CountryEntity(target, ctx.guild)
    country_id = country_entity.get_country_id()
    country_dict = country_entity.to_dict()  # Returns {name, id, role}
```

### 5. Error Handling & Embed Patterns
**Standard Error Response**:
```python
if not success_condition:
    embed = discord.Embed(
        title="❌ Error Title",
        description="Error description",
        color=ERROR_COLOR_INT
    )
    return await ctx.send(embed=embed)
```

**Success Response Colors**:
- `ERROR_COLOR_INT` - Red for errors
- `MONEY_COLOR_INT` - Yellow for financial operations  
- `P_POINTS_COLOR_INT` - Blue for political points
- `D_POINTS_COLOR_INT` - Purple for diplomatic points
- `ALL_COLOR_INT` - Green for general success

### 6. Permission Systems
**Administrative Commands**:
```python
@commands.hybrid_command()
@commands.has_permissions(administrator=True)
async def admin_command(self, ctx):
    """Admin-only command."""
    pass

# For bi_admins_id system (super admins):
if ctx.author.id not in self.bi_admins_id:
    return await ctx.send("Access denied.")
```

**Government Permissions** (from database):
- `can_spend_money` - Financial transactions
- `can_spend_points` - Political/diplomatic points
- `can_sign_treaties` - International relations
- `can_build` - Construction projects
- `can_recruit` - Military recruitment
- `can_produce` - Manufacturing
- `can_declare_war` - Military declarations

## Critical Configuration Files

### Global Data Loading
Administrative cogs load global configuration from `datas/main.json`:
```python
def _load_global_data(self):
    """Load global data from JSON file."""
    try:
        with open("datas/main.json", "r") as f:
            json_data = json.load(f)
            self.bi_admins_id = json_data.get("bi_admins_id", [])
            self.continents_dict = json_data.get("continents_dict", {})
            self.usefull_role_ids_dic = json_data.get("usefull_role_ids_dic", {})
    except Exception as e:
        print(f"Failed to load global data: {e}")
```

### Environment Variables (.env)
- `TOKEN` - Discord bot token
- `GROQ_API_KEY` - AI integration
- `NOTION_TOKEN` - Task management integration
- `REMOVEBG_API_KEY` - Image processing

## Geopolitical Context & Features

### Roleplay Setting
- **Year**: 2045 post-apocalyptic world
- **Theme**: Geopolitical reconstruction and nation-building
- **Scope**: Multi-country management with complex diplomatic relationships

### Economic System
- Multi-currency: Balance (primary), Political Points, Diplomatic Points
- Population capacity management
- Industrial infrastructure with factory levels and slot-based production
- Resource trading between countries

#### Production & Construction System
- **Factory Tiers**: Buildings use tier-based capacity system (max tier 7) with percentage scaling
- **Slot-Based Production**: Factories have capacity slots, technologies consume slots based on complexity
- **Technology Scaling**: Tech slot consumption = `base_slots * (1 + tech_level / 10)`
  - Example: Level 6 firearm = `1 * (1 + 6/10) = 1.6 slots`
- **Regional Production**: Production tracked per structure (not per country) for territorial control
- **Database Schema**: 
  - `Productions` table: Primary key `(Structure_Id, Technology_Id)`
  - `Structures` table: Contains capacity column for slot management
  - Production calculations use views to aggregate by country

### Government System
- Up to 5 government positions per country
- Composite key architecture: `(country_id, slot)`
- Granular permission system for each position
- Discord role synchronization

### Military & Territory
- Military unit recruitment and deployment
- Region assignment and conquest mechanics
- Strategic infrastructure (bases, training facilities)
- Conflict resolution with automated calculations

## External Integrations

### Groq AI Assistant
```python
# AI integration with permission levels
async def ask_groq(self, user_message: str, level: str = "user") -> str:
    # Levels: "user" (400 tokens), "trusted" (800), "moderator" (2000), "admin" (8000)
    pass
```

### Notion Integration
- Task management synchronization
- External documentation
- Error handling for API connectivity

### Web Components
- **Admin Panel** (`admin-panel/`): Flask web interface for database management
- **Mapping Library** (`mapping-library/`): Interactive geographic visualization

## Development Workflow

### Adding New Commands
1. Determine appropriate cog based on functionality
2. Use centralized utilities pattern
3. Follow embed color standards
4. Implement proper error handling
5. Add permission checks if needed
6. Test with multiple countries/users

### Database Changes
1. Create/modify schema files in `datas/db_schemas/`
2. Database auto-initializes from `.sql` files
3. Maintain foreign key relationships
4. Use CASCADE deletes appropriately

### Testing Patterns
- Test with multiple countries
- Verify permission systems
- Check database integrity after operations
- Validate Discord role synchronization

## Common Pitfalls to Avoid

1. **Never** import `db` or `discord_utils` directly - always use `shared_utils`
2. **Never** hardcode color values - use the centralized constants
3. **Always** handle missing country data gracefully
4. **Always** validate permissions before sensitive operations
5. **Never** assume a user belongs to a country - check `get_country_id()`
6. **Always** use transactions for multi-step database operations
7. **Never** forget to commit database changes

## File Structure Reference
```
src/
├── main.py                 # Core bot initialization & legacy commands
├── shared_utils.py         # Centralized utilities (CRITICAL)
├── db.py                   # Database operations class
├── discord_utils.py        # Discord helper functions
├── cogs/                   # Modular command organization
│   ├── economy.py         # Financial transactions
│   ├── points.py          # Political/diplomatic points  
│   ├── structures.py      # Building & construction
│   └── admin_utilities.py # Administrative tools
├── construction.py        # Building system logic
├── currency.py           # Currency formatting
├── events.py             # Discord event handling
├── notion_handler.py     # External API integration
└── text_formatting.py   # String formatting utilities

datas/
├── rts.db                # Main SQLite database
├── main.json            # Global configuration
├── contexts.json        # Game state contexts
└── db_schemas/          # Database structure definitions
    ├── countries.sql    # Countries table
    ├── inventory.sql    # Resource tracking
    ├── regions.sql      # Geographic data
    └── *.sql           # Other schema definitions
```

## Quick Development Commands
```python
# Reload cogs during development
@commands.hybrid_command()
async def reload_cogs(self, ctx):
    """Reload all cogs."""
    pass

# List all loaded cogs and commands  
@commands.hybrid_command()
async def list_cogs(self, ctx):
    """List all loaded cogs and their commands."""
    pass
```

This bot manages complex geopolitical roleplay with extensive database relationships, permission systems, and Discord integration. Always prioritize data integrity and proper permission checking in your implementations.

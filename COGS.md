# NEBot Cog System Documentation

## Overview

NewEra Bot uses Discord.py's **cog system** to organize commands into logical modules. This modular approach provides better code organization, easier maintenance, and the ability to dynamically load/reload functionality without restarting the bot.

## Architecture

### Directory Structure
```
src/
├── main.py                  # Main bot file with core functionality
├── cogs/                    # Cog modules directory
│   ├── __init__.py         # Package initialization
│   ├── economy.py          # Economic commands (bal, money)
│   └── example.py          # Template for new cogs
├── db.py                   # Database utilities
├── currency.py             # Currency formatting functions
└── discord_utils.py        # Discord helper functions
```

## Creating New Cogs

### Basic Cog Template

```python
"""
Description of your cog functionality.
"""

import discord
from discord.ext import commands
from typing import Union

# Import any required local modules
import db
from currency import convert

class YourCogName(commands.Cog):
    """Brief description of the cog's purpose."""
    
    def __init__(self, bot):
        self.bot = bot
        # Define any color constants
        self.error_color_int = int("FF5733", 16)
        self.success_color_int = int("00FF44", 16)
    
    @commands.hybrid_command(name='your_command')
    async def your_command_function(self, ctx, argument: str = None):
        """Command description for help system."""
        # Your command logic here
        embed = discord.Embed(
            title="Command Result",
            description="Your response here",
            color=self.success_color_int
        )
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Event listener example."""
        if message.author.bot:
            return
        # Your event handling logic here

async def setup(bot):
    """Required setup function for the cog."""
    await bot.add_cog(YourCogName(bot))
```

### Adding Commands

#### Basic Command
```python
@commands.hybrid_command(name='hello')
async def hello_command(self, ctx):
    """Say hello to the user."""
    await ctx.send(f"Hello {ctx.author.mention}!")
```

#### Command with Arguments
```python
@commands.hybrid_command(name='greet')
async def greet_command(self, ctx, user: discord.Member):
    """Greet a specific user."""
    await ctx.send(f"Hello {user.mention}!")
```

#### Command with Permission Checks
```python
@commands.hybrid_command(name='admin_only')
@commands.has_permissions(administrator=True)
async def admin_command(self, ctx):
    """Admin-only command."""
    await ctx.send("This is an admin command!")
```

### Adding Event Listeners

```python
@commands.Cog.listener()
async def on_member_join(self, member):
    """Welcome new members."""
    channel = member.guild.system_channel
    if channel:
        await channel.send(f"Welcome {member.mention}!")

@commands.Cog.listener()
async def on_message_delete(self, message):
    """Log deleted messages."""
    print(f"Message deleted: {message.content}")
```

## Loading and Managing Cogs

### Automatic Loading (main.py)

Cogs are automatically loaded when the bot starts:

```python
async def load_cogs():
    """Load all cogs for the bot."""
    cogs_to_load = [
        'cogs.economy',
        'cogs.moderation',
        'cogs.utility'
        # Add new cogs here
    ]
    
    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f"✅ {cog} loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")

@bot.event
async def on_ready():
    await load_cogs()
```

### Manual Cog Management Commands

#### Reload Command (for development)
```python
@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def reload_cogs(ctx):
    """Reload all cogs."""
    for extension in list(bot.extensions.keys()):
        try:
            await bot.reload_extension(extension)
        except Exception as e:
            await ctx.send(f"Failed to reload {extension}: {e}")
            return
    await ctx.send("✅ All cogs reloaded successfully!")
```

#### Load/Unload Specific Cogs
```python
@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def load_cog(ctx, cog_name: str):
    """Load a specific cog."""
    try:
        await bot.load_extension(f'cogs.{cog_name}')
        await ctx.send(f"✅ {cog_name} loaded successfully!")
    except Exception as e:
        await ctx.send(f"❌ Failed to load {cog_name}: {e}")

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def unload_cog(ctx, cog_name: str):
    """Unload a specific cog."""
    try:
        await bot.unload_extension(f'cogs.{cog_name}')
        await ctx.send(f"✅ {cog_name} unloaded successfully!")
    except Exception as e:
        await ctx.send(f"❌ Failed to unload {cog_name}: {e}")
```

## Best Practices

### 1. **Organize by Functionality**
- Create separate cogs for different command categories
- Example: `economy.py`, `moderation.py`, `utility.py`, `games.py`

### 2. **Error Handling**
```python
@commands.hybrid_command()
async def safe_command(self, ctx):
    try:
        # Your command logic
        pass
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=self.error_color_int
        )
        await ctx.send(embed=embed)
```

### 3. **Consistent Styling**
- Use embed messages for consistent formatting
- Define color constants at the cog level
- Include helpful error messages

### 4. **Documentation**
- Add docstrings to all commands
- Include parameter descriptions
- Document any complex logic

### 5. **Shared Resources**
- Import common utilities (db, currency, etc.)
- Reuse color constants and formatting functions
- Avoid duplicating database connection logic

## Example: Economy Cog

The economy cog demonstrates proper cog structure:

```python
class Economy(commands.Cog):
    """Economy-related commands for managing currencies and balances."""
    
    def __init__(self, bot):
        self.bot = bot
        self.error_color_int = int("FF5733", 16)
        self.money_color_int = int("FFF005", 16)
    
    @commands.hybrid_command(name='bal')
    async def balance(self, ctx, country: CountryConverter = None):
        """Check the balance of a country or user."""
        # Implementation with proper error handling
        # Uses shared utilities (db, convert function)
        # Consistent embed formatting
```

## Migration from Main Bot File

When moving commands from `main.py` to cogs:

1. **Copy the command function** to the appropriate cog
2. **Add `self` parameter** as the first argument
3. **Import required dependencies** at the top of the cog file
4. **Update any global variable references** to use `self.bot` or cog attributes
5. **Remove the command from main.py**
6. **Add the cog to the loading list**

## Troubleshooting

### Common Issues

**Import Errors:**
- Ensure all required modules are imported in the cog file
- Check that relative imports are correct
- Verify the cog file is in the correct directory

**Command Not Found:**
- Confirm the cog is loaded successfully (check console output)
- Verify the command name matches the decorator
- Ensure the setup function is correctly defined

**Permission Errors:**
- Check that permission decorators are properly applied
- Verify the bot has the necessary permissions in Discord
- Ensure admin commands have appropriate checks

**Database Errors:**
- Verify database connection is working
- Check that required database functions are available
- Ensure proper error handling for database operations

This modular approach makes NEBot more maintainable and allows for easier feature development and testing.

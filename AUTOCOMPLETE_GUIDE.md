# Country Autocomplete Guide for NEBot

This guide explains how to use the new autocomplete functionality for country parameters in Discord slash commands.

## What is Autocomplete?

The autocomplete feature provides real-time suggestions when users type in slash command parameters. For country parameters, it will suggest:

1. **🏛️ Country Roles** - Discord roles representing countries (e.g., "🏛️ France")
2. **👤 Country Players** - Users who have government positions (e.g., "👤 Jean Dupont (France)")

## How It Works

When users start typing a country parameter in a slash command, Discord will show a dropdown list of matching countries and players. Users can:
- Type part of a country name to filter results
- Type part of a player's name to find their country
- Click on a suggestion to auto-complete the parameter

## Implementation

### For Developers

To add autocomplete to a command parameter, follow these steps:

1. **Import the required modules** in your cog file:
```python
from discord import app_commands
from shared_utils import country_autocomplete
```

2. **Add the autocomplete decorator** to your command:
```python
@commands.hybrid_command(name="your_command")
@app_commands.autocomplete(country=country_autocomplete)  # Replace 'country' with your parameter name
async def your_command(self, ctx, country: CountryConverter):
    # Your command logic here
```

### Example Implementation

Here's a complete example from the economy cog:

```python
@commands.hybrid_command(
    name="bal",
    brief="Affiche le solde d'un pays ou utilisateur.",
    description="Consulte le solde monétaire d'un pays spécifique ou de votre propre pays.",
)
@app_commands.autocomplete(country=country_autocomplete)
async def balance(
    self,
    ctx,
    country: CountryConverter = commands.parameter(
        default=None,
        description="Pays dont afficher le solde (optionnel, votre pays par défaut)",
    ),
):
    # Command implementation
```

### How to Add to More Commands

To add autocomplete to other commands that use `CountryConverter`:

1. Add the import: `from shared_utils import country_autocomplete`
2. Add the decorator: `@app_commands.autocomplete(parameter_name=country_autocomplete)`
3. The parameter name in the decorator must match the actual parameter name in your function

### Example for Multiple Parameters

If you have multiple country parameters:

```python
@app_commands.autocomplete(
    sender_country=country_autocomplete,
    receiver_country=country_autocomplete
)
async def transfer_command(self, ctx, sender_country: CountryConverter, receiver_country: CountryConverter):
    # Implementation
```

## Troubleshooting

If autocomplete doesn't work:

1. **Check imports** - Make sure you've imported `app_commands` and `country_autocomplete`
2. **Verify decorator syntax** - The parameter name must match exactly
3. **Database connection** - Ensure the database is accessible
4. **Guild context** - Autocomplete only works in servers, not DMs
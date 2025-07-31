# Production System Documentation

## Overview
The production system allows countries to manufacture technologies they have licenses for in their factories (usines). It includes automated production processing and technology trading between countries.

## Features Implemented

### 1. Technology Production (`start_production` command)
Start manufacturing technologies in your factories.

**Usage:**
```
/start_production <structure_id> <technology_id> <quantity>
```

**Example:**
```
/start_production 5 12 10
```
This starts production of 10 units of technology ID 12 in factory ID 5.

**Requirements:**
- Factory must be owned by your country
- Factory must have available slots
- Your country must have the technology license (ownership or license)
- Sufficient resources (money/materials) based on technology costs

**Production Times:**
- Default: 1 month
- Frigates: 2 months
- Aircraft Carriers & Nuclear Submarines: 12 months

### 2. Technology Trading (`sell_technology` command)
Sell technology inventory to other countries.

**Usage:**
```
/sell_technology "<buyer_country>" <technology_id> <quantity> [price] [per_unit]
```

**Examples:**
```
/sell_technology "France" 12 5 1000
# Sells 5 units of tech 12 to France for 1000 total

/sell_technology "France" 12 5 200 True  
# Sells 5 units of tech 12 to France for 200 per unit (1000 total)
```

**Features:**
- Automatic inventory validation
- Secure money transfers
- Support for total price or per-unit pricing
- Transaction logging

### 3. Production Monitoring (`view_productions` command)
View all ongoing productions for your country.

**Usage:**
```
/view_productions
```

**Shows:**
- Factory ID and technology being produced
- Quantity and completion date
- Time remaining for each production
- Production status

### 4. Automated Processing
Production cycles are automatically processed daily at 7:00 AM Paris time.

**Features:**
- Automatic completion of finished productions
- Inventory updates
- Discord notifications for completed productions
- Special timing handling for military vehicles

## Database Tables

### StructureProduction
Tracks ongoing productions:
- `production_id`: Unique identifier
- `structure_id`: Factory performing production
- `technology_id`: Technology being produced
- `quantity`: Amount being produced
- `start_year/month`: Production start date
- `end_year/month`: Expected completion date

### Integration with Existing Systems
- Uses existing `Technologies` table for licensing
- Uses existing `Structures` table for factory validation
- Uses existing `CountryTechnologyInventory` for inventory management
- Integrates with economy system for cost calculations

## Admin Features
The admin panel includes full CRUD operations for:
- Production management
- Technology licensing
- Factory configuration
- Inventory tracking

## Technical Implementation

### Database Methods Added:
1. `start_production()` - Validates and starts production
2. `has_technology_access()` - Checks licensing rights
3. `sell_technology_inventory()` - Handles secure trading
4. `process_production_cycle()` - Automated daily processing
5. `get_country_productions()` - Retrieves active productions

### Discord Commands Added:
1. `start_production` - User interface for starting production
2. `sell_technology` - User interface for trading
3. `view_productions` - Monitor ongoing productions

### Task Loop Integration:
- Daily processing at 7:00 AM Paris time
- Automatic completion and notification
- Special timing for military vehicles

## Usage Tips

1. **Check Available Slots**: Factories have limited production slots
2. **Verify Licenses**: You need technology ownership or valid license
3. **Monitor Resources**: Ensure sufficient funds for production costs
4. **Plan Timing**: Military vehicles take longer to produce
5. **Use Trading**: Build diplomatic relationships through technology exchange

## Error Handling
The system includes comprehensive error handling for:
- Invalid factory IDs
- Insufficient resources
- Missing licenses
- Capacity limitations
- Database errors

All operations are logged and provide clear error messages to users.

# NewEra Bot Admin Panel

A comprehensive web-based administration panel for managing the NewEra Discord bot's database.

## Features

- **Dashboard**: Overview of all database tables with statistics
- **Countries**: Manage countries, their Discord roles, channels, and settings
- **Governments**: Manage government positions with detailed permission systems (using composite keys!)
- **Inventory**: Manage country resources (balance, points, military units)
- **Regions**: Manage geographical regions and their assignments
- **Structures**: Manage buildings, factories, and infrastructure
- **Technologies**: Manage technological developments and research

## Installation

1. Install required Python packages:
```bash
pip install flask flask-sqlalchemy
```

2. Navigate to the admin panel directory:
```bash
cd /home/ubuntu/Bots/NEBot/admin-panel
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and go to: `http://localhost:5000`

## Usage

### Adding New Countries
1. Go to Countries → Add Country
2. Fill in the required Discord role ID, channel IDs, and country name
3. The system will automatically create a country with a unique ID

### Managing Government Positions
1. Go to Governments → Add Government Position  
2. Select a country and slot (1-5)
3. Assign a Discord user ID and set permissions
4. The composite primary key (country_id, slot) ensures no duplicate positions

### Bulk Operations
- Use the dashboard for quick navigation between sections
- Each table shows current counts for easy monitoring
- Search and filter functionality available in each section

## Database Schema Highlights

### Composite Keys
The `Governments` table uses a composite primary key `(country_id, slot)` which allows:
- Each country to have up to 5 government positions
- Each position to be unique within a country
- Efficient querying and data integrity

### Foreign Key Relationships
- All tables maintain referential integrity with CASCADE deletes
- Countries are the central entity that other tables reference
- Regions can be assigned to countries or remain unassigned

### Permission System
Government positions have granular permissions:
- `can_spend_money`: Financial transactions
- `can_spend_points`: Political/diplomatic point usage  
- `can_sign_treaties`: International relations
- `can_build`: Construction projects
- `can_recruit`: Military recruitment
- `can_produce`: Manufacturing control
- `can_declare_war`: Military declarations

## Security Notes

**Important**: This admin panel is for development/administration use only:
- Change the `app.secret_key` in production
- Add authentication/authorization before deploying
- Consider IP restrictions for admin access
- Use HTTPS in production environments

## Troubleshooting

### Database Connection Issues
- Ensure the database file exists at `../datas/rts.db`
- Check file permissions for read/write access
- Verify SQLite database isn't corrupted

### Template Errors
- All templates extend `base.html` for consistency
- Bootstrap 5 is used for styling via CDN
- Flash messages provide user feedback for operations

### Development
- Debug mode is enabled by default
- The app runs on `0.0.0.0:5000` for network access
- Auto-reload is enabled for development

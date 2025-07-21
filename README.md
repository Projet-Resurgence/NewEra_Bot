# NewEra Bot - Complete Geopolitical RP Discord Management System

> **A comprehensive Discord bot ecosystem for managing post-apocalyptic geopolitical roleplay communities**

[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2-blue.svg)](https://github.com/Rapptz/discord.py)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌍 Project Overview

NewEra Bot is a sophisticated Discord bot designed specifically for the **NewEra RP** community - a post-apocalyptic geopolitical roleplay set in 2045. This comprehensive system manages countries, governments, economies, military operations, and complex diplomatic relationships in a persistent game world.

### 🎯 Core Mission
Transform Discord servers into immersive geopolitical simulation environments where players can:
- Lead nations in a post-apocalyptic world
- Manage complex economies and resources
- Engage in diplomatic negotiations and warfare
- Build infrastructure and technological advancement
- Experience dynamic storytelling through AI-assisted narratives

---

## 🚀 Key Features

### 🏛️ **Government & Political System**
- **Multi-tier Government Positions**: Up to 5 government slots per country with granular permissions
- **Permission Management**: Control over spending, building, military recruitment, treaty signing, and war declarations
- **Role-based Access Control**: Automatic Discord role assignment and management
- **Composite Key Architecture**: Ensures data integrity and prevents position conflicts

### 💰 **Economic Management**
- **Multi-currency System**: Balance management, political points, and resource tracking
- **Industrial Infrastructure**: Factory systems with multiple levels and production capabilities
- **Resource Trading**: Inter-country economic relationships and trade management
- **Construction Projects**: Building management with different types and upgrade paths

### ⚔️ **Military & Warfare**
- **Military Unit Management**: Recruitment, deployment, and battle systems
- **Strategic Infrastructure**: Military bases, training facilities, and defensive structures
- **Conflict Resolution**: Automated battle calculations and diplomatic consequences
- **Territorial Control**: Region assignment and conquest mechanics

### 🗺️ **Geographic Systems**
- **Interactive Mapping**: Visual country and region management through web interface
- **Territory Assignment**: Dynamic region control and boundary management
- **Continental Organization**: Structured geographic hierarchy with automated channel management

### 🤖 **AI Integration**
- **Groq AI Assistant**: Context-aware RP assistance for narrative generation
- **Anti-flood Protection**: Rate limiting and permission-based access controls
- **Contextual Responses**: AI responses tailored to the post-apocalyptic setting
- **Multiple Access Levels**: User, trusted, moderator, and admin AI interaction tiers

### 📊 **Data Management**
- **SQLite Database**: Robust data persistence with foreign key relationships
- **Automated Backups**: Database versioning and recovery systems
- **Notion Integration**: External documentation and planning synchronization
- **Comprehensive Logging**: Error tracking and system monitoring

---

## 🏗️ System Architecture

### **Core Components**

```
📁 NewEra_Bot/
├── 🤖 src/                     # Main bot application
│   ├── main.py                 # Primary bot logic & commands
│   ├── db.py                   # Database operations
│   ├── discord_utils.py        # Discord API utilities
│   ├── construction.py         # Building & infrastructure
│   ├── currency.py            # Economic systems
│   ├── events.py              # Event handling
│   └── notion_handler.py       # External integrations
│
├── 🌐 admin-panel/             # Web administration interface
│   ├── app.py                  # Flask web application
│   ├── templates/              # HTML templates
│   └── admin.db               # Admin user management
│
├── 🗺️ mapping-library/         # Interactive mapping system
│   ├── server.py              # Map server application
│   ├── maps_images/           # Geographic visualizations
│   └── gunicorn.conf.py       # Production server config
│
├── 📋 rules/                   # Game rules & regulations
│   ├── summary.json           # Rules overview
│   ├── hrp.json              # Out-of-character rules
│   ├── rp.json               # Roleplay guidelines
│   ├── military.json         # Combat regulations
│   └── territorial.json       # Geographic rules
│
├── 💾 datas/                   # Data storage & schemas
│   ├── rts.db                # Main game database
│   ├── contexts.json         # Game state contexts
│   └── db_schemas/           # Database structure definitions
│
└── 📜 old/                     # Legacy code & backups
```

---

## ⚡ Quick Start

### **Prerequisites**
- Python 3.10+
- Discord Bot Token
- SQLite3
- Git

### **Installation**

1. **Clone the Repository**
```bash
git clone git@github.com:AnnonyWOLFRODA/NewEra_Bot.git
cd NewEra_Bot
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Configuration**
Create a `.env` file in the root directory:
```env
TOKEN=your_discord_bot_token
REMOVEBG_API_KEY=your_removebg_api_key
GROQ_API_KEY=your_groq_api_key
NOTION_TOKEN=your_notion_integration_token
```

4. **Database Setup**
```bash
# The bot will automatically create necessary database tables on first run
python3 ./src/main.py
```

5. **Launch Admin Panel** (Optional)
```bash
cd admin-panel
python3 app.py
# Access at http://localhost:5000
```

6. **Start Mapping System** (Optional)
```bash
cd mapping-library
python3 server.py
# Access at http://localhost:8000
```

---

## 🎮 Bot Commands Reference

### **�️ Administrative Commands**
- `.del_betw <start_msg> <end_msg>` - Bulk delete messages
- `.send_rules <webhook_url>` - Deploy rules to channels
- `.reformat_rp_channels` - Standardize channel naming
- `.reload_cogs` - Reload all cogs (ADMIN ONLY)
- `.drop_all_except_inventory` - Database maintenance (ADMIN ONLY)

### **💰 Economic Commands** (Economy Cog)
- `.bal [country]` - Check balance of country or user
- `.money [country]` - Alias for balance command

### **💵 Financial Management Commands**
- `.add_money <user> <amount>` - Add funds to user account
- `.remove_money <user> <amount>` - Deduct funds from user account
- `.give <country> <amount>` - Transfer money to another country
- `.set_points <user> <amount>` - Set political points
- `.points <user>` - Check political points balance

### **🏭 Industrial Commands**
- `.usine <user> [level]` - Check factory holdings
- `.add_usine <user> <amount> <level>` - Add factories
- `.remove_usine <user> <amount> <level>` - Remove factories
- `.set_usine <user> <amount> <level>` - Set factory count
- `.batiments <type> [user]` - View buildings inventory

### **🏛️ Government Commands**
- `.set_base <type> <user> <amount> <level>` - Configure military bases
- `.remove_bat <building_id>` - Remove specific building
- `.sync_cats <target> <model>` - Synchronize category permissions

### **🤖 AI Assistance**
- `.groq_chat <message>` - Chat with AI assistant (3-minute cooldown)
- `.brief_chat_til <message_id>` - Summarize RP situation
- `.ask_rp_questions <question> <message_id>` - Ask contextual RP questions

### **🛠️ Administrative Commands**
- `.del_betw <start_msg> <end_msg>` - Bulk delete messages
- `.send_rules <webhook_url>` - Deploy rules to channels
- `.reformat_rp_channels` - Standardize channel naming
- `.drop_all_except_inventory` - Database maintenance (ADMIN ONLY)

---

## 🌐 Admin Panel Features

### **Dashboard Overview**
- Real-time statistics for all database tables
- Quick navigation between management sections
- System health monitoring and alerts

### **Country Management**
- Create and configure nations with Discord integration
- Assign roles, channels, and permissions automatically
- Track economic and military statistics
- Manage diplomatic relationships

### **Government Positions**
- Assign up to 5 government positions per country
- Granular permission system for each position
- Composite primary key ensures data integrity
- Real-time Discord role synchronization

### **Resource Management**
- Monitor and adjust country inventories
- Track balance, political points, and military units
- Bulk operations for administrative efficiency
- Export data for analysis

---

## 🗺️ Interactive Mapping System

### **Features**
- **Click-to-Color Interface**: Intuitive territory management
- **Multi-Map Support**: Countries and regions on separate views
- **Responsive Design**: Works on desktop and mobile devices
- **Dynamic Legend**: Shows only active territories
- **Production Ready**: Gunicorn deployment configuration

### **Deployment Options**
```bash
# Development Mode
./start-dev.sh

# Production Mode  
./start-production.sh
```

---

## 🔧 Configuration & Customization

### **Cog System Architecture**
NewEra Bot uses Discord.py's cog system for modular command organization:

```
📁 src/cogs/
├── __init__.py              # Package initialization
├── economy.py               # Economic commands (bal, money)
└── example.py               # Template for new cogs
```

**Creating New Cogs:**
```python
# src/cogs/my_cog.py
import discord
from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='mycommand')
    async def my_command(self, ctx):
        await ctx.send("Hello from my cog!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

**Loading Cogs:**
- Cogs are automatically loaded when the bot starts via `on_ready()` event
- Use `.reload_cogs` command (admin only) to reload during development
- Add new cogs to the `load_cogs()` function in `main.py`
- See [COGS.md](COGS.md) for detailed cog development documentation

### **Database Schema**
The system uses SQLite with carefully designed relationships:
- **Countries**: Central entity with Discord integration
- **Governments**: Composite keys for position management
- **Inventory**: Resource tracking with foreign key constraints
- **Regions**: Geographic assignments with cascade deletes
- **Structures**: Building management with type categorization
- **Technologies**: Research and development tracking

### **Permission System**
Government positions support granular permissions:
- `can_spend_money`: Financial transaction authority
- `can_spend_points`: Political point usage rights
- `can_sign_treaties`: Diplomatic agreement powers
- `can_build`: Construction project authorization
- `can_recruit`: Military recruitment capabilities
- `can_produce`: Manufacturing control access
- `can_declare_war`: Military conflict initiation

### **AI Integration Levels**
- **User** (400 tokens): Basic RP assistance
- **Trusted** (800 tokens): Enhanced responses
- **Moderator** (2000 tokens): Administrative support
- **Admin** (8000 tokens): Full system access

---

## 🔒 Security & Production Notes

### **Development Security**
- Change `app.secret_key` before production deployment
- Implement authentication for admin panel access
- Configure IP restrictions for sensitive operations
- Use HTTPS in production environments

### **Database Security**
- Regular automated backups to prevent data loss
- Foreign key constraints ensure referential integrity
- Transaction logging for audit trails
- Graceful error handling prevents data corruption

### **Discord Security**
- Role-based command access control
- Rate limiting on AI interactions
- Webhook validation for external integrations
- Anti-spam protection on sensitive commands

---

## 🐛 Troubleshooting

### **Common Issues**

**Bot Connection Problems**
```bash
# Check token validity
grep TOKEN .env
# Verify bot permissions in Discord Developer Portal
# Ensure all required intents are enabled
```

**Database Issues**
```bash
# Check database file permissions
ls -la datas/rts.db
# Backup current database
cp datas/rts.db datas/rts.db.backup
# Reset database (CAUTION: Data loss)
rm datas/rts.db  # Bot will recreate on restart
```

**Admin Panel Access**
```bash
# Check Flask dependencies
pip install flask flask-sqlalchemy
# Verify database path in app.py
# Test with curl: curl http://localhost:5000
```

**Mapping System Issues**
```bash
# Verify image files exist
ls mapping-library/maps_images/
# Check configuration files
cat mapping-library/map_*_config.txt
# Test with development server first
cd mapping-library && python3 server.py
```

---

## 🤝 Contributing

We welcome contributions to improve NewEra Bot! Here's how you can help:

### **Development Guidelines**
1. Fork the repository and create a feature branch
2. Follow Python PEP 8 style guidelines
3. Add comprehensive documentation for new features
4. Test changes thoroughly before submitting
5. Update relevant README sections for new functionality

### **Feature Requests**
- Open an issue with detailed feature description
- Explain the use case and expected behavior
- Consider backward compatibility implications
- Provide mockups or examples when relevant

### **Bug Reports**
- Include steps to reproduce the issue
- Provide relevant log files and error messages
- Specify your Python version and dependencies
- Test with the latest version before reporting

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🏆 Acknowledgments

- **Discord.py Community**: For the excellent Discord API wrapper
- **NewEra RP Community**: For testing and feedback
- **Groq**: For AI integration capabilities
- **Flask Community**: For the web framework powering the admin panel

---

## 📞 Support & Contact

For support, feature requests, or general questions:
- **GitHub Issues**: Use for bug reports and feature requests
- **Discord**: Join the NewEra RP community server
- **Documentation**: Check the individual component READMEs for detailed guides

---

*Built with ❤️ for the NewEra RP community* 
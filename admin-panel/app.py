from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    jsonify,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os
import json
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Generate secure random key

# Configure multiple databases
admin_db_path = os.path.join(os.path.dirname(__file__), "admin.db")
game_db_path = os.path.join(os.path.dirname(__file__), "../datas/rts.db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:////" + admin_db_path
)  # Default for admin users
app.config["SQLALCHEMY_BINDS"] = {
    "game": "sqlite:////" + game_db_path  # Game data database
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# All database models
class User(db.Model):
    """Admin Users - stored in separate admin database"""

    __tablename__ = "AdminUsers"
    # Uses default database (admin.db)

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_users = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.String, default=lambda: str(datetime.now()))
    last_login = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)


# Game database models
class Country(db.Model):
    """Countries - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Countries"

    country_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    public_channel_id = db.Column(db.String, nullable=False)
    secret_channel_id = db.Column(db.String)
    last_bilan = db.Column(db.String)


class Government(db.Model):
    """Governments - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Governments"

    country_id = db.Column(db.Integer, primary_key=True)
    slot = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.String, nullable=False)
    can_spend_money = db.Column(db.Boolean, default=False)
    can_spend_points = db.Column(db.Boolean, default=False)
    can_sign_treaties = db.Column(db.Boolean, default=False)
    can_build = db.Column(db.Boolean, default=False)
    can_recruit = db.Column(db.Boolean, default=False)
    can_produce = db.Column(db.Boolean, default=False)
    can_declare_war = db.Column(db.Boolean, default=False)


class Doctrine(db.Model):
    """Doctrines - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Doctrines"

    doctrine_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    category = db.Column(db.String)  # Régime, Idéologie, Économie, Religieux
    description = db.Column(db.Text)
    discord_role_id = db.Column(db.String)
    bonus_json = db.Column(db.Text)  # JSON string for bonuses


class Inventory(db.Model):
    """Inventory - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Inventory"

    country_id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Integer, default=0, nullable=False)
    pol_points = db.Column(db.Integer, default=0, nullable=False)
    diplo_points = db.Column(db.Integer, default=0, nullable=False)


class Region(db.Model):
    """Regions - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Regions"

    region_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    country_id = db.Column(db.Integer)
    name = db.Column(db.String, nullable=False)
    mapchart_name = db.Column(db.String, nullable=False)
    population = db.Column(db.Integer, default=0, nullable=False)


class Structure(db.Model):
    """Structures - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Structures"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    region_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String, nullable=False)
    specialisation = db.Column(db.String, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    capacity = db.Column(db.Integer, default=0, nullable=False)
    population = db.Column(db.Integer, default=0, nullable=False)


class Stats(db.Model):
    """Stats - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Stats"

    country_id = db.Column(db.Integer, primary_key=True)
    tech_level = db.Column(db.Integer, default=1, nullable=False)
    gdp = db.Column(db.Integer, default=0, nullable=False)


class Technology(db.Model):
    """Technologies - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Technologies"

    tech_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    cost = db.Column(db.Integer, default=0, nullable=False)
    specialisation = db.Column(db.String, nullable=False)
    development_time = db.Column(db.Integer, default=0, nullable=False)
    development_cost = db.Column(db.Integer, default=0, nullable=False)
    slots_taken = db.Column(db.Float, default=1.0, nullable=False)
    original_name = db.Column(db.String, nullable=False)
    technology_level = db.Column(db.Integer, default=1, nullable=False)
    image_url = db.Column(db.String)
    developed_by = db.Column(db.Integer)
    exported = db.Column(db.Boolean, default=False)
    is_secret = db.Column(db.Boolean, default=False)
    type = db.Column(db.String, nullable=False)
    difficulty_rating = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    created_at = db.Column(db.String)


class CountryTechnology(db.Model):
    """Country Technologies - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "CountryTechnologies"

    country_id = db.Column(db.Integer, primary_key=True)
    tech_field = db.Column(db.String, primary_key=True)
    level = db.Column(db.Integer, default=1, nullable=False)


class StructureData(db.Model):
    """Structure Data - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "StructuresDatas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String, nullable=False)
    specialisation = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer, default=0, nullable=False)
    population = db.Column(db.Integer, default=0, nullable=False)
    cout_construction = db.Column(db.Integer, nullable=False)


class StructureProduction(db.Model):
    """Structure Production - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "StructureProduction"

    structure_id = db.Column(db.Integer, primary_key=True)
    tech_id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    days_remaining = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.String)


class CountryDoctrine(db.Model):
    """Country Doctrines - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "CountryDoctrines"

    country_id = db.Column(db.Integer, primary_key=True)
    doctrine_id = db.Column(db.Integer, primary_key=True)


class TechnologyAttribute(db.Model):
    """Technology Attributes - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "TechnologyAttributes"

    tech_id = db.Column(db.Integer, primary_key=True)
    attribute_name = db.Column(db.String, primary_key=True)
    attribute_value = db.Column(db.String, nullable=False)


class TechnologyLicense(db.Model):
    """Technology Licenses - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "TechnologyLicenses"

    license_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tech_id = db.Column(db.Integer, nullable=False)
    country_id = db.Column(db.Integer, nullable=False)
    license_type = db.Column(
        db.String, nullable=False
    )  # Must be 'commercial' or 'personal' only
    granted_by = db.Column(db.Integer)
    granted_at = db.Column(
        db.String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


class CountryTechnologyInventory(db.Model):
    """Country Technology Inventory - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "CountryTechnologyInventory"

    country_id = db.Column(db.Integer, primary_key=True)
    tech_id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)


class CountryTechnologyProduction(db.Model):
    """Country Technology Production - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "CountryTechnologyProduction"

    production_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    country_id = db.Column(db.Integer, nullable=False)
    tech_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    days_remaining = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.String)


class GameDate(db.Model):
    """Game Dates - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Dates"

    year = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.Integer, primary_key=True)
    playday = db.Column(db.Integer, primary_key=True)
    real_date = db.Column(
        db.String, nullable=False
    )  # Changed to String to handle datetime parsing

    @property
    def real_date_formatted(self):
        """Return formatted date string for display"""
        try:
            if isinstance(self.real_date, str):
                # Handle datetime strings
                if "T" in self.real_date:
                    from datetime import datetime

                    dt = datetime.fromisoformat(self.real_date.replace("+00:00", ""))
                    return dt.strftime("%Y-%m-%d")
                else:
                    return self.real_date
            return str(self.real_date)
        except:
            return str(self.real_date)


class PlaydaysPerMonth(db.Model):
    """Playdays Per Month - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "PlaydaysPerMonth"

    month_number = db.Column(db.Integer, primary_key=True)
    playdays = db.Column(db.Integer, nullable=False)


class ServerSettings(db.Model):
    """Server Settings - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "ServerSettings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(500), nullable=False)


# New models for updated schema
class TechnologyData(db.Model):
    """Technology Data - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "TechnologyDatas"

    type = db.Column(db.String, primary_key=True)
    specialisation = db.Column(db.String, nullable=False)
    minimum_slots_taken = db.Column(db.Float, default=1.0, nullable=False)
    maximum_slots_taken = db.Column(db.Float, default=1.0, nullable=False)
    minimum_dev_cost = db.Column(db.Integer, default=0, nullable=False)
    minimum_dev_time = db.Column(db.Integer, default=0, nullable=False)
    minimum_prod_cost = db.Column(db.Integer, default=0, nullable=False)
    maximum_dev_cost = db.Column(db.Integer, default=0, nullable=False)
    maximum_dev_time = db.Column(db.Integer, default=0, nullable=False)
    maximum_prod_cost = db.Column(db.Integer, default=0, nullable=False)


class TechnologyRatio(db.Model):
    """Technology Ratios - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "TechnologyRatios"

    type = db.Column(db.String, primary_key=True)
    level = db.Column(db.Integer, primary_key=True)
    ratio_cost = db.Column(db.Integer, nullable=False)
    ratio_time = db.Column(db.Integer, nullable=False)
    ratio_slots = db.Column(db.Float, nullable=False)


class InventoryUnit(db.Model):
    """Inventory Units - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "InventoryUnits"

    country_id = db.Column(db.Integer, primary_key=True)
    unit_type = db.Column(db.String, primary_key=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)


class InventoryPricing(db.Model):
    """Inventory Pricings - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "InventoryPricings"

    item = db.Column(db.String, primary_key=True)
    price = db.Column(db.Integer, nullable=False)
    maintenance = db.Column(db.Integer, nullable=False)


class Treaty(db.Model):
    """Treaties - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Treaties"

    treaty_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    treaty_type = db.Column(db.String(50), nullable=False)
    country_a = db.Column(db.Integer, nullable=False)
    country_b = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.String, nullable=False)
    end_date = db.Column(db.String)
    status = db.Column(db.String(20), nullable=False)


class Alliance(db.Model):
    """Alliances - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "Alliances"

    alliance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alliance_name = db.Column(db.String(100), nullable=False)
    country_a = db.Column(db.Integer, nullable=False)
    country_b = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.String, nullable=False)
    end_date = db.Column(db.String)
    alliance_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)


class WarDeclaration(db.Model):
    """War Declarations - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "WarDeclarations"

    war_declaration_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    country_a = db.Column(db.Integer, nullable=False)
    country_b = db.Column(db.Integer, nullable=False)
    declaration_date = db.Column(db.String, nullable=False)
    status = db.Column(db.String(20), nullable=False)


# Authentication decorators
def login_required(f):
    """Decorator to require login for routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))

        user = db.session.get(User, session["user_id"])
        if not user or not user.can_manage_users:
            flash("Admin privileges required for this action.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """Get current logged in user"""
    if "user_id" in session:
        return db.session.get(User, session["user_id"])
    return None


# Routes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            session["user_id"] = user.user_id
            session["username"] = user.username
            session["is_admin"] = user.can_manage_users

            # Update last login
            user.last_login = str(datetime.now())
            db.session.commit()

            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials or account disabled.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        user = get_current_user()

        if not user.check_password(current_password):
            flash("Current password is incorrect.", "error")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "error")
        elif len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "error")
        else:
            user.set_password(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("index"))

    return render_template("change_password.html")


# User management routes (admin only)
@app.route("/users")
@admin_required
def users():
    users = User.query.all()
    return render_template("users.html", users=users)


@app.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        try:
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]

            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "error")
                return render_template("add_user.html")

            if User.query.filter_by(email=email).first():
                flash("Email already exists.", "error")
                return render_template("add_user.html")

            if len(password) < 6:
                flash("Password must be at least 6 characters long.", "error")
                return render_template("add_user.html")

            user = User(
                username=username,
                email=email,
                is_admin=bool(request.form.get("is_admin")),
                can_manage_users=bool(request.form.get("can_manage_users")),
                is_active=bool(request.form.get("is_active", True)),
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()
            flash(f"User {username} created successfully!", "success")
            return redirect(url_for("users"))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template("add_user.html")


@app.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        try:
            # Don't allow editing your own admin status
            current_user = get_current_user()
            if user_id == current_user.user_id and not bool(
                request.form.get("can_manage_users")
            ):
                flash("You cannot remove your own admin privileges.", "error")
                return render_template("edit_user.html", user=user)

            user.username = request.form["username"]
            user.email = request.form["email"]
            user.is_admin = bool(request.form.get("is_admin"))
            user.can_manage_users = bool(request.form.get("can_manage_users"))
            user.is_active = bool(request.form.get("is_active"))

            # Reset password if provided
            new_password = request.form.get("new_password")
            if new_password:
                if len(new_password) < 6:
                    flash("Password must be at least 6 characters long.", "error")
                    return render_template("edit_user.html", user=user)
                user.set_password(new_password)

            db.session.commit()
            flash(f"User {user.username} updated successfully!", "success")
            return redirect(url_for("users"))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template("edit_user.html", user=user)


@app.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        current_user = get_current_user()

        # Don't allow deleting yourself
        if user_id == current_user.user_id:
            flash("You cannot delete your own account.", "error")
        else:
            db.session.delete(user)
            db.session.commit()
            flash(f"User {user.username} deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for("users"))


@app.route("/")
@login_required
def index():
    # Get counts for each table
    tables_info = {
        "Countries": Country.query.count(),
        "Governments": Government.query.count(),
        "Doctrines": Doctrine.query.count(),
        "Inventory": Inventory.query.count(),
        "Regions": Region.query.count(),
        "Structures": Structure.query.count(),
        "Stats": Stats.query.count(),
        "Technologies": Technology.query.count(),
        "CountryTechnologies": CountryTechnology.query.count(),
        "Users": User.query.count(),
        "StructureData": StructureData.query.count(),
        "Productions": StructureProduction.query.count(),
        "TechnologyAttributes": TechnologyAttribute.query.count(),
        "TechnologyLicenses": TechnologyLicense.query.count(),
        "CountryTechInventory": CountryTechnologyInventory.query.count(),
        "CountryTechProduction": CountryTechnologyProduction.query.count(),
        "CountryDoctrines": CountryDoctrine.query.count(),
        "GameDate": GameDate.query.count(),
        "PlaydaysPerMonth": PlaydaysPerMonth.query.count(),
    }

    # Calculate total playdays across all months
    total_playdays = (
        db.session.query(db.func.sum(PlaydaysPerMonth.playdays)).scalar() or 0
    )

    # Get current game date
    current_date = GameDate.query.order_by(GameDate.real_date.desc()).first()

    # Get pause status from ServerSettings
    is_paused_setting = ServerSettings.query.filter_by(key="is_paused").first()
    is_paused = is_paused_setting.value == "1" if is_paused_setting else False

    current_user = get_current_user()
    return render_template(
        "index.html",
        tables_info=tables_info,
        current_user=current_user,
        current_date=current_date,
        is_paused=is_paused,
        total_playdays=total_playdays,
    )


# Routes
@app.route("/countries")
@login_required
def countries():
    countries = Country.query.all()
    return render_template("countries.html", countries=countries)


@app.route("/countries/add", methods=["GET", "POST"])
@login_required
def add_country():
    if request.method == "POST":
        try:
            country = Country(
                role_id=request.form["role_id"],
                name=request.form["name"],
                public_channel_id=request.form["public_channel_id"],
                secret_channel_id=request.form["secret_channel_id"] or None,
                last_bilan=request.form["last_bilan"] or None,
            )
            db.session.add(country)
            db.session.commit()
            flash("Country added successfully!", "success")
            return redirect("/countries")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("add_country.html")


@app.route("/countries/edit/<int:country_id>", methods=["GET", "POST"])
@login_required
def edit_country(country_id):
    country = Country.query.get_or_404(country_id)
    if request.method == "POST":
        try:
            country.role_id = request.form["role_id"]
            country.name = request.form["name"]
            country.public_channel_id = request.form["public_channel_id"]
            country.secret_channel_id = request.form["secret_channel_id"] or None
            country.last_bilan = request.form["last_bilan"] or None
            db.session.commit()
            flash("Country updated successfully!", "success")
            return redirect("/countries")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("edit_country.html", country=country)


@app.route("/countries/delete/<int:country_id>", methods=["POST"])
@login_required
def delete_country(country_id):
    try:
        country = Country.query.get_or_404(country_id)
        db.session.delete(country)
        db.session.commit()
        flash("Country deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/countries")


# Governments routes
@app.route("/governments")
@login_required
def governments():
    governments = Government.query.all()
    countries = Country.query.all()
    return render_template(
        "governments.html", governments=governments, countries=countries
    )


@app.route("/governments/add", methods=["GET", "POST"])
@login_required
def add_government():
    if request.method == "POST":
        try:
            government = Government(
                country_id=int(request.form["country_id"]),
                slot=int(request.form["slot"]),
                player_id=request.form["player_id"],
                can_spend_money=bool(request.form.get("can_spend_money")),
                can_spend_points=bool(request.form.get("can_spend_points")),
                can_sign_treaties=bool(request.form.get("can_sign_treaties")),
                can_build=bool(request.form.get("can_build")),
                can_recruit=bool(request.form.get("can_recruit")),
                can_produce=bool(request.form.get("can_produce")),
                can_declare_war=bool(request.form.get("can_declare_war")),
            )
            db.session.add(government)
            db.session.commit()
            flash("Government added successfully!", "success")
            return redirect("/governments")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_government.html", countries=countries)


@app.route("/governments/edit/<int:country_id>/<int:slot>", methods=["GET", "POST"])
@login_required
def edit_government(country_id, slot):
    government = Government.query.filter_by(
        country_id=country_id, slot=slot
    ).first_or_404()
    if request.method == "POST":
        try:
            government.player_id = request.form["player_id"]
            government.can_spend_money = bool(request.form.get("can_spend_money"))
            government.can_spend_points = bool(request.form.get("can_spend_points"))
            government.can_sign_treaties = bool(request.form.get("can_sign_treaties"))
            government.can_build = bool(request.form.get("can_build"))
            government.can_recruit = bool(request.form.get("can_recruit"))
            government.can_produce = bool(request.form.get("can_produce"))
            government.can_declare_war = bool(request.form.get("can_declare_war"))
            db.session.commit()
            flash("Government updated successfully!", "success")
            return redirect("/governments")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template(
        "edit_government.html", government=government, countries=countries
    )


@app.route("/governments/delete/<int:country_id>/<int:slot>", methods=["POST"])
@login_required
def delete_government(country_id, slot):
    try:
        government = Government.query.filter_by(
            country_id=country_id, slot=slot
        ).first_or_404()
        db.session.delete(government)
        db.session.commit()
        flash("Government deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/governments")


# Inventory routes
@app.route("/inventory")
@login_required
def inventory():
    inventories = Inventory.query.all()
    countries = Country.query.all()
    return render_template(
        "inventory.html", inventories=inventories, countries=countries
    )


@app.route("/inventory/add", methods=["GET", "POST"])
@login_required
def add_inventory():
    if request.method == "POST":
        try:
            inventory = Inventory(
                country_id=request.form["country_id"],
                balance=int(request.form["balance"]),
                pol_points=int(request.form["pol_points"]),
                diplo_points=int(request.form["diplo_points"]),
            )
            db.session.add(inventory)
            db.session.commit()
            flash("Inventory added successfully!", "success")
            return redirect("/inventory")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_inventory.html", countries=countries)


@app.route("/inventory/edit/<country_id>", methods=["GET", "POST"])
@login_required
def edit_inventory(country_id):
    inventory = Inventory.query.get_or_404(country_id)
    if request.method == "POST":
        try:
            inventory.balance = int(request.form["balance"])
            inventory.pol_points = int(request.form["pol_points"])
            inventory.diplo_points = int(request.form["diplo_points"])
            db.session.commit()
            flash("Inventory updated successfully!", "success")
            return redirect("/inventory")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("edit_inventory.html", inventory=inventory)


# Regions routes
@app.route("/regions")
@login_required
def regions():
    regions = Region.query.all()
    countries = Country.query.all()
    return render_template("regions.html", regions=regions, countries=countries)


@app.route("/regions/add", methods=["GET", "POST"])
@login_required
def add_region():
    if request.method == "POST":
        try:
            region = Region(
                country_id=request.form["country_id"] or None,
                name=request.form["name"],
                mapchart_name=request.form["mapchart_name"],
                population=int(request.form["population"]),
            )
            db.session.add(region)
            db.session.commit()
            flash("Region added successfully!", "success")
            return redirect("/regions")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_region.html", countries=countries)


@app.route("/regions/edit/<int:region_id>", methods=["GET", "POST"])
@login_required
def edit_region(region_id):
    region = Region.query.get_or_404(region_id)
    if request.method == "POST":
        try:
            region.country_id = request.form["country_id"] or None
            region.name = request.form["name"]
            region.mapchart_name = request.form["mapchart_name"]
            region.population = int(request.form["population"])
            db.session.commit()
            flash("Region updated successfully!", "success")
            return redirect("/regions")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("edit_region.html", region=region, countries=countries)


# Structures routes
@app.route("/structures")
@login_required
def structures():
    structures = Structure.query.all()
    regions = Region.query.all()
    return render_template("structures.html", structures=structures, regions=regions)


@app.route("/structures/add", methods=["GET", "POST"])
@login_required
def add_structure():
    if request.method == "POST":
        try:
            structure = Structure(
                region_id=int(request.form["region_id"]),
                type=request.form["type"],
                specialisation=request.form["specialisation"],
                level=int(request.form["level"]),
                capacity=int(request.form["capacity"]),
                population=int(request.form["population"]),
            )
            db.session.add(structure)
            db.session.commit()
            flash("Structure added successfully!", "success")
            return redirect("/structures")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    regions = Region.query.all()
    return render_template("add_structure.html", regions=regions)


# Technologies routes
@app.route("/technologies")
@login_required
def technologies():
    technologies = Technology.query.all()
    countries = Country.query.all()
    return render_template(
        "technologies.html", technologies=technologies, countries=countries
    )


@app.route("/technologies/add", methods=["GET", "POST"])
@login_required
def add_technology():
    if request.method == "POST":
        try:
            technology = Technology(
                name=request.form["name"],
                image_url=request.form["image_url"] or None,
                developed_by=(
                    int(request.form["developed_by"])
                    if request.form["developed_by"]
                    else None
                ),
                exported=bool(request.form.get("exported")),
                type=request.form["type"],
                description=request.form["description"] or None,
            )
            db.session.add(technology)
            db.session.commit()
            flash("Technology added successfully!", "success")
            return redirect("/technologies")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_technology.html", countries=countries)


# Doctrines Management
@app.route("/doctrines")
@login_required
def doctrines():
    doctrines = Doctrine.query.all()
    return render_template("doctrines.html", doctrines=doctrines)


@app.route("/doctrines/add", methods=["GET", "POST"])
@login_required
def add_doctrine():
    if request.method == "POST":
        try:
            doctrine = Doctrine(
                name=request.form["name"],
                category=request.form["category"],
                description=request.form["description"] or None,
                discord_role_id=request.form["discord_role_id"] or None,
                bonus_json=request.form["bonus_json"] or None,
            )
            db.session.add(doctrine)
            db.session.commit()
            flash("Doctrine added successfully!", "success")
            return redirect("/doctrines")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("add_doctrine.html")


@app.route("/doctrines/edit/<int:doctrine_id>", methods=["GET", "POST"])
@login_required
def edit_doctrine(doctrine_id):
    doctrine = Doctrine.query.get_or_404(doctrine_id)
    if request.method == "POST":
        try:
            doctrine.name = request.form["name"]
            doctrine.category = request.form["category"]
            doctrine.description = request.form["description"] or None
            doctrine.discord_role_id = request.form["discord_role_id"] or None
            doctrine.bonus_json = request.form["bonus_json"] or None
            db.session.commit()
            flash("Doctrine updated successfully!", "success")
            return redirect("/doctrines")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("edit_doctrine.html", doctrine=doctrine)


@app.route("/doctrines/delete/<int:doctrine_id>", methods=["POST"])
@login_required
def delete_doctrine(doctrine_id):
    try:
        doctrine = Doctrine.query.get_or_404(doctrine_id)
        db.session.delete(doctrine)
        db.session.commit()
        flash("Doctrine deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/doctrines")


# API endpoints for dynamic updates
@app.route("/api/countries")
@login_required
def api_countries():
    countries = Country.query.all()
    return jsonify(
        [
            {"country_id": c.country_id, "name": c.name, "role_id": c.role_id}
            for c in countries
        ]
    )


@app.route("/api/regions/<country_id>")
@login_required
def api_regions_by_country(country_id):
    regions = Region.query.filter_by(country_id=country_id).all()
    return jsonify([{"region_id": r.region_id, "name": r.name} for r in regions])


# Structure Data Management
@app.route("/structure-data")
@login_required
def structure_data():
    structure_datas = StructureData.query.all()
    return render_template("structure_data.html", structure_datas=structure_datas)


@app.route("/structure-data/add", methods=["GET", "POST"])
@login_required
def add_structure_data():
    if request.method == "POST":
        try:
            structure_data = StructureData(
                type=request.form["type"],
                capacity=int(request.form["capacity"]),
                population=int(request.form["population"]),
                cout_construction=int(request.form["cout_construction"]),
            )
            db.session.add(structure_data)
            db.session.commit()
            flash("Structure data added successfully!", "success")
            return redirect("/structure-data")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("add_structure_data.html")


@app.route("/structure-data/edit/<int:structure_id>", methods=["GET", "POST"])
@login_required
def edit_structure_data(structure_id):
    structure_data = StructureData.query.get_or_404(structure_id)
    if request.method == "POST":
        try:
            structure_data.type = request.form["type"]
            structure_data.capacity = int(request.form["capacity"])
            structure_data.population = int(request.form["population"])
            structure_data.cout_construction = int(request.form["cout_construction"])
            db.session.commit()
            flash("Structure data updated successfully!", "success")
            return redirect("/structure-data")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("edit_structure_data.html", structure_data=structure_data)


@app.route("/structure-data/delete/<int:structure_id>", methods=["POST"])
@login_required
def delete_structure_data(structure_id):
    try:
        structure_data = StructureData.query.get_or_404(structure_id)
        db.session.delete(structure_data)
        db.session.commit()
        flash("Structure data deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/structure-data")


# Structure Production Management
@app.route("/structure-production")
@login_required
def structure_production():
    productions = StructureProduction.query.all()
    structures = Structure.query.all()
    technologies = Technology.query.all()
    return render_template(
        "structure_production.html",
        productions=productions,
        structures=structures,
        technologies=technologies,
    )


@app.route("/structure-production/add", methods=["GET", "POST"])
@login_required
def add_structure_production():
    if request.method == "POST":
        try:
            production = StructureProduction(
                structure_id=int(request.form["structure_id"]),
                tech_id=int(request.form["tech_id"]),
                quantity=int(request.form["quantity"]),
                days_remaining=int(request.form["days_remaining"]),
                started_at=request.form["started_at"] or None,
            )
            db.session.add(production)
            db.session.commit()
            flash("Structure production added successfully!", "success")
            return redirect("/structure-production")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    structures = Structure.query.all()
    technologies = Technology.query.all()
    return render_template(
        "add_structure_production.html",
        structures=structures,
        technologies=technologies,
    )


@app.route(
    "/structure-production/delete/<int:structure_id>/<int:tech_id>", methods=["POST"]
)
@login_required
def delete_structure_production(structure_id, tech_id):
    try:
        production = StructureProduction.query.filter_by(
            structure_id=structure_id, tech_id=tech_id
        ).first_or_404()
        db.session.delete(production)
        db.session.commit()
        flash("Structure production deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/structure-production")


# Technology Attributes Management
@app.route("/technology-attributes")
@login_required
def technology_attributes():
    attributes = TechnologyAttribute.query.all()
    technologies = Technology.query.all()
    return render_template(
        "technology_attributes.html", attributes=attributes, technologies=technologies
    )


@app.route("/technology-attributes/add", methods=["GET", "POST"])
@login_required
def add_technology_attribute():
    if request.method == "POST":
        try:
            attribute = TechnologyAttribute(
                tech_id=int(request.form["tech_id"]),
                attribute_name=request.form["attribute_name"],
                attribute_value=request.form["attribute_value"],
            )
            db.session.add(attribute)
            db.session.commit()
            flash("Technology attribute added successfully!", "success")
            return redirect("/technology-attributes")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    technologies = Technology.query.all()
    return render_template("add_technology_attribute.html", technologies=technologies)


@app.route(
    "/technology-attributes/edit/<int:tech_id>/<attribute_name>",
    methods=["GET", "POST"],
)
@login_required
def edit_technology_attribute(tech_id, attribute_name):
    """Edit technology attribute."""
    attribute = TechnologyAttribute.query.filter_by(
        tech_id=tech_id, attribute_name=attribute_name
    ).first_or_404()

    if request.method == "POST":
        try:
            attribute.attribute_value = request.form["attribute_value"]
            db.session.commit()
            flash("Technology attribute updated successfully!", "success")
            return redirect("/technology-attributes")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    technologies = Technology.query.all()
    return render_template(
        "edit_technology_attribute.html", attribute=attribute, technologies=technologies
    )


@app.route(
    "/technology-attributes/delete/<int:tech_id>/<attribute_name>", methods=["POST"]
)
@login_required
def delete_technology_attribute(tech_id, attribute_name):
    try:
        attribute = TechnologyAttribute.query.filter_by(
            tech_id=tech_id, attribute_name=attribute_name
        ).first_or_404()
        db.session.delete(attribute)
        db.session.commit()
        flash("Technology attribute deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/technology-attributes")


# Technology Licenses Management
@app.route("/technology-licenses")
@login_required
def technology_licenses():
    licenses = TechnologyLicense.query.all()
    technologies = Technology.query.all()
    countries = Country.query.all()
    return render_template(
        "technology_licenses.html",
        licenses=licenses,
        technologies=technologies,
        countries=countries,
    )


@app.route("/technology-licenses/add", methods=["GET", "POST"])
@login_required
def add_technology_license():
    if request.method == "POST":
        try:
            # Validate license_type
            license_type = request.form["license_type"]
            if license_type not in ["commercial", "personal"]:
                flash("License type must be either 'commercial' or 'personal'", "error")
                technologies = Technology.query.all()
                countries = Country.query.all()
                return render_template(
                    "add_technology_license.html",
                    technologies=technologies,
                    countries=countries,
                )

            license = TechnologyLicense(
                tech_id=int(request.form["tech_id"]),
                country_id=int(request.form["country_id"]),
                license_type=license_type,
                granted_by=(
                    int(request.form["granted_by"])
                    if request.form["granted_by"]
                    else None
                ),
                granted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            db.session.add(license)
            db.session.commit()
            flash("Technology license added successfully!", "success")
            return redirect("/technology-licenses")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    technologies = Technology.query.all()
    countries = Country.query.all()
    return render_template(
        "add_technology_license.html", technologies=technologies, countries=countries
    )


@app.route("/technology-licenses/delete/<int:license_id>", methods=["POST"])
@login_required
def delete_technology_license(license_id):
    try:
        license = TechnologyLicense.query.get_or_404(license_id)
        db.session.delete(license)
        db.session.commit()
        flash("Technology license deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/technology-licenses")


# Country Technology Inventory Management
@app.route("/country-tech-inventory")
@login_required
def country_tech_inventory():
    inventory = CountryTechnologyInventory.query.all()
    countries = Country.query.all()
    technologies = Technology.query.all()
    return render_template(
        "country_tech_inventory.html",
        inventory=inventory,
        countries=countries,
        technologies=technologies,
    )


@app.route("/country-tech-inventory/add", methods=["GET", "POST"])
@login_required
def add_country_tech_inventory():
    if request.method == "POST":
        try:
            inventory = CountryTechnologyInventory(
                country_id=int(request.form["country_id"]),
                tech_id=int(request.form["tech_id"]),
                quantity=int(request.form["quantity"]),
            )
            db.session.add(inventory)
            db.session.commit()
            flash("Country technology inventory added successfully!", "success")
            return redirect("/country-tech-inventory")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    technologies = Technology.query.all()
    return render_template(
        "add_country_tech_inventory.html",
        countries=countries,
        technologies=technologies,
    )


@app.route(
    "/country-tech-inventory/edit/<int:country_id>/<int:tech_id>",
    methods=["GET", "POST"],
)
@login_required
def edit_country_tech_inventory(country_id, tech_id):
    """Edit country technology inventory."""
    inventory = CountryTechnologyInventory.query.filter_by(
        country_id=country_id, tech_id=tech_id
    ).first_or_404()

    if request.method == "POST":
        try:
            inventory.quantity = int(request.form["quantity"])
            db.session.commit()
            flash("Country technology inventory updated successfully!", "success")
            return redirect("/country-tech-inventory")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    countries = Country.query.all()
    technologies = Technology.query.all()
    return render_template(
        "edit_country_tech_inventory.html",
        inventory=inventory,
        countries=countries,
        technologies=technologies,
    )


@app.route(
    "/country-tech-inventory/delete/<int:country_id>/<int:tech_id>", methods=["POST"]
)
@login_required
def delete_country_tech_inventory(country_id, tech_id):
    try:
        inventory = CountryTechnologyInventory.query.filter_by(
            country_id=country_id, tech_id=tech_id
        ).first_or_404()
        db.session.delete(inventory)
        db.session.commit()
        flash("Country technology inventory deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/country-tech-inventory")


# Country Technology Production Management
@app.route("/country-tech-production")
@login_required
def country_tech_production():
    productions = CountryTechnologyProduction.query.all()
    countries = Country.query.all()
    technologies = Technology.query.all()
    return render_template(
        "country_tech_production.html",
        productions=productions,
        countries=countries,
        technologies=technologies,
    )


@app.route("/country-tech-production/add", methods=["GET", "POST"])
@login_required
def add_country_tech_production():
    if request.method == "POST":
        try:
            production = CountryTechnologyProduction(
                country_id=int(request.form["country_id"]),
                tech_id=int(request.form["tech_id"]),
                quantity=int(request.form["quantity"]),
                days_remaining=int(request.form["days_remaining"]),
                started_at=request.form["started_at"] or None,
            )
            db.session.add(production)
            db.session.commit()
            flash("Country technology production added successfully!", "success")
            return redirect("/country-tech-production")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    technologies = Technology.query.all()
    return render_template(
        "add_country_tech_production.html",
        countries=countries,
        technologies=technologies,
    )


@app.route("/country-tech-production/delete/<int:production_id>", methods=["POST"])
@login_required
def delete_country_tech_production(production_id):
    try:
        production = CountryTechnologyProduction.query.get_or_404(production_id)
        db.session.delete(production)
        db.session.commit()
        flash("Country technology production deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/country-tech-production")


# Country Doctrines Management
@app.route("/country-doctrines")
@login_required
def country_doctrines():
    country_doctrines = CountryDoctrine.query.all()
    countries = Country.query.all()
    doctrines = Doctrine.query.all()
    return render_template(
        "country_doctrines.html",
        country_doctrines=country_doctrines,
        countries=countries,
        doctrines=doctrines,
    )


@app.route("/country-doctrines/add", methods=["GET", "POST"])
@login_required
def add_country_doctrine():
    if request.method == "POST":
        try:
            country_doctrine = CountryDoctrine(
                country_id=int(request.form["country_id"]),
                doctrine_id=int(request.form["doctrine_id"]),
            )
            db.session.add(country_doctrine)
            db.session.commit()
            flash("Country doctrine added successfully!", "success")
            return redirect("/country-doctrines")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    doctrines = Doctrine.query.all()
    return render_template(
        "add_country_doctrine.html", countries=countries, doctrines=doctrines
    )


@app.route(
    "/country-doctrines/delete/<int:country_id>/<int:doctrine_id>", methods=["POST"]
)
@login_required
def delete_country_doctrine(country_id, doctrine_id):
    try:
        country_doctrine = CountryDoctrine.query.filter_by(
            country_id=country_id, doctrine_id=doctrine_id
        ).first_or_404()
        db.session.delete(country_doctrine)
        db.session.commit()
        flash("Country doctrine deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/country-doctrines")


# Game Date Management
# Game Date Management
@app.route("/game-date")
@login_required
def game_date():
    # Get the latest date
    latest_date = GameDate.query.order_by(GameDate.real_date.desc()).first()

    # Get recent dates for history (show more entries)
    recent_dates = GameDate.query.order_by(GameDate.real_date.desc()).limit(20).all()

    # Get the current pause state from ServerSettings
    is_paused_setting = ServerSettings.query.filter_by(key="is_paused").first()
    is_paused = is_paused_setting.value == "1" if is_paused_setting else False

    if not latest_date:
        # Create initial date if none exists
        from datetime import date

        today = date.today()
        latest_date = GameDate(
            year=2045, month=1, playday=1, real_date=today.isoformat()
        )
        db.session.add(latest_date)
        db.session.commit()
        recent_dates = [latest_date]

    return render_template(
        "game_date.html",
        date=latest_date,
        recent_dates=recent_dates,
        is_paused=is_paused,
    )


@app.route("/game-date/add", methods=["POST"])
@login_required
def add_game_date():
    try:
        from datetime import date

        year = int(request.form["year"])
        month = int(request.form["month"])
        playday = int(request.form["playday"])
        real_date = date.today()

        # Check if this combination already exists
        existing = GameDate.query.filter_by(
            year=year, month=month, playday=playday
        ).first()
        if existing:
            flash(f"Date {year}-{month}-{playday} already exists!", "error")
            return redirect("/game-date")

        new_date = GameDate(
            year=year,
            month=month,
            playday=playday,
            real_date=real_date.isoformat(),
        )
        db.session.add(new_date)
        db.session.commit()
        flash("New game date added successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/game-date")


@app.route("/game-date/advance", methods=["POST"])
@login_required
def advance_game_date():
    try:
        from datetime import date

        # Get the latest date
        latest_date = GameDate.query.order_by(GameDate.real_date.desc()).first()
        if not latest_date:
            flash("No game date found!", "error")
            return redirect("/game-date")

        # Check if game is paused
        server_settings = ServerSettings.query.filter_by(key="is_paused").first()
        if server_settings and server_settings.value == "1":
            flash("Cannot advance date while game is paused!", "warning")
            return redirect("/game-date")

        # Get playdays for current month
        month_data = PlaydaysPerMonth.query.filter_by(
            month_number=latest_date.month
        ).first()
        if not month_data:
            flash(
                f"Playdays configuration not found for month {latest_date.month}!",
                "error",
            )
            return redirect("/game-date")

        # Calculate next date
        year, month, playday = latest_date.year, latest_date.month, latest_date.playday

        if playday < month_data.playdays:
            playday += 1
        else:
            playday = 1
            if month == 12:
                # Move to next year
                year += 1
                month = 1
            else:
                month += 1

        # Check if this date already exists
        existing = GameDate.query.filter_by(
            year=year, month=month, playday=playday
        ).first()
        if existing:
            flash(
                f"Date {year}-{month}-{playday} already exists in history!", "warning"
            )
            return redirect("/game-date")

        # Add new date entry
        new_date = GameDate(
            year=year,
            month=month,
            playday=playday,
            real_date=date.today().isoformat(),
        )
        db.session.add(new_date)
        db.session.commit()

        flash(f"Advanced to {year}-{month:02d}-{playday:02d}!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/game-date")


@app.route("/game-date/delete/<int:year>/<int:month>/<int:playday>", methods=["POST"])
@login_required
def delete_game_date(year, month, playday):
    try:
        date_entry = GameDate.query.filter_by(
            year=year, month=month, playday=playday
        ).first_or_404()
        db.session.delete(date_entry)
        db.session.commit()
        flash(f"Date {year}-{month:02d}-{playday:02d} deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/game-date")


# Playdays Per Month Management
@app.route("/playdays-per-month")
@login_required
def playdays_per_month():
    playdays = PlaydaysPerMonth.query.order_by(PlaydaysPerMonth.month_number).all()
    # Ensure all 12 months exist
    if len(playdays) < 12:
        existing_months = {p.month_number for p in playdays}
        for month_num in range(1, 13):
            if month_num not in existing_months:
                new_month = PlaydaysPerMonth(month_number=month_num, playdays=30)
                db.session.add(new_month)
        db.session.commit()
        playdays = PlaydaysPerMonth.query.order_by(PlaydaysPerMonth.month_number).all()

    return render_template("playdays_per_month.html", playdays=playdays)


@app.route("/playdays-per-month/edit", methods=["POST"])
@login_required
def edit_playdays_per_month():
    try:
        for month_num in range(1, 13):
            month_data = PlaydaysPerMonth.query.filter_by(
                month_number=month_num
            ).first()
            if not month_data:
                month_data = PlaydaysPerMonth(month_number=month_num)
                db.session.add(month_data)

            playdays_value = request.form.get(f"month_{month_num}")
            if playdays_value:
                month_data.playdays = int(playdays_value)

        db.session.commit()
        flash("Playdays per month updated successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/playdays-per-month")


# Settings Routes
@app.route("/settings")
@login_required
def settings():
    """Display and manage all server settings with full CRUD functionality."""
    try:
        # Get all settings
        settings_data = ServerSettings.query.all()

        # Define useful default settings for the game
        default_settings = {
            "is_paused": "0",  # Game pause state
            "current_day": "1",  # Current game day
            "current_season": "Spring",  # Current season (Spring, Summer, Autumn, Winter)
            "current_year": "1900",  # Starting year
            "day_duration_minutes": "60",  # How long each in-game day lasts in real minutes
            "daily_income_base": "1000",  # Base daily income for countries
            "research_speed_multiplier": "1.0",  # Research time multiplier
            "production_speed_multiplier": "1.0",  # Production time multiplier
            "max_active_countries": "50",  # Maximum number of active countries
            "technology_transfer_cost": "5000",  # Cost to transfer technology
            "max_tech_level": "11",  # Maximum technology level
            "default_tech_slots": "3",  # Default technology slots per country
            "war_declaration_cooldown": "7",  # Days between war declarations
            "alliance_formation_cost": "2000",  # Cost to form alliances
            "treaty_negotiation_time": "3",  # Days needed to negotiate treaties
            "maintenance_mode": "0",  # Maintenance mode toggle
            "allow_new_players": "1",  # Allow new player registration
            "discord_notifications": "1",  # Enable Discord notifications
        }

        # Create missing default settings
        existing_keys = {setting.key for setting in settings_data}
        for key, default_value in default_settings.items():
            if key not in existing_keys:
                new_setting = ServerSettings(key=key, value=default_value)
                db.session.add(new_setting)

        db.session.commit()

        # Refresh settings data after adding defaults
        settings_data = ServerSettings.query.order_by(ServerSettings.key).all()

        return render_template("settings.html", settings=settings_data)
    except Exception as e:
        flash(f"Error loading settings: {str(e)}", "error")
        return redirect("/")


@app.route("/settings/add", methods=["GET", "POST"])
@login_required
def add_setting():
    """Add a new server setting."""
    if request.method == "POST":
        try:
            key = request.form["key"].strip()
            value = request.form["value"].strip()

            # Validate key doesn't already exist
            existing_setting = ServerSettings.query.filter_by(key=key).first()
            if existing_setting:
                flash(
                    f"Setting '{key}' already exists. Use edit to modify it.", "error"
                )
                return render_template("add_setting.html")

            # Create new setting
            new_setting = ServerSettings(key=key, value=value)
            db.session.add(new_setting)
            db.session.commit()

            flash(f"Setting '{key}' added successfully!", "success")
            return redirect("/settings")

        except Exception as e:
            flash(f"Error adding setting: {str(e)}", "error")

    return render_template("add_setting.html")


@app.route("/settings/edit/<setting_key>", methods=["GET", "POST"])
@login_required
def edit_setting(setting_key):
    """Edit an existing server setting."""
    setting = ServerSettings.query.filter_by(key=setting_key).first_or_404()

    if request.method == "POST":
        try:
            # Update setting value
            setting.value = request.form["value"].strip()
            db.session.commit()

            flash(f"Setting '{setting_key}' updated successfully!", "success")
            return redirect("/settings")

        except Exception as e:
            flash(f"Error updating setting: {str(e)}", "error")

    return render_template("edit_setting.html", setting=setting)


@app.route("/settings/delete/<setting_key>", methods=["POST"])
@login_required
def delete_setting(setting_key):
    """Delete a server setting."""
    try:
        # Prevent deletion of critical settings
        protected_settings = ["is_paused"]
        if setting_key in protected_settings:
            flash(f"Cannot delete protected setting '{setting_key}'.", "error")
            return redirect("/settings")

        setting = ServerSettings.query.filter_by(key=setting_key).first_or_404()
        db.session.delete(setting)
        db.session.commit()

        flash(f"Setting '{setting_key}' deleted successfully!", "success")

    except Exception as e:
        flash(f"Error deleting setting: {str(e)}", "error")

    return redirect("/settings")


@app.route("/settings/bulk-update", methods=["POST"])
@login_required
def bulk_update_settings():
    """Update multiple settings at once."""
    try:
        updated_count = 0

        # Process all form data
        for key, value in request.form.items():
            if key.startswith("setting_"):
                setting_key = key.replace("setting_", "")
                setting = ServerSettings.query.filter_by(key=setting_key).first()

                if setting and setting.value != value.strip():
                    setting.value = value.strip()
                    updated_count += 1

        db.session.commit()
        flash(f"Updated {updated_count} settings successfully!", "success")

    except Exception as e:
        flash(f"Error updating settings: {str(e)}", "error")

    return redirect("/settings")


@app.route("/settings/update", methods=["POST"])
@login_required
def update_settings():
    """Update server settings (legacy route for backward compatibility)."""
    try:
        # Update is_paused setting
        is_paused = "1" if request.form.get("is_paused") else "0"

        setting = ServerSettings.query.filter_by(key="is_paused").first()
        if setting:
            setting.value = is_paused
        else:
            setting = ServerSettings(key="is_paused", value=is_paused)
            db.session.add(setting)

        db.session.commit()
        flash("Settings updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating settings: {str(e)}", "error")

    return redirect("/settings")


# New routes for updated schema tables


# Technology Data routes
@app.route("/technology_datas")
@login_required
def technology_datas():
    """List all technology data entries."""
    tech_datas = TechnologyData.query.all()
    return render_template("technology_datas.html", tech_datas=tech_datas)


@app.route("/technology_datas/add", methods=["GET", "POST"])
@login_required
def add_technology_data():
    """Add new technology data."""
    if request.method == "POST":
        try:
            tech_data = TechnologyData(
                type=request.form["type"],
                specialisation=request.form["specialisation"],
                minimum_slots_taken=float(request.form["minimum_slots_taken"]),
                maximum_slots_taken=float(request.form["maximum_slots_taken"]),
                minimum_dev_cost=int(request.form["minimum_dev_cost"]),
                minimum_dev_time=int(request.form["minimum_dev_time"]),
                minimum_prod_cost=int(request.form["minimum_prod_cost"]),
                maximum_dev_cost=int(request.form["maximum_dev_cost"]),
                maximum_dev_time=int(request.form["maximum_dev_time"]),
                maximum_prod_cost=int(request.form["maximum_prod_cost"]),
            )
            db.session.add(tech_data)
            db.session.commit()
            flash("Technology data added successfully!", "success")
            return redirect("/technology_datas")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("add_technology_data.html")


@app.route("/technology_datas/edit/<string:tech_type>", methods=["GET", "POST"])
@login_required
def edit_technology_data(tech_type):
    """Edit technology data."""
    tech_data = TechnologyData.query.get_or_404(tech_type)
    if request.method == "POST":
        try:
            tech_data.specialisation = request.form["specialisation"]
            tech_data.minimum_slots_taken = float(request.form["minimum_slots_taken"])
            tech_data.maximum_slots_taken = float(request.form["maximum_slots_taken"])
            tech_data.minimum_dev_cost = int(request.form["minimum_dev_cost"])
            tech_data.minimum_dev_time = int(request.form["minimum_dev_time"])
            tech_data.minimum_prod_cost = int(request.form["minimum_prod_cost"])
            tech_data.maximum_dev_cost = int(request.form["maximum_dev_cost"])
            tech_data.maximum_dev_time = int(request.form["maximum_dev_time"])
            tech_data.maximum_prod_cost = int(request.form["maximum_prod_cost"])
            db.session.commit()
            flash("Technology data updated successfully!", "success")
            return redirect("/technology_datas")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("edit_technology_data.html", tech_data=tech_data)


@app.route("/technology_datas/delete/<string:tech_type>", methods=["POST"])
@login_required
def delete_technology_data(tech_type):
    """Delete technology data."""
    try:
        tech_data = TechnologyData.query.get_or_404(tech_type)
        db.session.delete(tech_data)
        db.session.commit()
        flash("Technology data deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/technology_datas")


# Technology Ratio routes
@app.route("/technology_ratios")
@login_required
def technology_ratios():
    """List all technology ratios."""
    tech_ratios = TechnologyRatio.query.all()
    return render_template("technology_ratios.html", tech_ratios=tech_ratios)


@app.route("/technology_ratios/add", methods=["GET", "POST"])
@login_required
def add_technology_ratio():
    """Add new technology ratio."""
    if request.method == "POST":
        try:
            tech_ratio = TechnologyRatio(
                type=request.form["type"],
                level=int(request.form["level"]),
                ratio_cost=int(request.form["ratio_cost"]),
                ratio_time=int(request.form["ratio_time"]),
                ratio_slots=float(request.form["ratio_slots"]),
            )
            db.session.add(tech_ratio)
            db.session.commit()
            flash("Technology ratio added successfully!", "success")
            return redirect("/technology_ratios")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("add_technology_ratio.html")


@app.route(
    "/technology_ratios/edit/<string:tech_type>/<int:level>", methods=["GET", "POST"]
)
@login_required
def edit_technology_ratio(tech_type, level):
    """Edit technology ratio."""
    tech_ratio = TechnologyRatio.query.filter_by(
        type=tech_type, level=level
    ).first_or_404()
    if request.method == "POST":
        try:
            tech_ratio.ratio_cost = int(request.form["ratio_cost"])
            tech_ratio.ratio_time = int(request.form["ratio_time"])
            tech_ratio.ratio_slots = float(request.form["ratio_slots"])
            db.session.commit()
            flash("Technology ratio updated successfully!", "success")
            return redirect("/technology_ratios")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("edit_technology_ratio.html", tech_ratio=tech_ratio)


@app.route("/technology_ratios/delete/<string:tech_type>/<int:level>", methods=["POST"])
@login_required
def delete_technology_ratio(tech_type, level):
    """Delete technology ratio."""
    try:
        tech_ratio = TechnologyRatio.query.filter_by(
            type=tech_type, level=level
        ).first_or_404()
        db.session.delete(tech_ratio)
        db.session.commit()
        flash("Technology ratio deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/technology_ratios")


# Inventory Units routes
@app.route("/inventory_units")
@login_required
def inventory_units():
    """List all inventory units."""
    units = InventoryUnit.query.all()
    countries = Country.query.all()
    return render_template("inventory_units.html", units=units, countries=countries)


@app.route("/inventory_units/add", methods=["GET", "POST"])
@login_required
def add_inventory_unit():
    """Add new inventory unit entry."""
    if request.method == "POST":
        try:
            unit = InventoryUnit(
                country_id=int(request.form["country_id"]),
                unit_type=request.form["unit_type"],
                quantity=int(request.form["quantity"]),
            )
            db.session.add(unit)
            db.session.commit()
            flash("Inventory unit added successfully!", "success")
            return redirect("/inventory_units")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_inventory_unit.html", countries=countries)


@app.route(
    "/inventory_units/edit/<int:country_id>/<unit_type>", methods=["GET", "POST"]
)
@login_required
def edit_inventory_unit(country_id, unit_type):
    """Edit inventory unit entry."""
    unit = InventoryUnit.query.filter_by(
        country_id=country_id, unit_type=unit_type
    ).first_or_404()

    if request.method == "POST":
        try:
            unit.quantity = int(request.form["quantity"])
            db.session.commit()
            flash("Inventory unit updated successfully!", "success")
            return redirect("/inventory_units")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    countries = Country.query.all()
    return render_template("edit_inventory_unit.html", unit=unit, countries=countries)


@app.route("/inventory_units/delete/<int:country_id>/<unit_type>", methods=["POST"])
@login_required
def delete_inventory_unit(country_id, unit_type):
    """Delete inventory unit entry."""
    try:
        unit = InventoryUnit.query.filter_by(
            country_id=country_id, unit_type=unit_type
        ).first_or_404()
        db.session.delete(unit)
        db.session.commit()
        flash("Inventory unit deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/inventory_units")


# Inventory Pricing routes
@app.route("/inventory_pricings")
@login_required
def inventory_pricings():
    """List all inventory pricings."""
    pricings = InventoryPricing.query.all()
    return render_template("inventory_pricings.html", pricings=pricings)


@app.route("/inventory_pricings/add", methods=["GET", "POST"])
@login_required
def add_inventory_pricing():
    """Add new inventory pricing."""
    if request.method == "POST":
        try:
            pricing = InventoryPricing(
                item=request.form["item"],
                price=int(request.form["price"]),
                maintenance=int(request.form["maintenance"]),
            )
            db.session.add(pricing)
            db.session.commit()
            flash("Inventory pricing added successfully!", "success")
            return redirect("/inventory_pricings")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    return render_template("add_inventory_pricing.html")


# Diplomacy routes
@app.route("/treaties")
@login_required
def treaties():
    """List all treaties."""
    treaties = Treaty.query.all()
    countries = Country.query.all()
    return render_template("treaties.html", treaties=treaties, countries=countries)


@app.route("/treaties/add", methods=["GET", "POST"])
@login_required
def add_treaty():
    """Add new treaty."""
    if request.method == "POST":
        try:
            treaty = Treaty(
                treaty_type=request.form["treaty_type"],
                country_a=int(request.form["country_a"]),
                country_b=int(request.form["country_b"]),
                start_date=request.form["start_date"],
                end_date=request.form["end_date"] if request.form["end_date"] else None,
                status=request.form["status"],
            )
            db.session.add(treaty)
            db.session.commit()
            flash("Treaty added successfully!", "success")
            return redirect("/treaties")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_treaty.html", countries=countries)


@app.route("/treaties/edit/<int:treaty_id>", methods=["GET", "POST"])
@login_required
def edit_treaty(treaty_id):
    """Edit treaty."""
    treaty = Treaty.query.get_or_404(treaty_id)
    if request.method == "POST":
        try:
            treaty.treaty_type = request.form["treaty_type"]
            treaty.country_a = int(request.form["country_a"])
            treaty.country_b = int(request.form["country_b"])
            treaty.start_date = request.form["start_date"]
            treaty.end_date = (
                request.form["end_date"] if request.form["end_date"] else None
            )
            treaty.status = request.form["status"]
            db.session.commit()
            flash("Treaty updated successfully!", "success")
            return redirect("/treaties")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("edit_treaty.html", treaty=treaty, countries=countries)


@app.route("/treaties/delete/<int:treaty_id>", methods=["POST"])
@login_required
def delete_treaty(treaty_id):
    """Delete treaty."""
    try:
        treaty = Treaty.query.get_or_404(treaty_id)
        db.session.delete(treaty)
        db.session.commit()
        flash("Treaty deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/treaties")


@app.route("/alliances")
@login_required
def alliances():
    """List all alliances."""
    alliances = Alliance.query.all()
    countries = Country.query.all()
    return render_template("alliances.html", alliances=alliances, countries=countries)


@app.route("/alliances/add", methods=["GET", "POST"])
@login_required
def add_alliance():
    """Add new alliance."""
    if request.method == "POST":
        try:
            alliance = Alliance(
                alliance_name=request.form["alliance_name"],
                country_a=int(request.form["country_a"]),
                country_b=int(request.form["country_b"]),
                start_date=request.form["start_date"],
                end_date=request.form["end_date"] if request.form["end_date"] else None,
                alliance_type=request.form["alliance_type"],
                status=request.form["status"],
            )
            db.session.add(alliance)
            db.session.commit()
            flash("Alliance added successfully!", "success")
            return redirect("/alliances")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_alliance.html", countries=countries)


@app.route("/alliances/edit/<int:alliance_id>", methods=["GET", "POST"])
@login_required
def edit_alliance(alliance_id):
    """Edit alliance."""
    alliance = Alliance.query.get_or_404(alliance_id)
    if request.method == "POST":
        try:
            alliance.alliance_name = request.form["alliance_name"]
            alliance.country_a = int(request.form["country_a"])
            alliance.country_b = int(request.form["country_b"])
            alliance.start_date = request.form["start_date"]
            alliance.end_date = (
                request.form["end_date"] if request.form["end_date"] else None
            )
            alliance.alliance_type = request.form["alliance_type"]
            alliance.status = request.form["status"]
            db.session.commit()
            flash("Alliance updated successfully!", "success")
            return redirect("/alliances")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("edit_alliance.html", alliance=alliance, countries=countries)


@app.route("/alliances/delete/<int:alliance_id>", methods=["POST"])
@login_required
def delete_alliance(alliance_id):
    """Delete alliance."""
    try:
        alliance = Alliance.query.get_or_404(alliance_id)
        db.session.delete(alliance)
        db.session.commit()
        flash("Alliance deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/alliances")


@app.route("/war_declarations")
@login_required
def war_declarations():
    """List all war declarations."""
    wars = WarDeclaration.query.all()
    countries = Country.query.all()
    return render_template("war_declarations.html", wars=wars, countries=countries)


@app.route("/war_declarations/add", methods=["GET", "POST"])
@login_required
def add_war_declaration():
    """Add new war declaration."""
    if request.method == "POST":
        try:
            war = WarDeclaration(
                country_a=int(request.form["country_a"]),
                country_b=int(request.form["country_b"]),
                declaration_date=request.form["declaration_date"],
                status=request.form["status"],
            )
            db.session.add(war)
            db.session.commit()
            flash("War declaration added successfully!", "success")
            return redirect("/war_declarations")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("add_war_declaration.html", countries=countries)


@app.route("/war_declarations/edit/<int:war_id>", methods=["GET", "POST"])
@login_required
def edit_war_declaration(war_id):
    """Edit war declaration."""
    war = WarDeclaration.query.get_or_404(war_id)
    if request.method == "POST":
        try:
            war.country_a = int(request.form["country_a"])
            war.country_b = int(request.form["country_b"])
            war.declaration_date = request.form["declaration_date"]
            war.status = request.form["status"]
            db.session.commit()
            flash("War declaration updated successfully!", "success")
            return redirect("/war_declarations")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
    countries = Country.query.all()
    return render_template("edit_war_declaration.html", war=war, countries=countries)


@app.route("/war_declarations/delete/<int:war_id>", methods=["POST"])
@login_required
def delete_war_declaration(war_id):
    """Delete war declaration."""
    try:
        war = WarDeclaration.query.get_or_404(war_id)
        db.session.delete(war)
        db.session.commit()
        flash("War declaration deleted successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/war_declarations")


@app.route("/settings/pause-toggle", methods=["POST"])
@login_required
def toggle_pause():
    """Toggle the game pause state - can be called from anywhere."""
    try:
        current_setting = ServerSettings.query.filter_by(key="is_paused").first()

        if current_setting:
            # Toggle current value
            current_value = current_setting.value
            new_value = "0" if current_value == "1" else "1"
            current_setting.value = new_value
        else:
            # Create with default paused state
            current_setting = ServerSettings(key="is_paused", value="1")
            db.session.add(current_setting)
            new_value = "1"

        db.session.commit()
        status = "paused" if new_value == "1" else "resumed"
        flash(f"Game {status} successfully!", "success")

    except Exception as e:
        flash(f"Error toggling pause state: {str(e)}", "error")

    # Return to the page that called this action
    return redirect(request.referrer or "/")


if __name__ == "__main__":
    with app.app_context():
        try:
            # Create admin database tables (User model)
            db.create_all()

            # Create game database tables (all game models)
            db.create_all(bind_key="game")

            print("✓ Database tables created successfully")

        except Exception as e:
            print(f"Database initialization error: {e}")

    try:
        app.run(debug=False, host="0.0.0.0", port=8080)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print("Port 8080 is already in use, trying port 8081...")
            app.run(debug=False, host="0.0.0.0", port=8081)

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

    country_id = db.Column(db.String, primary_key=True)
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
    soldiers = db.Column(db.Integer, default=0, nullable=False)
    reserves = db.Column(db.Integer, default=0, nullable=False)


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
    region_id = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    specialization = db.Column(db.String, nullable=False)
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
    image_url = db.Column(db.String)
    developed_by = db.Column(db.Integer)
    exported = db.Column(db.Boolean, default=False)
    type = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.String)


class CountryTechnology(db.Model):
    """Country Technologies - stored in game database"""

    __bind_key__ = "game"
    __tablename__ = "CountryTechnologies"

    country_id = db.Column(db.Integer, primary_key=True)
    tech_field = db.Column(db.String, primary_key=True)
    level = db.Column(db.Integer, default=1, nullable=False)


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

        user = User.query.get(session["user_id"])
        if not user or not user.can_manage_users:
            flash("Admin privileges required for this action.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """Get current logged in user"""
    if "user_id" in session:
        return User.query.get(session["user_id"])
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
    }
    current_user = get_current_user()
    return render_template(
        "index.html", tables_info=tables_info, current_user=current_user
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
                country_id=request.form["country_id"],
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


@app.route("/governments/edit/<country_id>/<int:slot>", methods=["GET", "POST"])
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


@app.route("/governments/delete/<country_id>/<int:slot>", methods=["POST"])
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
                soldiers=int(request.form["soldiers"]),
                reserves=int(request.form["reserves"]),
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
            inventory.soldiers = int(request.form["soldiers"])
            inventory.reserves = int(request.form["reserves"])
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
                region_id=request.form["region_id"],
                type=request.form["type"],
                specialization=request.form["specialization"],
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

    app.run(debug=False, host="0.0.0.0", port=8080)

import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "gignexa.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    phone = db.Column(db.String(30))
    area = db.Column(db.String(120), nullable=False, default="")
    category = db.Column(db.String(80))
    price = db.Column(db.Integer)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    worker_bookings = db.relationship(
        "Booking", foreign_keys="Booking.worker_id", backref="worker", lazy=True
    )
    customer_bookings = db.relationship(
        "Booking", foreign_keys="Booking.customer_id", backref="customer", lazy=True
    )


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    service_date = db.Column(db.String(20), nullable=False)
    service_time = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                flash("You don't have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    area = request.args.get("area", "").strip()
    query = User.query.filter_by(role="worker")
    if category:
        query = query.filter(User.category == category)
    if area:
        query = query.filter(User.area.ilike(f"%{area}%"))
    workers = query.order_by(User.name.asc()).all()
    categories = [
        "Electrician", "Plumber", "AC Technician", "Cleaner",
        "Painter", "Carpenter", "Appliance Repair", "Other"
    ]
    return render_template(
        "index.html", workers=workers, categories=categories,
        selected_category=category, selected_area=area
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    categories = [
        "Electrician", "Plumber", "AC Technician", "Cleaner",
        "Painter", "Carpenter", "Appliance Repair", "Other"
    ]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "customer")
        phone = request.form.get("phone", "").strip()
        area = request.form.get("area", "").strip()
        category = request.form.get("category", "").strip()
        price_raw = request.form.get("price", "").strip()
        bio = request.form.get("bio", "").strip()

        if not name or not email or len(password) < 8 or not area:
            flash("Fill all required fields. Password must be at least 8 characters.", "error")
            return render_template("register.html", categories=categories)
        if role not in ("customer", "worker"):
            flash("Choose a valid account type.", "error")
            return render_template("register.html", categories=categories)
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template("register.html", categories=categories)
        price = None
        if role == "worker":
            if not category:
                flash("Workers must choose a service category.", "error")
                return render_template("register.html", categories=categories)
            try:
                price = int(price_raw) if price_raw else None
                if price is not None and price < 0:
                    raise ValueError
            except ValueError:
                flash("Enter a valid starting price.", "error")
                return render_template("register.html", categories=categories)

        user = User(
            name=name, email=email, password_hash=generate_password_hash(password),
            role=role, phone=phone, area=area, category=category if role == "worker" else None,
            price=price, bio=bio if role == "worker" else None
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to GigNexa! Your account is ready.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", categories=categories)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("You are now logged in.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/worker/<int:worker_id>")
def worker_detail(worker_id):
    worker = User.query.filter_by(id=worker_id, role="worker").first_or_404()
    reviews = Review.query.filter_by(worker_id=worker.id).order_by(Review.created_at.desc()).all()
    average = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None
    return render_template("worker_detail.html", worker=worker, reviews=reviews, average=average)


@app.route("/book/<int:worker_id>", methods=["GET", "POST"])
@role_required("customer")
def book_worker(worker_id):
    worker = User.query.filter_by(id=worker_id, role="worker").first_or_404()
    if request.method == "POST":
        service_date = request.form.get("service_date", "").strip()
        service_time = request.form.get("service_time", "").strip()
        address = request.form.get("address", "").strip()
        description = request.form.get("description", "").strip()
        if not all([service_date, service_time, address, description]):
            flash("Please complete every booking field.", "error")
        else:
            booking = Booking(
                customer_id=current_user.id, worker_id=worker.id,
                service_date=service_date, service_time=service_time,
                address=address, description=description, status="pending"
            )
            db.session.add(booking)
            db.session.commit()
            flash("Booking request sent. Wait for the worker to respond.", "success")
            return redirect(url_for("dashboard"))
    return render_template("book.html", worker=worker, today=datetime.utcnow().date().isoformat())


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "worker":
        bookings = Booking.query.filter_by(worker_id=current_user.id).order_by(Booking.created_at.desc()).all()
    else:
        bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    review_booking_ids = {
        row[0] for row in db.session.query(Review.booking_id).filter_by(customer_id=current_user.id).all()
    } if current_user.role == "customer" else set()
    return render_template("dashboard.html", bookings=bookings, review_booking_ids=review_booking_ids)


@app.route("/booking/<int:booking_id>/status", methods=["POST"])
@role_required("worker")
def update_booking_status(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.worker_id != current_user.id:
        abort(404)
    new_status = request.form.get("status", "")
    allowed = {
        "pending": {"accepted", "rejected"},
        "accepted": {"completed"}
    }
    if new_status not in allowed.get(booking.status, set()):
        flash("That status change is not allowed.", "error")
    else:
        booking.status = new_status
        db.session.commit()
        flash(f"Booking #{booking.id} marked as {new_status}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/booking/<int:booking_id>/review", methods=["POST"])
@role_required("customer")
def review_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.customer_id != current_user.id:
        abort(404)
    if booking.status != "completed":
        flash("You can review only completed services.", "error")
        return redirect(url_for("dashboard"))
    if Review.query.filter_by(booking_id=booking.id).first():
        flash("You have already reviewed this booking.", "error")
        return redirect(url_for("dashboard"))
    try:
        rating = int(request.form.get("rating", ""))
    except ValueError:
        rating = 0
    comment = request.form.get("comment", "").strip()
    if rating not in range(1, 6):
        flash("Choose a rating from 1 to 5.", "error")
    else:
        db.session.add(Review(
            booking_id=booking.id, customer_id=current_user.id,
            worker_id=booking.worker_id, rating=rating, comment=comment[:500]
        ))
        db.session.commit()
        flash("Thanks for reviewing the service.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

from datetime import date
from functools import wraps
import os

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)

from werkzeug.security import (
    generate_password_hash, check_password_hash
)


# ================= APPLICATION CONFIGURATION =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(
        BASE_DIR, "..", "frontend", "templates"
    ),
    static_folder=os.path.join(BASE_DIR, "..", "static")
)

app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///brightloop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ================= INITIALIZE EXTENSIONS =================

db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ================= DATABASE MODELS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(120))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    product_type = db.Column(db.String(60), default="Software")
    sales_price = db.Column(db.Float, nullable=False, default=0)
    cost_price = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)


class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    billing_cycle = db.Column(db.String(20), default="Monthly")
    min_quantity = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer.id"), nullable=False
    )
    plan_id = db.Column(
        db.Integer, db.ForeignKey("plan.id"), nullable=False
    )
    quantity = db.Column(db.Integer, default=1)
    start_date = db.Column(db.Date, default=date.today)
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="Active")

    customer = db.relationship("Customer")
    plan = db.relationship("Plan")


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(
        db.Integer, db.ForeignKey("subscription.id")
    )
    amount = db.Column(db.Float, nullable=False)
    tax_percent = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="Pending")

    subscription = db.relationship(
        "Subscription", backref="invoices"
    )


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer, db.ForeignKey("invoice.id"), nullable=False
    )
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(40), default="UPI")
    paid_on = db.Column(db.Date, default=date.today)
    note = db.Column(db.String(255))

    invoice = db.relationship("Invoice")


# ================= LOGIN MANAGEMENT =================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator


# ================= HOME =================

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ================= REGISTRATION =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            flash("Please enter all required details.", "danger")

        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")

        elif (
            len(password) <= 8
            or not any(c.isupper() for c in password)
            or not any(c.islower() for c in password)
            or not any(not c.isalnum() for c in password)
        ):
            flash(
                "Password must be longer than 8 characters and "
                "include uppercase, lowercase and special characters.",
                "danger"
            )

        else:
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role="customer"
            )
            db.session.add(user)
            db.session.commit()

            flash("Account created successfully.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ================= LOGOUT =================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ================= DASHBOARD =================

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "customer":
        return render_template(
            "dashboard.html",
            customer_view=True,
            active=0,
            revenue=0,
            owed=0,
            overdue=0
        )

    active = Subscription.query.filter_by(
        status="Active"
    ).count()

    revenue = db.session.query(
        db.func.coalesce(db.func.sum(Payment.amount), 0)
    ).scalar()

    owed = db.session.query(
        db.func.coalesce(db.func.sum(Invoice.total), 0)
    ).filter(Invoice.status != "Paid").scalar()

    overdue = Invoice.query.filter(
        Invoice.status != "Paid",
        Invoice.due_date < date.today()
    ).count()

    return render_template(
        "dashboard.html",
        customer_view=False,
        active=active,
        revenue=revenue,
        owed=owed,
        overdue=overdue
    )


# ================= CUSTOMERS =================

@app.route("/customers", methods=["GET", "POST"])
@roles_required("admin", "staff")
def customers():
    if request.method == "POST":
        customer = Customer(
            name=request.form["name"].strip(),
            email=request.form["email"].strip(),
            company=request.form.get("company")
        )

        db.session.add(customer)
        db.session.commit()

        flash("Customer added successfully.", "success")
        return redirect(url_for("customers"))

    return render_template(
        "customers.html",
        customers=Customer.query.order_by(
            Customer.id.desc()
        ).all()
    )


# ================= PRODUCTS =================

@app.route("/products", methods=["GET", "POST"])
@roles_required("admin", "staff")
def products():
    if request.method == "POST":
        try:
            sales_price = float(request.form["sales_price"])
            cost_price = float(request.form.get("cost_price") or 0)
        except (ValueError, KeyError):
            flash("Please enter valid product prices.", "danger")
            return redirect(url_for("products"))

        if sales_price < 0 or cost_price < 0:
            flash("Prices cannot be negative.", "danger")
            return redirect(url_for("products"))

        product = Product(
            name=request.form["name"].strip(),
            product_type=request.form.get(
                "product_type", "Software"
            ),
            sales_price=sales_price,
            cost_price=cost_price,
            notes=request.form.get("notes")
        )

        db.session.add(product)
        db.session.commit()

        flash("Product added successfully.", "success")
        return redirect(url_for("products"))

    return render_template(
        "products.html",
        products=Product.query.order_by(
            Product.id.desc()
        ).all()
    )


# ================= PLANS =================

@app.route("/plans", methods=["GET", "POST"])
@roles_required("admin", "staff")
def plans():
    if request.method == "POST":
        try:
            price = float(request.form["price"])
            min_quantity = int(
                request.form.get("min_quantity") or 1
            )
        except (ValueError, KeyError):
            flash("Please enter valid plan details.", "danger")
            return redirect(url_for("plans"))

        if price < 0 or min_quantity < 1:
            flash("Invalid price or minimum quantity.", "danger")
            return redirect(url_for("plans"))

        plan = Plan(
            name=request.form["name"].strip(),
            price=price,
            billing_cycle=request.form["billing_cycle"],
            min_quantity=min_quantity
        )

        db.session.add(plan)
        db.session.commit()

        flash("Plan added successfully.", "success")
        return redirect(url_for("plans"))

    return render_template(
        "plans.html",
        plans=Plan.query.all()
    )


# ================= SUBSCRIPTIONS =================

@app.route("/subscriptions", methods=["GET", "POST"])
@roles_required("admin", "staff")
def subscriptions():
    if request.method == "POST":
        try:
            plan_id = int(request.form["plan_id"])
            customer_id = int(request.form["customer_id"])
            quantity = int(request.form.get("quantity") or 1)
            start = date.fromisoformat(request.form["start_date"])

            expiry_text = request.form.get("expiry_date")
            expiry = (
                date.fromisoformat(expiry_text)
                if expiry_text else None
            )

        except (ValueError, KeyError):
            flash("Invalid subscription details.", "danger")
            return redirect(url_for("subscriptions"))

        plan = db.session.get(Plan, plan_id)
        customer = db.session.get(Customer, customer_id)

        if not plan or not customer or not plan.active:
            flash("Invalid customer or plan.", "danger")

        elif quantity < plan.min_quantity or quantity < 1:
            flash("Invalid subscription quantity.", "danger")

        elif expiry and expiry < start:
            flash(
                "Expiry date cannot be before the start date.",
                "danger"
            )

        else:
            sub = Subscription(
                customer_id=customer.id,
                plan_id=plan.id,
                quantity=quantity,
                start_date=start,
                expiry_date=expiry,
                status="Active"
            )

            db.session.add(sub)
            db.session.commit()

            flash("Subscription created.", "success")

        return redirect(url_for("subscriptions"))

    return render_template(
        "subscriptions.html",
        subscriptions=Subscription.query.order_by(
            Subscription.id.desc()
        ).all(),
        customers=Customer.query.all(),
        plans=Plan.query.filter_by(active=True).all()
    )


# ================= CREATE INVOICE FROM SUBSCRIPTION =================

@app.route("/subscriptions/<int:sid>/invoice", methods=["POST"])
@roles_required("admin", "staff")
def create_invoice(sid):
    sub = db.session.get(Subscription, sid) or abort(404)

    try:
        tax = float(request.form.get("tax_percent") or 0)
    except ValueError:
        flash("Invalid tax percentage.", "danger")
        return redirect(url_for("subscriptions"))

    if tax < 0 or tax > 100:
        flash("Invalid tax percentage.", "danger")
        return redirect(url_for("subscriptions"))

    amount = sub.plan.price * sub.quantity
    total = amount + amount * tax / 100

    invoice = Invoice(
        subscription_id=sid,
        amount=amount,
        tax_percent=tax,
        total=total,
        due_date=date.today(),
        status="Pending"
    )

    db.session.add(invoice)
    db.session.commit()

    flash("Invoice generated successfully.", "success")
    return redirect(url_for("invoices"))


# ================= INVOICES =================

@app.route("/invoices", methods=["GET", "POST"])
@roles_required("admin", "staff")
def invoices():
    if request.method == "POST":
        try:
            sub_id = int(request.form["subscription_id"])
            amount = float(request.form["amount"])
            tax = float(request.form.get("tax_percent") or 0)
            due = date.fromisoformat(request.form["due_date"])

        except (ValueError, KeyError):
            flash("Invalid invoice details.", "danger")
            return redirect(url_for("invoices"))

        sub = db.session.get(Subscription, sub_id)

        if (
            not sub
            or amount <= 0
            or tax < 0
            or tax > 100
        ):
            flash("Please check invoice details.", "danger")

        else:
            total = amount + amount * tax / 100

            invoice = Invoice(
                subscription_id=sub.id,
                amount=amount,
                tax_percent=tax,
                total=total,
                due_date=due,
                status="Pending"
            )

            db.session.add(invoice)
            db.session.commit()

            flash("Invoice created.", "success")

        return redirect(url_for("invoices"))

    return render_template(
        "invoices.html",
        invoices=Invoice.query.order_by(
            Invoice.id.desc()
        ).all(),
        subscriptions=Subscription.query.all()
    )


# ================= INVOICE STATUS =================

@app.route(
    "/invoices/<int:iid>/status/<status>",
    methods=["POST"]
)
@roles_required("admin", "staff")
def invoice_status(iid, status):
    invoice = db.session.get(Invoice, iid) or abort(404)

    if status not in [
        "Draft", "Pending", "Confirmed", "Paid", "Cancelled"
    ]:
        abort(400)

    invoice.status = status
    db.session.commit()

    flash("Invoice status updated.", "success")
    return redirect(url_for("invoices"))


# ================= PAYMENTS =================

@app.route("/payments", methods=["GET", "POST"])
@roles_required("admin", "staff")
def payments():
    if request.method == "POST":
        try:
            invoice_id = int(request.form["invoice_id"])
            amount = float(request.form["amount"])
        except (ValueError, KeyError):
            flash("Invalid payment details.", "danger")
            return redirect(url_for("payments"))

        inv = db.session.get(Invoice, invoice_id)

        if not inv or inv.status in ["Paid", "Cancelled"]:
            flash("Invalid invoice for payment.", "danger")
            return redirect(url_for("payments"))

        already_paid = sum(
            p.amount
            for p in Payment.query.filter_by(
                invoice_id=inv.id
            ).all()
        )

        outstanding = inv.total - already_paid

        if amount <= 0 or amount > outstanding:
            flash("Invalid payment amount.", "danger")

        else:
            payment = Payment(
                invoice_id=inv.id,
                amount=amount,
                method=request.form.get("method", "UPI"),
                paid_on=date.today(),
                note=request.form.get("note")
            )

            db.session.add(payment)

            if already_paid + amount >= inv.total:
                inv.status = "Paid"

            db.session.commit()
            flash("Payment recorded successfully.", "success")

        return redirect(url_for("payments"))

    return render_template(
        "payments.html",
        invoices=Invoice.query.filter(
            Invoice.status != "Paid",
            Invoice.status != "Cancelled"
        ).all(),
        payments=Payment.query.order_by(
            Payment.id.desc()
        ).all()
    )


# ================= STAFF MANAGEMENT =================

@app.route("/staff", methods=["GET", "POST"])
@roles_required("admin")
def staff():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            flash("Please enter all required details.", "danger")

        elif User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")

        else:
            staff_user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role="staff"
            )

            db.session.add(staff_user)
            db.session.commit()

            flash("Staff account created.", "success")

        return redirect(url_for("staff"))

    return render_template(
        "staff.html",
        staff=User.query.filter_by(role="staff").all()
    )


# ================= ERROR HANDLING =================

@app.errorhandler(403)
def forbidden(error):
    return render_template(
        "error.html",
        message="You don't have permission to access this page."
    ), 403


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        message="The requested page or record was not found."
    ), 404


# ================= DATABASE INITIALIZATION =================

with app.app_context():
    db.create_all()

    if not User.query.filter_by(
        email="admin@brightloop.test"
    ).first():
        admin = User(
            name="Demo Admin",
            email="admin@brightloop.test",
            password=generate_password_hash("Admin@12345"),
            role="admin"
        )

        db.session.add(admin)
        db.session.commit()


# ================= RUN APPLICATION =================

if __name__ == "__main__":
    app.run(debug=True)
from datetime import date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, abort
)

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)

from werkzeug.security import (
    generate_password_hash, check_password_hash
)


# -------------------- APPLICATION CONFIGURATION --------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = "change-this-before-deployment"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///brightloop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


# -------------------- DATABASE MODELS --------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")


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


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(120))


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
        db.Integer,
        db.ForeignKey("subscription.id")
    )

    amount = db.Column(db.Float, nullable=False)
    tax_percent = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="Pending")

    subscription = db.relationship(
        "Subscription",
        backref="invoices"
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


# -------------------- LOGIN MANAGEMENT --------------------

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


# -------------------- HOME PAGE --------------------

@app.route("/")
def home():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# -------------------- REGISTRATION --------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        exists = User.query.filter_by(email=email).first()

        if exists:

            flash("That email is already registered.", "danger")

        elif (
            len(password) <= 8
            or not any(c.isupper() for c in password)
            or not any(c.islower() for c in password)
            or not any(not c.isalnum() for c in password)
        ):

            flash(
                "Password must be longer than 8 characters "
                "and include uppercase, lowercase and "
                "a special character.",
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

            flash("Account created. Please log in.", "success")

            return redirect(url_for("login"))

    return render_template("register.html")


# -------------------- LOGIN --------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        user = User.query.filter_by(
            email=request.form["email"].strip().lower()
        ).first()

        if user and check_password_hash(
            user.password, request.form["password"]
        ):

            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# -------------------- LOGOUT --------------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


# -------------------- DASHBOARD --------------------

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


# -------------------- PRODUCTS --------------------

@app.route("/products", methods=["GET", "POST"])
@roles_required("admin", "staff")
def products():

    if request.method == "POST":

        db.session.add(
            Product(
                name=request.form["name"],
                product_type=request.form.get(
                    "product_type", "Software"
                ),
                sales_price=float(request.form["sales_price"]),
                cost_price=float(
                    request.form.get("cost_price") or 0
                ),
                notes=request.form.get("notes")
            )
        )

        db.session.commit()

        flash("Product added.", "success")

        return redirect(url_for("products"))

    return render_template(
        "products.html",
        products=Product.query.order_by(Product.id.desc()).all()
    )


# -------------------- PLANS --------------------

@app.route("/plans", methods=["GET", "POST"])
@roles_required("admin", "staff")
def plans():

    if request.method == "POST":

        db.session.add(
            Plan(
                name=request.form["name"],
                price=float(request.form["price"]),
                billing_cycle=request.form["billing_cycle"],
                min_quantity=int(
                    request.form.get("min_quantity") or 1
                )
            )
        )

        db.session.commit()

        flash("Plan added.", "success")

        return redirect(url_for("plans"))

    return render_template(
        "plans.html",
        plans=Plan.query.all()
    )


# -------------------- CUSTOMERS --------------------

@app.route("/customers", methods=["GET", "POST"])
@roles_required("admin", "staff")
def customers():

    if request.method == "POST":

        db.session.add(
            Customer(
                name=request.form["name"],
                email=request.form["email"],
                company=request.form.get("company")
            )
        )

        db.session.commit()

        flash("Customer added.", "success")

        return redirect(url_for("customers"))

    return render_template(
        "customers.html",
        customers=Customer.query.order_by(Customer.id.desc()).all()
    )


# -------------------- SUBSCRIPTIONS --------------------

@app.route("/subscriptions", methods=["GET", "POST"])
@roles_required("admin", "staff")
def subscriptions():

    if request.method == "POST":

        plan = db.session.get(
            Plan, int(request.form["plan_id"])
        )

        quantity = int(request.form.get("quantity") or 1)

        start = date.fromisoformat(
            request.form["start_date"]
        )

        expiry_text = request.form.get("expiry_date")

        expiry = (
            date.fromisoformat(expiry_text)
            if expiry_text else None
        )

        if not plan:
            flash("Please select a valid plan.", "danger")
            return redirect(url_for("subscriptions"))

        if quantity < plan.min_quantity:
            flash("Quantity is below the minimum quantity.", "danger")
            return redirect(url_for("subscriptions"))

        db.session.add(
            Subscription(
                customer_id=int(request.form["customer_id"]),
                plan_id=plan.id,
                quantity=quantity,
                start_date=start,
                expiry_date=expiry,
                status="Active"
            )
        )

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


# -------------------- CREATE INVOICE --------------------

@app.route(
    "/subscriptions/<int:sid>/invoice",
    methods=["POST"]
)
@roles_required("admin", "staff")
def create_invoice(sid):

    sub = db.session.get(Subscription, sid) or abort(404)

    existing_invoice = Invoice.query.filter_by(
        subscription_id=sid,
        due_date=date.today()
    ).first()

    if existing_invoice:

        flash(
            "An invoice for this subscription already exists today.",
            "warning"
        )

    else:

        amount = sub.plan.price * sub.quantity

        tax = float(request.form.get("tax_percent") or 0)

        if tax < 0 or tax > 100:
            flash("Invalid tax percentage.", "danger")
            return redirect(url_for("subscriptions"))

        total = amount + amount * tax / 100

        db.session.add(
            Invoice(
                subscription_id=sid,
                amount=amount,
                tax_percent=tax,
                total=total,
                due_date=date.today(),
                status="Confirmed"
            )
        )

        db.session.commit()

        flash("Invoice generated.", "success")

    return redirect(url_for("invoices"))


# -------------------- INVOICES --------------------

@app.route("/invoices", methods=["GET", "POST"])
@login_required
def invoices():

    if current_user.role == "customer":
        abort(403)

    if request.method == "POST":

        try:
            subscription_id = int(request.form["subscription_id"])
            amount = float(request.form["amount"])
            tax = float(request.form.get("tax_percent") or 0)
            due_date = date.fromisoformat(request.form["due_date"])

        except (ValueError, KeyError):
            flash("Please enter valid invoice details.", "danger")
            return redirect(url_for("invoices"))

        sub = db.session.get(Subscription, subscription_id)

        if not sub:

            flash("Please select a valid subscription.", "danger")

        elif amount <= 0:

            flash("Invoice amount must be greater than zero.", "danger")

        elif tax < 0 or tax > 100:

            flash("Tax percentage must be between 0 and 100.", "danger")

        else:

            total = amount + (amount * tax / 100)

            invoice = Invoice(
                subscription_id=sub.id,
                amount=amount,
                tax_percent=tax,
                total=total,
                due_date=due_date,
                status="Pending"
            )

            db.session.add(invoice)
            db.session.commit()

            flash("Invoice created successfully!", "success")

            return redirect(url_for("invoices"))

    return render_template(
        "invoices.html",
        invoices=Invoice.query.order_by(Invoice.id.desc()).all(),
        subscriptions=Subscription.query.order_by(
            Subscription.id.desc()
        ).all()
    )


@app.route(
    "/invoices/<int:iid>/status/<status>",
    methods=["POST"]
)
@roles_required("admin", "staff")
def invoice_status(iid, status):

    inv = db.session.get(Invoice, iid) or abort(404)

    if status in ["Draft", "Confirmed", "Paid", "Cancelled"]:

        inv.status = status

        db.session.commit()

    return redirect(url_for("invoices"))


# -------------------- PAYMENTS --------------------

@app.route("/payments", methods=["GET", "POST"])
@roles_required("admin", "staff")
def payments():

    if request.method == "POST":

        inv = db.session.get(
            Invoice, int(request.form["invoice_id"])
        ) or abort(404)

        amount = float(request.form["amount"])

        already_paid = sum(
            p.amount
            for p in Payment.query.filter_by(
                invoice_id=inv.id
            ).all()
        )

        outstanding = inv.total - already_paid

        if amount <= 0 or amount > outstanding:

            flash(
                "Enter an amount greater than zero "
                "and no more than the outstanding balance.",
                "danger"
            )

        else:

            db.session.add(
                Payment(
                    invoice_id=inv.id,
                    amount=amount,
                    method=request.form["method"],
                    paid_on=date.today(),
                    note=request.form.get("note")
                )
            )

            if already_paid + amount >= inv.total:
                inv.status = "Paid"

            db.session.commit()

            flash("Payment recorded.", "success")

        return redirect(url_for("payments"))

    return render_template(
        "payments.html",
        invoices=Invoice.query.filter(
            Invoice.status != "Paid"
        ).all(),
        payments=Payment.query.order_by(Payment.id.desc()).all()
    )


# -------------------- STAFF MANAGEMENT --------------------

@app.route("/staff", methods=["GET", "POST"])
@roles_required("admin")
def staff():

    if request.method == "POST":

        email = request.form["email"].strip().lower()

        if User.query.filter_by(email=email).first():

            flash("Email already exists.", "danger")

        else:

            db.session.add(
                User(
                    name=request.form["name"],
                    email=email,
                    password=generate_password_hash(
                        request.form["password"]
                    ),
                    role="staff"
                )
            )

            db.session.commit()

            flash("Staff account created.", "success")

        return redirect(url_for("staff"))

    return render_template(
        "staff.html",
        staff=User.query.filter_by(role="staff").all()
    )


# -------------------- ERROR HANDLING --------------------

@app.errorhandler(403)
def forbidden(e):

    return render_template(
        "error.html",
        message="You don't have permission to view this page."
    ), 403


# -------------------- DATABASE INITIALIZATION --------------------

with app.app_context():

    db.create_all()

    if not User.query.filter_by(
        email="admin@brightloop.test"
    ).first():

        db.session.add(
            User(
                name="Demo Admin",
                email="admin@brightloop.test",
                password=generate_password_hash("Admin@12345"),
                role="admin"
            )
        )

        db.session.commit()


# -------------------- RUN APPLICATION --------------------

if __name__ == "__main__":
    app.run(debug=True)
from datetime import date
from flask_sqlalchemy import SQLAlchemy

from backend.extensions import db


# ================= USER MODEL =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(
        db.String(150), unique=True, nullable=False
    )
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")


# ================= CUSTOMER MODEL =================

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(120))


# ================= PRODUCT MODEL =================

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    product_type = db.Column(
        db.String(60), default="Software"
    )
    sales_price = db.Column(
        db.Float, nullable=False, default=0
    )
    cost_price = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)


# ================= PLAN MODEL =================

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    billing_cycle = db.Column(
        db.String(20), default="Monthly"
    )
    min_quantity = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)


# ================= SUBSCRIPTION MODEL =================

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=False
    )

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("plan.id"),
        nullable=False
    )

    quantity = db.Column(db.Integer, default=1)
    start_date = db.Column(db.Date, default=date.today)
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="Active")

    customer = db.relationship("Customer")
    plan = db.relationship("Plan")


# ================= INVOICE MODEL =================

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


# ================= PAYMENT MODEL =================

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoice.id"),
        nullable=False
    )

    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(40), default="UPI")
    paid_on = db.Column(db.Date, default=date.today)
    note = db.Column(db.String(255))

    invoice = db.relationship("Invoice")
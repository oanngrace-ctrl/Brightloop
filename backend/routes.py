from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from backend.models import (
    db, User, Customer, Product, Plan,
    Subscription, Invoice, Payment
)

main = Blueprint("main", __name__)


@main.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@main.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    if request.method == "POST":
        customer = Customer(
            name=request.form.get("name"),
            email=request.form.get("email"),
            company=request.form.get("company")
        )
        db.session.add(customer)
        db.session.commit()
        flash("Customer added successfully!", "success")
        return redirect(url_for("main.customers"))

    all_customers = Customer.query.all()
    return render_template(
        "customers.html",
        customers=all_customers
    )


@main.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        product = Product(
            name=request.form.get("name"),
            product_type=request.form.get("product_type", "Software"),
            sales_price=float(request.form.get("sales_price") or 0),
            cost_price=float(request.form.get("cost_price") or 0),
            notes=request.form.get("notes")
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully!", "success")
        return redirect(url_for("main.products"))

    all_products = Product.query.all()
    return render_template("products.html", products=all_products)


@main.route("/plans", methods=["GET", "POST"])
@login_required
def plans():
    if request.method == "POST":
        plan = Plan(
            name=request.form.get("name"),
            price=float(request.form.get("price") or 0),
            billing_cycle=request.form.get("billing_cycle"),
            min_quantity=int(request.form.get("min_quantity") or 1)
        )
        db.session.add(plan)
        db.session.commit()
        flash("Plan added successfully!", "success")
        return redirect(url_for("main.plans"))

    all_plans = Plan.query.all()
    return render_template("plans.html", plans=all_plans)
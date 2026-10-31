<<<<<<< HEAD
# Brightloop Subscription Management System (Hackathon MVP)

## Requirements
- Python 3.10+
- VS Code
- VS Code Python extension

## Run in VS Code terminal

### Windows
```powershell
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
If `py` does not work, try `python` instead.

Open the local address printed in the terminal, usually http://127.0.0.1:5000.

## Demo admin
- Email: admin@brightloop.test
- Password: Admin@12345

Register another account to test customer registration. Admin can create staff accounts.

## Suggested demo flow
1. Login as admin.
2. Add a product.
3. Create a monthly plan.
4. Add a customer.
5. Create a subscription for that customer.
6. Generate an invoice from the subscription.
7. Record a payment.
8. Return to Dashboard and show the updated figures.

## Included
- Registration with the requested password rules and unique email
- Login/logout and role-based admin/staff/customer access
- Product, plan, customer and subscription creation
- Invoice generation with tax and same-day duplicate protection
- Payment records and invoice paid status
- Basic revenue / active subscription / outstanding / overdue dashboard
- Admin-only staff creation

## Important prototype limitations
This is a hackathon starter, not a production billing platform. Password reset email, quotation templates, product variants and price add-ons, discount rules, automated recurring scheduler, partial-payment balance handling, customer-specific portal data, invoice PDF/email, CSRF protection, audit logs, and performance indexing/caching still need to be implemented. Do not use real customer/payment data or deploy with the demo secret/password.
=======
# Brightloop
Brightloop is a Flask-based Subscription Management System designed to simplify subscription tracking, customer management, billing, invoicing, and payment monitoring through an organized and user-friendly web application.
>>>>>>> 168f6634c7da38afd0330d5a838dd81493e4a73c

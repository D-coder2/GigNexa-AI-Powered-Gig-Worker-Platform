# GigNexa — Local Service Marketplace

GigNexa connects local customers with service professionals such as electricians, plumbers, AC technicians, cleaners, painters, carpenters, and appliance repair workers. It is a booking marketplace, not a job board.

## MVP features

- Customer and worker registration/login
- Worker service profiles and starting prices
- Filter professionals by service category and area
- Customers submit booking requests
- Workers accept/reject pending requests
- Workers mark accepted bookings as completed
- Customers review completed services
- Separate customer and worker dashboards

## Tech stack

- Python, Flask, Flask-SQLAlchemy, Flask-Login
- SQLite for the local MVP
- HTML, CSS, JavaScript
- Gunicorn for deployment

## Run locally on Windows PowerShell

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

If PowerShell blocks virtual-environment activation, run the environment's Python directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

The SQLite database `gignexa.db` is created automatically on first run.

## Test the main flow

1. Register one account as a Worker. Add category, area, and optional starting price.
2. Log out and register another account as a Customer.
3. Browse professionals and open the worker profile.
4. Submit a booking request.
5. Log in as the Worker; accept or reject the request.
6. If accepted, mark it completed.
7. Log back in as the Customer and submit a review.

Use different email addresses for the worker and customer.

## Deploy to Render

1. Push this project to a GitHub repository.
2. Create a new **Web Service** on Render and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Create a managed PostgreSQL database and copy its **internal connection URL** into the web service environment variable `DATABASE_URL`. The app supports both local SQLite and PostgreSQL.
5. Add an environment variable named `SECRET_KEY` with a long random value.
6. Start command: `gunicorn app:app`
7. Deploy and test registration, login, and bookings on the live URL.

**Important:** Use PostgreSQL for deployed testing so account and booking data is not lost with an ephemeral local filesystem. Before public production use, add CSRF protection/rate limiting, verify worker identities, and test database backups. No payments are collected by this MVP.

## Suggested next features

- Managed PostgreSQL
- Location/geocoding and distance-based search
- Worker availability calendar
- Email/SMS notifications
- Admin moderation and report handling
- AI recommendations based on category, area, availability, price, and review score
- Payment integration only after defining cancellation/refund and dispute policies

from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import ccxt
import os
import bcrypt
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    trading_mode = db.Column(db.String(20), default='backtest')
    api_key = db.Column(db.String(100))
    api_secret = db.Column(db.String(100))

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password'].encode('utf-8')
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password, user.password.encode('utf-8')):
        session['user_id'] = user.id
        return redirect('/dashboard')
    return "Login fehlgeschlagen!"

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/set_mode', methods=['POST'])
def set_mode():
    user = User.query.get(session['user_id'])
    user.trading_mode = request.form['trading_mode']
    db.session.commit()
    return redirect('/dashboard')

@app.route('/trigger_snipping')
def snipping():
    target_price = float(request.args.get('price'))
    user = User.query.get(session['user_id'])
    exchange = ccxt.binance({
        'apiKey': user.api_key,
        'secret': user.api_secret,
    })
    try:
        for _ in range(60):
            ticker = exchange.fetch_ticker('BTC/USDT')
            current_price = ticker['last']
            if current_price >= target_price:
                exchange.create_order('BTC/USDT', 'market', 'buy', 0.001)
                return "Order ausgeführt bei " + str(current_price)
            time.sleep(10)
        return "Timeout: Preis nicht erreicht."
    except Exception as e:
        return f"Fehler: {str(e)}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
import os

from decimal import Decimal
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    if request.method == "GET":

        data = []
        totalCash = 0
        # get holdings of a user
        rawData = db.execute("SELECT * FROM holdings WHERE userId = ?", session["user_id"])
        for row in rawData:
            amount = row["amount"]
            symbol = lookup(row["symbol"])
            price = symbol["price"]
            value = symbol["price"] * amount
            symbol = symbol["symbol"]
            data.append({
                "symbol" : symbol,
                "amount" : amount,
                "price" : price,
                "value" : value
            })
            print(data[0])
            totalCash = totalCash + value

        userCash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        totalCash = totalCash + userCash[0]["cash"]

        for row in data:
            print(row["symbol"])
            print(row["price"])

        #data being an array with data of the user
        return (render_template("index.html", data=data, totalCash = totalCash, userCash=userCash))
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return(render_template("buy.html"))
    elif request.method == "POST":
        oldSymbol = request.form.get("symbol")
        symbol = lookup(oldSymbol)
        if (symbol==None):
            return apology("invalid ticker")

        try:
            amount = int(request.form.get("shares"))
            symbol["price"] = float(symbol["price"])
        except:
            return apology("insert valid input")

        if amount<0 or symbol["price"]<0:
            return apology("insert correct input")

        cost = symbol["price"] * amount;

        # check if the user already has that symbol on their holdings
        rawHoldings = db.execute("SELECT symbol FROM holdings WHERE userId = ?", session["user_id"])
        existingHoldings = []
        for i in rawHoldings:
            existingHoldings.append(i["symbol"])

        if (symbol["symbol"] not in existingHoldings):
            #create a symbol for that user
            db.execute("INSERT INTO holdings (userId, symbol, amount) VALUES (?, ?, ?)", session["user_id"], symbol["symbol"], 0)
        # once we created a row

        userCash = db.execute("SELECT cash from users where id = ?", session["user_id"])
        print (userCash[0]["cash"])
        userCash = userCash[0]["cash"]

        if (cost > userCash):
                return apology("you do not have enough money")
        elif (userCash >= cost):
            try:
                #subtract money from user and add to their stocks
                db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", cost, session["user_id"])
                db.execute("UPDATE holdings SET amount = amount + ? WHERE symbol = ? AND userId = ?", amount, symbol["symbol"], session["user_id"])
                db.execute("INSERT INTO transactions (userId, transactionType, symbol, amount, price) VALUES (?, ?, ?, ?, ?)", session["user_id"], "purchase", symbol["symbol"], amount, symbol["price"])
                # print message
                flash("Bought!")
                return redirect(url_for("index"))
            except Exception as e:
                return apology(f"{e}")

    #return apology("TODO")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        data = db.execute("SELECT * FROM transactions WHERE userId = ?", session["user_id"])
        print(data)
        return(render_template("history.html", data=data))
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        object = lookup(request.form.get("symbol"))
        if (object == None):
            return apology("insert valid ticker")
        name = object["name"]
        symbol = object["symbol"]
        price = object["price"]
        return render_template("quoted.html", name=name, price=price, symbol=symbol)

    return apology("TODO")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        if (request.form.get("username") == ''):
            return apology("must provide username")
        if (request.form.get("password") == ''):
            return apology("must provide password")
        if (request.form.get("confirmation") == ''):
            return apology("must provide password")
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide username")
        if request.form.get("password")!=request.form.get("confirmation"):
            return apology("password and confirmation must match")
        totalUsers = db.execute("SELECT username FROM users")
        for user in totalUsers:
            print(user["username"])
            print(request.form.get("username"))
            if request.form.get("username") == user["username"]:
                return apology("username already in use")

        password = generate_password_hash(request.form.get("password"), method='scrypt')

        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), password)
            return (render_template('login.html'))
        except Exception:
            return (apology("there was an error", 500))
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":

         # send every holding of the user
        holdings = db.execute("SELECT * FROM holdings WHERE userId = ?", session["user_id"])

        return(render_template("sell.html", holdings=holdings))
    elif request.method == "POST":
        oldSymbol = request.form.get("symbol")
        symbol = lookup(oldSymbol)

        if (symbol == None):
            return apology("incorrect input")

        amount = float(request.form.get("shares"))
        symbol["price"] = float(symbol["price"])

        cost = symbol["price"] * amount;

        #add money to user and subtract from their stocks
        try:
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", cost, session["user_id"])
            db.execute("UPDATE holdings SET amount = amount - ? WHERE symbol = ? AND userId = ?", amount, symbol["symbol"], session["user_id"])
            db.execute("INSERT INTO transactions (userId, transactionType, symbol, amount, price) VALUES (?, ?, ?, ?, ?)", session["user_id"], "sale", symbol["symbol"], amount, symbol["price"])
            flash("Sold!")
            return redirect(url_for("index"))

        except:
            return apology("error")
        # print message
    #return apology("TODO")
    return apology("TODO")

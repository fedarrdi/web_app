from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import logging

app = Flask(__name__)
app.secret_key = "your_secret_key"


client = MongoClient("mongodb://localhost:27017/")
db = client["flask_web_app"]
forms_collection = db["forms"]
user_collection = db["users"]
logging.info("Connected to MongoDB.")

@app.route("/")
def home():
    if "username" not in session:
        flash("Please log in to view your forms.")
        return redirect(url_for("login"))
    try:
        forms = list(forms_collection.find({"creator": session["username"]}))
    except Exception as e:
        logging.error(f"Error fetching forms for user {session['username']}: {e}")
        forms = []

    return render_template("index.html", forms=forms)

@app.route("/code", methods=["GET", "POST"])
def code():
    if "username" not in session:
        return redirect(url_for("login"))

    forms = []
    if request.method == "POST":
        secret_code = request.form.get("secret_code")
        if not secret_code:
            flash("Please enter a secret code.")
            return redirect(url_for("code"))
        try:
            forms = list(forms_collection.find({"code": secret_code}))

            if not forms:
                flash("No forms found with the provided secret code.")

        except Exception as e:
            logging.error(f"Error fetching forms by secret code: {e}")
            flash("An error occurred. Please try again.")

    print(forms)
    return render_template("code.html", forms=forms)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        logging.debug(f"Login attempt for user: {username}")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("login"))

        user = user_collection.find_one({"name": username})
        if user and user["pass"] == password:
            session["username"] = username
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        logging.debug(f"Sign-up attempt for user: {username}")

        if not username or not password or not confirm_password:
            flash("All fields are required.")
            return redirect(url_for("signup"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("signup"))

        if user_collection.find_one({"name": username}):
            flash("Username already exists. Please choose a different one.")
            return redirect(url_for("signup"))

        user_data = {"name": username, "pass": password}
        user_collection.insert_one(user_data)
        logging.info(f"User signed up: {username}")

        flash("Sign-up successful! You can now log in.")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/create_form", methods=["GET", "POST"])
def create_form():
    if "username" in session:
        if request.method == "POST":
            try:
                quiz_data = request.json
                quiz_data["creator"] = session["username"]
                result = forms_collection.insert_one(quiz_data)
                return redirect(url_for("home"))
            except Exception as e:
                return e
        return render_template("create_form.html")
    else:
        return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)


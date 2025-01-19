from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId

import logging

app = Flask(__name__)
app.secret_key = "your_secret_key"

client = MongoClient("mongodb://localhost:27017/")
db = client["flask_web_app"]
forms_collection = db["forms"]
user_collection = db["users"]
answers_collection = db["answer"]

logging.info("Connected to MongoDB.")

@app.route('/user_made_forms')
def user_forms():

    if "username" not in session:
        flash("Please log in to view your forms.")
        return redirect(url_for("login"))

    user_answers = list(answers_collection.find({'user': session["username"]}))
    completed_forms = []

    form_ids = set()

    for answer in user_answers:
        form = forms_collection.find_one({'_id': ObjectId(answer['form_id'])})
        if not form:
            continue

        form_details = {
            'form_name': form['formName'],
            'code': form['code'],
            'creator': form['creator'],
            'questions': []
        }

        if answer['form_id'] not in form_ids:
            form_ids.add(answer['form_id'])
            completed_forms.append(form_details)

        for idx, question in enumerate(form['questions']):
            question_data = {
                'question_text': question['question'],
                'possible_answers': question['answers'],
                'correct_answer': question['correctAnswer'],
                'user_answer': question['answers'][int(answer['answers'][str(idx)])],
                'is_correct': str(question['correctAnswer']) == answer['answers'].get(str(idx), None)
            }
            form_details['questions'].append(question_data)


    return render_template('dispaly_made_forms.html', forms=completed_forms, username=session["username"])


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
    print(forms)
    return render_template("index.html", forms=forms)


@app.route("/code", methods=["GET", "POST"])
def code():
    if "username" not in session:
        return redirect(url_for("login"))

    forms = []
    if request.method == "POST":
        if "secret_code" in request.form:
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

        elif "submit_answers" in request.form:
            try:
                form_id = request.form.get("form_id")
                answers = {}

                for key, value in request.form.items():
                    if key.startswith("question_"):
                        question_id = key.split("_")[1]
                        answers[str(int(question_id) - 1)] = value

                existing_entry = answers_collection.find_one({
                    "form_id": form_id,
                    "user": session["username"]
                })

                if existing_entry:
                    # Update the existing entry
                    answers_collection.update_one(
                        {"_id": existing_entry["_id"]},
                        {"$set": {"answers": answers}}
                    )
                    flash("Your answers have been updated successfully!")
                else:
                    # Create a new entry
                    answer_doc = {
                        "form_id": form_id,
                        "user": session["username"],
                        "answers": answers,
                    }
                    answers_collection.insert_one(answer_doc)
                    flash("Answers submitted successfully!")

                return redirect(url_for("code"))

            except Exception as e:
                logging.error(f"Error saving answers: {e}")
                flash("An error occurred while saving your answers.")

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



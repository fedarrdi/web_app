from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd
from io import BytesIO
from pymongo import MongoClient
from datetime import datetime
import logging
from collections import Counter


app = Flask(__name__)
app.secret_key = "your_secret_key"

client = MongoClient("mongodb://localhost:27017/")
db = client["flask_web_app"]
forms_collection = db["forms"]
user_collection = db["users"]
answers_collection = db["answer"]

logging.info("Connected to MongoDB.")
def create_export(form_code, export_format):
    # Find form by code
    form = forms_collection.find_one({'code': form_code})
    if not form:
        return None

    # Get all answers for this form
    answers = list(answers_collection.find({'form_id': str(form['_id'])}))
    print(answers)
    # Create workbook
    output = BytesIO()

    if export_format == 'csv':
        df = create_form_dataframe(form, answers)
        df.to_csv(output, index=False)
    else:  # Excel format
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Form Information Sheet
            create_form_info_sheet(writer, form)
            print("kjadsadjsalkjdlsakdjsaldlas")
            # Questions and Statistics Sheet
            create_questions_stats_sheet(writer, form, answers)

            # Individual Responses Sheet
            create_responses_sheet(writer, form, answers)

    output.seek(0)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{form['formName']}_{timestamp}.{export_format}"

    return output, filename

def create_form_info_sheet(writer, form):
    """Creates the basic form information sheet"""
    info_data = {
        'Property': ['Form Name', 'Creator', 'Code', 'Number of Questions'],
        'Value': [
            form['formName'],
            form['creator'],
            form['code'],
            len(form['questions'])
        ]
    }
    df_info = pd.DataFrame(info_data)
    df_info.to_excel(writer, sheet_name='Form Information', index=False)

def create_questions_stats_sheet(writer, form, answers):
    """Creates detailed statistics for each question"""
    all_stats = []
    print("*************************************************************")

    for q_idx, question in enumerate(form['questions']):
        # Basic question info
        question_stats = {
            'Question Number': q_idx + 1,
            'Question Text': question['question'],
            'Correct Answer': question['answers'][question['correctAnswer']],
            'Total Responses': len(answers)
        }

        # Calculate statistics for each possible answer
        answer_counts = Counter()
        for answer_doc in answers:
            if q_idx in answer_doc['answers']:
                selected_idx = int(answer_doc['answers'][q_idx])
                if selected_idx < len(question['answers']):
                    selected_answer = question['answers'][selected_idx]
                    answer_counts[selected_answer] += 1
        print("======================================================================")
        print(answer_counts)

        # Calculate percentages for each answer
        total_responses = len(answers)
        for idx, answer in enumerate(question['answers']):
            count = answer_counts[answer]
            percentage = (count / total_responses * 100) if total_responses > 0 else 0
            question_stats[f'Answer Option {idx + 1}'] = answer
            question_stats[f'Count for Option {idx + 1}'] = count
            question_stats[f'Percentage for Option {idx + 1}'] = f"{percentage:.1f}%"

            # Mark if this is the correct answer
            if idx == question['correctAnswer']:
                question_stats[f'Note for Option {idx + 1}'] = "CORRECT ANSWER"

        all_stats.append(question_stats)

    # Create DataFrame and write to Excel
    df_stats = pd.DataFrame(all_stats)
    df_stats.to_excel(writer, sheet_name='Questions & Statistics', index=False)

def create_responses_sheet(writer, form, answers):
    """Creates detailed sheet of individual responses"""
    rows = []

    for answer_doc in answers:
        row = {
            'User': answer_doc['user']
        }

        # Add each question and the user's answer
        for q_idx, question in enumerate(form['questions']):
            q_num = q_idx + 1
            row[f'Q{q_num} - {question["question"]}'] = question['answers'][
                int(answer_doc['answers'][q_idx])
            ]

            # Add if answer was correct
            user_answer_idx = int(answer_doc['answers'][q_idx])
            is_correct = user_answer_idx == question['correctAnswer']
            row[f'Q{q_num} Correct?'] = 'Yes' if is_correct else 'No'

        rows.append(row)

    df_responses = pd.DataFrame(rows)
    df_responses.to_excel(writer, sheet_name='Individual Responses', index=False)

def create_form_dataframe(form, answers):
    """Creates a single DataFrame for CSV export"""
    # First, create the form information section
    rows = [
        {'Section': 'Form Information', 'Field': 'Form Name', 'Value': form['formName']},
        {'Section': 'Form Information', 'Field': 'Creator', 'Value': form['creator']},
        {'Section': 'Form Information', 'Field': 'Code', 'Value': form['code']},
        {'Section': 'Form Information', 'Field': 'Total Questions', 'Value': len(form['questions'])},
        {'Section': 'Form Information', 'Field': 'Total Responses', 'Value': len(answers)},
        {'Section': '', 'Field': '', 'Value': ''}  # Empty row for spacing
    ]

    # Add questions section with statistics
    for q_idx, question in enumerate(form['questions']):
        # Add question information
        rows.append({
            'Section': f'Question {q_idx + 1}',
            'Field': 'Question Text',
            'Value': question['question']
        })
        rows.append({
            'Section': f'Question {q_idx + 1}',
            'Field': 'Correct Answer',
            'Value': question['answers'][question['correctAnswer']]
        })

        # Calculate answer statistics
        answer_counts = Counter()
        total_responses = Counter()
        for answer_doc in answers:
            print(q_idx, answer_doc)
            if q_idx in answer_doc['answers']:
                selected_idx = int(answer_doc['answers'][q_idx])
                print(f"Selected idx: {selected_idx}, options: {len(question['answers'])}")
                if selected_idx < len(question['answers']):
                    selected_answer = question['answers'][selected_idx]
                    answer_counts[selected_answer] += 1
                    total_responses[q_idx] += 1

        print(answer_counts)
        print(total_responses)

        # Add statistics for each answer option
        total_responses = len(answers)
        for idx, answer in enumerate(question['answers']):
            count = answer_counts[answer]
            percentage = (count / total_responses * 100) if total_responses > 0 else 0
            rows.append({
                'Section': f'Question {q_idx + 1}',
                'Field': f'Option {idx + 1}',
                'Value': f"{answer} - {count} responses ({percentage:.1f}%)"
                f"{' (CORRECT ANSWER)' if idx == question['correctAnswer'] else ''}"
            })

        rows.append({'Section': '', 'Field': '', 'Value': ''})  # Spacing

    return pd.DataFrame(rows)

@app.route('/export', methods=['GET', 'POST'])
def export_form():
    if request.method == 'POST':
        secret_code = request.form.get('secret_code')
        export_format = request.form.get('format', 'csv')
        print(secret_code + " " + export_format)

        result = create_export(secret_code, export_format)
        print(result)
        if result is None:
            print("aleadnroooooo")
            flash('No form found with this code')
            return redirect(url_for('export_form'))

        output, filename = result

        mimetype = 'text/csv' if export_format == 'csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    return render_template('export.html')

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
                'user_answer': question['answers'][int(answer['answers'][idx])],
                'is_correct': question['correctAnswer'] == answer['answers'][idx]
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
                answers = [None for q in request.form.keys() if q.startswith("question_")]

                for key, value in request.form.items():
                    if key.startswith("question_"):
                        question_id = int(key.split("_")[1])
                        answers[question_id - 1] = int(value)

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
                print(quiz_data)
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



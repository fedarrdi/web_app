from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for using flash messages

client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB connection string
db = client.form_builder  # Database name
forms_collection = db.forms  # Collection name


@app.route("/")
def home():
    forms = list(forms_collection.find())
    return render_template("index.html", forms=forms)


@app.route("/create_form", methods=["GET", "POST"])
def create_form():
    if request.method == "POST":
        # Retrieve form data
        form_name = request.form.get("name")
        fields = request.form.getlist("fields[]")

        # Basic validation
        if not form_name or not fields:
            flash("Form name and at least one field are required.")
            return redirect(url_for("create_form"))

        # Save form data to MongoDB
        form_data = {"form_name": form_name, "fields": fields}
        forms_collection.insert_one(form_data)

        # Redirect to index.html with a success message
        flash("Form created successfully!")
        return redirect(url_for("home"))  # Redirect to the home route rendering index.html

    return render_template("create_form.html")


if __name__ == "__main__":
    app.run(debug=True)


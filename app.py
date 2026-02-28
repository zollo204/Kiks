# ===============================
# IMPORTS
# ===============================

import os
import csv
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, send_from_directory
)

from werkzeug.security import generate_password_hash, check_password_hash


# ===============================
# APP INITIALIZATION
# ===============================

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")  # Use environment variable if possible


# ===============================
# M-PESA ENVIRONMENT VARIABLES
# ===============================

consumer_key = os.getenv("awFICQ3XydFTsJTZp0SNJOSxGSx5zeAdlHuc1d6T2rWQvwGN")
consumer_secret = os.getenv("KzGBDBfuHxfnkWMpJ1UvdaAr4nY9ivKVRS3JZMZppr8aVcHB2fw5LM5GNFgsR85n")
passkey = os.getenv("PASSKEY")
shortcode = os.getenv("174379")


# ===============================
# M-PESA ACCESS TOKEN FUNCTION
# ===============================

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    return response.json().get('access_token')

# -----------------------------
# CONFIG
# -----------------------------

DATA_FILE = "registrations.csv"
CONTACT_FILE = "contact_messages.csv"
EXAMS_FILE = "exam_results.csv"
STUDENT_RESULTS = "student_results.csv"
INSTRUCTOR_FILE = "instructors.csv"

UPLOAD_FOLDER = "static/uploads"
DOWNLOAD_FOLDER = "static/downloads"
PASSPORT_FOLDER = os.path.join(UPLOAD_FOLDER, "passports")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(PASSPORT_FOLDER, exist_ok=True)

# -----------------------------
# CREATE CSV FILES
# -----------------------------

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "Full Name","DOB","Gender","Email","Phone",
            "Course","Constituency","Admission No",
            "Payment Status","Amount Paid","Notes",
            "Password","Passport"
        ])

if not os.path.exists(CONTACT_FILE):
    with open(CONTACT_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "Date","Full Name","Email","Phone","Message","Attachment"
        ])

if not os.path.exists(EXAMS_FILE):
    with open(EXAMS_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "Year","First Class","Second Upper",
            "Second Lower","Pass","Fail"
        ])

if not os.path.exists(STUDENT_RESULTS):
    with open(STUDENT_RESULTS, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "Admission No","Full Name","Course",
            "Year","Achievement","Passport"
        ])

if not os.path.exists(INSTRUCTOR_FILE):
    with open(INSTRUCTOR_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "Fullname","Username","Password","Course"
        ])

# -----------------------------
# PUBLIC PAGES
# -----------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/courses")
def courses():
    return render_template("courses.html")

@app.route("/downloads")
def downloads():
    return render_template("downloads.html")

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route("/admissions")
def admissions():
    return render_template("admissions.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/success")
def success():
    return render_template("success.html")

# -----------------------------
# STUDENT REGISTRATION
# -----------------------------

@app.route("/register", methods=["POST"])
def register():
    data = [
        request.form.get("fullname"),
        request.form.get("dob"),
        request.form.get("gender"),
        request.form.get("email"),
        request.form.get("phone"),
        request.form.get("course"),
        request.form.get("constituency"),
        "",  # Admission No
        "Pending",
        "0",
        "",
        "",  # Password (admin sets)
        ""
    ]
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(data)
    return redirect(url_for("success"))

# -----------------------------
# CONTACT FORM
# -----------------------------

@app.route("/contact-submit", methods=["POST"])
def contact_submit():
    file = request.files.get("attachment")
    filename = ""

    if file and file.filename:
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))

    with open(CONTACT_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            request.form.get("fullName"),
            request.form.get("email"),
            request.form.get("phone"),
            request.form.get("message"),
            filename
        ])

    return jsonify({"success": True})

# =========================
# INSTRUCTOR SYSTEM
# =========================

@app.route("/instructor/login", methods=["GET", "POST"])
def instructor_login():
    error = None
    message = None

    if request.method == "POST":
        # Check if forgot password form was submitted
        if request.form.get("username_forgot"):
            username = request.form.get("username_forgot").strip()
            if username:
                with open(CONTACT_FILE, "a", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "INSTRUCTOR PASSWORD RESET REQUEST",
                        "",
                        "",
                        f"Instructor '{username}' requested password reset",
                        ""
                    ])
                message = "Password reset request sent. Contact admin."
            else:
                error = "Username is required"
            return render_template("instructor_login.html", error=error, message=message)

        # Normal login form
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if os.path.exists(INSTRUCTOR_FILE):
            with open(INSTRUCTOR_FILE, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) < 4:
                        continue
                    file_fullname, file_username, file_password, file_course, *_ = row
                    if file_username == username and check_password_hash(file_password, password):
                        session["instructor"] = file_fullname
                        session["instructor_course"] = file_course
                        return redirect(url_for("instructor_dashboard"))

        error = "Invalid username or password"

    return render_template("instructor_login.html", error=error, message=message)

# =========================
# INSTRUCTOR DASHBOARD
# =========================

@app.route("/instructor/dashboard")
def instructor_dashboard():
    if "instructor" not in session:
        return redirect(url_for("instructor_login"))

    instructor_info = None
    if os.path.exists(INSTRUCTOR_FILE):
        with open(INSTRUCTOR_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=["fullname","username","password","course"])
            for row in reader:
                if row["fullname"] == session.get("instructor"):
                    instructor_info = row
                    break

    course = session.get("instructor_course")
    students = []

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, newline="", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            data = reader[1:]
            for idx, row in enumerate(data):
                if row[5].strip() == course.strip():
                    students.append((idx, row))

    return render_template(
        "instructor_dashboard.html",
        students=students,
        instructor=instructor_info
    )

# =========================
# INSTRUCTOR EDIT / DELETE
# =========================

@app.route("/admin/edit_instructor/<int:index>", methods=["GET", "POST"])
def edit_instructor(index):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with open(INSTRUCTOR_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    instructor = rows[index + 1]

    if request.method == "POST":
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        password = request.form.get("password")
        course = request.form.get("course")

        if fullname: instructor[0] = fullname
        if username: instructor[1] = username
        if password: instructor[2] = generate_password_hash(password)
        if course: instructor[3] = course

        photo = request.files.get("photo")
        if photo and photo.filename:
            os.makedirs("static/uploads/instructors", exist_ok=True)
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + photo.filename
            photo.save(os.path.join("static/uploads/instructors", filename))
            if len(instructor) > 4:
                instructor[4] = filename
            else:
                instructor.append(filename)

        rows[index + 1] = instructor
        with open(INSTRUCTOR_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        return redirect(url_for("admin"))

    return render_template("edit_instructor.html", instructor=instructor, index=index)

@app.route("/admin/delete_instructor/<int:index>", methods=["POST"])
def delete_instructor(index):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with open(INSTRUCTOR_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if index + 1 < len(rows):
        rows.pop(index + 1)

    with open(INSTRUCTOR_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    return redirect(url_for("admin"))

# =========================
# INSTRUCTOR LOGOUT
# =========================

@app.route("/instructor/logout")
def instructor_logout():
    session.pop("instructor", None)
    session.pop("instructor_course", None)
    return redirect(url_for("instructor_login"))

# =========================
# ADMIN LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["username"] == ADMIN_USERNAME and request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)

# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))

    # Load students
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        students = list(enumerate(list(csv.reader(f))[1:]))

    # Load contacts
    with open(CONTACT_FILE, newline="", encoding="utf-8") as f:
        contacts = list(enumerate(list(csv.reader(f))[1:]))

    # Load instructors
    instructors = []
    if os.path.exists(INSTRUCTOR_FILE):
        with open(INSTRUCTOR_FILE, newline="", encoding="utf-8") as f:
            instructors = list(enumerate(list(csv.reader(f))[1:]))

    return render_template(
        "admin.html",
        students=students,
        contacts=contacts,
        instructors=instructors
    )
# =========================
# ADMIN EXAMS
# =========================

@app.route("/admin/exams", methods=["GET", "POST"])
def admin_exams():
    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        with open(EXAMS_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                request.form.get("year"),
                request.form.get("first"),
                request.form.get("upper"),
                request.form.get("lower"),
                request.form.get("pass"),
                request.form.get("fail")
            ])
        return redirect(url_for("admin_exams"))

    with open(EXAMS_FILE, newline="", encoding="utf-8") as f:
        results = list(csv.reader(f))[1:]

    return render_template("admin_exams.html", results=results)

# =========================
# EXPORT EXAM RESULTS
# ==========================

@app.route("/admin/export-exams")
def export_exams():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return send_from_directory(
        directory=".",
        path=EXAMS_FILE,
        as_attachment=True,
        download_name="exam_performance.xlsx"
    )

# =========================
# ADMIN STUDENT RESULTS
# ==========================

@app.route("/admin/student-results", methods=["GET", "POST"])
def admin_student_results():
    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        passport = request.files.get("passport")
        passport_path = ""
        if passport and passport.filename:
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + passport.filename
            passport_path = f"uploads/{filename}"
            passport.save(os.path.join("static", passport_path))
        with open(STUDENT_RESULTS, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                request.form.get("adm"),
                request.form.get("name"),
                request.form.get("course"),
                request.form.get("year"),
                request.form.get("achievement"),
                passport_path
            ])
        return redirect(url_for("admin_student_results"))

    with open(STUDENT_RESULTS, newline="", encoding="utf-8") as f:
        results = list(csv.reader(f))[1:]

    return render_template("admin_student_results.html", results=results)

# =========================
# ADMIN EDIT STUDENT
# ==========================

@app.route("/edit/<int:index>", methods=["POST"])
def edit(index):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    student = rows[index + 1]
    fields = [
        "fullname","dob","gender","email","phone",
        "course","constituency","admission_no",
        "payment_status","amount_paid","notes","password"
    ]
    for i, field in enumerate(fields):
        value = request.form.get(field)
        if value:
            student[i] = value
    rows[index + 1] = student

    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return redirect(url_for("admin"))

# =========================
# ADMIN DELETE STUDENT
# ==========================

@app.route("/delete-student/<int:index>", methods=["POST"])
def delete_student(index):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if index + 1 < len(rows):
        rows.pop(index + 1)
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return redirect(url_for("admin"))

# =========================
# CREATE INSTRUCTOR
# ==========================

@app.route("/admin/create_instructor", methods=["GET", "POST"])
def create_instructor():
    if not session.get("admin"):
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        fullname = (request.form.get("fullname") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        course = (request.form.get("course") or "").strip()
        if not fullname or not username or not password or not course:
            message = "All fields are required!"
        else:
            hashed_password = generate_password_hash(password)
            with open(INSTRUCTOR_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([fullname, username, hashed_password, course])
            message = "Instructor created successfully!"
    return render_template("create_instructor.html", message=message)
    # =========================
# STUDENT LOGIN
# =========================

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    error = None
    if request.method == "POST":
        adm = request.form.get("admission_no")
        pwd = request.form.get("password")
        with open(DATA_FILE, newline="", encoding="utf-8") as f:
            students = list(csv.reader(f))[1:]
            for i, s in enumerate(students):
                if s[7] == adm and s[11] == pwd:
                    session["student_index"] = i
                    return redirect(url_for("student_dashboard"))
        error = "Invalid Admission Number or Password"
    return render_template("student_login.html", error=error)

# =========================
# STUDENT PROFILE
# =========================

@app.route("/student/profile", methods=["GET", "POST"])
def student_profile():
    if "student_index" not in session:
        return redirect(url_for("student_login"))

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        student = rows[session["student_index"] + 1]

    message = None
    if request.method == "POST":
        passport = request.files.get("passport")
        if passport and passport.filename:
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + passport.filename
            save_path = os.path.join(PASSPORT_FOLDER, filename)
            passport.save(save_path)
            student[12] = filename
            message = "Passport uploaded successfully"

        password = request.form.get("password")
        if password:
            student[11] = password
            message = "Password updated successfully"

        rows[session["student_index"] + 1] = student
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

    return render_template("student_profile.html", student=student, message=message)

# =========================
# STUDENT FORGOT PASSWORD
# =========================

@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    admission_no = request.form.get("admission_no")
    if not admission_no:
        return render_template("student_login.html", error="Admission number required", show_forgot=True)
    with open(CONTACT_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            "PASSWORD RESET REQUEST",
            "",
            "",
            f"Student with Admission No {admission_no} requested password reset",
            ""
        ])
    return render_template("student_login.html", message="Password reset request sent. Contact admin.", show_forgot=True)

# =========================
# STUDENT DASHBOARD
# =========================

@app.route("/student/dashboard")
def student_dashboard():
    if "student_index" not in session:
        return redirect(url_for("student_login"))
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        student = list(csv.reader(f))[session["student_index"] + 1]
    return render_template("student_dashboard.html", student=student)

# =========================
# DELETE CONTACT (ADMIN)
# =========================

@app.route("/delete-contact/<int:index>", methods=["POST"])
def delete_contact(index):
    if not session.get("admin"):
        return redirect(url_for("login"))

    with open(CONTACT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if index + 1 < len(rows):
        rows.pop(index + 1)
    with open(CONTACT_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return redirect(url_for("admin"))

# =========================
# LOGOUTS
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/student/logout")
def student_logout():
    session.clear()
    return redirect(url_for("student_login"))

# =========================
# RUN
# =========================

if __name__ == "__main__":

    app.run(debug=True)

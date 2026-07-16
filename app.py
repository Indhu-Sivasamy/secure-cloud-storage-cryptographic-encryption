from flask import Flask, render_template, request, redirect, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
import os
app = Flask(__name__)
app.secret_key = "securecloudkey"
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
def log_activity(action):

    with open("activity.log", "a", encoding="utf-8") as log:

        log.write(f"{action}\n")

# Generate key file only once
if not os.path.exists("secret.key"):
    with open("secret.key", "wb") as key_file:
        key_file.write(Fernet.generate_key())

# Load saved key
with open("secret.key", "rb") as key_file:
    key = key_file.read()

f = Fernet(key)

# User Table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        new_user = User(
            username=username,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(
            username=username,
            password=password
        ).first()

        if user:
          session['user'] = username
          log_activity(f"🔐 {username} logged in")
          flash('Login Successful')
          return redirect('/dashboard')
        else:
            return "<h1>Invalid Username or Password ❌</h1>"

    return render_template('login.html')

# Dashboard Page
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    if 'user' not in session:
        return redirect('/login')
    user_folder = os.path.join(
    app.config['UPLOAD_FOLDER'],
    session['user']
)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    if request.method == 'POST':

        file = request.files['file']

        if file:

            filepath = os.path.join(
                user_folder,
                file.filename
            )

            # Save file
            file.save(filepath)

            # Read file
            with open(filepath, 'rb') as f1:
                data = f1.read()

            # Encrypt file
            encrypted_data = f.encrypt(data)

            # Save encrypted file
            with open(filepath, 'wb') as f2:
                f2.write(encrypted_data)

            flash('File Uploaded & Encrypted Successfully')
            log_activity(f"📂 {session['user']} uploaded {file.filename}")

    # Show uploaded files
    total_storage = 0
    files = []

    for file in os.listdir(user_folder):

        if not file.startswith('decrypted_'):

            filepath = os.path.join(
                user_folder,
                file
            )

            # File size
            size = os.path.getsize(filepath)

            # Convert KB
            size_kb = round(size / 1024, 2)

            total_storage += size_kb

            # Upload time
            upload_time = os.path.getmtime(filepath)

            from datetime import datetime

            upload_time = datetime.fromtimestamp(
                upload_time
            ).strftime('%d-%m-%Y %H:%M')

            files.append({
                'name': file,
                'size': size_kb,
                'time': upload_time
            })

    # Read recent activities
    activities = []

    if os.path.exists("activity.log"):

        with open("activity.log", "r", encoding="utf-8") as log:

            activities = log.readlines()

        # Latest 5 activities
        activities = activities[-5:]

        # Latest first
        activities.reverse()

    # Current logged-in user
    current_user = User.query.filter_by(
        username=session['user']
    ).first()

    return render_template(
        'dashboard.html',
        files=files,
        total_files=len(files),
        user=current_user,
        storage=round(total_storage, 2),
        storage_percent=round((total_storage / (1024 * 1024)) * 100, 2),
        activities=activities
    )
   
# Decrypt File
@app.route('/decrypt/<filename>')
def decrypt_file(filename):

    if 'user' not in session:
        return redirect('/login')

    filepath = os.path.join(
    app.config['UPLOAD_FOLDER'],
    session['user'],
    filename
    )

    # Read encrypted file
    with open(filepath, 'rb') as file:
        encrypted_data = file.read()

    # Decrypt file
    decrypted_data = f.decrypt(encrypted_data)

    # Create decrypted file
    decrypted_path = os.path.join(
    app.config['UPLOAD_FOLDER'],
    session['user'],
    'decrypted_' + filename
)

    with open(decrypted_path, 'wb') as file:
        file.write(decrypted_data)
        log_activity(f"🔓 {session['user']} decrypted {filename}")

    # Download decrypted file
    return send_file(
        decrypted_path,
        as_attachment=True
    )
# Delete File
@app.route('/delete/<filename>')
def delete_file(filename):

    if 'user' not in session:
        return redirect('/login')

    filepath = os.path.join(
    app.config['UPLOAD_FOLDER'],
    session['user'],
    filename
)

    # Delete file if exists
    if os.path.exists(filepath):
        os.remove(filepath)
        flash('File Deleted Successfully')
        log_activity(f"🗑 {session['user']} deleted {filename}")


    return redirect('/dashboard')
# Logout
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')

# Create Database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
    
    
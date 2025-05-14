# Inshallah - Employee Duty Management App (One-File Version)

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'inshallah_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'masterlists')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(10))  # 'admin' or 'employee'
    password = db.Column(db.String(200), default=generate_password_hash("God is the Greatest"))

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_number = db.Column(db.String(20))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_number = request.form['emp_number']
        password = request.form['password']
        user = User.query.filter_by(emp_number=emp_number).first()
        if user and check_password_hash(user.password, password):
            session['emp_number'] = user.emp_number
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('employee_dashboard'))
        else:
            flash("Invalid login credentials", "danger")
    return render_template_string(login_html)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['masterlist']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            flash("Masterlist uploaded successfully", "success")
    complaints = Complaint.query.order_by(Complaint.timestamp.desc()).all()
    return render_template_string(admin_html, complaints=complaints)

@app.route('/employee')
def employee_dashboard():
    if session.get('role') != 'employee':
        return redirect(url_for('login'))
    emp_number = session['emp_number']
    duty_info = "No duty assigned. Please check with admin."
    days_worked = 0
    sick_leave = False
    try:
        duty_file = os.path.join(app.config['UPLOAD_FOLDER'], 'duties.xlsx')
        if os.path.exists(duty_file):
            df = pd.read_excel(duty_file)
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df[df['employee number'] == int(emp_number)]
            today = datetime.today()
            current_month = today.month
            days_worked = df[df['date'].dt.month == current_month].shape[0]
            user_duty = df[df['date'].dt.date == today.date()]
            if not user_duty.empty:
                row = user_duty.iloc[0]
                duty_info = f"You are scheduled at {row['location']} - Bus {row['bus number']} at {row['time']}"
            if 'status' in df.columns and (df['status'] == 'sick').any():
                sick_leave = True
        else:
            print("Duty file not found.")
    except Exception as e:
        print("Duty info error:", e)
    return render_template_string(employee_html, emp_number=emp_number, duty_info=duty_info, days_worked=days_worked, sick_leave=sick_leave)

@app.route('/complaint', methods=['POST'])
def complaint():
    if 'emp_number' in session:
        emp_number = session['emp_number']
        message = request.form['message']
        db.session.add(Complaint(emp_number=emp_number, message=message))
        db.session.commit()
        flash("Complaint submitted", "success")
    return redirect(url_for('employee_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# HTML templates embedded
login_html = '''
<!doctype html>
<html>
<head>
  <title>Inshallah - Login</title>
  <style>
    body { font-family: Arial, sans-serif; background: linear-gradient(to right, #4CAF50, #2196F3, #9C27B0); color: white; text-align: center; padding: 50px; }
    form { background: white; color: black; display: inline-block; padding: 30px; border-radius: 15px; box-shadow: 0 0 15px rgba(0,0,0,0.3); }
    input { padding: 12px; margin: 10px; width: 80%; border-radius: 8px; border: 1px solid #ccc; }
    button { padding: 12px 25px; border: none; border-radius: 8px; background: linear-gradient(to right, #4CAF50, #2196F3); color: white; font-weight: bold; cursor: pointer; }
    h2 { color: #fff; }
  </style>
</head>
<body>
  <h2>Login to Inshallah</h2>
  <form method="post">
    <input name="emp_number" placeholder="Employee Number" required><br>
    <input name="password" type="password" placeholder="Password" required><br>
    <button type="submit">Login</button>
  </form>
</body>
</html>
'''

admin_html = '''
<!doctype html>
<title>Admin Dashboard - Inshallah</title>
<h2 style="color: green;">Welcome Admin</h2>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="masterlist" required>
  <button type="submit" style="background: linear-gradient(to right, #2196F3, #9C27B0); color: white; padding: 10px; border: none; border-radius: 5px;">Upload Masterlist</button>
</form>
<h3 style="color: purple;">Complaints</h3>
<ul>
  {% for c in complaints %}
    <li><b>{{ c.emp_number }}</b>: {{ c.message }} ({{ c.timestamp.strftime('%Y-%m-%d %H:%M') }})</li>
  {% endfor %}
</ul>
<a href="/logout">Logout</a>
'''

employee_html = '''
<!doctype html>
<title>Employee Dashboard - Inshallah</title>
<h2 style="color: green;">Welcome {{ emp_number }}</h2>
<p><strong>Duty Info:</strong> {{ duty_info }}</p>
<p><strong>Days Worked This Month:</strong> {{ days_worked }}</p>
<p><strong>Sick Leave Status:</strong> {% if sick_leave %}You are on sick leave.{% else %}None{% endif %}</p>
<canvas id="workChart" width="400" height="200"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const ctx = document.getElementById('workChart').getContext('2d');
  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Days Worked'],
      datasets: [{
        label: 'Work Progress',
        data: [{{ days_worked }}],
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1
      }]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
</script>
<form method="post" action="/complaint">
  <textarea name="message" placeholder="Your complaint" required></textarea><br>
  <button type="submit" style="background: linear-gradient(to right, #9C27B0, #4CAF50); color: white; padding: 10px; border: none; border-radius: 5px;">Submit Complaint</button>
</form>
<a href="/logout">Logout</a>
'''

# Initialize the database
if __name__ == '__main__':
    if not os.path.exists('database.db'):
        db.create_all()
        db.session.add(User(emp_number='1001', name='Admin User', role='admin'))
        db.session.add(User(emp_number='2001', name='John Guard', role='employee'))
        db.session.commit()
    app.run(debug=True)

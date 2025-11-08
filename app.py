from functools import wraps

# In-memory store for demo
users = {}

# Require login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


from flask import Flask, render_template, request, redirect, url_for, session, flash
import numpy as np
import joblib
from datetime import datetime
from functools import wraps  # ✅ needed for login_required decorator

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Load model and scaler
model = joblib.load("sleep_model.pkl")
scaler = joblib.load("scaler.pkl")

# ----------------------------------------------------------------
# TEMPORARY USER STORE (in-memory)
# ----------------------------------------------------------------
users = {}  # username: password


# ----------------------------------------------------------------
# HELPER: LOGIN REQUIRED DECORATOR
# ----------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ----------------------------------------------------------------
# HEALTH CALCULATION & RECOMMENDATIONS
# ----------------------------------------------------------------
def calculate_health_score(age, sleep_duration, activity_level, stress_level, heart_rate, bp_systolic, bp_diastolic):
    score = 0
    if 7 <= sleep_duration <= 9:
        score += 30
    elif 6 <= sleep_duration < 7 or 9 < sleep_duration <= 10:
        score += 20
    elif 5 <= sleep_duration < 6 or 10 < sleep_duration <= 11:
        score += 10
    else:
        score += 5

    if activity_level >= 7:
        score += 20
    elif activity_level >= 5:
        score += 15
    elif activity_level >= 3:
        score += 10
    else:
        score += 5

    if stress_level <= 3:
        score += 20
    elif stress_level <= 5:
        score += 15
    elif stress_level <= 7:
        score += 10
    else:
        score += 5

    if 40 <= heart_rate <= 60:
        score += 15
    elif 60 < heart_rate <= 80:
        score += 12
    elif 80 < heart_rate <= 100:
        score += 8
    else:
        score += 5

    if bp_systolic < 120 and bp_diastolic < 80:
        score += 15
    elif bp_systolic < 130 and bp_diastolic < 85:
        score += 12
    elif bp_systolic < 140 and bp_diastolic < 90:
        score += 8
    else:
        score += 5
    return min(score, 100)


def generate_recommendations(age, sleep_duration, workout, phone, work, caffeine, relax):
    recs = []
    if 7 <= sleep_duration <= 9:
        recs.append({"title": "Good Sleep Duration", "message": f"Your sleep duration of {sleep_duration:.1f} hours is within the optimal range."})
    elif sleep_duration < 7:
        recs.append({"title": "Insufficient Sleep", "message": "Try to increase your sleep to 7–9 hours per night for better recovery."})
    else:
        recs.append({"title": "Too Much Sleep", "message": "Sleeping too much can also reduce sleep quality. Aim for 7–9 hours."})

    if workout < 0.5:
        recs.append({"title": "Low Activity", "message": "Try at least 30 minutes of daily physical activity."})
    elif workout < 1.5:
        recs.append({"title": "Moderate Activity", "message": "Great! A little more activity can help optimize sleep."})
    else:
        recs.append({"title": "Excellent Routine", "message": "Your exercise habits support great sleep quality."})

    if phone > 4:
        recs.append({"title": "High Screen Time", "message": "Consider reducing screen time before bed to improve sleep quality."})
    elif phone > 2:
        recs.append({"title": "Moderate Screen Time", "message": "Try to reduce phone usage before bedtime for better rest."})
    else:
        recs.append({"title": "Healthy Screen Habits", "message": "Your screen time is within a good range for restful sleep."})
    return recs[:3]


# ----------------------------------------------------------------
# LOGIN SYSTEM
# ----------------------------------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            flash('Username already exists! Please log in.', 'error')
            return redirect(url_for('login'))

        users[username] = password
        session['username'] = username
        flash('Account created successfully! You are now logged in.', 'success')
        return redirect(url_for('home'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username] == password:
            session['username'] = username
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ----------------------------------------------------------------
# PREDICTION ROUTES
# ----------------------------------------------------------------
# ----------------------------------------------------------------
# ROUTES
# ----------------------------------------------------------------

# 1️⃣ Public homepage — no login needed
@app.route("/")
def index():
    return render_template("index.html")

# 2️⃣ Predictor form (login required)
@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    prediction = None
    if request.method == "POST":
        try:
            age = int(request.form["age"])
            workout = float(request.form["workout"])
            reading = float(request.form["reading"])
            phone = float(request.form["phone"])
            work = float(request.form["work"])
            caffeine = float(request.form["caffeine"])
            relax = float(request.form["relax"])

            # Predict sleep hours
            features = np.array([[workout, reading, phone, work, caffeine, relax]])
            scaled = scaler.transform(features)
            predicted_sleep = model.predict(scaled)[0]

            # Calculate health metrics (optional)
            activity_level = min(10, max(1, int((workout / 3.0) * 10)))
            stress_factor = (work / 10.0) + (phone / 5.0) - (relax / 2.0)
            stress_level = min(10, max(1, int(stress_factor * 2)))
            heart_rate = int(60 + (10 - activity_level) * 2 + stress_level * 2 - 20)
            heart_rate = min(100, max(40, heart_rate))
            bp_systolic = int(110 + (caffeine / 300 * 20) + (stress_level * 2) - (activity_level * 1.5))
            bp_diastolic = int(70 + (caffeine / 300 * 10) + (stress_level * 1) - (activity_level * 0.5))

            health_score = calculate_health_score(age, predicted_sleep, activity_level, stress_level, heart_rate, bp_systolic, bp_diastolic)
            recommendations = generate_recommendations(age, predicted_sleep, workout, phone, work, caffeine, relax)

            # Store data in session
            session['health_metrics'] = {
                'age': age,
                'sleep_duration': round(predicted_sleep, 1),
                'activity_level': activity_level,
                'stress_level': stress_level,
                'heart_rate': heart_rate,
                'blood_pressure': f"{bp_systolic}/{bp_diastolic}",
                'health_score': health_score,
                'recommendations': recommendations,
                'timestamp': datetime.now().strftime("%m/%d/%Y")
            }

            insights = (
                "Your habits suggest you might get less sleep than recommended. "
                "Consider reducing screen time or caffeine intake for better rest."
            )

            return render_template("predict.html",
                                   prediction=round(predicted_sleep, 1),
                                   insights=insights)

        except Exception as e:
            prediction = f"Invalid input: {str(e)}"

    return render_template("home.html", prediction=prediction)


# 3️⃣ Dashboard (login required)
@app.route("/dashboard")
@login_required
def dashboard():
    health_metrics = session.get('health_metrics')
    if not health_metrics:
        return render_template("dashboard.html",
                               error="No health data available. Please complete the assessment first.",
                               health_metrics=None)
    return render_template("dashboard.html", health_metrics=health_metrics)

# 4️⃣ Home redirect (optional)
@app.route("/home")
@login_required
def home():
    return redirect(url_for('predict'))


# 5️⃣ About (public)
@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)

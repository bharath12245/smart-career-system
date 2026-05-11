from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import execute_query
from recommendation_engine import get_recommendations
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.secret_key = 'smart_career_secret_key'

print("\n" + "="*40)
print("🚀 SMART CAREER SYSTEM: FINAL QUALITY PASS")
print("="*40)

# Startup AI Test
def test_gemini():
    api_key = os.getenv("SMART_CAREER_GEMINI_KEY")
    if not api_key:
        print("❌ ERROR: SMART_CAREER_GEMINI_KEY NOT FOUND")
        return
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        model.generate_content("test")
        print("✅ SUCCESS: GEMINI AI READY")
    except Exception as e:
        print(f"❌ ERROR: GEMINI AI FAILED: {e}")

test_gemini()

# Helper for AI Roadmaps
def get_ai_roadmap(career_name, user_skills, required_skills):
    api_key = os.getenv("SMART_CAREER_GEMINI_KEY")
    if not api_key: return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"Mentor student to become '{career_name}'. Skills: {user_skills}. Requirements: {required_skills}. 3-step roadmap."
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return f"Step 1: Master {career_name} basics.\nStep 2: Build projects with {required_skills}.\nStep 3: Network in the field."

# --- Middleware ---
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.utcnow()}

# --- Core Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            skills_raw = request.form.get('skills', '')
            interests = request.form.get('interests', '')
            
            # Split comma-separated skills into a list
            skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
            
            execute_query("INSERT INTO users (name, email, password, interests) VALUES (?, ?, ?, ?)", 
                          (name, email, password, interests))
            
            user_data = execute_query("SELECT user_id FROM users WHERE email = ?", (email,), fetch=True)
            if not user_data:
                flash("Could not create user. Please try a different email.")
                return redirect(url_for('register'))
            
            user = user_data[0]
            
            for skill in skills:
                execute_query("INSERT INTO user_skills (user_id, skill_name) VALUES (?, ?)", (user['user_id'], skill))
            
            session.update({
                'user_id': user['user_id'], 
                'user_name': name, 
                'user_skills': skills, 
                'user_interests': interests
            })
            return redirect(url_for('results'))
        except Exception as e:
            flash(f"Error during registration: {e}")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = execute_query("SELECT * FROM users WHERE email = ? AND password = ?", (request.form['email'], request.form['password']), fetch=True)
        if user:
            u = user[0]
            skills = execute_query("SELECT skill_name FROM user_skills WHERE user_id = ?", (u['user_id'],), fetch=True)
            session.update({'user_id': u['user_id'], 'user_name': u['name'], 'user_interests': u['interests'], 'user_skills': [s['skill_name'] for s in skills]})
            return redirect(url_for('results'))
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/recommendations')
@app.route('/results')
def results():
    if 'user_id' not in session: return redirect(url_for('login'))
    careers = execute_query("SELECT * FROM careers", fetch=True)
    recs = get_recommendations(session.get('user_skills', []), session.get('user_interests', ''), careers)
    return render_template('results.html', recommendations=recs)

@app.route('/search')
def search():
    q = request.args.get('query', '')
    careers = execute_query("SELECT * FROM careers WHERE career_name LIKE ? OR description LIKE ?", (f'%{q}%', f'%{q}%'), fetch=True)
    return render_template('results.html', recommendations=careers, is_search=True)

@app.route('/career/<int:career_id>')
def career_detail(career_id):
    career = execute_query("SELECT * FROM careers WHERE career_id = ?", (career_id,), fetch=True)
    if not career: return redirect(url_for('results'))
    return render_template('career_detail.html', career=career[0])

@app.route('/generate_roadmap/<int:career_id>')
def generate_roadmap(career_id):
    career = execute_query("SELECT * FROM careers WHERE career_id = ?", (career_id,), fetch=True)
    if not career: return jsonify({"error": "Not found"}), 404
    text = get_ai_roadmap(career[0]['career_name'], ", ".join(session.get('user_skills', [])), career[0]['required_skills'])
    return jsonify({"roadmap": text})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Admin Routes (To match layout.html) ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == 'admin@career.com' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Admin access denied")
    return render_template('admin/login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    stats = {
        'users_count': execute_query("SELECT COUNT(*) as c FROM users", fetch=True)[0]['c'],
        'careers_count': execute_query("SELECT COUNT(*) as c FROM careers", fetch=True)[0]['c'],
        'recent_users': execute_query("SELECT * FROM users ORDER BY user_id DESC LIMIT 5", fetch=True)
    }
    return render_template('admin/dashboard.html', **stats)

@app.route('/admin/users')
def manage_users():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    users = execute_query("SELECT * FROM users", fetch=True)
    return render_template('admin/users.html', users=users)

@app.route('/admin/careers')
def manage_careers():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    careers = execute_query("SELECT * FROM careers", fetch=True)
    return render_template('admin/manage_careers.html', careers=careers)

if __name__ == '__main__':
    app.run(debug=True)

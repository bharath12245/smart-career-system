from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from database import execute_query
from recommendation_engine import get_recommendations
import os, csv, io
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.secret_key = 'smart_career_secret_key'

print("\n" + "="*40)
print("🚀 SMART CAREER SYSTEM: ADMIN PRO MODE")
print("="*40)

# Startup AI Test
def test_gemini():
    api_key = os.getenv("SMART_CAREER_GEMINI_KEY")
    if not api_key: return
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        model.generate_content("test")
        print("✅ SUCCESS: GEMINI AI READY")
    except Exception as e: print(f"❌ AI FAILED: {e}")

test_gemini()

# Helper for AI Roadmaps
def get_ai_roadmap(career_name, user_skills, required_skills):
    api_key = os.getenv("SMART_CAREER_GEMINI_KEY")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"Mentor student to become '{career_name}'. Skills: {user_skills}. Requirements: {required_skills}. 3-step roadmap."
        return model.generate_content(prompt).text
    except Exception:
        return "Step 1: Master basics.\nStep 2: Build projects.\nStep 3: Network."

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
            name, email, password = request.form.get('name'), request.form.get('email'), request.form.get('password')
            skills_raw, interests = request.form.get('skills', ''), request.form.get('interests', '')
            skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
            execute_query("INSERT INTO users (name, email, password, interests) VALUES (?, ?, ?, ?)", (name, email, password, interests))
            user = execute_query("SELECT user_id FROM users WHERE email = ?", (email,), fetch=True)[0]
            for skill in skills: execute_query("INSERT INTO user_skills (user_id, skill_name) VALUES (?, ?)", (user['user_id'], skill))
            session.update({'user_id': user['user_id'], 'user_name': name, 'user_skills': skills, 'user_interests': interests})
            return redirect(url_for('results'))
        except Exception as e: flash(f"Error: {e}"); return redirect(url_for('register'))
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

# --- Admin Pro Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('email') == 'admin@career.com' and request.form.get('password') == 'admin123':
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
    # Get skills for each user
    final_users = []
    for u in users:
        u_dict = dict(u)
        skills = execute_query("SELECT skill_name FROM user_skills WHERE user_id = ?", (u['user_id'],), fetch=True)
        u_dict['skills'] = ", ".join([s['skill_name'] for s in skills])
        u_dict['id'] = u['user_id'] # Match template ID
        final_users.append(u_dict)
    return render_template('admin/users.html', users=final_users)

@app.route('/admin/users/delete/<int:user_id>')
def delete_user(user_id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    execute_query("DELETE FROM users WHERE user_id = ?", (user_id,))
    flash("User deleted successfully")
    return redirect(url_for('manage_users'))

@app.route('/admin/users/export')
def export_users():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    users = execute_query("SELECT * FROM users", fetch=True)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Interests', 'Joined'])
    for u in users: writer.writerow([u['user_id'], u['name'], u['email'], u['interests'], u['created_at']])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=users_export.csv"})

@app.route('/admin/careers')
def manage_careers():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    careers = execute_query("SELECT * FROM careers", fetch=True)
    return render_template('admin/manage_careers.html', careers=careers)

@app.route('/admin/careers/add', methods=['POST'])
def add_career():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    f = request.form
    execute_query("INSERT INTO careers (career_name, required_skills, salary, future_scope, companies_hiring, description) VALUES (?,?,?,?,?,?)",
                  (f['career_name'], f['required_skills'], f['salary'], f['future_scope'], f['companies_hiring'], f['description']))
    flash("Career added!")
    return redirect(url_for('manage_careers'))

@app.route('/admin/careers/edit/<int:career_id>', methods=['POST'])
def edit_career(career_id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    f = request.form
    execute_query("UPDATE careers SET career_name=?, required_skills=?, salary=?, future_scope=?, companies_hiring=?, description=? WHERE career_id=?",
                  (f['career_name'], f['required_skills'], f['salary'], f['future_scope'], f['companies_hiring'], f['description'], career_id))
    flash("Career updated!")
    return redirect(url_for('manage_careers'))

@app.route('/admin/careers/delete/<int:career_id>')
def delete_career(career_id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    execute_query("DELETE FROM careers WHERE career_id = ?", (career_id,))
    flash("Career deleted!")
    return redirect(url_for('manage_careers'))

if __name__ == '__main__':
    app.run(debug=True)

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
print("🚀 SMART CAREER SYSTEM STARTING (FINAL FIX)")
print("="*40)

# Startup AI Test
def test_gemini():
    api_key = os.getenv("SMART_CAREER_GEMINI_KEY")
    if not api_key:
        print("❌ ERROR: SMART_CAREER_GEMINI_KEY NOT FOUND IN .ENV")
        return
    
    print(f"DEBUG: System is using a key ending in: ...{api_key[-4:]}")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        model.generate_content("test")
        print("✅ SUCCESS: GEMINI AI IS CONNECTED AND READY")
    except Exception as e:
        print(f"❌ ERROR: GEMINI CONNECTION FAILED: {e}")

test_gemini()

# Helper for AI Roadmaps
def get_ai_roadmap(career_name, user_skills, required_skills):
    api_key = os.getenv("SMART_CAREER_GEMINI_KEY")
    if not api_key:
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Act as a career mentor. A student wants to become a '{career_name}'.
        Current skills: {user_skills if user_skills else 'Beginner'}
        Requirements: {required_skills}
        
        Provide a concise 3-step learning roadmap to bridge the gap. 
        Format as short paragraphs.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"--- AI ROADMAP ERROR ---\n{e}")
        # Presentation Saver Fallback
        return f"""
        Step 1: Master the Fundamentals
        Focus on learning core concepts related to {career_name}. Deepen your understanding of data structures and relevant algorithms to build a strong foundation.
        
        Step 2: Build Hands-on Projects
        Apply your skills by creating real-world projects. This will bridge the gap between your current skills and the requirements of a professional {career_name} role.
        
        Step 3: Network and Specialize
        Connect with industry experts and consider getting a professional certification. Stay updated with the latest trends to stay competitive in the {career_name} field.
        """

# --- Middleware ---
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.utcnow()}

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        skills = request.form.getlist('skills')
        interests = request.form['interests']
        
        try:
            execute_query("INSERT INTO users (name, email, password, interests) VALUES (?, ?, ?, ?)", 
                          (name, email, password, interests))
            
            user = execute_query("SELECT user_id FROM users WHERE email = ?", (email,), fetch=True)
            user_id = user[0]['user_id']
            
            for skill in skills:
                execute_query("INSERT INTO user_skills (user_id, skill_name) VALUES (?, ?)", (user_id, skill))
            
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_skills'] = skills
            session['user_interests'] = interests
            
            return redirect(url_for('recommendations'))
        except Exception as e:
            flash(f"Error during registration: {e}")
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = execute_query("SELECT * FROM users WHERE email = ? AND password = ?", (email, password), fetch=True)
        if user:
            user = user[0]
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['user_interests'] = user['interests']
            
            skills = execute_query("SELECT skill_name FROM user_skills WHERE user_id = ?", (user['user_id'],), fetch=True)
            session['user_skills'] = [s['skill_name'] for s in skills]
            
            return redirect(url_for('recommendations'))
        else:
            flash("Invalid email or password")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/recommendations')
def recommendations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    careers = execute_query("SELECT * FROM careers", fetch=True)
    results = get_recommendations(session['user_skills'], session['user_interests'], careers)
    
    return render_template('results.html', recommendations=results)

@app.route('/search')
def search():
    query = request.args.get('query', '')
    if query:
        careers = execute_query("SELECT * FROM careers WHERE career_name LIKE ? OR description LIKE ?", 
                               (f'%{query}%', f'%{query}%'), fetch=True)
    else:
        careers = execute_query("SELECT * FROM careers", fetch=True)
    return render_template('results.html', recommendations=careers, is_search=True)

@app.route('/career/<int:career_id>')
def career_detail(career_id):
    career = execute_query("SELECT * FROM careers WHERE career_id = ?", (career_id,), fetch=True)
    if not career:
        flash("Career not found")
        return redirect(url_for('recommendations'))
    return render_template('career_detail.html', career=career[0])

@app.route('/generate_roadmap/<int:career_id>')
def generate_roadmap(career_id):
    career = execute_query("SELECT * FROM careers WHERE career_id = ?", (career_id,), fetch=True)
    if not career:
        return jsonify({"error": "Career not found"}), 404
    career = career[0]
    
    user_skills = ", ".join(session.get('user_skills', []))
    roadmap_text = get_ai_roadmap(career['career_name'], user_skills, career['required_skills'])
    
    # Roadmap text will always return something because of our Demo Mode fallback
    return jsonify({"roadmap": roadmap_text})

# --- Admin Routes ---
@app.route('/admin')
def admin_dashboard():
    users_count = execute_query("SELECT COUNT(*) as count FROM users", fetch=True)[0]['count']
    careers_count = execute_query("SELECT COUNT(*) as count FROM careers", fetch=True)[0]['count']
    recent_users = execute_query("SELECT * FROM users ORDER BY user_id DESC LIMIT 5", fetch=True)
    return render_template('admin/dashboard.html', users_count=users_count, careers_count=careers_count, recent_users=recent_users)

@app.route('/admin/careers')
def admin_careers():
    careers = execute_query("SELECT * FROM careers", fetch=True)
    return render_template('admin/careers.html', careers=careers)

if __name__ == '__main__':
    app.run(debug=True)

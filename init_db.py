import sqlite3
import os

DB_PATH = 'career_system.db'

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Careers Table
    cursor.execute('''
    CREATE TABLE careers (
        career_id INTEGER PRIMARY KEY AUTOINCREMENT,
        career_name TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        salary TEXT,
        future_scope TEXT,
        companies_hiring TEXT,
        description TEXT
    )
    ''')
    
    # Create Users Table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        skills TEXT,
        interests TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Recommendations Table
    cursor.execute('''
    CREATE TABLE recommendations (
        rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        career_id INTEGER,
        match_percentage REAL,
        missing_skills TEXT,
        search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (career_id) REFERENCES careers(career_id) ON DELETE CASCADE
    )
    ''')
    
    # Seed Data for Careers
    careers = [
        ('AI Engineer', 'Python, Machine Learning, Deep Learning, SQL, Statistics, PyTorch', '$100k - $180k', 'Huge growth with the rise of LLMs and automation.', 'Google, Meta, OpenAI, Microsoft, NVIDIA', 'Build and deploy intelligent models to solve complex problems.'),
        ('Web Developer', 'HTML, CSS, JavaScript, React, Node.js, SQL, Git', '$70k - $130k', 'Steady demand for digital transformation and SaaS.', 'Amazon, Netflix, Adobe, Shopify, Vercel', 'Create responsive and dynamic websites and web applications.'),
        ('UI/UX Designer', 'Figma, Adobe XD, Design Principles, User Research, HTML, CSS', '$65k - $120k', 'Critical for product success in a user-centric world.', 'Apple, Airbnb, Uber, Spotify, Canva', 'Design intuitive and beautiful user interfaces and experiences.'),
        ('Data Scientist', 'Python, R, SQL, Data Visualization, Statistics, Machine Learning, Tableau', '$90k - $150k', 'Essential for data-driven decision making.', 'IBM, Oracle, Walmart, Mastercard', 'Extract insights from large datasets to guide business strategy.'),
        ('Backend Developer', 'Java, Spring Boot, SQL, Docker, Microservices, Kubernetes', '$80k - $140k', 'Core infrastructure needs for cloud services.', 'JPMorgan, Goldman Sachs, AWS, PayPal', 'Develop and maintain server-side logic and database integration.'),
        ('Cloud Architect', 'AWS, Azure, Docker, Kubernetes, Networking, Security, Terraform', '$110k - $190k', 'Dominant as businesses move entirely to the cloud.', 'Microsoft, AWS, Google Cloud, IBM', 'Design and manage scalable cloud infrastructure and services.'),
        ('Cybersecurity Analyst', 'Networking, Linux, Security Tools, Ethical Hacking, SQL, Python', '$85k - $150k', 'Increasing importance due to rising cyber threats.', 'CrowdStrike, Cisco, Palo Alto Networks, FBI', 'Protect systems and data from unauthorized access and attacks.'),
        ('Mobile App Developer', 'Swift, Kotlin, Flutter, React Native, Mobile Design, API Integration', '$75k - $135k', 'Growing demand for personalized mobile experiences.', 'Uber, DoorDash, Instagram, WhatsApp', 'Build high-performance apps for iOS and Android platforms.'),
        ('DevOps Engineer', 'Linux, CI/CD, Docker, Jenkins, Python, Shell Scripting, Monitoring', '$95k - $160k', 'Bridge between development and operations is vital.', 'GitLab, HashiCorp, Red Hat, Datadog', 'Automate and streamline the software delivery process.'),
        ('Blockchain Developer', 'Solidity, Ethereum, Cryptography, Node.js, Smart Contracts, Rust', '$100k - $200k', 'High potential in finance and decentralized apps.', 'Coinbase, Binance, Polygon, ConsenSys', 'Develop decentralized applications and secure blockchain networks.')
    ]
    
    cursor.executemany('''
    INSERT INTO careers (career_name, required_skills, salary, future_scope, companies_hiring, description) 
    VALUES (?, ?, ?, ?, ?, ?)
    ''', careers)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully with seed data.")

if __name__ == "__main__":
    init_db()

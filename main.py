from flask import Flask, render_template_string, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timezone, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = 'hhs-tutoring-secret-key-2024'

DB_NAME = 'tutoring_kiosk.db'

ATHLETES = [
    "Marcus Allen", "DeShawn Brooks", "Tyrone Carter", "Isaiah Davis",
    "Jalen Edwards", "Khalil Foster", "Darius Green", "Malik Harris",
    "D'Andre Jackson", "Tavon Johnson", "DeMarcus King", "Jordan Lee",
    "Brandon Mitchell", "Aiden Nelson", "Omari Parker", "Christian Reed",
    "Rashawn Simmons", "Terrence Thompson", "Keon Williams", "Xavier Young"
]

GRADES = ["9th", "10th", "11th", "12th"]
FOCUS_AREAS = ["Math", "English/Language Arts", "Science", "Social Studies", "Spanish/World Language", "Study Hall/Makeup Work"]

RULES_LIST = [
    ("📵 No Phones", "All phones go in numbered pouch at check-in. No exceptions."),
    ("📝 Evidence of Work", "Must show what you accomplished to check out."),
    ("🎯 Stay on Task", "No games, social media, or non-academic browsing."),
    ("😴 No Sleeping", "If you can't stay awake, stand at side table."),
    ("👂 One Earbud Rule", "Keep one earbud out so you can hear the tutor.")
]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_name TEXT,
            grade TEXT,
            focus_area TEXT,
            assignment TEXT,
            focus_rating INTEGER,
            phone_pouch_number TEXT,
            check_in_time TEXT,
            check_out_time TEXT,
            evidence_of_work TEXT,
            status TEXT DEFAULT 'checked_in',
            was_on_time INTEGER DEFAULT 0,
            session_date TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS athlete_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_name TEXT UNIQUE,
            tardy_count INTEGER DEFAULT 0,
            noshow_count INTEGER DEFAULT 0,
            consecutive_ontime INTEGER DEFAULT 0,
            prize_tickets INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_name TEXT,
            rule_name TEXT,
            violation_time TEXT
        )
    ''')
    
    for athlete in ATHLETES:
        c.execute('''
            INSERT OR IGNORE INTO athlete_stats (athlete_name, tardy_count, noshow_count, consecutive_ontime, prize_tickets)
            VALUES (?, 0, 0, 0, 0)
        ''', (athlete,))
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_est_time():
    utc_dt = datetime.now(timezone.utc)
    year = utc_dt.year
    dst_start = datetime(year, 3, 14, 7, 0, 0)
    dst_end = datetime(year, 11, 7, 6, 0, 0)
    
    if dst_start <= utc_dt.replace(tzinfo=None) <= dst_end:
        est_dt = utc_dt - timedelta(hours=4)
    else:
        est_dt = utc_dt - timedelta(hours=5)
    
    return est_dt

def is_ontime(check_in_time_str):
    try:
        check_in = datetime.strptime(check_in_time_str, '%Y-%m-%d %I:%M:%S %p')
        cutoff = check_in.replace(hour=14, minute=50, second=0)
        return check_in <= cutoff
    except:
        return False

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HHS Football Tutoring Kiosk</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
            color: #333;
            min-height: 100vh;
        }
        
        .container {
            max-width: 650px;
            margin: 0 auto;
            padding: 15px;
        }
        
        .header {
            text-align: center;
            padding: 30px 15px 20px;
        }
        
        .header h1 {
            font-size: 28px;
            color: #1a1a2e;
            margin-bottom: 5px;
        }
        
        .header p {
            color: #666;
            font-size: 14px;
        }
        
        .menu-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        
        .menu-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 25px 15px;
            border-radius: 15px;
            font-size: 17px;
            font-weight: bold;
            color: white;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: transform 0.1s;
            min-height: 110px;
        }
        
        .menu-btn:active { transform: scale(0.95); }
        
        .menu-btn .emoji { font-size: 32px; margin-bottom: 8px; }
        
        .btn-crimson { background: #DC143C; }
        .btn-gray { background: #808080; }
        .btn-green { background: #2e7d32; }
        .btn-orange { background: #e65100; }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }
        
        .card h2 {
            color: #DC143C;
            margin-bottom: 15px;
            font-size: 20px;
        }
        
        .form-group { margin-bottom: 15px; }
        
        .form-group label {
            display: block;
            font-weight: bold;
            font-size: 14px;
            color: #444;
            margin-bottom: 5px;
        }
        
        .form-group select, .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            background: #f9f9f9;
        }
        
        .form-group select:focus, .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #DC143C;
            background: white;
        }
        
        .form-group textarea { min-height: 80px; resize: vertical; }
        
        .submit-btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: bold;
            color: white;
            cursor: pointer;
        }
        
        .submit-btn:hover { opacity: 0.9; }
        
        .back-btn {
            display: inline-block;
            padding: 8px 12px;
            margin-bottom: 15px;
            color: #DC143C;
            text-decoration: none;
            font-weight: bold;
            font-size: 15px;
        }
        
        .alert {
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 15px;
            font-weight: bold;
            text-align: center;
            font-size: 14px;
        }
        
        .alert-success { background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
        .alert-error { background: #ffebee; color: #c62828; border: 1px solid #f44336; }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 12px;
        }
        
        .admin-btn-row {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .admin-action-btn {
            flex: 1;
            min-width: 120px;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            text-align: center;
        }
        
        .admin-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 10px;
        }
        
        .admin-table th {
            background: #DC143C;
            color: white;
            padding: 8px 4px;
            text-align: center;
            font-size: 11px;
        }
        
        .admin-table td {
            padding: 6px 4px;
            text-align: center;
            border-bottom: 1px solid #eee;
            font-size: 11px;
        }
        
        .admin-table tr:nth-child(even) td { background: #f9f9f9; }
        
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: bold;
        }
        
        .badge-in { background: #e8f5e9; color: #2e7d32; }
        .badge-out { background: #eee; color: #666; }
        .badge-ontime { background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
        .badge-late { background: #ffebee; color: #c62828; border: 1px solid #f44336; }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 16px;
        }
        
        .stats-summary {
            display: flex;
            justify-content: space-around;
            padding: 12px;
            background: #f9f9f9;
            border-radius: 10px;
            margin-bottom: 15px;
            font-size: 13px;
        }
        
        .stats-summary span { font-weight: bold; }
        .stats-ontime { color: #2e7d32; }
        .stats-late { color: #c62828; }
        
        .rule-card {
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 10px;
            border: 2px solid #4caf50;
            background: #e8f5e9;
        }
        
        .rule-card strong { font-size: 15px; }
        .rule-card p { font-size: 13px; color: #555; margin-top: 3px; }
        
        .violate-btn {
            margin-top: 8px;
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            background: #DC143C;
            color: white;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
        }
        
        .violate-btn:hover { opacity: 0.9; }
        
        .athlete-stat-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }
        
        .athlete-stat-row .name { font-weight: bold; flex: 1; }
        .athlete-stat-row .stat { margin: 0 8px; text-align: center; min-width: 30px; }
        .athlete-stat-row .stars { color: #f9a825; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

INDEX_TEMPLATE = '''
{% extends "base" %}
{% block content %}
    <div class="header">
        <h1>🏈 HHS Football Tutoring</h1>
        <p>Student-Athlete Check-In Kiosk</p>
    </div>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <div class="menu-grid">
        <a href="{{ url_for('check_in') }}" class="menu-btn btn-crimson">
            <span class="emoji">📝</span>
            Check In
        </a>
        <a href="{{ url_for('check_out') }}" class="menu-btn btn-gray">
            <span class="emoji">🚪</span>
            Check Out
        </a>
        <a href="{{ url_for('rules') }}" class="menu-btn btn-crimson">
            <span class="emoji">📋</span>
            Rules
        </a>
        <a href="{{ url_for('admin') }}" class="menu-btn btn-gray">
            <span class="emoji">📊</span>
            Admin
        </a>
        <a href="{{ url_for('rewards') }}" class="menu-btn btn-green" style="grid-column: 1/-1;">
            <span class="emoji">⭐</span>
            Rewards & Streaks
        </a>
    </div>
    
    <div class="footer">Howard High School - Athletic Tutoring Program</div>
{% endblock %}
'''

CHECKIN_TEMPLATE = '''
{% extends "base" %}
{% block content %}
    <a href="{{ url_for('index') }}" class="back-btn">← Back to Menu</a>
    
    <div class="card">
        <h2>📝 Check In</h2>
        <p style="color:#666; margin-bottom:12px; font-size:13px;">⏰ On time = check-in by <strong>2:50 PM EST</strong></p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label>Athlete Name</label>
                <select name="name" required>
                    <option value="">— Select Name —</option>
                    {% for a in athletes %}
                    <option value="{{ a }}">{{ a }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-group">
                <label>Grade</label>
                <select name="grade" required>
                    <option value="">— Select Grade —</option>
                    {% for g in grades %}
                    <option value="{{ g }}">{{ g }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-group">
                <label>Focus Area</label>
                <select name="focus" required>
                    <option value="">— Select Subject —</option>
                    {% for f in focus_areas %}
                    <option value="{{ f }}">{{ f }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-group">
                <label>Assignment / Task</label>
                <input type="text" name="assignment" placeholder="e.g. Algebra Ch.5 worksheet" required>
            </div>
            
            <div class="form-group">
                <label>Focus Rating</label>
                <select name="rating" required>
                    <option value="">— Rate Yourself —</option>
                    <option value="5">5 - Locked In</option>
                    <option value="4">4 - Focused</option>
                    <option value="3">3 - Okay</option>
                    <option value="2">2 - Struggling</option>
                    <option value="1">1 - Distracted</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Phone Pouch Number</label>
                <select name="pouch" required>
                    <option value="">— Select Pouch # —</option>
                    {% for p in pouches %}
                    <option value="{{ p }}">{{ p }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <button type="submit" class="submit-btn" style="background:#DC143C;">✅ Check In</button>
        </form>
    </div>
{% endblock %}
'''

CHECKOUT_TEMPLATE = '''
{% extends "base" %}
{% block content %}
    <a href="{{ url_for('index') }}" class="back-btn">← Back to Menu</a>
    
    <div class="card">
        <h2>🚪 Check Out</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% if checked_in %}
        <form method="POST">
            <div class="form-group">
                <label>Select Athlete</label>
                <select name="name" required>
                    <option value="">— Select Name —</option>
                    {% for n in checked_in %}
                    <option value="{{ n }}">{{ n }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-group">
                <label>Evidence of Work Completed</label>
                <textarea name="evidence" placeholder="Describe what you accomplished today..." required></textarea>
            </div>
            
            <button type="submit" class="submit-btn" style="background:#808080;">🚪 Check Out</button>
        </form>
        {% else %}
            <div class="no-data">😴 No athletes currently checked in.</div>
        {% endif %}
    </div>
{% endblock %}
'''

RULES_TEMPLATE = '''
{% extends "base" %}
{% block content %}
    <a href="{{ url_for('index') }}" class="back-btn">← Back to Menu</a>
    
    <div class="card">
        <h2>📋 Rules & Violation Reporting</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <h3 style="color:#DC143C; margin-bottom:10px;">1️⃣ Non-Negotiable Rules</h3>
        
        {% for rule_name, rule_desc in rules %}
        <div class="rule-card">
            <strong>{{ rule_name }}</strong>
            <p>{{ rule_desc }}</p>
            
            <form method="POST" action="{{ url_for('report_violation') }}" style="margin-top:8px;">
                <input type="hidden" name="rule_name" value="{{ rule_name }}">
                <select name="athlete_name" required style="padding:8px; border-radius:8px; border:1px solid #ccc; font-size:13px;">
                    <option value="">— Select Athlete —</option>
                    {% for a in athletes %}
                    <option value="{{ a }}">{{ a }}</option>
                    {% endfor %}
                </select>
                <button type="submit" class="violate-btn">🚨 Report Violation</button>
            </form>
        </div>
        {% endfor %}
        
        <h3 style="color:#DC143C; margin:20px 0 10px;">2️⃣ Tardiness Policy</h3>
        
        <div style="background:#e8f5e9; border:2px solid #2e7d32; border-radius:10px; padding:10px; margin-bottom:6px;">
            <strong>🟢 1st Tardy (≤10 min)</strong> — Verbal warning. Must stay full session.
        </div>
        <div style="background:#fff8e1; border:2px solid #f57f17; border-radius:10px; padding:10px; margin-bottom:6px;">
            <strong>🟡 2nd Tardy</strong> — Coach notified. Athlete stays 15 min extra.
        </div>
        <div style="background:#ffe0b2; border:2px solid #e65100; border-radius:10px; padding:10px; margin-bottom:6px;">
            <strong>🟠 3rd Tardy</strong> — Loss of playing time in next game.
        </div>
        <div style="background:#ffebee; border:2px solid #c62828; border-radius:10px; padding:10px; margin-bottom:20px;">
            <strong>🔴 4+ Tardies</strong> — Referral to athletic director. Eligibility review.
        </div>
        
        <h3 style="color:#DC143C; margin-bottom:10px;">3️⃣ No-Show Policy</h3>
        
        <div style="background:#fff8e1; border:2px solid #f57f17; border-radius:10px; padding:10px; margin-bottom:6px;">
            <strong>🟡 1st No-Show</strong> — Coach notified. Must make up session next day.
        </div>
        <div style="background:#ffe0b2; border:2px solid #e65100; border-radius:10px; padding:10px; margin-bottom:6px;">
            <strong>🟠 2nd No-Show</strong> — Athlete sits first half of next game.
        </div>
        <div style="background:#ffebee; border:2px solid #c62828; border-radius:10px; padding:10px;">
            <strong>🔴 3rd No-Show</strong> — Ineligible until 2 consecutive sessions completed.
        </div>
    </div>
{% endblock %}
'''

ADMIN_TEMPLATE = '''
{% extends "base" %}
{% block content %}
    <a href="{{ url_for('index') }}" class="back-btn">← Back to Menu</a>
    
    <div class="card">
        <h2>📊 Admin Panel</h2>
        
        <div class="stats-summary">
            <div>✅ On Time: <span class="stats-ontime">{{ stats.on_time }}</span></div>
            <div>⏰ Late: <span class="stats-late">{{ stats.late }}</span></div>
            <div>📊 Total: <span>{{ stats.total }}</span></div>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="admin-btn-row">
            <a href="{{ url_for('export_csv') }}" class="admin-action-btn" style="background:#DC143C;">📥 Export CSV</a>
            <a href="{{ url_for('clear_all') }}" class="admin-action-btn" style="background:#666;" onclick="return confirm('Delete ALL records? This cannot be undone.')">🗑️ Clear All</a>
        </div>
        
        <div style="background:#fff8e1; border:2px solid #f57f17; border-radius:10px; padding:12px; margin-bottom:10px;">
            <form method="POST" action="{{ url_for('mark_tardy') }}" style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <strong>🟡 Mark Tardy:</strong>
                <select name="athlete_name" required style="flex:1; min-width:150px; padding:8px; border-radius:8px; border:1px solid #ccc; font-size:13px;">
                    <option value="">— Select —</option>
                    {% for a in athletes %}
                    <option value="{{ a }}">{{ a }}</option>
                    {% endfor %}
                </select>
                <button type="submit" class="admin-action-btn" style="background:#f57f17; flex:0; padding:8px 20px;">Mark Tardy</button>
            </form>
        </div>
        
        <div style="background:#ffebee; border:2px solid #c62828; border-radius:10px; padding:12px; margin-bottom:15px;">
            <form method="POST" action="{{ url_for('mark_noshow') }}" style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <strong>🔴 Mark No-Show:</strong>
                <select name="athlete_name" required style="flex:1; min-width:150px; padding:8px; border-radius:8px; border:1px solid #ccc; font-size:13px;">
                    <option value="">— Select —</option>
                    {% for a in athletes %}
                    <option value="{{ a }}">{{ a }}</option>
                    {% endfor %}
                </select>
                <button type="submit" class="admin-action-btn" style="background:#c62828; flex:0; padding:8px 20px;">Mark No-Show</button>
            </form>
        </div>
        
        <h3 style="color:#333; margin:15px 0 8px; font-size:16px;">📈 Athlete Statistics</h3>
        <div style="overflow-x:auto;">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Athlete</th>
                        <th>Tardies</th>
                        <th>No-Shows</th>
                        <th>Streak</th>
                        <th>🎟️ Tickets</th>
                    </tr>
                </thead>
                <tbody>
                    {% for stat in athlete_stats %}
                    <tr>
                        <td style="text-align:left; font-weight:bold;">{{ stat.athlete_name[:18] }}</td>
                        <td>{{ stat.tardy_count }}</td>
                        <td>{{ stat.noshow_count }}</td>
                        <td>
                            {% if stat.consecutive_ontime > 0 %}
                                {% for i in range(stat.consecutive_ontime) %}
                                    {% if i < 5 %}
                                        ⭐
                                    {% endif %}
                                {% endfor %}
                                ({{ stat.consecutive_ontime }})
                            {% else %}
                                —
                            {% endif %}
                        </td>
                        <td><strong style="color:#f9a825;">{{ stat.prize_tickets }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <h3 style="color:#333; margin:20px 0 8px; font-size:16px;">📋 Session Records</h3>
        
        {% if records %}
        <div style="overflow-x:auto;">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Subject</th>
                        <th>In</th>
                        <th>Out</th>
                        <th>Pouch</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in records %}
                    <tr>
                        <td>{{ r.athlete_name[:15] }}</td>
                        <td>{{ r.focus_area[:12] }}</td>
                        <td>{{ r.check_in_time[10:16] if r.check_in_time else '-' }}
                            {% if r.was_on_time == 1 %}
                                <span class="badge badge-ontime">✓</span>
                            {% elif r.was_on_time == 0 and r.check_in_time %}
                                <span class="badge badge-late">✗</span>
                            {% endif %}
                        </td>
                        <td>{{ r.check_out_time[10:16] if r.check_out_time else '—' }}</td>
                        <td>#{{ r.phone_pouch_number }}</td>
                        <td>
                            {% if r.status == 'checked_in' %}
                                <span class="badge badge-in">✅ In</span>
                            {% else %}
                                <span class="badge badge-out">⬜ Out</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
            <div class="no-data">📭 No tutoring sessions recorded yet.</div>
        {% endif %}
    </div>
{% endblock %}
'''

REWARDS_TEMPLATE = '''
{% extends "base" %}
{% block content %}
    <a href="{{ url_for('index') }}" class="back-btn">← Back to Menu</a>
    
    <div class="card">
        <h2>⭐ Rewards & Streaks</h2>
        <p style="color:#666; margin-bottom:15px; font-size:13px;">
            🎯 <strong>5 consecutive on-time days</strong> = 1 Prize Ticket<br>
            📅 Streak resets if tardy or no-show
        </p>
        
        {% if athlete_stats %}
        <div style="overflow-x:auto;">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Athlete</th>
                        <th>Streak</th>
                        <th>Progress to Next Ticket</th>
                        <th>🎟️ Tickets</th>
                    </tr>
                </thead>
                <tbody>
                    {% for stat in athlete_stats %}
                    <tr>
                        <td style="text-align:left; font-weight:bold;">{{ stat.athlete_name[:18] }}</td>
                        <td>
                            {% if stat.consecutive_ontime > 0 %}
                                <span style="font-size:18px;">
                                {% for i in range(stat.consecutive_ontime) %}
                                    {% if i < 5 %}
                                        ⭐
                                    {% endif %}
                                {% endfor %}
                                </span>
                                <span style="font-size:13px; color:#666;">({{ stat.consecutive_ontime }})</span>
                            {% else %}
                                <span style="color:#999;">No streak</span>
                            {% endif %}
                        </td>
                        <td>
                            {% set progress = stat.consecutive_ontime|default(0) %}
                            {% if progress >= 5 %}
                                {% set remaining = progress % 5 %}
                                <div style="background:#e8f5e9; border-radius:20px; padding:3px; width:100px; margin:0 auto;">
                                    <div style="background:#4caf50; height:8px; border-radius:20px; width:{{ (progress % 5) * 20 }}%;"></div>
                                </div>
                                <span style="font-size:11px; color:#666;">{{ remaining }}/5</span>
                            {% else %}
                                <div style="background:#eee; border-radius:20px; padding:3px; width:100px; margin:0 auto;">
                                    <div style="background:#4caf50; height:8px; border-radius:20px; width:{{ progress * 20 }}%;"></div>
                                </div>
                                <span style="font-size:11px; color:#666;">{{ progress }}/5</span>
                            {% endif %}
                        </td>
                        <td><strong style="color:#f9a825; font-size:20px;">🎟️ {{ stat.prize_tickets }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
            <div class="no-data">No athlete data yet.</div>
        {% endif %}
    </div>
{% endblock %}
'''

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE + INDEX_TEMPLATE)

@app.route('/check-in', methods=['GET', 'POST'])
def check_in():
    if request.method == 'POST':
        name = request.form.get('name')
        grade = request.form.get('grade')
        focus = request.form.get('focus')
        assignment = request.form.get('assignment')
        rating = request.form.get('rating')
        pouch = request.form.get('pouch')
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT id FROM sessions WHERE athlete_name = ? AND status = ?', (name, 'checked_in'))
        if c.fetchone():
            flash(f'{name} is already checked in!', 'error')
            conn.close()
            return redirect(url_for('check_in'))
        
        now_est = get_est_time()
        check_in_time = now_est.strftime('%Y-%m-%d %I:%M:%S %p')
        session_date = now_est.strftime('%Y-%m-%d')
        
        on_time = is_ontime(check_in_time)
        
        c.execute('''
            INSERT INTO sessions (athlete_name, grade, focus_area, assignment, focus_rating, phone_pouch_number, check_in_time, status, was_on_time, session_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, grade, focus, assignment, int(rating), pouch, check_in_time, 'checked_in', 1 if on_time else 0, session_date))
        
        if on_time:
            c.execute('''
                UPDATE athlete_stats 
                SET consecutive_ontime = consecutive_ontime + 1,
                    prize_tickets = prize_tickets + CASE WHEN (consecutive_ontime + 1) % 5 = 0 THEN 1 ELSE 0 END
                WHERE athlete_name = ?
            ''', (name,))
        
        conn.commit()
        conn.close()
        
        if on_time:
            flash(f'✅ {name} checked in ON TIME! Phone: Pouch #{pouch}', 'success')
        else:
            flash(f'⏰ {name} checked in LATE ({check_in_time[10:16]}). Phone: Pouch #{pouch}', 'error')
        
        return redirect(url_for('index'))
    
    pouches = list(range(1, 31))
    return render_template_string(BASE_TEMPLATE + CHECKIN_TEMPLATE, athletes=ATHLETES, grades=GRADES, focus_areas=FOCUS_AREAS, pouches=pouches)

@app.route('/check-out', methods=['GET', 'POST'])
def check_out():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        evidence = request.form.get('evidence')
        
        c.execute('SELECT id FROM sessions WHERE athlete_name = ? AND status = ?', (name, 'checked_in'))
        session = c.fetchone()
        
        if not session:
            flash(f'{name} is not checked in!', 'error')
            conn.close()
            return redirect(url_for('check_out'))
        
        now_est = get_est_time()
        check_out_time = now_est.strftime('%Y-%m-%d %I:%M:%S %p')
        
        c.execute('UPDATE sessions SET check_out_time = ?, evidence_of_work = ?, status = ? WHERE id = ?',
                  (check_out_time, evidence, 'checked_out', session['id']))
        conn.commit()
        conn.close()
        
        flash(f'✅ {name} checked out!', 'success')
        return redirect(url_for('index'))
    
    c.execute('SELECT athlete_name FROM sessions WHERE status = ?', ('checked_in',))
    checked_in = [row['athlete_name'] for row in c.fetchall()]
    conn.close()
    
    return render_template_string(BASE_TEMPLATE + CHECKOUT_TEMPLATE, checked_in=checked_in)

@app.route('/rules')
def rules():
    return render_template_string(BASE_TEMPLATE + RULES_TEMPLATE, rules=RULES_LIST, athletes=ATHLETES)

@app.route('/report-violation', methods=['POST'])
def report_violation():
    athlete_name = request.form.get('athlete_name')
    rule_name = request.form.get('rule_name')
    
    if not athlete_name or not rule_name:
        flash('Please select an athlete and a rule.', 'error')
        return redirect(url_for('rules'))
    
    now_est = get_est_time()
    violation_time = now_est.strftime('%Y-%m-%d %I:%M:%S %p')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO violations (athlete_name, rule_name, violation_time) VALUES (?, ?, ?)',
              (athlete_name, rule_name, violation_time))
    conn.commit()
    conn.close()
    
    flash(f'🚨 Violation reported: {athlete_name} - {rule_name}', 'success')
    return redirect(url_for('rules'))

@app.route('/admin')
def admin():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT athlete_name, grade, focus_area, assignment, focus_rating,
               phone_pouch_number, check_in_time, check_out_time, evidence_of_work, status, was_on_time
        FROM sessions ORDER BY id DESC
    ''')
    records = c.fetchall()
    
    c.execute('''
        SELECT athlete_name, tardy_count, noshow_count, consecutive_ontime, prize_tickets
        FROM athlete_stats ORDER BY athlete_name
    ''')
    athlete_stats = c.fetchall()
    
    on_time = 0
    late = 0
    
    for r in records:
        if r['check_in_time']:
            if r['was_on_time'] == 1:
                on_time += 1
            else:
                late += 1
    
    stats = {'on_time': on_time, 'late': late, 'total': len(records)}
    
    conn.close()
    
    return render_template_string(BASE_TEMPLATE + ADMIN_TEMPLATE, records=records, stats=stats, athletes=ATHLETES, athlete_stats=athlete_stats)

@app.route('/mark-tardy', methods=['POST'])
def mark_tardy():
    athlete_name = request.form.get('athlete_name')
    
    if not athlete_name:
        flash('Please select an athlete.', 'error')
        return redirect(url_for('admin'))
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('UPDATE athlete_stats SET tardy_count = tardy_count + 1 WHERE athlete_name = ?', (athlete_name,))
    c.execute('UPDATE athlete_stats SET consecutive_ontime = 0 WHERE athlete_name = ?', (athlete_name,))
    
    conn.commit()
    conn.close()
    
    flash(f'🟡 {athlete_name} marked as TARDY. Streak reset.', 'error')
    return redirect(url_for('admin'))

@app.route('/mark-noshow', methods=['POST'])
def mark_noshow():
    athlete_name = request.form.get('athlete_name')
    
    if not athlete_name:
        flash('Please select an athlete.', 'error')
        return redirect(url_for('admin'))
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('UPDATE athlete_stats SET noshow_count = noshow_count + 1 WHERE athlete_name = ?', (athlete_name,))
    c.execute('UPDATE athlete_stats SET consecutive_ontime = 0 WHERE athlete_name = ?', (athlete_name,))
    
    conn.commit()
    conn.close()
    
    flash(f'🔴 {athlete_name} marked as NO-SHOW. Streak reset.', 'error')
    return redirect(url_for('admin'))

@app.route('/rewards')
def rewards():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT athlete_name, tardy_count, noshow_count, consecutive_ontime, prize_tickets
        FROM athlete_stats ORDER BY consecutive_ontime DESC, prize_tickets DESC
    ''')
    athlete_stats = c.fetchall()
    conn.close()
    
    return render_template_string(BASE_TEMPLATE + REWARDS_TEMPLATE, athlete_stats=athlete_stats)

@app.route('/export-csv')
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT athlete_name, grade, focus_area, assignment, focus_rating,
               phone_pouch_number, check_in_time, check_out_time, evidence_of_work, status,
               was_on_time, session_date
        FROM sessions ORDER BY id DESC
    ''')
    records = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Grade', 'Subject', 'Assignment', 'Focus Rating', 'Phone Pouch', 
                     'Check In Time', 'Check Out Time', 'Evidence', 'Status', 'On Time', 'Date'])
    writer.writerows([[
        r['athlete_name'], r['grade'], r['focus_area'], r['assignment'], r['focus_rating'],
        r['phone_pouch_number'], r['check_in_time'], r['check_out_time'], r['evidence_of_work'],
        r['status'], 'Yes' if r['was_on_time'] else 'No', r['session_date']
    ] for r in records])
    
    output.seek(0)
    
    from flask import Response
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=tutoring_records_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

@app.route('/clear-all')
def clear_all():
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM sessions')
    
    for athlete in ATHLETES:
        c.execute('''
            UPDATE athlete_stats SET tardy_count = 0, noshow_count = 0, consecutive_ontime = 0, prize_tickets = 0
            WHERE athlete_name = ?
        ''', (athlete,))
    
    c.execute('DELETE FROM violations')
    
    conn.commit()
    conn.close()
    
    flash('✅ All records cleared! Stats reset.', 'success')
    return redirect(url_for('admin'))

# ===== RUN =====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

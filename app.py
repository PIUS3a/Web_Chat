import sqlite3, os, random, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from google import genai 

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neural_shield_final_v2'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- AI CONFIGURATION ---
GEN_KEY = os.getenv("GEMINI_KEY", "").replace('"', '').replace("'", "").strip()
ai_client = None

if GEN_KEY:
    try:
        ai_client = genai.Client(api_key=GEN_KEY)
        print("✅ AI Client Initialized Successfully")
    except Exception as e:
        print(f"❌ AI Client Error: {e}")

DB_NAME = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT)')
    conn.commit()
    conn.close()

def send_mail(target_email, otp, subject="Security Verification"):
    sender = os.getenv("EMAIL_USER", "").strip()
    password = os.getenv("EMAIL_PASS", "").replace(" ", "").strip()
    msg = MIMEText(f"Your secure verification code is: {otp}")
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = target_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

init_db()
pending_registrations = {}
pending_resets = {}

@app.route('/')
def index():
    return render_template('index.html')

# --- AUTH LOGIC ---
@socketio.on('login_user')
def handle_login(data):
    user, pwd = data.get('user', '').lower().strip(), data.get('pass', '')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (user,))
    res = cursor.fetchone()
    conn.close()
    if res and res[0] == pwd:
        emit('auth_status', {'success': True, 'is_login': True, 'user': user, 'msg': 'Verified.'})
    else:
        emit('auth_status', {'success': False, 'msg': 'Invalid credentials.'})

@socketio.on('register_step_1')
def handle_reg(data):
    user, pwd, email = data.get('user', '').lower().strip(), data.get('pass', ''), data.get('email', '').strip()
    if len(pwd) < 7:
        emit('auth_status', {'success': False, 'msg': 'Min 7 chars required!'})
        return
    otp = str(random.randint(100000, 999999))
    pending_registrations[user] = {'pass': pwd, 'email': email, 'otp': otp}
    try:
        send_mail(email, otp)
        emit('auth_status', {'success': True, 'needs_otp': True, 'msg': 'OTP sent to email.'})
    except:
        emit('auth_status', {'success': False, 'msg': 'Email failed.'})

@socketio.on('verify_otp')
def handle_verify(data):
    user, otp = data.get('user', '').lower().strip(), data.get('otp', '').strip()
    if user in pending_registrations and pending_registrations[user]['otp'] == otp:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users VALUES (?, ?, ?)", 
                           (user, pending_registrations[user]['pass'], pending_registrations[user]['email']))
            conn.commit()
            emit('auth_status', {'success': True, 'msg': 'Account Created! Log in.'})
        except:
            emit('auth_status', {'success': False, 'msg': 'User exists.'})
        conn.close()
    else:
        emit('auth_status', {'success': False, 'msg': 'Incorrect OTP.'})

@socketio.on('request_reset')
def handle_reset_req(data):
    email = data.get('email', '').strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE email=?", (email,))
    user_found = cursor.fetchone()
    conn.close()
    if user_found:
        otp = str(random.randint(100000, 999999))
        pending_resets[email] = otp
        send_mail(email, otp, "Recovery Code")
        emit('auth_status', {'success': True, 'needs_otp': True, 'msg': 'Code sent!'})
    else:
        emit('auth_status', {'success': False, 'msg': 'Email not found.'})

@socketio.on('confirm_reset')
def handle_reset_confirm(data):
    email, otp, new_p = data.get('email'), data.get('otp'), data.get('pass')
    if pending_resets.get(email) == otp and len(new_p) >= 7:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=? WHERE email=?", (new_p, email))
        conn.commit()
        conn.close()
        emit('auth_status', {'success': True, 'msg': 'Password updated!'})
    else:
        emit('auth_status', {'success': False, 'msg': 'Invalid OTP or password short.'})

# --- CHAT & AI ---
@socketio.on('chat_msg')
def handle_chat(data):
    ts = datetime.now().strftime('%H:%M')
    data['time'] = ts
    emit('receive_msg', data, broadcast=True)
    
    text = data.get('text', '')
    if text.startswith('@bot'):
        if not ai_client:
            emit('receive_msg', {'user': 'System', 'text': 'AI not configured.', 'time': ts}, broadcast=True)
            return
        try:
            query = text[5:]
            prompt = f"You are a grounded, witty, highly capable male lead expert. Respond concisely to: {query}"
            response = ai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            emit('receive_msg', {'user': 'Assistant 🤖', 'text': response.text, 'time': ts}, broadcast=True)
        except Exception as e:
            print(f"BOT ERROR: {e}")
            emit('receive_msg', {'user': 'System', 'text': 'Bot offline. Check terminal.', 'time': ts}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5001)
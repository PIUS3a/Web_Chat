# Web_Chat
A secure, real-time chat platform featuring email-based OTP verification and a custom-personality AI assistant. Built with Flask and Gemini 2.0, the app includes a sleek dark-mode interface and a witty, expert-level bot that responds to @bot commands. It’s designed for high-speed communication with a focus on user privacy and smart interactions.

1. Requirements
You must have Python installed and a Google Gemini API Key.

2. Installation
Open your terminal in the project folder and run:

PowerShell
# Install all necessary libraries
pip install flask flask-socketio google-genai python-dotenv
3. Environment Setup
Create a file named .env and paste your keys there (No spaces or quotes):

Plaintext
GEMINI_KEY=Your_Gemini_API_Key
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
4. Launch
PowerShell
python app.py
Go to http://127.0.0.1:5001 in your browser.

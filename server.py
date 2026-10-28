import os, json
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
app.secret_key = "niraj_secret_key_12345"
CORS(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"trades": {}, "approvals": {}, "pending": {}, "slave_settings": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

db = load_data()

LOGIN_HTML = """
<!DOCTYPE html><html><head><title>Login</title>
<style>body{font-family:Arial;background:#1a1a2e;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.box{background:white;padding:30px;border-radius:10px;width:300px}
input{width:100%;padding:10px;margin:10px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}
button{width:100%;padding:12px;background:#16213e;color:white;border:none;border-radius:5px;cursor:pointer}
h2{text-align:center;color:#16213e}</style>
</head><body><div class="box"><h2>MT5 Copier Login</h2>
<form method="POST"><input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button></form></div></body></html>
"""

ADMIN_HTML = """
<!DOCTYPE html><html><head><title>Admin</title>
<style>body{font-family:Arial;background:#f0f2f5;padding:20px}
.card{background:white;padding:20px;border-radius:10px;margin:10px 0}
.approve{background:#27ae60;color:white;padding:8px 15px;border:none;border-radius:5px}
.deny{background:#e74c3c;color:white;padding:8px 15px;border:none;border-radius:5px}
</style></head><body><h1>Master Dashboard</h1>
<a href="/logout">Logout</a><br><br>
{% for slave_id, info in pending.items() %}
<div class="card"><b>{{slave_id}}</b><br>{{info.get('ip','')}}<br>{{info.get('time','')}}
<br><br><a href="/admin?approve={{slave_id}}"><button class="approve">Approve</button></a>
<a href="/admin?deny={{slave_id}}"><button class="deny">Deny</button></a></div>
{% endfor %}
{% if not pending %}<p>No pending</p>{% endif %}
<h2>Approved: {{approvals|length}}</h2>
{% for sid in approvals %}<div class="card">{{sid}}</div>{% endfor %}
</body></html>
"""

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username')==ADMIN_USERNAME and request.form.get('password')==ADMIN_PASSWORD:
            session['logged_in']=True
            return redirect('/admin')
        return LOGIN_HTML + "<p style='color:red;text-align:center'>Wrong</p>"
    return LOGIN_HTML

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/admin')
@login_required
def admin():
    global db
    db = load_data()
    approve = request.args.get('approve')
    deny = request.args.get('deny')
    if approve:
        db['approvals'][approve]=True
        if approve in db['pending']: del db['pending'][approve]
        save_data(db)
    if deny:
        if deny in db['pending']: del db['pending'][deny]
        if deny in db['approvals']: del db['approvals'][deny]
        save_data(db)
    return render_template_string(ADMIN_HTML, pending=db.get('pending',{}), approvals=db.get('approvals',{}))

@app.route('/api/update', methods=['POST'])
def api_update():
    global db
    data = request.get_json()
    if not data: return jsonify({"error":"no data"}),400
    slave_id = data.get('slave_id')
    if slave_id:
        if slave_id not in db['approvals']:
            db['pending'][slave_id]={'ip':request.remote_addr,'time':str(datetime.now())}
            save_data(db)
            return jsonify({"status":"pending_approval"})
    master_trades = data.get('trades')
    if master_trades is not None:
        db['trades']=master_trades
        save_data(db)
    if slave_id and 'settings' in data:
        db['slave_settings'][slave_id]=data['settings']
        save_data(db)
    return jsonify({"status":"ok"})

@app.route('/api/get', methods=['GET'])
def api_get():
    global db
    slave_id = request.args.get('slave_id')
    if slave_id and slave_id not in db['approvals']:
        if slave_id not in db['pending']:
            db['pending'][slave_id]={'ip':request.remote_addr,'time':str(datetime.now())}
            save_data(db)
        return jsonify({"status":"pending_approval"})
    return jsonify({"trades": db.get('trades',{}),"settings": db.get('slave_settings',{}).get(slave_id,{}) if slave_id else {},"status":"ok"})

@app.route('/')
def home():
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

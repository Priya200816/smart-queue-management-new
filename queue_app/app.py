from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.secret_key = "secret"

# ================= DB =================
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT,
        password TEXT,
        name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        email TEXT,
        token INTEGER,
        priority INTEGER DEFAULT 0,
        reason TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

current_token = 1

# ================= LOGIN =================
@app.route('/', methods=['GET', 'POST'])
def login():
    error = ""

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == "admin@gmail.com" and password == "admin":
            session['admin'] = True
            return redirect('/admin')

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()

        if user:
            session['user'] = email
            session['name'] = user[2]
            return redirect('/dashboard')
        else:
            error = "Invalid login"

        conn.close()

    return render_template("login.html", error=error)

# ================= SIGNUP =================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("INSERT INTO users VALUES (?,?,?)",
                    (request.form['email'], request.form['password'], request.form['name']))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("signup.html")

# ================= DASHBOARD =================
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    global current_token

    if 'user' not in session:
        return redirect('/')

    email = session['user']

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT token, priority FROM tokens WHERE email=?", (email,))
    data = cur.fetchone()

    user_token = data[0] if data else 0
    priority = data[1] if data else 0

    if request.method == 'POST':
        action = request.form.get("action")

        if action == "get" and user_token == 0:
            cur.execute("SELECT MAX(token) FROM tokens WHERE priority=0")
            last = cur.fetchone()[0]
            new_token = 1 if last is None else last + 1

            cur.execute("INSERT INTO tokens VALUES (?,?,?,?)",
                        (email, new_token, 0, None))
            conn.commit()
            return redirect('/dashboard')

        elif action == "emergency" and user_token == 0:
            reason = request.form.get("reason")

            if reason:
                cur.execute("SELECT MIN(token) FROM tokens")
                first = cur.fetchone()[0]
                new_token = 1 if first is None else first - 1

                cur.execute("INSERT INTO tokens VALUES (?,?,?,?)",
                            (email, new_token, 1, reason))
                conn.commit()
                return redirect('/dashboard')

        elif action == "cancel":
            cur.execute("DELETE FROM tokens WHERE email=?", (email,))
            conn.commit()
            return redirect('/dashboard')

    cur.execute("SELECT COUNT(*) FROM tokens WHERE token < ?", (user_token,))
    people = cur.fetchone()[0] if user_token else 0

    wait = people * 2

    status = "🟢 Waiting"

    if user_token == 0:
        status = "⚪ Not in queue"
    elif priority == 1:
        status = "🚨 Emergency"
    elif user_token == current_token:
        status = "🔴 Your Turn!"
    elif user_token - current_token <= 2:
        status = "🟠 Near"
    else:
        status = "🟢 Waiting"

    conn.close()

    return render_template("dashboard.html",
                           name=session.get('name'),
                           token=user_token,
                           current=current_token,
                           people=people,
                           wait=wait,
                           status=status)

# ================= ADMIN =================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global current_token

    if 'admin' not in session:
        return redirect('/')

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == 'POST':
        action = request.form.get("action")

        if action == "next":
            current_token += 1

        elif action == "remove":
            email = request.form.get("email")
            cur.execute("DELETE FROM tokens WHERE email=?", (email,))
            conn.commit()

    cur.execute("SELECT * FROM tokens ORDER BY token ASC")
    queue = cur.fetchall()

    conn.close()

    return render_template("admin.html",
                           queue=queue,
                           current=current_token)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == '__main__':
    import os

app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

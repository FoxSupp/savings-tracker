import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, g

DATABASE = os.path.join(os.path.dirname(__file__), 'data', 'savings.db')
CATEGORIES = ['Bar', 'Trade Republic', 'ETF', 'Tagesgeld', 'Aktien', 'Krypto', 'Other']

app = Flask(__name__)
app.config['DATABASE'] = DATABASE

# ─── Database ─────────────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )''')
        db.commit()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def row_to_dict(row):
    return dict(row) if row else None

def get_totals_by_category():
    db = get_db()
    rows = db.execute('''SELECT category, SUM(amount) as total
                          FROM savings GROUP BY category''').fetchall()
    totals = {cat: 0.0 for cat in CATEGORIES}
    for r in rows:
        totals[r['category']] = r['total']
    return totals

def get_entries(order_desc=True):
    db = get_db()
    direction = 'DESC' if order_desc else 'ASC'
    return db.execute(f'SELECT * FROM savings ORDER BY date {direction}, id {direction}').fetchall()

# ─── Web UI ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    totals = get_totals_by_category()
    grand_total = sum(totals.values())
    entries = get_entries()
    return render_template('index.html', totals=totals, grand_total=grand_total,
                           entries=entries, categories=CATEGORIES)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', type=float)
        date = request.form.get('date', '').strip()
        notes = request.form.get('notes', '').strip()

        if not category or category not in CATEGORIES:
            return render_template('form.html', entry=None, categories=CATEGORIES,
                                   error='Invalid category.', date_default=''), 400
        if not amount or amount <= 0:
            return render_template('form.html', entry=None, categories=CATEGORIES,
                                   error='Amount must be positive.', date_default=''), 400
        if not date:
            return render_template('form.html', entry=None, categories=CATEGORIES,
                                   error='Date is required.', date_default=''), 400

        db = get_db()
        db.execute('INSERT INTO savings (category, amount, date, notes, created_at) VALUES (?, ?, ?, ?, ?)',
                    (category, amount, date, notes, datetime.utcnow().isoformat()))
        db.commit()
        return redirect(url_for('index'))

    today = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('form.html', entry=None, categories=CATEGORIES,
                           error=None, date_default=today, action=url_for('add'))

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit(entry_id):
    db = get_db()
    entry = row_to_dict(db.execute('SELECT * FROM savings WHERE id = ?', (entry_id,)).fetchone())
    if not entry:
        return redirect(url_for('index'))

    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', type=float)
        date = request.form.get('date', '').strip()
        notes = request.form.get('notes', '').strip()

        if not category or category not in CATEGORIES:
            return render_template('form.html', entry=entry, categories=CATEGORIES,
                                   error='Invalid category.', action=url_for('edit', entry_id=entry_id)), 400
        if not amount or amount <= 0:
            return render_template('form.html', entry=entry, categories=CATEGORIES,
                                   error='Amount must be positive.', action=url_for('edit', entry_id=entry_id)), 400
        if not date:
            return render_template('form.html', entry=entry, categories=CATEGORIES,
                                   error='Date is required.', action=url_for('edit', entry_id=entry_id)), 400

        db.execute('UPDATE savings SET category=?, amount=?, date=?, notes=? WHERE id=?',
                   (category, amount, date, notes, entry_id))
        db.commit()
        return redirect(url_for('index'))

    return render_template('form.html', entry=entry, categories=CATEGORIES,
                           error=None, action=url_for('edit', entry_id=entry_id))

@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete(entry_id):
    db = get_db()
    db.execute('DELETE FROM savings WHERE id = ?', (entry_id,))
    db.commit()
    return redirect(url_for('index'))

# ─── JSON API ─────────────────────────────────────────────────────────────────

@app.route('/api/entries', methods=['GET'])
def api_list():
    return jsonify([row_to_dict(r) for r in get_entries()])

@app.route('/api/entries', methods=['POST'])
def api_create():
    data = request.get_json() or {}
    category = data.get('category', '').strip()
    amount = data.get('amount', type=float)
    date = data.get('date', '').strip()
    notes = data.get('notes', '').strip()

    if not category or category not in CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
    if not amount or amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    if not date:
        return jsonify({'error': 'Date is required'}), 400

    db = get_db()
    cur = db.execute('INSERT INTO savings (category, amount, date, notes, created_at) VALUES (?, ?, ?, ?, ?)',
                     (category, amount, date, notes, datetime.utcnow().isoformat()))
    db.commit()
    entry = row_to_dict(db.execute('SELECT * FROM savings WHERE id = ?', (cur.lastrowid,)).fetchone())
    return jsonify(entry), 201

@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
def api_update(entry_id):
    db = get_db()
    entry = row_to_dict(db.execute('SELECT * FROM savings WHERE id = ?', (entry_id,)).fetchone())
    if not entry:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json() or {}
    category = data.get('category', entry['category']).strip()
    amount = data.get('amount', entry['amount'])
    date = data.get('date', entry['date']).strip()
    notes = data.get('notes', entry['notes'] or '').strip()

    if category not in CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
    if not amount or amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    db.execute('UPDATE savings SET category=?, amount=?, date=?, notes=? WHERE id=?',
               (category, amount, date, notes, entry_id))
    db.commit()
    return jsonify(row_to_dict(db.execute('SELECT * FROM savings WHERE id = ?', (entry_id,)).fetchone()))

@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def api_delete(entry_id):
    db = get_db()
    db.execute('DELETE FROM savings WHERE id = ?', (entry_id,))
    db.commit()
    return '', 204

# ─── Init ─────────────────────────────────────────────────────────────────────

# Initialize DB on module load (works with both gunicorn and python -m)
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask, render_template, request, jsonify, session, redirect
from functools import wraps
import sqlite3
import random
import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Change this in production

# Admin credentials (change these in production)
ADMIN_ID = "Hiren"  # Change this to your admin ID
ADMIN_PASSWORD_HASH = hashlib.sha256("hiren123".encode()).hexdigest()  # Change "admin123" to your password

# Helper function for authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect('/manage/admin/login')
        return f(*args, **kwargs)
    return decorated_function

# Database setup - Support both SQLite (local) and PostgreSQL (Vercel)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

def get_db_connection():
    """Get database connection - PostgreSQL on Vercel, SQLite locally"""
    if USE_POSTGRES:
        import psycopg2
        # Parse DATABASE_URL (format: postgres://user:pass@host:port/dbname)
        # Handle both postgres:// and postgresql://
        db_url = DATABASE_URL
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        result = urlparse(db_url)
        conn = psycopg2.connect(
            database=result.path[1:],  # Remove leading /
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode='require'  # SSL required for cloud databases
        )
        return conn
    else:
        return sqlite3.connect('spin_wheel.db')

def get_cursor(conn):
    """Get cursor with proper row factory for SQLite"""
    if USE_POSTGRES:
        return conn.cursor()
    else:
        conn.row_factory = sqlite3.Row
        return conn.cursor()

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    c = get_cursor(conn)
    
    if USE_POSTGRES:
        # PostgreSQL syntax
        c.execute('''CREATE TABLE IF NOT EXISTS spins
                     (id SERIAL PRIMARY KEY,
                      user_id VARCHAR(255) NOT NULL,
                      prize INTEGER NOT NULL,
                      timestamp VARCHAR(255) NOT NULL,
                      ip_address VARCHAR(255),
                      upi_id TEXT,
                      order_id TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS orders
                     (id SERIAL PRIMARY KEY,
                      order_id VARCHAR(255) UNIQUE NOT NULL,
                      user_id VARCHAR(255),
                      created_at VARCHAR(255) NOT NULL,
                      used_at VARCHAR(255),
                      is_used INTEGER DEFAULT 0)''')
        
        # Add columns if they don't exist (PostgreSQL)
        try:
            c.execute("ALTER TABLE spins ADD COLUMN upi_id TEXT")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE spins ADD COLUMN order_id TEXT")
        except Exception:
            pass
    else:
        # SQLite syntax
        c.execute('''CREATE TABLE IF NOT EXISTS spins
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      prize INTEGER NOT NULL,
                      timestamp TEXT NOT NULL,
                      ip_address TEXT,
                      upi_id TEXT,
                      order_id TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS orders
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      order_id TEXT UNIQUE NOT NULL,
                      user_id TEXT,
                      created_at TEXT NOT NULL,
                      used_at TEXT,
                      is_used INTEGER DEFAULT 0)''')
        
        # Add columns if they don't exist (SQLite)
        try:
            c.execute("ALTER TABLE spins ADD COLUMN upi_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE spins ADD COLUMN order_id TEXT")
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

# Prize values (12 segments) - ₹30 is Jackpot
PRIZES = [1, 5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100]

# Probability configuration (admin variable)
# Users will only get ₹1-₹10 prizes
# Format: {prize: probability_weight}
PRIZE_PROBABILITIES = {
    1: 25,    # Common
    5: 25,    # Common
    10: 20,   # Common
    15: 0,    # Disabled - users only get ₹1-₹10
    20: 0,    # Disabled
    25: 0,    # Disabled
    30: 0,    # Jackpot - disabled for regular users
    40: 0,    # Disabled
    50: 0,    # Disabled
    60: 0,    # Disabled
    75: 0,    # Disabled
    100: 0    # Disabled
}

def get_user_id():
    """Generate unique user ID from session + IP + browser fingerprint"""
    if 'user_id' not in session:
        # Create user ID from IP + user agent
        ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        fingerprint = f"{ip}_{user_agent}"
        user_id = hashlib.md5(fingerprint.encode()).hexdigest()
        session['user_id'] = user_id
    return session['user_id']

def has_user_spun(user_id, order_id=None):
    """Check if user has already spun (without order ID)"""
    conn = get_db_connection()
    c = get_cursor(conn)
    
    # If order_id is provided, check if it's valid and unused
    if order_id:
        c.execute("SELECT is_used FROM orders WHERE order_id = %s" if USE_POSTGRES else "SELECT is_used FROM orders WHERE order_id = ?", (order_id,))
        order = c.fetchone()
        if order and order[0] == 0:  # Order exists and is unused
            conn.close()
            return False  # Can spin with valid order ID
        elif order and order[0] == 1:  # Order already used
            conn.close()
            return True  # Already used this order
    
    # Check regular spins (without order ID)
    c.execute("SELECT COUNT(*) FROM spins WHERE user_id = %s AND (order_id IS NULL OR order_id = '')" if USE_POSTGRES else "SELECT COUNT(*) FROM spins WHERE user_id = ? AND (order_id IS NULL OR order_id = '')", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def select_prize():
    """Select prize based on probability weights - only ₹1-₹10 for regular users"""
    # Filter out prizes with 0 weight (disabled prizes)
    available_prizes = [p for p, w in PRIZE_PROBABILITIES.items() if w > 0]
    available_weights = [PRIZE_PROBABILITIES[p] for p in available_prizes]
    
    # Select prize based on weighted random (only ₹1-₹20 will be selected)
    selected = random.choices(available_prizes, weights=available_weights, k=1)[0]
    return selected

def record_spin(user_id, prize, order_id=None):
    """Record spin in database"""
    conn = get_db_connection()
    c = get_cursor(conn)
    timestamp = datetime.now().isoformat()
    ip_address = request.remote_addr
    
    # If order_id provided, mark it as used
    if order_id:
        if USE_POSTGRES:
            c.execute("UPDATE orders SET is_used = 1, user_id = %s, used_at = %s WHERE order_id = %s",
                      (user_id, timestamp, order_id))
            c.execute("INSERT INTO spins (user_id, prize, timestamp, ip_address, order_id) VALUES (%s, %s, %s, %s, %s)",
                      (user_id, prize, timestamp, ip_address, order_id))
        else:
            c.execute("UPDATE orders SET is_used = 1, user_id = ?, used_at = ? WHERE order_id = ?",
                      (user_id, timestamp, order_id))
            c.execute("INSERT INTO spins (user_id, prize, timestamp, ip_address, order_id) VALUES (?, ?, ?, ?, ?)",
                      (user_id, prize, timestamp, ip_address, order_id))
    else:
        if USE_POSTGRES:
            c.execute("INSERT INTO spins (user_id, prize, timestamp, ip_address) VALUES (%s, %s, %s, %s)",
                      (user_id, prize, timestamp, ip_address))
        else:
            c.execute("INSERT INTO spins (user_id, prize, timestamp, ip_address) VALUES (?, ?, ?, ?)",
                      (user_id, prize, timestamp, ip_address))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validate-order', methods=['POST'])
def validate_order():
    """Validate order ID before spin"""
    data = request.get_json() or {}
    order_id = data.get('order_id', '').strip().upper() if data else None
    
    if not order_id:
        return jsonify({
            'success': False,
            'message': 'Please enter an order ID'
        }), 400
    
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute("SELECT is_used FROM orders WHERE order_id = %s" if USE_POSTGRES else "SELECT is_used FROM orders WHERE order_id = ?", (order_id,))
    order = c.fetchone()
    conn.close()
    
    if not order:
        return jsonify({
            'success': False,
            'message': 'Invalid order ID. Please check and try again.'
        }), 404
    
    if order[0] == 1:
        return jsonify({
            'success': False,
            'message': 'This order ID has already been used.'
        }), 403
    
    return jsonify({
        'success': True,
        'message': 'Valid Order ID'
    })

@app.route('/spin', methods=['POST'])
def spin():
    """Handle spin request - Order ID is required for all spins"""
    user_id = get_user_id()
    data = request.get_json() or {}
    order_id = data.get('order_id', '').strip().upper() if data else None
    
    # Order ID is required for all spins (to prevent unlimited spins)
    if not order_id:
        return jsonify({
            'success': False,
            'message': 'Order ID is required to spin. Please enter a valid order ID.',
            'prize': None
        }), 400
    
    # Validate order ID exists in database
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute("SELECT is_used FROM orders WHERE order_id = %s" if USE_POSTGRES else "SELECT is_used FROM orders WHERE order_id = ?", (order_id,))
    order = c.fetchone()
    
    if not order:
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Invalid order ID. This order ID does not exist in our system.',
            'prize': None
        }), 404
    
    # Check if order ID is already used
    if order[0] == 1:
        conn.close()
        return jsonify({
            'success': False,
            'message': 'This order ID has already been used.',
            'prize': None
        }), 403
    
    conn.close()
    
    # Select prize based on probability
    prize = select_prize()
    
    # Record spin with order ID
    record_spin(user_id, prize, order_id)
    
    return jsonify({
        'success': True,
        'prize': prize,
        'message': f'You won {prize} rupees!'
    })

@app.route('/check-status', methods=['GET'])
def check_status():
    """Check if user has already spun"""
    user_id = get_user_id()
    has_spun = has_user_spun(user_id)
    
    if has_spun:
        conn = get_db_connection()
        c = get_cursor(conn)
        c.execute("SELECT prize FROM spins WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1" if USE_POSTGRES else "SELECT prize FROM spins WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
        result = c.fetchone()
        conn.close()
        prize = result[0] if result else None
        return jsonify({
            'has_spun': True,
            'prize': prize
        })
    
    return jsonify({
        'has_spun': False,
        'prize': None
    })

@app.route('/submit-upi', methods=['POST'])
def submit_upi():
    """Save UPI ID for the user's spin"""
    import re
    try:
        user_id = get_user_id()
        
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Invalid request format'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data received'
            }), 400
        
        upi_id = data.get('upi_id', '').strip()
        
        if not upi_id:
            return jsonify({
                'success': False,
                'message': 'UPI ID is required'
            }), 400
        
        # Validate UPI ID format - must have @ symbol
        if '@' not in upi_id:
            return jsonify({
                'success': False,
                'message': 'Invalid UPI ID. Must include @ symbol (e.g., yourname@paytm)'
            }), 400
        
        # Split by @ to check both parts
        parts = upi_id.split('@')
        if len(parts) != 2:
            return jsonify({
                'success': False,
                'message': 'Invalid UPI ID format. Use format: yourname@paytm'
            }), 400
        
        username, provider = parts[0].strip(), parts[1].strip()
        
        # Validate username (before @)
        if not username or len(username) < 2:
            return jsonify({
                'success': False,
                'message': 'Invalid username. Must be at least 2 characters before @'
            }), 400
        
        # Validate provider (after @)
        if not provider or len(provider) < 2:
            return jsonify({
                'success': False,
                'message': 'Invalid provider. Must include provider name after @ (e.g., @paytm, @ybl, @upi)'
            }), 400
        
        # Full pattern validation
        upi_pattern = re.compile(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$')
        if not upi_pattern.match(upi_id):
            return jsonify({
                'success': False,
                'message': 'Invalid UPI ID format. Use format: yourname@paytm (only letters, numbers, dots, hyphens, underscores allowed)'
            }), 400
        
        # Check database
        conn = get_db_connection()
        c = get_cursor(conn)
        
        # Get the latest spin for this user
        if USE_POSTGRES:
            c.execute("SELECT id, upi_id FROM spins WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1",
                      (user_id,))
        else:
            c.execute("SELECT id, upi_id FROM spins WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
                      (user_id,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'No spin found for this user'
            }), 404
        
        spin_id = result[0]
        existing_upi_id = result[1] if len(result) > 1 else None
        
        # Check if latest spin already has UPI ID
        if existing_upi_id and existing_upi_id.strip():
            conn.close()
            return jsonify({
                'success': False,
                'message': 'UPI ID already submitted for this spin.'
            }), 400
        
        # Update the latest spin with UPI ID
        if USE_POSTGRES:
            c.execute("UPDATE spins SET upi_id = %s WHERE id = %s",
                      (upi_id, spin_id))
        else:
            c.execute("UPDATE spins SET upi_id = ? WHERE id = ?",
                      (upi_id, spin_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'UPI ID saved successfully! Payment will be processed manually.'
        })
            
    except Exception as e:
        # Log error for debugging
        print(f"Error in submit_upi: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/add-order', methods=['POST'])
@admin_required
def add_order():
    """Add order ID (admin function)"""
    data = request.get_json() or {}
    order_id = data.get('order_id', '').strip().upper()
    
    if not order_id:
        return jsonify({
            'success': False,
            'message': 'Order ID is required'
        }), 400
    
    # Validate order ID format (alphanumeric, 4-20 characters)
    if not order_id.replace('_', '').replace('-', '').isalnum() or len(order_id) < 4 or len(order_id) > 20:
        return jsonify({
            'success': False,
            'message': 'Order ID must be 4-20 characters (letters, numbers, dash, underscore only)'
        }), 400
    
    conn = get_db_connection()
    c = get_cursor(conn)
    
    # Check if order already exists
    if USE_POSTGRES:
        c.execute("SELECT id FROM orders WHERE order_id = %s", (order_id,))
    else:
        c.execute("SELECT id FROM orders WHERE order_id = ?", (order_id,))
    if c.fetchone():
        conn.close()
        return jsonify({
            'success': False,
            'message': 'This order ID already exists'
        }), 400
    
    # Insert order
    timestamp = datetime.now().isoformat()
    try:
        if USE_POSTGRES:
            c.execute("INSERT INTO orders (order_id, created_at) VALUES (%s, %s)",
                      (order_id, timestamp))
        else:
            c.execute("INSERT INTO orders (order_id, created_at) VALUES (?, ?)",
                      (order_id, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Order ID added successfully'
        })
    except Exception as e:
        conn.close()
        return jsonify({
            'success': False,
            'message': f'Error adding order ID: {str(e)}'
        }), 500

@app.route('/manage/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'GET':
        # If already logged in, redirect to admin
        if session.get('admin_logged_in'):
            return redirect('/manage/admin')
        return render_template('admin_login.html')
    
    # Handle POST request
    data = request.get_json() or request.form.to_dict()
    admin_id = data.get('admin_id', '').strip()
    password = data.get('password', '')
    
    # Hash password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Validate credentials
    if admin_id == ADMIN_ID and password_hash == ADMIN_PASSWORD_HASH:
        session['admin_logged_in'] = True
        session['admin_id'] = admin_id
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid Admin ID or Password'}), 401

@app.route('/manage/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    return redirect('/manage/admin/login')

@app.route('/manage/admin')
@admin_required
def admin():
    """Admin panel to view all spins and statistics"""
    conn = get_db_connection()
    c = get_cursor(conn)
    
    # Get limited spins with user info (last 10)
    c.execute('''SELECT user_id, prize, timestamp, ip_address, upi_id, order_id 
                 FROM spins ORDER BY timestamp DESC LIMIT 10''')
    spins = c.fetchall()
    
    # Calculate statistics
    c.execute('SELECT COUNT(*) FROM spins')
    total_spins = c.fetchone()[0]
    
    c.execute('SELECT COUNT(DISTINCT user_id) FROM spins')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT SUM(prize) FROM spins')
    total_amount = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM spins WHERE upi_id IS NOT NULL AND upi_id != ""')
    upi_submitted = c.fetchone()[0]
    
    # Get order statistics
    c.execute('SELECT COUNT(*) FROM orders')
    total_orders = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM orders WHERE is_used = 1')
    used_orders = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM orders WHERE is_used = 0')
    available_orders = c.fetchone()[0]
    
    # Get limited orders (last 10)
    c.execute('''SELECT order_id, user_id, created_at, used_at, is_used 
                 FROM orders ORDER BY created_at DESC LIMIT 10''')
    all_orders = c.fetchall()
    
    # Group by user (limited to last 10)
    if USE_POSTGRES:
        c.execute('''SELECT user_id, COUNT(*) as spin_count, SUM(prize) as total_prize, 
                     MAX(timestamp) as last_spin, STRING_AGG(DISTINCT upi_id, ',') as upi_ids
                     FROM spins 
                     GROUP BY user_id 
                     ORDER BY last_spin DESC
                     LIMIT 10''')
    else:
        c.execute('''SELECT user_id, COUNT(*) as spin_count, SUM(prize) as total_prize, 
                     MAX(timestamp) as last_spin, GROUP_CONCAT(DISTINCT upi_id) as upi_ids
                     FROM spins 
                     GROUP BY user_id 
                     ORDER BY last_spin DESC
                     LIMIT 10''')
    user_stats = c.fetchall()
    
    conn.close()
    
    return render_template('admin.html', 
                         spins=spins,
                         total_spins=total_spins,
                         total_users=total_users,
                         total_amount=total_amount,
                         upi_submitted=upi_submitted,
                         user_stats=user_stats,
                         total_orders=total_orders,
                         used_orders=used_orders,
                         available_orders=available_orders,
                         all_orders=all_orders)

@app.route('/manage/admin/orders')
@admin_required
def admin_orders():
    """View all orders"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute('''SELECT order_id, user_id, created_at, used_at, is_used 
                 FROM orders ORDER BY created_at DESC''')
    all_orders = c.fetchall()
    conn.close()
    return render_template('admin_orders.html', all_orders=all_orders)

@app.route('/manage/admin/users')
@admin_required
def admin_users():
    """View all user statistics"""
    conn = get_db_connection()
    c = get_cursor(conn)
    if USE_POSTGRES:
        c.execute('''SELECT user_id, COUNT(*) as spin_count, SUM(prize) as total_prize, 
                     MAX(timestamp) as last_spin, STRING_AGG(DISTINCT upi_id, ',') as upi_ids
                     FROM spins 
                     GROUP BY user_id 
                     ORDER BY last_spin DESC''')
    else:
        c.execute('''SELECT user_id, COUNT(*) as spin_count, SUM(prize) as total_prize, 
                     MAX(timestamp) as last_spin, GROUP_CONCAT(DISTINCT upi_id) as upi_ids
                     FROM spins 
                     GROUP BY user_id 
                     ORDER BY last_spin DESC''')
    user_stats = c.fetchall()
    conn.close()
    return render_template('admin_users.html', user_stats=user_stats)

@app.route('/manage/admin/spins')
@admin_required
def admin_spins():
    """View all spins history"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute('''SELECT user_id, prize, timestamp, ip_address, upi_id, order_id 
                 FROM spins ORDER BY timestamp DESC''')
    spins = c.fetchall()
    conn.close()
    return render_template('admin_spins.html', spins=spins)

@app.route('/clear-all-data', methods=['POST'])
@admin_required
def clear_all_data():
    """Clear all data from database (admin function)"""
    try:
        conn = get_db_connection()
        c = get_cursor(conn)
        
        # Delete all spins
        c.execute("DELETE FROM spins")
        
        # Delete all orders
        c.execute("DELETE FROM orders")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'All data cleared successfully!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error clearing data: {str(e)}'
        }), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)

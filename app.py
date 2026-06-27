from flask import Flask, request, jsonify
import os
import pymysql
import pymysql.cursors
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# DATABASE CONFIGURATION
# ─────────────────────────────────────────────
DB_HOST = os.environ.get('MYSQL_HOST', 'syncstroam.in') # Can be overwritten via Render Env Variables
DB_NAME = 'u635307059_u12345_db'
DB_USER = 'u635307059_u12345_usr'
DB_PASS = 'Urvisha1213$'

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# Auto-initialize database tables if they do not exist
def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100) UNIQUE,
                    password VARCHAR(100),
                    createdAt VARCHAR(50),
                    purchasedProjects TEXT
                )
            """)
            # Projects table (LONGTEXT is used to store high-res images and base64 project zip files)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100),
                    category VARCHAR(50),
                    description TEXT,
                    price DECIMAL(10, 2),
                    image LONGTEXT,
                    projectFiles LONGTEXT,
                    projectFilesName VARCHAR(255),
                    requirements TEXT,
                    documentation TEXT,
                    demoUrl TEXT,
                    sellerId VARCHAR(50),
                    sellerName VARCHAR(100),
                    status VARCHAR(50),
                    createdAt VARCHAR(50),
                    likes INT DEFAULT 0
                )
            """)
            # Inquiries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inquiries (
                    id VARCHAR(50) PRIMARY KEY,
                    projectId VARCHAR(50),
                    projectName VARCHAR(100),
                    sellerId VARCHAR(50),
                    sellerName VARCHAR(100),
                    userId VARCHAR(50),
                    userName VARCHAR(100),
                    email VARCHAR(100),
                    phone VARCHAR(50),
                    message TEXT,
                    status VARCHAR(50),
                    createdAt VARCHAR(50)
                )
            """)
            conn.commit()
    finally:
        conn.close()

# Initialize tables
try:
    init_db()
except Exception as e:
    print("Warning: Database connection failed during initialization. Verify Host/Credentials:", e)

# ─────────────────────────────────────────────
# PROJECTS ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/projects', methods=['GET', 'POST'])
def handle_projects():
    if request.method == 'POST':
        p = request.json
        proj_id = f"proj{int(datetime.now().timestamp() * 1000)}"
        created_at = datetime.now().isoformat()
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = """INSERT INTO projects (id, name, category, description, price, image, 
                         projectFiles, projectFilesName, requirements, documentation, demoUrl, 
                         sellerId, sellerName, status, createdAt) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (
                    proj_id, p.get('name'), p.get('category'), p.get('description'), 
                    float(p.get('price', 0)), p.get('image'), p.get('projectFiles'), 
                    p.get('projectFilesName'), p.get('requirements'), p.get('documentation'), 
                    p.get('demoUrl'), p.get('sellerId'), p.get('sellerName'), 
                    p.get('status', 'pending'), created_at
                ))
                conn.commit()
            p['id'] = proj_id
            p['createdAt'] = created_at
            p['likes'] = 0
            return jsonify(p), 201
        finally:
            conn.close()
            
    # GET
    status = request.args.get('status')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if status:
                cursor.execute("SELECT * FROM projects WHERE status = %s", (status,))
            else:
                cursor.execute("SELECT * FROM projects")
            projects = cursor.fetchall()
            # Convert decimal objects to float for json compatibility
            for p in projects:
                p['price'] = float(p['price'])
            return jsonify(projects)
    finally:
        conn.close()

@app.route('/api/projects/<project_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_project_by_id(project_id):
    conn = get_db_connection()
    try:
        # GET project by ID
        if request.method == 'GET':
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
                p = cursor.fetchone()
                if p:
                    p['price'] = float(p['price'])
                    return jsonify(p)
            return jsonify({"error": "Project not found"}), 404
            
        # PUT update project by ID
        elif request.method == 'PUT':
            updates = request.json
            with conn.cursor() as cursor:
                # Construct dynamic update query
                set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                if not set_clause:
                    return jsonify({"error": "No update fields provided"}), 400
                sql = f"UPDATE projects SET {set_clause} WHERE id = %s"
                params = list(updates.values()) + [project_id]
                cursor.execute(sql, params)
                conn.commit()
                
                # Fetch updated
                cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
                p = cursor.fetchone()
                p['price'] = float(p['price'])
                return jsonify(p)
                
        # DELETE project by ID
        elif request.method == 'DELETE':
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                affected = cursor.rowcount
                conn.commit()
                if affected > 0:
                    return jsonify({"message": "Project deleted"}), 200
            return jsonify({"error": "Project not found"}), 404
    finally:
        conn.close()

# ─────────────────────────────────────────────
# USERS ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/users', methods=['GET', 'POST'])
def handle_users():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            u = request.json
            email = u.get('email', '')
            
            with conn.cursor() as cursor:
                # Check duplication
                cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s", (email.lower(),))
                if cursor.fetchone():
                    return jsonify({"error": "Email already exists"}), 400
                
                user_id = f"user{int(datetime.now().timestamp() * 1000)}"
                created_at = datetime.now().isoformat()
                
                sql = "INSERT INTO users (id, name, email, password, createdAt, purchasedProjects) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (user_id, u.get('name'), email, u.get('password'), created_at, ''))
                conn.commit()
                
            u['id'] = user_id
            u['createdAt'] = created_at
            u['purchasedProjects'] = []
            return jsonify(u), 201
            
        # GET
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, email, createdAt, purchasedProjects FROM users")
            users = cursor.fetchall()
            for user in users:
                # Parse comma separated string list
                pps = user.get('purchasedProjects')
                user['purchasedProjects'] = pps.split(',') if pps else []
            return jsonify(users)
    finally:
        conn.close()

@app.route('/api/users/purchase', methods=['POST'])
def purchase_project():
    req = request.json
    user_id = req.get('userId')
    project_id = req.get('projectId')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            pps = user.get('purchasedProjects')
            purchased_list = pps.split(',') if pps else []
            if project_id not in purchased_list:
                purchased_list.append(project_id)
                new_pps = ",".join(purchased_list)
                cursor.execute("UPDATE users SET purchasedProjects = %s WHERE id = %s", (new_pps, user_id))
                conn.commit()
                user['purchasedProjects'] = purchased_list
            else:
                user['purchasedProjects'] = purchased_list
                
            # clean response keys
            user.pop('password', None)
            return jsonify(user), 200
    finally:
        conn.close()

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            affected = cursor.rowcount
            conn.commit()
            if affected > 0:
                return jsonify({"message": "User deleted"}), 200
        return jsonify({"error": "User not found"}), 404
    finally:
        conn.close()

# ─────────────────────────────────────────────
# INQUIRIES ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/inquiries', methods=['GET', 'POST'])
def handle_inquiries():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            i = request.json
            inq_id = f"inq{int(datetime.now().timestamp() * 1000)}"
            created_at = datetime.now().isoformat()
            
            with conn.cursor() as cursor:
                sql = """INSERT INTO inquiries (id, projectId, projectName, sellerId, sellerName, 
                         userId, userName, email, phone, message, status, createdAt) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (
                    inq_id, i.get('projectId'), i.get('projectName'), i.get('sellerId'),
                    i.get('sellerName'), i.get('userId'), i.get('userName'), i.get('email'),
                    i.get('phone'), i.get('message'), 'pending', created_at
                ))
                conn.commit()
            i['id'] = inq_id
            i['createdAt'] = created_at
            i['status'] = 'pending'
            return jsonify(i), 201
            
        # GET
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM inquiries")
            inquiries = cursor.fetchall()
            return jsonify(inquiries)
    finally:
        conn.close()

@app.route('/api/inquiries/<inquiry_id>', methods=['PUT'])
def update_inquiry(inquiry_id):
    updates = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            if not set_clause:
                return jsonify({"error": "No update fields provided"}), 400
            sql = f"UPDATE inquiries SET {set_clause} WHERE id = %s"
            params = list(updates.values()) + [inquiry_id]
            cursor.execute(sql, params)
            conn.commit()
            
            # Fetch updated
            cursor.execute("SELECT * FROM inquiries WHERE id = %s", (inquiry_id,))
            inq = cursor.fetchone()
            return jsonify(inq)
    finally:
        conn.close()

# Run the server
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

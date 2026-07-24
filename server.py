# -*- coding: utf-8 -*-
# Core Python Flask Server for Noi That Bao Khang
# Built with Flask + MS SQL Server (pymssql)

import os
import sys
import math
from hashlib import sha256
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import pymssql
from mail_helper import send_order_notification_email, format_price, EMAIL_RECEIVER, HOTLINE_DISPLAY, OFFICE_ADDRESS

app = Flask(__name__)
app.secret_key = 'noithatbaokhang_secret_key_9988'

# Database Configuration
DB_HOST = "127.0.0.1"
DB_PORT = "1433"
DB_USER = "sa"
DB_PASS = "ntBK01011227"
DB_NAME = "noithatbaokhang_db"

# Brand constants
BRAND_NAME = "Nội Thất Bảo Khang"
HOTLINE = "0903979525"
ZALO_LINK = "https://zalo.me/0903979525"
FACEBOOK_LINK = "https://www.facebook.com/noithatbaokhanghcm"
FACTORY_ADDRESS = "Xuân Thới Thượng, Hóc Môn, TP.HCM"
STANDARD_DESCRIPTION = "Sản phẩm nội thất cao cấp Bảo Khang, thiết kế hiện đại, chất liệu bền bỉ, bảo hành chính hãng, hỗ trợ vận chuyển và lắp đặt tận nơi."

# Setup uploads directory
UPLOAD_FOLDER = 'data/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# DB Connection Helper
def get_db_connection(database_name=DB_NAME):
    return pymssql.connect(
        server=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=database_name,
        autocommit=True
    )

# Dynamic Logo Path Finder
@app.context_processor
def utility_processor():
    def get_logo_path():
        dirs = ['logo ', 'logo']
        for d in dirs:
            path = os.path.join(app.root_path, d)
            if os.path.isdir(path):
                files = os.listdir(path)
                for f in files:
                    ext = f.split('.')[-1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        return f"{d}/{f}"
        return 'logo /Picture1.jpg'  # Default fallback
        
    return dict(
        format_price=format_price,
        get_logo_path=get_logo_path,
        brand_name=BRAND_NAME,
        hotline=HOTLINE,
        hotline_display=HOTLINE_DISPLAY,
        zalo_link=ZALO_LINK,
        facebook_link=FACEBOOK_LINK,
        factory_address=FACTORY_ADDRESS,
        office_address=OFFICE_ADDRESS,
        standard_description=STANDARD_DESCRIPTION
    )

# 1. Database and Tables Initialization
def init_database():
    print("Connecting to SQL Server to verify database schema...")
    try:
        # Connect to master first to check/create database
        conn = pymssql.connect(
            server=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database='master',
            autocommit=True
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT database_id FROM sys.databases WHERE name = %s", (DB_NAME,))
        if not cursor.fetchone():
            print(f"Database '{DB_NAME}' does not exist. Creating...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
        conn.close()

        # Connect to the actual database and create tables
        conn = get_db_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Users]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[Users] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [username] NVARCHAR(50) NOT NULL UNIQUE,
                [password] NVARCHAR(255) NOT NULL,
                [fullname] NVARCHAR(100) DEFAULT NULL,
                [phone] NVARCHAR(20) DEFAULT NULL,
                [role] NVARCHAR(20) DEFAULT N'customer',
                [created_at] DATETIME DEFAULT GETDATE()
            )
        END
        """)

        # Categories table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Categories]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[Categories] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [name] NVARCHAR(100) NOT NULL,
                [slug] NVARCHAR(100) NOT NULL UNIQUE,
                [parent_id] INT DEFAULT NULL,
                FOREIGN KEY ([parent_id]) REFERENCES [dbo].[Categories] ([id])
            )
        END
        """)

        # Products table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Products]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[Products] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [code] NVARCHAR(50) NOT NULL UNIQUE,
                [name] NVARCHAR(150) NOT NULL,
                [category_id] INT DEFAULT NULL,
                [price_text] NVARCHAR(100) DEFAULT NULL,
                [original_price] DECIMAL(15, 2) DEFAULT NULL,
                [sale_price] DECIMAL(15, 2) DEFAULT NULL,
                [description] NVARCHAR(MAX) DEFAULT NULL,
                [is_sale] TINYINT DEFAULT 0,
                [created_at] DATETIME DEFAULT GETDATE(),
                FOREIGN KEY ([category_id]) REFERENCES [dbo].[Categories] ([id]) ON DELETE SET NULL
            )
        END
        """)

        # ProductImages table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ProductImages]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[ProductImages] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [product_id] INT NOT NULL,
                [image_path] NVARCHAR(255) NOT NULL,
                FOREIGN KEY ([product_id]) REFERENCES [dbo].[Products] ([id]) ON DELETE CASCADE
            )
        END
        """)

        # Orders table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Orders]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[Orders] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [customer_name] NVARCHAR(100) NOT NULL,
                [customer_phone] NVARCHAR(20) NOT NULL,
                [customer_address] NVARCHAR(MAX) NOT NULL,
                [note] NVARCHAR(MAX) DEFAULT NULL,
                [total_amount] DECIMAL(15, 2) DEFAULT 0.00,
                [status] NVARCHAR(50) DEFAULT N'pending',
                [created_at] DATETIME DEFAULT GETDATE()
            )
        END
        """)

        # OrderItems table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[OrderItems]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[OrderItems] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [order_id] INT NOT NULL,
                [product_id] INT NOT NULL,
                [quantity] INT DEFAULT 1,
                FOREIGN KEY ([order_id]) REFERENCES [dbo].[Orders] ([id]) ON DELETE CASCADE,
                FOREIGN KEY ([product_id]) REFERENCES [dbo].[Products] ([id]) ON DELETE CASCADE
            )
        END
        """)

        # ChatMessages table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[chat_messages]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[chat_messages] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [session_id] NVARCHAR(100) NOT NULL,
                [sender_type] NVARCHAR(20) NOT NULL CHECK ([sender_type] IN ('customer', 'admin')),
                [sender_name] NVARCHAR(100) DEFAULT NULL,
                [message] NVARCHAR(MAX) NOT NULL,
                [is_read] TINYINT DEFAULT 0,
                [message_type] NVARCHAR(20) DEFAULT 'text' CHECK ([message_type] IN ('text', 'image')),
                [image_url] NVARCHAR(255) DEFAULT NULL,
                [created_at] DATETIME DEFAULT GETDATE()
            )
        END
        """)

        # Database migrations for existing ChatMessages tables
        cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE object_id = OBJECT_ID(N'[dbo].[chat_messages]') AND name = 'message_type'
        )
        BEGIN
            ALTER TABLE [dbo].[chat_messages] ADD [message_type] NVARCHAR(20) DEFAULT 'text';
        END
        """)
        cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE object_id = OBJECT_ID(N'[dbo].[chat_messages]') AND name = 'image_url'
        )
        BEGIN
            ALTER TABLE [dbo].[chat_messages] ADD [image_url] NVARCHAR(255) DEFAULT NULL;
        END
        """)

        # ChatMessages index
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_chat_messages_session' AND object_id = OBJECT_ID(N'[dbo].[chat_messages]'))
        BEGIN
            CREATE INDEX IX_chat_messages_session ON [dbo].[chat_messages] (session_id)
        END
        """)

        # Create default Admin if not exists
        cursor.execute("SELECT id FROM Users WHERE username = %s", ('admin',))
        if not cursor.fetchone():
            print("Creating default admin account...")
            hashed_pass = sha256('admin123'.encode('utf-8')).hexdigest()
            cursor.execute(
                "INSERT INTO Users (username, password, fullname, phone, role) VALUES (%s, %s, %s, %s, %s)",
                ('admin', hashed_pass, 'Quản trị viên', '0903979525', 'admin')
            )

        conn.close()
        print("Database schemas initialized.")
    except Exception as e:
        print(f"Error initializing DB: {e}", file=sys.stderr)

# 2. Scanning and Seeding Products
def run_import_seeding():
    print("Running automated scanning of 'data/' directory...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if products already exist to avoid duplicate seeding
    cursor.execute("SELECT COUNT(*) FROM Products")
    prod_count = cursor.fetchone()[0]
    if prod_count > 0:
        print("Products table already has data. Skipping auto import.")
        conn.close()
        return

    # Helper: Insert Category
    category_ids = {}
    categories_list = [
        # Office Furniture
        ('Nội thất văn phòng', 'noi-that-van-phong', None),
        ('Bàn văn phòng', 'ban-van-phong', 'noi-that-van-phong'),
        ('Ghế văn phòng', 'ghe-van-phong', 'noi-that-van-phong'),
        ('Tủ văn phòng', 'tu-van-phong', 'noi-that-van-phong'),
        # Home Furniture
        ('Nội thất gia đình', 'noi-that-gia-dinh', None),
        ('Bàn học sinh', 'ban-hoc-sinh', 'noi-that-gia-dinh'),
        ('Bộ giường tủ', 'bo-giuong-tu', 'noi-that-gia-dinh'),
        ('Kệ vách tivi', 'ke-vach-tivi', 'noi-that-gia-dinh'),
        ('Phòng bếp', 'phong-bep', 'noi-that-gia-dinh'),
        ('Giường tầng', 'giuong-tang', 'noi-that-gia-dinh')
    ]

    # Insert parents
    for name, slug, parent_slug in categories_list:
        if parent_slug is None:
            cursor.execute("SELECT id FROM Categories WHERE slug = %s", (slug,))
            row = cursor.fetchone()
            if row:
                category_ids[slug] = row[0]
            else:
                cursor.execute("INSERT INTO Categories (name, slug, parent_id) VALUES (%s, %s, NULL)", (name, slug))
                cursor.execute("SELECT @@IDENTITY")
                category_ids[slug] = int(cursor.fetchone()[0])

    # Insert children
    for name, slug, parent_slug in categories_list:
        if parent_slug is not None:
            cursor.execute("SELECT id FROM Categories WHERE slug = %s", (slug,))
            row = cursor.fetchone()
            if row:
                category_ids[slug] = row[0]
            else:
                p_id = category_ids[parent_slug]
                cursor.execute("INSERT INTO Categories (name, slug, parent_id) VALUES (%s, %s, %s)", (name, slug, p_id))
                cursor.execute("SELECT @@IDENTITY")
                category_ids[slug] = int(cursor.fetchone()[0])

    counters = {'BVP': 1, 'GVP': 1, 'TVP': 1, 'BHS': 1, 'BGT': 1, 'KTV': 1, 'PB': 1, 'GT': 1}

    def insert_prod(code, name, cat_id, price_txt, orig, sale, desc, is_sale):
        cursor.execute("INSERT INTO Products (code, name, category_id, price_text, original_price, sale_price, description, is_sale) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       (code, name, cat_id, price_txt, orig, sale, desc, is_sale))
        cursor.execute("SELECT @@IDENTITY")
        return int(cursor.fetchone()[0])

    def insert_img(prod_id, path):
        cursor.execute("INSERT INTO ProductImages (product_id, image_path) VALUES (%s, %s)", (prod_id, path))

    # Folders scanner
    base_dir = os.path.join(app.root_path, 'data')
    if not os.path.isdir(base_dir):
        print(f"Data directory '{base_dir}' not found.")
        conn.close()
        return

    # List of categories to scan
    scan_configs = [
        ('banvanphong', 'BVP', 'ban-van-phong', 'single', 'Bàn văn phòng'),
        ('ghevanphong', 'GVP', 'ghe-van-phong', 'single', 'Ghế văn phòng'),
        ('tuvanphong/tu1hinh', 'TVP', 'tu-van-phong', 'single', 'Tủ văn phòng'),
        ('tuvanphong/tunhieuhinh', 'TVP', 'tu-van-phong', 'multiple', 'Tủ văn phòng'),
        ('tuvanphong/tusale', 'TVP', 'tu-van-phong', 'sale', 'Tủ văn phòng Khuyến mãi'),
        ('banhocsinh', 'BHS', 'ban-hoc-sinh', 'single', 'Bàn học sinh'),
        ('bogiuongtu', 'BGT', 'bo-giuong-tu', 'single', 'Bộ giường tủ cao cấp'),
        ('kevachtivi', 'KTV', 'ke-vach-tivi', 'single', 'Kệ vách tivi'),
        ('phongbep', 'PB', 'phong-bep', 'single', 'Nội thất phòng bếp'),
        ('giuongtang', 'GT', 'giuong-tang', 'multiple', 'Giường tầng đa năng')
    ]

    for rel_path, prefix, cat_slug, structure_type, name_prefix in scan_configs:
        folder_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        cat_id = category_ids.get(cat_slug)
        if not cat_id or not os.path.isdir(folder_path):
            continue

        imported = 0
        if structure_type == 'single' or structure_type == 'sale':
            files = sorted(os.listdir(folder_path))
            for f in files:
                ext = f.split('.')[-1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    code = f"{prefix}{counters[prefix]:03d}"
                    counters[prefix] += 1
                    
                    price_txt = f"Liên hệ Hotline / Zalo: {HOTLINE_DISPLAY}"
                    orig_p, sale_p, is_s = None, None, 0
                    
                    if structure_type == 'sale':
                        price_txt = None
                        orig_p, sale_p, is_s = 4800000, 3800000, 1

                    p_id = insert_prod(code, f"{name_prefix} {code}", cat_id, price_txt, orig_p, sale_p, STANDARD_DESCRIPTION, is_s)
                    insert_img(p_id, f"data/{rel_path}/{f}")
                    imported += 1

        elif structure_type == 'multiple':
            subdirs = sorted(os.listdir(folder_path))
            for sub in subdirs:
                sub_path = os.path.join(folder_path, sub)
                if os.path.isdir(sub_path):
                    code = f"{prefix}{counters[prefix]:03d}"
                    counters[prefix] += 1
                    
                    p_id = insert_prod(code, f"{name_prefix} {code}", cat_id, f"Liên hệ Hotline / Zalo: {HOTLINE_DISPLAY}", None, None, STANDARD_DESCRIPTION, 0)
                    
                    # Scan all files inside subdirectory
                    subfiles = sorted(os.listdir(sub_path))
                    for f in subfiles:
                        ext = f.split('.')[-1].lower()
                        if ext in ALLOWED_EXTENSIONS:
                            insert_img(p_id, f"data/{rel_path}/{sub}/{f}")
                    imported += 1
                    
        print(f"Scanned 'data/{rel_path}': Imported {imported} products.")

    conn.close()
    print("Database seeding completed successfully.")

# 3. Dynamic Sidebar Navigation Category Fetch
def get_navigation_categories():
    categories = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get parents
        cursor.execute("SELECT id, name, slug FROM Categories WHERE parent_id IS NULL")
        parents = cursor.fetchall()
        for p_id, p_name, p_slug in parents:
            cursor.execute("SELECT id, name, slug FROM Categories WHERE parent_id = %s", (p_id,))
            children = [{"id": r[0], "name": r[1], "slug": r[2]} for r in cursor.fetchall()]
            categories.append({
                "id": p_id,
                "name": p_name,
                "slug": p_slug,
                "children": children
            })
        conn.close()
    except Exception:
        pass
    return categories

# Register Navigation helper on template load
@app.context_processor
def inject_nav_categories():
    return dict(nav_categories=get_navigation_categories())

# Helper: Retrieve Cart count
def get_cart_count():
    count = 0
    if 'cart' in session:
        for item in session['cart'].values():
            count += item['quantity']
    return count

@app.context_processor
def inject_cart_count():
    return dict(cart_count=get_cart_count())

# --- FRONTEND ROUTING ---

# Route: Index/Homepage
@app.route('/')
def index():
    sale_products = []
    latest_products = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        
        # 1. Fetch sale products
        cursor.execute("""
            SELECT p.*, (SELECT TOP 1 image_path FROM ProductImages WHERE product_id = p.id) as image_path 
            FROM Products p 
            WHERE p.is_sale = 1 
            ORDER BY p.id DESC
        """)
        sale_products = cursor.fetchall()[:4]

        # 2. Fetch latest products
        cursor.execute("""
            SELECT p.*, (SELECT TOP 1 image_path FROM ProductImages WHERE product_id = p.id) as image_path 
            FROM Products p 
            WHERE p.is_sale = 0 
            ORDER BY p.id DESC
        """)
        latest_products = cursor.fetchall()[:8]
        conn.close()
    except Exception as e:
        print(f"Error fetching home prods: {e}", file=sys.stderr)
        
    return render_template('index.html', sale_products=sale_products, latest_products=latest_products)

def make_pagination(current_page, total_pages):
    pages = []
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
        
    pages.append(1)
    if current_page > 3:
        pages.append('...')
        
    start = max(2, current_page - 1)
    end = min(total_pages - 1, current_page + 1)
    
    if current_page <= 3:
        end = 4
    if current_page >= total_pages - 2:
        start = total_pages - 3
        
    for p in range(start, end + 1):
        if p not in pages:
            pages.append(p)
            
    if current_page < total_pages - 2:
        pages.append('...')
        
    if total_pages not in pages:
        pages.append(total_pages)
        
    return pages

# Route: Catalog Browsing
@app.route('/category')
def category():
    page = request.args.get('page', 1, type=int)
    if page < 1: page = 1
    limit = 12
    
    slug = request.args.get('slug', '').strip()
    is_sale_filter = request.args.get('sale', 0, type=int) == 1
    search_query = request.args.get('search', '').strip()
    
    where_clauses = []
    params = []
    
    if is_sale_filter:
        where_clauses.append("p.is_sale = 1")
        
    current_category = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        
        if slug:
            cursor.execute("SELECT * FROM Categories WHERE slug = %s", (slug,))
            current_category = cursor.fetchone()
            if current_category:
                if current_category['parent_id'] is None:
                    # Parent category: fetch children ids
                    cursor.execute("SELECT id FROM Categories WHERE parent_id = %s", (current_category['id'],))
                    child_ids = [r['id'] for r in cursor.fetchall()]
                    cat_ids = [current_category['id']] + child_ids
                    
                    placeholders = ",".join(["%s"] * len(cat_ids))
                    where_clauses.append(f"p.category_id IN ({placeholders})")
                    params.extend(cat_ids)
                else:
                    where_clauses.append("p.category_id = %s")
                    params.append(current_category['id'])
                    
        if search_query:
            where_clauses.append("(p.name LIKE %s OR p.code LIKE %s)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])
            
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
        # Count total
        count_sql = f"SELECT COUNT(*) as cnt FROM Products p {where_sql}"
        cursor.execute(count_sql, tuple(params))
        total_rows = cursor.fetchone()['cnt']
        
        total_pages = int(math.ceil(total_rows / limit))
        if total_pages < 1: total_pages = 1
        if page > total_pages: page = total_pages
        offset = (page - 1) * limit
        
        # Fetch items
        # To handle OFFSET in SQL Server, we can use ROW_NUMBER or OFFSET FETCH (SQL Server 2012+)
        select_sql = f"""
            SELECT p.*, c.name as category_name,
                   (SELECT TOP 1 image_path FROM ProductImages WHERE product_id = p.id) as image_path
            FROM Products p
            LEFT JOIN Categories c ON p.category_id = c.id
            {where_sql}
            ORDER BY p.id DESC
            OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
        """
        cursor.execute(select_sql, tuple(params))
        products = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error category listing: {e}", file=sys.stderr)
        products = []
        total_rows = 0
        total_pages = 1
        
    filter_text = "Tất cả sản phẩm"
    if is_sale_filter:
        filter_text = "Sản phẩm khuyến mãi"
    elif current_category:
        filter_text = current_category['name']
    if search_query:
        filter_text += f" (Tìm kiếm: \"{search_query}\")"
        
    pages = make_pagination(page, total_pages)
    return render_template('category.html', products=products, current_category=current_category, slug=slug,
                           sale=is_sale_filter, search=search_query, total_rows=total_rows, page=page,
                           total_pages=total_pages, pages=pages, filter_text=filter_text)

# Route: Product Details
@app.route('/product/<int:product_id>')
def detail(product_id):
    product = None
    images = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT p.*, c.name as category_name, c.slug as category_slug 
            FROM Products p 
            LEFT JOIN Categories c ON p.category_id = c.id 
            WHERE p.id = %s
        """, (product_id,))
        product = cursor.fetchone()
        
        if product:
            cursor.execute("SELECT * FROM ProductImages WHERE product_id = %s", (product_id,))
            images = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error details: {e}", file=sys.stderr)
        
    if not product:
        flash("Sản phẩm không tồn tại.", "error")
        return redirect(url_for('index'))
        
    return render_template('detail.html', product=product, images=images)

# --- CART MANAGEMENT ---

@app.route('/cart')
def cart_view():
    return render_template('cart.html')

@app.route('/cart/add')
def cart_add():
    p_id = request.args.get('id', type=int)
    qty = request.args.get('qty', 1, type=int)
    if qty < 1: qty = 1
    
    if p_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT p.*, (SELECT TOP 1 image_path FROM ProductImages WHERE product_id = p.id) as image_path 
                FROM Products p 
                WHERE p.id = %s
            """, (p_id,))
            product = cursor.fetchone()
            conn.close()
            
            if product:
                if 'cart' not in session:
                    session['cart'] = {}
                
                # Convert keys to string for JSON serialization safety in sessions
                str_id = str(p_id)
                price = float(product['sale_price']) if product['is_sale'] else 0
                
                if str_id in session['cart']:
                    session['cart'][str_id]['quantity'] += qty
                else:
                    session['cart'][str_id] = {
                        'id': product['id'],
                        'code': product['code'],
                        'name': product['name'],
                        'price': price,
                        'price_text': product['price_text'],
                        'image_path': product['image_path'],
                        'is_sale': bool(product['is_sale']),
                        'quantity': qty
                    }
                session.modified = True
                flash("Đã thêm sản phẩm vào giỏ hàng.", "success")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
            
    return redirect(url_for('cart_view'))

@app.route('/cart/update', methods=['POST'])
def cart_update():
    if 'cart' in session:
        quantities = request.form.getlist('quantities')
        for key in list(session['cart'].keys()):
            qty_val = request.form.get(f"quantities[{key}]", type=int)
            if qty_val is not None:
                if qty_val <= 0:
                    session['cart'].pop(key)
                else:
                    session['cart'][key]['quantity'] = qty_val
        session.modified = True
        flash("Đã cập nhật giỏ hàng.", "success")
    return redirect(url_for('cart_view'))

@app.route('/cart/delete/<int:product_id>')
def cart_delete(product_id):
    if 'cart' in session:
        str_id = str(product_id)
        if str_id in session['cart']:
            session['cart'].pop(str_id)
            session.modified = True
            flash("Đã xóa sản phẩm khỏi giỏ hàng.", "success")
    return redirect(url_for('cart_view'))

@app.route('/cart/clear')
def cart_clear():
    session['cart'] = {}
    session.modified = True
    flash("Đã xóa toàn bộ giỏ hàng.", "success")
    return redirect(url_for('cart_view'))

# --- CHECKOUT & ORDERING ---

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    action = request.args.get('action', '')
    success_order = None
    
    # Check for POST checkout action
    if request.method == 'POST':
        # Quick Order flow
        if action == 'quick_order':
            p_id = request.form.get('product_id', type=int)
            customer_name = request.form.get('customer_name', '').strip()
            customer_phone = request.form.get('customer_phone', '').strip()
            customer_address = request.form.get('customer_address', '').strip()
            note = request.form.get('note', '').strip()
            
            if not customer_name or not customer_phone or not customer_address:
                flash("Vui lòng nhập đầy đủ các thông tin bắt buộc.", "error")
                return redirect(url_for('detail', product_id=p_id))
                
            try:
                conn = get_db_connection()
                cursor = conn.cursor(as_dict=True)
                cursor.execute("SELECT * FROM Products WHERE id = %s", (p_id,))
                product = cursor.fetchone()
                
                if not product:
                    conn.close()
                    flash("Sản phẩm không tồn tại.", "error")
                    return redirect(url_for('index'))
                    
                total_amount = float(product['sale_price']) if product['is_sale'] else 0
                
                # Transaction to insert
                cursor.execute("INSERT INTO Orders (customer_name, customer_phone, customer_address, note, total_amount, status) VALUES (%s, %s, %s, %s, %s, N'pending')",
                               (customer_name, customer_phone, customer_address, note, total_amount))
                cursor.execute("SELECT @@IDENTITY")
                order_id = int(cursor.fetchone()[0])
                
                cursor.execute("INSERT INTO OrderItems (order_id, product_id, quantity) VALUES (%s, %s, 1)", (order_id, p_id))
                
                conn.close()
                
                # Send email
                order_details = {'id': order_id, 'customer_name': customer_name, 'customer_phone': customer_phone, 'customer_address': customer_address, 'note': note}
                items = [{
                    'code': product['code'],
                    'name': product['name'],
                    'quantity': 1,
                    'sale_price': product['sale_price'],
                    'original_price': product['original_price'],
                    'price_text': product['price_text']
                }]
                send_order_notification_email(order_details, items)
                success_order = order_id
                
            except Exception as e:
                flash(f"Lỗi đặt hàng nhanh: {e}", "error")
                return redirect(url_for('detail', product_id=p_id))
                
        # Full Cart Order flow
        elif action == 'place_order':
            if 'cart' not in session or not session['cart']:
                return redirect(url_for('cart_view'))
                
            customer_name = request.form.get('customer_name', '').strip()
            customer_phone = request.form.get('customer_phone', '').strip()
            customer_address = request.form.get('customer_address', '').strip()
            note = request.form.get('note', '').strip()
            
            if not customer_name or not customer_phone or not customer_address:
                flash("Vui lòng nhập đầy đủ các thông tin bắt buộc.", "error")
                return render_template('checkout.html')
                
            try:
                total_amount = 0
                items = []
                for item in session['cart'].values():
                    if item['is_sale']:
                        total_amount += float(item['price']) * int(item['quantity'])
                    items.append(item)
                    
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Orders (customer_name, customer_phone, customer_address, note, total_amount, status) VALUES (%s, %s, %s, %s, %s, N'pending')",
                               (customer_name, customer_phone, customer_address, note, total_amount))
                cursor.execute("SELECT @@IDENTITY")
                order_id = int(cursor.fetchone()[0])
                
                for item in session['cart'].values():
                    cursor.execute("INSERT INTO OrderItems (order_id, product_id, quantity) VALUES (%s, %s, %s)",
                                   (order_id, item['id'], item['quantity']))
                                   
                conn.close()
                
                # Send email
                order_details = {'id': order_id, 'customer_name': customer_name, 'customer_phone': customer_phone, 'customer_address': customer_address, 'note': note}
                send_order_notification_email(order_details, items)
                
                session.pop('cart', None)
                success_order = order_id
                
            except Exception as e:
                flash(f"Lỗi gửi đặt hàng: {e}", "error")
                return render_template('checkout.html')
                
    return render_template('checkout.html', success_order=success_order)

# --- USER AUTHENTICATION ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        phone = request.form.get('phone', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not fullname or not phone or not username or not password:
            flash("Vui lòng nhập đầy đủ thông tin bắt buộc (*).", "error")
        elif password != confirm_password:
            flash("Mật khẩu xác nhận không khớp.", "error")
        elif len(password) < 6:
            flash("Mật khẩu phải dài từ 6 ký tự.", "error")
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM Users WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash("Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.", "error")
                else:
                    hashed = sha256(password.encode('utf-8')).hexdigest()
                    cursor.execute(
                        "INSERT INTO Users (username, password, fullname, phone, role) VALUES (%s, %s, %s, %s, N'customer')",
                        (username, hashed, fullname, phone)
                    )
                    flash("Đăng ký tài khoản thành công! Mời bạn đăng nhập.", "success")
                    conn.close()
                    return redirect(url_for('login'))
                conn.close()
            except Exception as e:
                flash(f"Lỗi đăng ký: {e}", "error")
                
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session.get('is_admin') else 'index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash("Vui lòng điền tên đăng nhập và mật khẩu.", "error")
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(as_dict=True)
                hashed = sha256(password.encode('utf-8')).hexdigest()
                cursor.execute("SELECT * FROM Users WHERE username = %s AND password = %s", (username, hashed))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['user_fullname'] = user['fullname']
                    session['user_phone'] = user['phone']
                    session['is_admin'] = (user['role'] == 'admin')
                    
                    flash(f"Đăng nhập thành công. Xin chào {user['fullname']}!", "success")
                    if user['role'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('index'))
                else:
                    flash("Tên đăng nhập hoặc mật khẩu không chính xác.", "error")
            except Exception as e:
                flash(f"Lỗi đăng nhập: {e}", "error")
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất thành công.", "success")
    return redirect(url_for('index'))

# --- ADMIN PANEL ROUTING ---

# Guard helper
def check_admin_auth():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Bạn không có quyền truy cập trang quản trị.", "error")
        return False
    return True

@app.route('/admin')
def admin_dashboard():
    if not check_admin_auth(): return redirect(url_for('login'))
    
    recent_orders = []
    count_orders, count_products, count_users = 0, 0, 0
    total_revenue = 0
    count_pending, count_completed = 0, 0
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Recent orders
        cursor.execute("SELECT TOP 5 * FROM Orders ORDER BY id DESC")
        recent_orders = cursor.fetchall()
        
        # Summary counts
        cursor.execute("SELECT COUNT(*) as cnt FROM Orders")
        count_orders = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM Products")
        count_products = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM Users")
        count_users = cursor.fetchone()['cnt']
        
        # Revenue
        cursor.execute("SELECT SUM(total_amount) as rev FROM Orders WHERE status = N'completed'")
        total_revenue = cursor.fetchone()['rev'] or 0
        
        # States counts
        cursor.execute("SELECT COUNT(*) as cnt FROM Orders WHERE status = N'pending'")
        count_pending = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM Orders WHERE status = N'completed'")
        count_completed = cursor.fetchone()['cnt']
        
        conn.close()
    except Exception as e:
        print(f"Admin Dashboard Error: {e}", file=sys.stderr)
        
    return render_template('admin_index.html', recent_orders=recent_orders, count_orders=count_orders,
                           count_products=count_products, count_users=count_users, total_revenue=total_revenue,
                           count_pending=count_pending, count_completed=count_completed)

@app.route('/admin/orders', methods=['GET', 'POST'])
def admin_orders():
    if not check_admin_auth(): return redirect(url_for('login'))
    
    action = request.args.get('action', '')
    
    # Handle order operations
    if request.method == 'POST' and action == 'update_status':
        o_id = request.form.get('order_id', type=int)
        status = request.form.get('status', '').strip()
        if o_id and status in ['pending', 'processing', 'completed', 'cancelled']:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE Orders SET status = %s WHERE id = %s", (status, o_id))
                conn.close()
                flash(f"Đã cập nhật trạng thái đơn hàng #{o_id} thành công.", "success")
            except Exception as e:
                flash(f"Lỗi cập nhật: {e}", "error")
        return redirect(url_for('admin_orders'))
        
    if action == 'delete':
        o_id = request.args.get('id', type=int)
        if o_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Orders WHERE id = %s", (o_id,))
                conn.close()
                flash(f"Đã xóa đơn hàng #{o_id} khỏi hệ thống.", "success")
            except Exception as e:
                flash(f"Lỗi xóa đơn hàng: {e}", "error")
        return redirect(url_for('admin_orders'))

    # Load orders
    orders = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute("SELECT * FROM Orders ORDER BY id DESC")
        orders = cursor.fetchall()
        
        for ord in orders:
            cursor.execute("""
                SELECT oi.quantity, p.code, p.name, p.is_sale, p.sale_price, p.original_price, p.price_text
                FROM OrderItems oi
                LEFT JOIN Products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (ord['id'],))
            ord['items'] = cursor.fetchall()
        conn.close()
    except Exception as e:
        flash(f"Lỗi tải đơn hàng: {e}", "error")
        
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    if not check_admin_auth(): return redirect(url_for('login'))
    
    action = request.args.get('action', '')
    
    # 1. Handle delete product
    if action == 'delete':
        p_id = request.args.get('id', type=int)
        if p_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(as_dict=True)
                # Fetch paths to delete physical files
                cursor.execute("SELECT image_path FROM ProductImages WHERE product_id = %s", (p_id,))
                imgs = cursor.fetchall()
                
                cursor.execute("DELETE FROM Products WHERE id = %s", (p_id,))
                conn.close()
                
                for im in imgs:
                    filepath = os.path.join(app.root_path, im['image_path'])
                    if 'data/uploads/' in im['image_path'] and os.path.exists(filepath):
                        try: os.unlink(filepath)
                        except Exception: pass
                        
                flash("Đã xóa sản phẩm thành công.", "success")
            except Exception as e:
                flash(f"Lỗi xóa sản phẩm: {e}", "error")
        return redirect(url_for('admin_products'))

    # 2. Handle add product
    if request.method == 'POST' and action == 'add':
        code = request.form.get('code', '').strip()
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        price_type = request.form.get('price_type', 'contact')
        
        price_text = None
        original_price = None
        sale_price = None
        is_sale = 0
        
        if price_type == 'contact':
            price_text = f"Liên hệ Hotline / Zalo: {HOTLINE_DISPLAY}"
        else:
            try:
                original_price = float(request.form.get('original_price', '0').replace('.', ''))
                sale_price = float(request.form.get('sale_price', '0').replace('.', ''))
                is_sale = 1 if request.form.get('is_sale') else 0
            except ValueError:
                flash("Vui lòng nhập định dạng số tiền hợp lệ.", "error")
                return redirect(url_for('admin_products', action='add_new'))

        description = request.form.get('description', '').strip() or STANDARD_DESCRIPTION
        
        if not code or not name or not category_id:
            flash("Vui lòng nhập đầy đủ các thông tin bắt buộc (*).", "error")
            return redirect(url_for('admin_products', action='add_new'))
            
        uploaded_files = request.files.getlist('images')
        if not uploaded_files or not uploaded_files[0].filename:
            flash("Vui lòng chọn hình ảnh sản phẩm để tải lên.", "error")
            return redirect(url_for('admin_products', action='add_new'))
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check code uniqueness
            cursor.execute("SELECT id FROM Products WHERE code = %s", (code,))
            if cursor.fetchone():
                flash("Mã sản phẩm đã tồn tại. Hãy dùng mã khác.", "error")
                conn.close()
                return redirect(url_for('admin_products', action='add_new'))
                
            cursor.execute("INSERT INTO Products (code, name, category_id, price_text, original_price, sale_price, description, is_sale) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (code, name, category_id, price_text, original_price, sale_price, description, is_sale))
            cursor.execute("SELECT @@IDENTITY")
            product_id = int(cursor.fetchone()[0])
            
            # Save files
            uploaded_count = 0
            uploads_dir = os.path.join(app.root_path, UPLOAD_FOLDER)
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
                
            for file in uploaded_files:
                if file and allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    sec_name = f"{code}_{uploaded_count + 1}_{int(product_id)}.{ext}"
                    filepath = os.path.join(uploads_dir, sec_name)
                    file.save(filepath)
                    
                    db_path = f"data/uploads/{sec_name}"
                    cursor.execute("INSERT INTO ProductImages (product_id, image_path) VALUES (%s, %s)", (product_id, db_path))
                    uploaded_count += 1
                    
            conn.close()
            flash(f"Đã thêm sản phẩm {code} thành công với {uploaded_count} ảnh.", "success")
            return redirect(url_for('admin_products'))
        except Exception as e:
            flash(f"Lỗi thêm sản phẩm: {e}", "error")
            return redirect(url_for('admin_products', action='add_new'))

    # Load resources
    products = []
    categories = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        # Fetch prods
        cursor.execute("""
            SELECT p.*, c.name as category_name,
                   (SELECT TOP 1 image_path FROM ProductImages WHERE product_id = p.id) as image_path
            FROM Products p
            LEFT JOIN Categories c ON p.category_id = c.id
            ORDER BY p.id DESC
        """)
        products = cursor.fetchall()
        
        # Fetch child categories for selector
        cursor.execute("""
            SELECT c.*, p.name as parent_name
            FROM Categories c
            LEFT JOIN Categories p ON c.parent_id = p.id
            WHERE c.parent_id IS NOT NULL
            ORDER BY parent_name, c.name
        """)
        categories = cursor.fetchall()
        conn.close()
    except Exception as e:
        flash(f"Lỗi tải danh sách: {e}", "error")
        
    return render_template('admin_products.html', products=products, categories=categories, action=action)

@app.route('/admin/users')
def admin_users():
    if not check_admin_auth(): return redirect(url_for('login'))
    
    users = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute("SELECT id, username, fullname, phone, role, created_at FROM Users ORDER BY id ASC")
        users = cursor.fetchall()
        conn.close()
    except Exception as e:
        flash(f"Lỗi tải danh sách: {e}", "error")
        
    return render_template('admin_users.html', users=users)

# --- LIVE CHAT ENDPOINTS ---

def get_current_chat_session():
    if session.get('user_id'):
        return {
            'session_id': f"user_{session['user_id']}",
            'name': session.get('user_fullname'),
            'phone': session.get('user_phone', ''),
            'is_logged_in': True
        }
    elif session.get('chat_session_id'):
        return {
            'session_id': session['chat_session_id'],
            'name': session.get('chat_customer_name'),
            'phone': session.get('chat_customer_phone', ''),
            'is_logged_in': False
        }
    return None

@app.route('/api/chat/register', methods=['POST'])
def chat_register():
    data = request.json or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    if not name or not phone:
        return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ Họ tên và SĐT'}), 400
    
    import uuid
    session['chat_session_id'] = f"guest_{uuid.uuid4().hex[:12]}"
    session['chat_customer_name'] = name
    session['chat_customer_phone'] = phone
    
    return jsonify({
        'success': True,
        'session_id': session['chat_session_id'],
        'name': name,
        'phone': phone
    })

@app.route('/api/chat/messages', methods=['GET'])
def chat_get_messages():
    session_id = request.args.get('session_id')
    
    if session_id:
        if 'user_id' not in session or not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                UPDATE chat_messages 
                SET is_read = 1 
                WHERE session_id = %s AND sender_type = 'customer' AND is_read = 0
            """, (session_id,))
            
            cursor.execute("""
                SELECT id, session_id, sender_type, sender_name, message, is_read, message_type, image_url, 
                       CONVERT(VARCHAR(19), created_at, 120) as created_at 
                FROM chat_messages 
                WHERE session_id = %s 
                ORDER BY id ASC
            """, (session_id,))
            messages = cursor.fetchall()
            conn.close()
            return jsonify({'success': True, 'messages': messages})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        chat_sess = get_current_chat_session()
        if not chat_sess:
            return jsonify({'success': True, 'messages': []})
            
        my_session_id = chat_sess['session_id']
        try:
            conn = get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                UPDATE chat_messages 
                SET is_read = 1 
                WHERE session_id = %s AND sender_type = 'admin' AND is_read = 0
            """, (my_session_id,))
            
            cursor.execute("""
                SELECT id, session_id, sender_type, sender_name, message, is_read, message_type, image_url, 
                       CONVERT(VARCHAR(19), created_at, 120) as created_at 
                FROM chat_messages 
                WHERE session_id = %s 
                ORDER BY id ASC
            """, (my_session_id,))
            messages = cursor.fetchall()
            conn.close()
            return jsonify({'success': True, 'messages': messages})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/chat/send', methods=['POST'])
def chat_send_message():
    file = None
    if 'file' in request.files:
        file = request.files['file']
    elif 'image' in request.files:
        file = request.files['image']
        
    message_text = ""
    message_type = 'text'
    image_url = None
    
    if file and file.filename != '':
        import os
        import uuid
        import time
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({'success': False, 'message': 'Định dạng file không hỗ trợ. Chỉ cho phép PNG, JPG, JPEG, WEBP, GIF.'}), 400
            
        os.makedirs('uploads/chat', exist_ok=True)
        
        new_filename = f"{uuid.uuid4().hex}_{int(time.time())}.{ext}"
        save_path = os.path.join('uploads/chat', new_filename)
        file.save(save_path)
        
        image_url = f"/uploads/chat/{new_filename}"
        message_type = 'image'
        message_text = request.form.get('message', '').strip() or 'Đã gửi một hình ảnh'
    else:
        if request.is_json:
            data = request.json or {}
            message_text = data.get('message', '').strip()
        else:
            message_text = request.form.get('message', '').strip()
            
    if not message_text and not image_url:
        return jsonify({'success': False, 'message': 'Nội dung tin nhắn trống'}), 400
        
    target_session_id = request.form.get('session_id') or (request.json.get('session_id') if request.is_json else None)
    
    if target_session_id:
        if 'user_id' not in session or not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor(as_dict=True)
            admin_name = session.get('user_fullname', 'Quản trị viên')
            
            cursor.execute("""
                INSERT INTO chat_messages (session_id, sender_type, sender_name, message, is_read, message_type, image_url) 
                VALUES (%s, 'admin', %s, %s, 0, %s, %s)
            """, (target_session_id, admin_name, message_text, message_type, image_url))
            conn.close()
            return jsonify({'success': True, 'message_type': message_type, 'image_url': image_url, 'message': message_text})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        chat_sess = get_current_chat_session()
        if not chat_sess:
            return jsonify({'success': False, 'message': 'Chưa đăng ký phiên chat'}), 400
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                INSERT INTO chat_messages (session_id, sender_type, sender_name, message, is_read, message_type, image_url) 
                VALUES (%s, 'customer', %s, %s, 0, %s, %s)
            """, (chat_sess['session_id'], chat_sess['name'], message_text, message_type, image_url))
            conn.close()
            return jsonify({'success': True, 'message_type': message_type, 'image_url': image_url, 'message': message_text})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/chat/conversations', methods=['GET'])
def chat_get_conversations():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute("""
            WITH LatestMessages AS (
                SELECT 
                    session_id,
                    sender_type,
                    sender_name,
                    message,
                    is_read,
                    message_type,
                    created_at,
                    ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY id DESC) as rn
                FROM chat_messages
            ),
            UnreadCounts AS (
                SELECT 
                    session_id,
                    COUNT(*) as unread_count
                FROM chat_messages
                WHERE sender_type = 'customer' AND is_read = 0
                GROUP BY session_id
            )
            SELECT 
                lm.session_id,
                lm.sender_type,
                lm.sender_name,
                lm.message,
                lm.message_type,
                CONVERT(VARCHAR(19), lm.created_at, 120) as created_at,
                COALESCE(uc.unread_count, 0) as unread_count
            FROM LatestMessages lm
            LEFT JOIN UnreadCounts uc ON lm.session_id = uc.session_id
            WHERE lm.rn = 1
            ORDER BY lm.created_at DESC
        """)
        conversations = cursor.fetchall()
        conn.close()
        return jsonify({'success': True, 'conversations': conversations})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/chat')
def admin_chat():
    if not check_admin_auth(): return redirect(url_for('login'))
    return render_template('admin_chat.html')

# Custom static routes to serve data and logo folders directly from workspace
@app.route('/data/<path:filename>')
def serve_data_files(filename):
    return send_from_directory('data', filename)

@app.route('/logo/<path:filename>')
def serve_logo_files(filename):
    return send_from_directory('logo', filename)

@app.route('/logo /<path:filename>')
def serve_logo_space_files(filename):
    return send_from_directory('logo ', filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory('uploads', filename)


if __name__ == '__main__':
    # Initialize DB schemas on startup
    init_database()
    # Import seeding directories if DB empty
    run_import_seeding()
    
    print("Starting Noi That Bao Khang Flask server...")
    app.run(host='0.0.0.0', port=8000, debug=True)

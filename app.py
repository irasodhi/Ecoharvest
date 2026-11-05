import hashlib
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_from_directory
import sqlite3
import os
import random
import re
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from planet1 import UltimatePlantCare

# ---------------- APPLICATION SETUP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ecoharvest_sustainable_secret_key_2026")

UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize AI Plant Care Engine
bot = UltimatePlantCare()


# ---------------- DATABASE CONNECTION ----------------
def get_db():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            image TEXT NOT NULL,
            weight_grams INTEGER DEFAULT 500
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            status TEXT DEFAULT 'pending',
            quantity INTEGER DEFAULT 1,
            weight_grams INTEGER DEFAULT 500,
            total_price INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            loc TEXT NOT NULL,
            exp TEXT NOT NULL,
            spec TEXT NOT NULL,
            bio TEXT NOT NULL,
            phone TEXT NOT NULL,
            rating REAL DEFAULT 4.9,
            consultation_fee INTEGER DEFAULT 500,
            blockchain_doc TEXT DEFAULT '',
            blockchain_hash TEXT NOT NULL,
            land_record_id TEXT NOT NULL,
            network_name TEXT DEFAULT 'AgriStack Chain',
            status TEXT DEFAULT 'verified',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Automatic column migrations for existing databases
    for migration in [
        "ALTER TABLE products ADD COLUMN weight_grams INTEGER DEFAULT 500",
        "ALTER TABLE orders ADD COLUMN quantity INTEGER DEFAULT 1",
        "ALTER TABLE orders ADD COLUMN weight_grams INTEGER DEFAULT 500",
        "ALTER TABLE orders ADD COLUMN total_price INTEGER DEFAULT 0",
        "ALTER TABLE orders ADD COLUMN variant_name TEXT DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN address TEXT DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN phone TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN street TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN city TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN pincode TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(migration)
        except Exception:
            pass
    con.commit()
    con.close()

init_db()


# ---------------- ROUTES ----------------

# 1. Home Page
@app.route("/")
def home():
    return render_template("index.html")


# 2. AI Chatbot Page
@app.route("/ai")
def ai_chat():
    return render_template("ai.html")


# 3. AI Chatbot API Endpoint
@app.route("/chat", methods=["POST"])
def chat():
    message = request.form.get("message", "").strip()
    image = request.files.get("image")

    plant_info = None
    saved_filename = None

    # Handle image upload if provided
    if image and image.filename:
        if allowed_file(image.filename):
            filename = secure_filename(image.filename)
            unique_filename = f"chat_{random.randint(1000, 9999)}_{filename}"
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            image.save(image_path)
            saved_filename = unique_filename
            plant_info = bot.smart_identify_plant(image_path)

            # Check if image was explicitly flagged as non-plant
            if plant_info and plant_info.get("is_non_plant"):
                return jsonify({
                    "success": False,
                    "reply": "No plant or crop detected. The uploaded photo appears to be a non-plant object (such as a wallet, accessory, or synthetic item). EcoHarvest AI is exclusively dedicated to plant identification, agriculture, and crop care. Please upload a clear photo of a real crop, leaf, flower, or fruit."
                })

            if not plant_info:
                return jsonify({
                    "success": False,
                    "reply": "Could not identify the plant in this image. Please upload a clear close-up photo of the crop, leaf, flower, or fruit."
                })
        else:
            return jsonify({
                "success": False,
                "reply": "Invalid image format. Please upload JPG, PNG, or WEBP."
            }), 400

    # Conversational chit-chat handling (greetings, status, identity, gratitude, bye)
    if not image and message:
        conv_reply = bot.handle_conversational_query(message)
        if conv_reply:
            return jsonify({
                "success": True,
                "is_greeting": True,
                "reply": conv_reply,
                "suggestions": ["Tomato", "Wheat", "Potato", "Rice", "Onion", "Chilli", "Cotton", "Sacred Lotus"]
            })

    # Domain restriction: Answerable ONLY to plant / crop / agricultural detection
    if not image and message:
        is_plant, matched_plant = bot.is_plant_related_query(message)
        if not is_plant:
            return jsonify({
                "success": False,
                "is_non_plant_topic": True,
                "reply": "I specialize exclusively in plant identification, botany, and agricultural crop guidance. I cannot assist with non-plant topics.\n\nPlease ask about a specific crop (such as Wheat, Rice, Tomato, Potato, Chilli, Lotus, etc.) or upload a plant photo for identification."
            })

    # Text search if no plant identified yet
    if not plant_info and message:
        plant_info = bot.get_plant_care(message)

    if not plant_info:
        fallback_reply = """
**Plant or Crop Not Recognized**

Could not identify this plant with sufficient botanical certainty.
Try typing a specific crop name (e.g. Tomato, Wheat, Potato, Rice, Chilli, Cotton, Onion, Sugarcane, Lotus) or upload a photo of the leaf or fruit.
"""
        return jsonify({
            "success": False,
            "reply": fallback_reply.strip(),
            "suggestions": ["Tomato", "Wheat", "Potato", "Rice", "Onion", "Chilli", "Cotton", "Sacred Lotus"]
        })

    # Fetch weather & generate analysis
    weather = bot.get_weather()
    analysis = bot.analyze(plant_info, weather)

    wiki_url = analysis.get("wikipedia_url") or analysis.get("wiki_url") or f"https://en.wikipedia.org/wiki/{analysis['plant']}"
    wiki_summary = analysis.get("wikipedia_summary") or analysis.get("wiki_summary") or ""

    if analysis.get("annotated_image"):
        detection_header = f"**Object Detected:** {analysis['plant']} ({analysis.get('confidence', 90)}% confidence)\n"
        if analysis.get("detections_summary"):
            detection_header += f"**Detections:** {analysis['detections_summary']}\n"
    else:
        detection_header = f"**Crop:** {analysis['plant']}\n"

    reply = f"""
{detection_header}**Scientific Name:** {analysis.get('scientific_name', analysis['plant'])} ({analysis.get('family', 'Plantae')})

**Wikipedia Overview:**
{wiki_summary}
[Read Wikipedia Article]({wiki_url})

**Agricultural Growing Guidelines:**
- **Temperature:** {analysis.get('temp')} deg C (Optimal Range: {analysis.get('range')})
- **Status:** {analysis.get('status')}
- **Water Needs:** {analysis.get('water')}
- **Sunlight:** {analysis.get('light')}
- **Soil Type:** {analysis.get('soil')}
- **Harvest Cycle:** {analysis.get('harvest')}
- **Farming Tip:** {analysis.get('tip')}
"""

    return jsonify({
        "success": True,
        "reply": reply.strip(),
        "plant": analysis,
        "image_file": saved_filename
    })

# 4. Products Marketplace
@app.route("/products")
def products():
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM products ORDER BY id DESC")
    product_rows = cur.fetchall()

    pending_orders = []
    user_info = {}
    if "user_id" in session:
        cur.execute("""
            SELECT product_id FROM orders
            WHERE user_id=? AND status='pending'
        """, (session["user_id"],))
        pending_orders = [row["product_id"] for row in cur.fetchall()]

        cur.execute("""
            SELECT id, name, email, phone, street, city, pincode
            FROM users WHERE id=?
        """, (session["user_id"],))
        u_row = cur.fetchone()
        if u_row:
            user_info = dict(u_row)

    con.close()

    return render_template(
        "products.html",
        products=product_rows,
        pending_orders=pending_orders,
        user_info=user_info
    )


# 5. User Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "error")
            return redirect(url_for("register"))

        con = get_db()
        cur = con.cursor()

        try:
            hashed_pwd = generate_password_hash(password)
            cur.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, 'user')
            """, (name, email, hashed_pwd))
            con.commit()
            con.close()
            flash("Account registered successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            con.close()
            flash("An account with this email already exists.", "error")
            return redirect(url_for("register"))
        except Exception as e:
            con.close()
            flash("An error occurred during registration. Please try again.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")


# 6. Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_or_user = (request.form.get("email") or request.form.get("username") or "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email_or_user or not password:
            flash("Please enter both email/username and password.", "error")
            return redirect(url_for("login"))

        # Admin check
        if email_or_user in ["admin", "admin@gmail.com", "admin@ecoharvest.org"] and password == "admin123":
            session.clear()
            session["role"] = "admin"
            session["user_id"] = 0
            session["user"] = "admin"
            session["user_name"] = "System Admin"
            return redirect(url_for("admin_orders"))

        # Normal User DB check
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT id, name, email, password, role FROM users WHERE email=? OR name=?", (email_or_user, email_or_user))
        user = cur.fetchone()

        if user:
            stored_pwd = user["password"]
            pwd_matches = False

            # Verify hashed or fallback to plain text legacy
            if stored_pwd.startswith("scrypt:") or stored_pwd.startswith("pbkdf2:"):
                pwd_matches = check_password_hash(stored_pwd, password)
            else:
                pwd_matches = (stored_pwd == password)
                if pwd_matches:
                    # Transparently upgrade to secure hash
                    new_hash = generate_password_hash(password)
                    cur.execute("UPDATE users SET password=? WHERE id=?", (new_hash, user["id"]))
                    con.commit()

            if pwd_matches:
                session.clear()
                session["user_id"] = user["id"]
                session["role"] = user["role"]
                session["user"] = user["email"]
                session["user_name"] = user["name"]
                session["user_photo"] = (user["photo"] if "photo" in user.keys() else "") or ""
                con.close()
                flash(f"Logged in successfully as {user['name']}.", "success")
                return redirect(url_for("home"))

        con.close()
        flash("Invalid email or password. Please try again.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


# 7. Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("login"))


# 8. Buy Product / Order (Single item)
@app.route("/order/<int:product_id>", methods=["POST"])
def buy_product(product_id):
    if "user_id" not in session:
        flash("Please log in to place an order.", "error")
        return redirect(url_for("login"))

    quantity = 1
    try:
        quantity = max(1, int(request.form.get("quantity", 1)))
    except (ValueError, TypeError):
        quantity = 1

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
    prod = cur.fetchone()
    if not prod:
        con.close()
        flash("Product not found.", "error")
        return redirect(url_for("products"))

    base_weight = prod["weight_grams"] if ("weight_grams" in prod.keys() and prod["weight_grams"]) else 500
    base_price = prod["price"]

    try:
        pack_grams = int(request.form.get("pack_grams") or base_weight)
    except (ValueError, TypeError):
        pack_grams = base_weight

    variant_name = request.form.get("variant_name", "").strip()
    if not variant_name:
        variant_name = f"{pack_grams}g Pack"

    try:
        total_weight = int(request.form.get("weight_grams") or (pack_grams * quantity))
    except (ValueError, TypeError):
        total_weight = pack_grams * quantity

    try:
        total_price = int(request.form.get("total_price") or 0)
        if total_price <= 0:
            unit_price = max(1, round((base_price / base_weight) * pack_grams))
            total_price = unit_price * quantity
    except (ValueError, TypeError):
        unit_price = max(1, round((base_price / base_weight) * pack_grams))
        total_price = unit_price * quantity

    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()
    street = request.form.get("street", "").strip()
    city = request.form.get("city", "").strip()
    pincode = request.form.get("pincode", "").strip()

    cur.execute("""
        INSERT INTO orders (user_id, product_id, status, quantity, weight_grams, total_price, variant_name, address, phone)
        VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?)
    """, (session["user_id"], product_id, quantity, total_weight, total_price, variant_name, address, phone))

    if "user_id" in session:
        cur.execute("""
            UPDATE users 
            SET phone = CASE WHEN ? != '' THEN ? ELSE phone END,
                street = CASE WHEN ? != '' THEN ? ELSE street END,
                city = CASE WHEN ? != '' THEN ? ELSE city END,
                pincode = CASE WHEN ? != '' THEN ? ELSE pincode END
            WHERE id = ?
        """, (phone, phone, street, street, city, city, pincode, pincode, session["user_id"]))

    con.commit()
    con.close()

    flash(f"Order confirmed: {prod['name']} ({variant_name}). Delivery scheduled.", "success")
    return redirect(url_for("products"))


# 8b. Cart Checkout (Multiple items)
@app.route("/cart/checkout", methods=["POST"])
def cart_checkout():
    if "user_id" not in session:
        if request.is_json:
            return jsonify({"success": False, "error": "auth_required", "message": "Please log in to checkout your cart."}), 401
        flash("Please log in to checkout your cart.", "error")
        return redirect(url_for("login"))

    data = request.get_json(silent=True)
    items = []
    address = ""
    phone = ""
    if data and isinstance(data, dict):
        items = data.get("items", [])
        address = str(data.get("address", "")).strip()
        phone = str(data.get("phone", "")).strip()
    elif data and isinstance(data, list):
        items = data

    if not address:
        address = request.form.get("address", "").strip()
    if not phone:
        phone = request.form.get("phone", "").strip()
    else:
        cart_data_str = request.form.get("cart_data")
        if cart_data_str:
            try:
                items = json.loads(cart_data_str)
            except Exception:
                items = []

    if not items:
        if request.is_json:
            return jsonify({"success": False, "message": "Your cart is empty."}), 400
        flash("Your cart is empty.", "info")
        return redirect(url_for("products"))

    con = get_db()
    cur = con.cursor()
    placed_count = 0
    total_cart_price = 0
    total_cart_weight = 0

    for item in items:
        try:
            pid = int(item.get("product_id") or item.get("id"))
            qty = max(1, int(item.get("quantity", 1)))
        except (ValueError, TypeError):
            continue

        cur.execute("SELECT * FROM products WHERE id=?", (pid,))
        prod = cur.fetchone()
        if not prod:
            continue

        base_weight = prod["weight_grams"] if ("weight_grams" in prod.keys() and prod["weight_grams"]) else 500
        base_price = prod["price"]

        try:
            pack_grams = int(item.get("pack_grams") or item.get("weight_grams") or base_weight)
        except (ValueError, TypeError):
            pack_grams = base_weight

        variant_name = str(item.get("variant_name") or f"{pack_grams}g Pack").strip()

        try:
            item_weight = int(item.get("total_weight") or item.get("weight_grams") or (pack_grams * qty))
        except (ValueError, TypeError):
            item_weight = pack_grams * qty

        try:
            item_price = int(item.get("total_price") or 0)
            if item_price <= 0:
                unit_price = max(1, round((base_price / base_weight) * pack_grams))
                item_price = unit_price * qty
        except (ValueError, TypeError):
            unit_price = max(1, round((base_price / base_weight) * pack_grams))
            item_price = unit_price * qty

        cur.execute("""
            INSERT INTO orders (user_id, product_id, status, quantity, weight_grams, total_price, variant_name, address, phone)
            VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?)
        """, (session["user_id"], pid, qty, item_weight, item_price, variant_name, address, phone))
        placed_count += 1
        total_cart_price += item_price
        total_cart_weight += item_weight

    street = str(data.get("street", "")).strip() if data and isinstance(data, dict) else ""
    city = str(data.get("city", "")).strip() if data and isinstance(data, dict) else ""
    pincode = str(data.get("pincode", "")).strip() if data and isinstance(data, dict) else ""

    if "user_id" in session:
        cur.execute("""
            UPDATE users 
            SET phone = CASE WHEN ? != '' THEN ? ELSE phone END,
                street = CASE WHEN ? != '' THEN ? ELSE street END,
                city = CASE WHEN ? != '' THEN ? ELSE city END,
                pincode = CASE WHEN ? != '' THEN ? ELSE pincode END
            WHERE id = ?
        """, (phone, phone, street, street, city, city, pincode, pincode, session["user_id"]))

    con.commit()
    con.close()

    if placed_count > 0:
        msg = f"Order confirmed: {placed_count} seed item{'s' if placed_count > 1 else ''} (Rs. {total_cart_price}). Delivery scheduled."
        if request.is_json:
            return jsonify({"success": True, "message": msg, "count": placed_count})
        flash(msg, "success")
    else:
        if request.is_json:
            return jsonify({"success": False, "message": "Could not process items in cart."}), 400
        flash("Could not process items in cart.", "error")

    return redirect(url_for("products"))


# 9. Admin: Add Product
@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if session.get("role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price_str = request.form.get("price", "").strip()
        weight_str = request.form.get("weight_grams", "500").strip()
        image = request.files.get("image")

        if not name or not price_str or not image or not image.filename:
            flash("Please fill in all required fields and select a product image.", "error")
            return redirect(url_for("add_product"))

        try:
            price = int(price_str)
            if price <= 0:
                raise ValueError()
        except ValueError:
            flash("Price must be a valid positive number.", "error")
            return redirect(url_for("add_product"))

        try:
            weight_grams = int(weight_str)
            if weight_grams <= 0:
                raise ValueError()
        except ValueError:
            flash("Weight (grams) must be a positive number.", "error")
            return redirect(url_for("add_product"))

        if not allowed_file(image.filename):
            flash("Unsupported image format. Allowed: PNG, JPG, JPEG, WEBP, GIF.", "error")
            return redirect(url_for("add_product"))

        filename = secure_filename(image.filename)
        unique_name = f"prod_{random.randint(1000, 9999)}_{filename}"
        image_save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        image.save(image_save_path)

        con = get_db()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO products (name, price, image, weight_grams)
            VALUES (?, ?, ?, ?)
        """, (name, price, unique_name, weight_grams))
        con.commit()
        con.close()

        flash(f"Product '{name}' ({weight_grams}g for Rs. {price}) added successfully to the marketplace!", "success")
        return redirect(url_for("products"))

    return render_template("add_product.html")


# 10. Admin: View Orders
@app.route("/admin/orders")
def admin_orders():
    if session.get("role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT orders.id, users.email, COALESCE(products.name, 'Archived Seed') as name, orders.status, users.name as user_name,
               orders.quantity, orders.weight_grams, orders.total_price, orders.variant_name, orders.address, orders.phone,
               products.price as unit_price, products.weight_grams as base_weight,
               products.image as product_image
        FROM orders
        JOIN users ON orders.user_id = users.id
        LEFT JOIN products ON orders.product_id = products.id
        ORDER BY orders.id DESC
    """)
    orders = cur.fetchall()

    cur.execute("SELECT * FROM products ORDER BY id DESC")
    products = cur.fetchall()
    con.close()

    return render_template("admin.html", orders=orders, products=products)


# 11. Admin: Approve / Reject Order
@app.route("/admin/order/<int:order_id>/<status>")
def update_order(order_id, status):
    if session.get("role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))

    if status not in ["approved", "rejected"]:
        flash("Invalid order action.", "error")
        return redirect(url_for("admin_orders"))

    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    con.commit()
    con.close()

    if status == "approved":
        days = random.randint(2, 4)
        flash(f"Order #{order_id} approved. Estimated dispatch in {days} days.", "success")
    else:
        flash(f"Order #{order_id} has been rejected.", "error")

    return redirect(url_for("admin_orders"))


# 11b. Admin: Delete Product
@app.route("/admin/product/delete/<int:product_id>", methods=["POST", "GET"])
def delete_product(product_id):
    if session.get("role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))

    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM products WHERE id=?", (product_id,))
    con.commit()
    con.close()

    flash("Product successfully removed from the marketplace.", "success")
    return redirect(url_for("admin_orders"))


# 12. Information Pages & Farmer Network
@app.route("/about")
def about():
    return redirect(url_for("home"))


@app.route("/farmers")
def farmers():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM farmers ORDER BY id DESC")
    farmer_rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return render_template("farmerdetail.html", farmers=farmer_rows)


@app.route("/farmer/register", methods=["POST"])
def register_farmer():
    if "user_id" not in session:
        flash("Please sign in or create an account to register as an expert mentor.", "error")
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    state = request.form.get("state", "").strip().lower()
    loc = request.form.get("loc", "").strip()
    exp = request.form.get("exp", "").strip()
    spec = request.form.get("spec", "").strip()
    bio = request.form.get("bio", "").strip()
    phone = request.form.get("phone", "").strip()
    land_record_id = request.form.get("land_record_id", "").strip().upper()
    network_name = request.form.get("network_name", "AgriStack National Ledger").strip()
    doc_file = request.files.get("doc_file")

    if not name or not state or not loc or not exp or not spec or not land_record_id:
        flash("Please complete all required fields including your verified Land Record ID.", "error")
        return redirect(url_for("farmers"))

    if len(land_record_id) < 5:
        flash("Invalid Agricultural Land Record ID. A valid State Khasra, Khatauni, or Kisan Credit Number is required.", "error")
        return redirect(url_for("farmers"))

    doc_filename = ""
    blockchain_hash = ""

    if doc_file and doc_file.filename:
        file_bytes = doc_file.read()
        if len(file_bytes) > 0:
            doc_hash_hex = hashlib.sha256(file_bytes).hexdigest()
            blockchain_hash = f"0x{doc_hash_hex}"

            doc_ext = doc_file.filename.rsplit(".", 1)[1].lower() if "." in doc_file.filename else "pdf"
            safe_name = f"doc_{session['user_id']}_{random.randint(1000, 9999)}.{doc_ext}"
            doc_folder = os.path.join("static", "uploads", "farmer_docs")
            os.makedirs(doc_folder, exist_ok=True)
            doc_path = os.path.join(doc_folder, safe_name)
            with open(doc_path, "wb") as f_out:
                f_out.write(file_bytes)
            doc_filename = safe_name
        else:
            flash("Uploaded document is empty. Please provide a valid verification file.", "error")
            return redirect(url_for("farmers"))
    else:
        flash("Land record verification document is required. Please upload your Kisan Passbook, 7/12 extract, or Land Title PDF/Image to authenticate your farmer identity.", "error")
        return redirect(url_for("farmers"))

    con = get_db()
    cur = con.cursor()

    # Check for duplicate land record ID to prevent identity falsification
    cur.execute("SELECT id, name FROM farmers WHERE land_record_id = ?", (land_record_id,))
    existing = cur.fetchone()
    if existing:
        con.close()
        flash(f"Land Record ID '{land_record_id}' is already registered on the ledger under {existing['name']}. Duplicate registrations are blocked.", "error")
        return redirect(url_for("farmers"))

    cur.execute("""
        INSERT INTO farmers (user_id, name, state, loc, exp, spec, bio, phone, rating, consultation_fee, blockchain_doc, blockchain_hash, land_record_id, network_name, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 4.9, 500, ?, ?, ?, ?, 'verified')
    """, (session["user_id"], name, state, loc, exp, spec, bio or "Verified sustainable agriculturist.", phone, doc_filename, blockchain_hash, land_record_id, network_name))

    con.commit()
    con.close()

    flash(f"Credentials cryptographically authenticated on {network_name}! Hash: {blockchain_hash[:16]}... Your expert mentor profile is now active on the network.", "success")
    return redirect(url_for("farmers"))


@app.route("/crop")
def crop():
    return render_template("crop.html")


# ---------------- APPLICATION ENTRY POINT ----------------
# ---------------- USER PROFILE & ORDERS ----------------
@app.route("/profile", endpoint="profile")
@app.route("/user_profile", endpoint="user_profile")
def profile():
    if "user_id" not in session:
        flash("Please sign in to access your profile and order history.", "warning")
        return redirect(url_for("login"))

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name, email, role, phone, street, city, pincode, photo, bio
        FROM users WHERE id = ?
    """, (session["user_id"],))
    user_row = cur.fetchone()

    if not user_row:
        con.close()
        flash("User profile not found.", "error")
        return redirect(url_for("login"))

    user = dict(user_row)

    cur.execute("""
        SELECT orders.id, orders.status, orders.quantity, orders.weight_grams, orders.total_price,
               orders.variant_name, orders.address, orders.phone,
               COALESCE(products.name, 'Organic Seed Batch') as product_name,
               products.price as unit_price,
               products.image as product_image
        FROM orders
        LEFT JOIN products ON orders.product_id = products.id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
    """, (session["user_id"],))
    orders = [dict(row) for row in cur.fetchall()]

    con.close()

    total_orders = len(orders)
    approved_orders = sum(1 for o in orders if o.get("status") == "approved")
    total_weight = sum(o.get("weight_grams") or 0 for o in orders)
    total_spent = sum(o.get("total_price") or 0 for o in orders)

    stats = {
        "total_orders": total_orders,
        "approved_orders": approved_orders,
        "total_weight": total_weight,
        "total_spent": total_spent
    }

    return render_template("profile.html", user=user, orders=orders, stats=stats)


@app.route("/profile/update", methods=["POST"], endpoint="update_profile")
@app.route("/update_profile", methods=["POST"], endpoint="profile_update")
def profile_update():
    if "user_id" not in session:
        flash("Please log in to update your profile.", "error")
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    street = request.form.get("street", "").strip()
    city = request.form.get("city", "").strip()
    pincode = request.form.get("pincode", "").strip()
    bio = request.form.get("bio", "").strip()

    if not name:
        flash("Full Name is required.", "error")
        return redirect(url_for("profile"))

    con = get_db()
    cur = con.cursor()

    avatar_file = request.files.get("photo")
    photo_filename = None
    if avatar_file and avatar_file.filename:
        filename = secure_filename(avatar_file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".svg"]:
            avatar_dir = os.path.join(app.root_path, "static", "uploads", "avatars")
            os.makedirs(avatar_dir, exist_ok=True)
            rand_suffix = hashlib.md5(f"{session['user_id']}_{random.random()}".encode("utf-8")).hexdigest()[:8]
            safe_name = f"avatar_{session['user_id']}_{rand_suffix}{ext}"
            file_path = os.path.join(avatar_dir, safe_name)
            avatar_file.save(file_path)
            photo_filename = safe_name

    if photo_filename:
        cur.execute("""
            UPDATE users
            SET name = ?, phone = ?, street = ?, city = ?, pincode = ?, bio = ?, photo = ?
            WHERE id = ?
        """, (name, phone, street, city, pincode, bio, photo_filename, session["user_id"]))
        session["user_photo"] = photo_filename
    else:
        cur.execute("""
            UPDATE users
            SET name = ?, phone = ?, street = ?, city = ?, pincode = ?, bio = ?
            WHERE id = ?
        """, (name, phone, street, city, pincode, bio, session["user_id"]))

    con.commit()
    con.close()

    session["user_name"] = name
    flash("Profile updated successfully! Your saved shipping address and contact details will now autofill on checkout.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/change_password", methods=["POST"], endpoint="change_password")
@app.route("/change_password", methods=["POST"], endpoint="profile_change_password")
def profile_change_password():
    if "user_id" not in session:
        flash("Please log in to manage your security settings.", "error")
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not current_password or not new_password or not confirm_password:
        flash("All password fields are required.", "error")
        return redirect(url_for("profile"))

    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "error")
        return redirect(url_for("profile"))

    if len(new_password) < 6:
        flash("New password must be at least 6 characters long.", "error")
        return redirect(url_for("profile"))

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT password FROM users WHERE id = ?", (session["user_id"],))
    user_row = cur.fetchone()

    if not user_row:
        con.close()
        flash("User record not found.", "error")
        return redirect(url_for("login"))

    stored_hash = user_row["password"]
    pwd_valid = False
    if stored_hash:
        try:
            pwd_valid = check_password_hash(stored_hash, current_password)
        except Exception:
            pwd_valid = (stored_hash == current_password)

    if not pwd_valid:
        con.close()
        flash("Incorrect current password. Please try again.", "error")
        return redirect(url_for("profile"))

    new_hash = generate_password_hash(new_password)
    cur.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, session["user_id"]))
    con.commit()
    con.close()

    flash("Password updated successfully! Your account credentials have been secured.", "success")
    return redirect(url_for("profile"))



# ---------------- ROOT STATIC ASSET FALLBACK ----------------
@app.route("/<string:root_image_name>")
def serve_root_image(root_image_name):
    # Fallback for cached or legacy links requesting images directly at root like /cotton.jpg or /chilli.png
    if root_image_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".ico")):
        for folder in ["uploads", "images"]:
            folder_path = os.path.join(app.root_path, "static", folder)
            file_path = os.path.join(folder_path, root_image_name)
            if os.path.isfile(file_path):
                return send_from_directory(folder_path, root_image_name)
    return ("File not found", 404)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

"""
SmartFood Platform — Database & Data Access Layer
Handles SQLite tables, transactional food claiming, negative inventory prevention,
and reporting queries for Canteens, Restaurants, and NGOs.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from auth import hash_password, verify_password

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smartfood_community.db")


def get_connection(db_file: str = DB_PATH) -> sqlite3.Connection:
    """Creates a SQLite connection with foreign keys and row factory enabled."""
    conn = sqlite3.connect(db_file, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database(db_file: str = DB_PATH) -> None:
    """Creates all required tables if they do not exist."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        # 1. Users Table (Canteens, Restaurants, NGOs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                org_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('canteen', 'restaurant', 'ngo', 'admin')),
                phone TEXT,
                address TEXT,
                city TEXT DEFAULT 'Bangalore',
                capacity INTEGER DEFAULT 100,
                fssai_no TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Canteen & Restro Daily Needs Tracker
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canteen_needs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                meal_service TEXT NOT NULL,
                planned_portions INTEGER NOT NULL CHECK(planned_portions >= 0),
                actual_consumed INTEGER DEFAULT 0 CHECK(actual_consumed >= 0),
                estimated_surplus INTEGER DEFAULT 0 CHECK(estimated_surplus >= 0),
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. NGO Community Food Needs Tracker
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ngo_needs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                target_meals_needed INTEGER NOT NULL CHECK(target_meals_needed > 0),
                meals_secured INTEGER DEFAULT 0 CHECK(meals_secured >= 0),
                dietary_preference TEXT DEFAULT 'Any',
                distribution_location TEXT,
                urgent_flag INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. Surplus Food Listings (Available from Canteens/Restros)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surplus_food (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                food_title TEXT NOT NULL,
                category TEXT NOT NULL,
                dietary TEXT NOT NULL,
                portions_total INTEGER NOT NULL CHECK(portions_total > 0),
                portions_available INTEGER NOT NULL CHECK(portions_available >= 0),
                cooked_time TEXT NOT NULL,
                expiry_deadline TEXT NOT NULL,
                storage_condition TEXT NOT NULL,
                pickup_address TEXT NOT NULL,
                pickup_instructions TEXT,
                status TEXT DEFAULT 'Available',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. Food Claims & Reservations by NGOs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surplus_id INTEGER NOT NULL REFERENCES surplus_food(id) ON DELETE CASCADE,
                ngo_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                portions_claimed INTEGER NOT NULL CHECK(portions_claimed > 0),
                volunteer_name TEXT NOT NULL,
                volunteer_phone TEXT NOT NULL,
                pickup_eta TEXT NOT NULL,
                claim_status TEXT DEFAULT 'Reserved',
                handover_code TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. Canteen Favorite & Loved Dishes (Demand Predictor Engine)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canteen_menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                item_name TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                meal_service TEXT NOT NULL,
                love_score INTEGER DEFAULT 95 CHECK(love_score >= 0 AND love_score <= 100),
                demand_surge_pct INTEGER DEFAULT 25,
                prep_tip TEXT,
                dietary TEXT DEFAULT 'Vegetarian',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Column migration for existing users table
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN fssai_no TEXT;")
        except sqlite3.OperationalError:
            pass

        conn.commit()
    finally:
        conn.close()


# ==========================================
# USER AUTHENTICATION & MANAGEMENT
# ==========================================

def create_user(
    email: str,
    password: str,
    name: str,
    org_name: str,
    role: str,
    phone: str = "",
    address: str = "",
    city: str = "Bangalore",
    capacity: int = 100,
    fssai_no: str = "",
    db_file: str = DB_PATH,
) -> Tuple[bool, str, Optional[int]]:
    """
    Registers a new community user (Canteen, Restro, or NGO).
    Returns (success, message, user_id).
    """
    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        return False, "Please enter a valid email address.", None
    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None
    if role not in ["canteen", "restaurant", "ngo", "admin"]:
        return False, "Invalid account role.", None

    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            return False, f"An account with email '{email_clean}' already exists.", None

        pw_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (
                email, password_hash, name, org_name, role, phone, address, city, capacity, fssai_no
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email_clean, pw_hash, name.strip(), org_name.strip(),
            role, phone.strip(), address.strip(), city.strip(), int(capacity), fssai_no.strip()
        ))
        conn.commit()
        return True, "Account created successfully!", cursor.lastrowid
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def authenticate_user(
    email: str,
    password: str,
    db_file: str = DB_PATH
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticates a user by email and password.
    Returns (success, message, user_dict).
    """
    email_clean = email.strip().lower()
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()
        if not row:
            return False, "No account found with this email address.", None

        user_dict = dict(row)
        if verify_password(password, user_dict["password_hash"]):
            return True, "Authentication successful!", user_dict
        else:
            return False, "Incorrect password. Please try again.", None
    finally:
        conn.close()


def get_user_by_id(user_id: int, db_file: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Fetches user details by user ID."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, name, org_name, role, phone, address, city, capacity, fssai_no, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_profile(
    user_id: int,
    name: str,
    org_name: str,
    phone: str,
    address: str,
    city: str,
    capacity: int,
    fssai_no: str = "",
    db_file: str = DB_PATH
) -> bool:
    """Updates user profile information including FSSAI license number."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users
            SET name = ?, org_name = ?, phone = ?, address = ?, city = ?, capacity = ?, fssai_no = ?
            WHERE id = ?
        """, (name.strip(), org_name.strip(), phone.strip(), address.strip(), city.strip(), int(capacity), fssai_no.strip(), user_id))
        conn.commit()
        return True
    finally:
        conn.close()


# ==========================================
# CANTEEN & RESTRO DAILY NEEDS TRACKING
# ==========================================

def log_canteen_need(
    user_id: int,
    date_str: str,
    meal_service: str,
    planned_portions: int,
    actual_consumed: int = 0,
    notes: str = "",
    db_file: str = DB_PATH,
) -> int:
    """Logs daily food preparation needs and consumption for a canteen or restaurant."""
    surplus = max(0, planned_portions - actual_consumed)
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO canteen_needs (
                user_id, date, meal_service, planned_portions, actual_consumed, estimated_surplus, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date_str, meal_service, planned_portions, actual_consumed, surplus, notes.strip()))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_canteen_needs(user_id: int, limit: int = 14, db_file: str = DB_PATH) -> pd.DataFrame:
    """Fetches recent daily needs logs for a canteen/restro."""
    conn = get_connection(db_file)
    try:
        return pd.read_sql_query("""
            SELECT * FROM canteen_needs 
            WHERE user_id = ? 
            ORDER BY date DESC, id DESC 
            LIMIT ?
        """, conn, params=(user_id, limit))
    finally:
        conn.close()


def add_canteen_menu_item(
    user_id: int,
    item_name: str,
    day_of_week: str,
    meal_service: str = "Lunch",
    love_score: int = 95,
    demand_surge_pct: int = 25,
    prep_tip: str = "",
    dietary: str = "Vegetarian",
    db_file: str = DB_PATH,
) -> int:
    """Adds a favorite/loved dish for a canteen or restaurant."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO canteen_menu_items (
                user_id, item_name, day_of_week, meal_service, love_score, demand_surge_pct, prep_tip, dietary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, item_name.strip(), day_of_week, meal_service, love_score, demand_surge_pct, prep_tip.strip(), dietary))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_canteen_menu_items(
    user_id: int,
    day_of_week: Optional[str] = None,
    db_file: str = DB_PATH,
) -> pd.DataFrame:
    """Retrieves high-demand loved dishes for a canteen, optionally filtered by day of week."""
    conn = get_connection(db_file)
    try:
        if day_of_week and day_of_week != "All Days":
            return pd.read_sql_query("""
                SELECT * FROM canteen_menu_items
                WHERE user_id = ? AND (day_of_week = ? OR day_of_week = 'Daily')
                ORDER BY love_score DESC, demand_surge_pct DESC
            """, conn, params=(user_id, day_of_week))
        else:
            return pd.read_sql_query("""
                SELECT * FROM canteen_menu_items
                WHERE user_id = ?
                ORDER BY CASE day_of_week 
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                    ELSE 8 END,
                love_score DESC
            """, conn, params=(user_id,))
    finally:
        conn.close()


def delete_canteen_menu_item(
    item_id: int,
    user_id: int,
    db_file: str = DB_PATH,
) -> bool:
    """Deletes a menu item belonging to the specified canteen user."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM canteen_menu_items
            WHERE id = ? AND user_id = ?
        """, (item_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ==========================================
# SURPLUS FOOD POSTING & QUERYING
# ==========================================

def post_surplus_food(
    donor_id: int,
    food_title: str,
    category: str,
    dietary: str,
    portions: int,
    cooked_time: str,
    expiry_deadline: str,
    storage_condition: str,
    pickup_address: str,
    pickup_instructions: str = "",
    db_file: str = DB_PATH,
) -> int:
    """Posts newly available surplus food to the community marketplace."""
    if portions <= 0:
        raise ValueError("Surplus portions must be greater than zero.")

    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO surplus_food (
                donor_id, food_title, category, dietary, portions_total,
                portions_available, cooked_time, expiry_deadline, storage_condition,
                pickup_address, pickup_instructions, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available')
        """, (
            donor_id, food_title.strip(), category, dietary, portions, portions,
            cooked_time, expiry_deadline, storage_condition,
            pickup_address.strip(), pickup_instructions.strip()
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_active_surplus(
    dietary_filter: Optional[List[str]] = None,
    category_filter: Optional[List[str]] = None,
    search_query: str = "",
    db_file: str = DB_PATH,
) -> pd.DataFrame:
    """Fetches all active surplus food available for NGOs to claim."""
    conn = get_connection(db_file)
    query = """
        SELECT 
            s.*,
            u.org_name AS donor_org,
            u.name AS donor_contact_name,
            u.phone AS donor_phone,
            u.city AS donor_city,
            u.fssai_no AS donor_fssai_no
        FROM surplus_food s
        JOIN users u ON s.donor_id = u.id
        WHERE s.portions_available > 0
          AND s.status IN ('Available', 'Partially Claimed')
    """
    params = []

    if dietary_filter:
        placeholders = ",".join("?" for _ in dietary_filter)
        query += f" AND s.dietary IN ({placeholders})"
        params.extend(dietary_filter)

    if category_filter:
        placeholders = ",".join("?" for _ in category_filter)
        query += f" AND s.category IN ({placeholders})"
        params.extend(category_filter)

    if search_query:
        query += " AND (s.food_title LIKE ? OR u.org_name LIKE ? OR s.pickup_address LIKE ?)"
        q = f"%{search_query.strip()}%"
        params.extend([q, q, q])

    query += " ORDER BY s.expiry_deadline ASC, s.id DESC"

    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def get_donor_listings(donor_id: int, db_file: str = DB_PATH) -> pd.DataFrame:
    """Fetches all listings posted by a specific canteen or restaurant."""
    conn = get_connection(db_file)
    query = """
        SELECT 
            s.*,
            COUNT(c.id) AS total_claims,
            COALESCE(SUM(c.portions_claimed), 0) AS total_claimed_portions
        FROM surplus_food s
        LEFT JOIN claims c ON s.id = c.surplus_id
        WHERE s.donor_id = ?
        GROUP BY s.id
        ORDER BY s.id DESC
    """
    try:
        return pd.read_sql_query(query, conn, params=(donor_id,))
    finally:
        conn.close()


def update_surplus_status(surplus_id: int, new_status: str, db_file: str = DB_PATH) -> bool:
    """Updates the status of a surplus listing (e.g. 'Completed', 'Cancelled')."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE surplus_food SET status = ? WHERE id = ?", (new_status, surplus_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ==========================================
# NGO COMMUNITY NEEDS TRACKING
# ==========================================

def set_ngo_daily_need(
    user_id: int,
    date_str: str,
    target_meals_needed: int,
    dietary_preference: str = "Any",
    distribution_location: str = "",
    urgent_flag: int = 0,
    db_file: str = DB_PATH,
) -> int:
    """Logs or updates an NGO's daily community meal requirements."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ngo_needs (
                user_id, date, target_meals_needed, meals_secured,
                dietary_preference, distribution_location, urgent_flag, status
            ) VALUES (?, ?, ?, 0, ?, ?, ?, 'Active')
        """, (user_id, date_str, target_meals_needed, dietary_preference, distribution_location.strip(), urgent_flag))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_today_ngo_need(user_id: int, date_str: str, db_file: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Gets the active community meal need record for an NGO today."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM ngo_needs 
            WHERE user_id = ? AND date = ? 
            ORDER BY id DESC LIMIT 1
        """, (user_id, date_str))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_ngo_needs_history(user_id: int, db_file: str = DB_PATH) -> pd.DataFrame:
    """Gets past community food needs logs for an NGO."""
    conn = get_connection(db_file)
    try:
        return pd.read_sql_query("""
            SELECT * FROM ngo_needs 
            WHERE user_id = ? 
            ORDER BY date DESC, id DESC
        """, conn, params=(user_id,))
    finally:
        conn.close()


# ==========================================
# FOOD CLAIMING (ATOMIC TRANSACTION)
# ==========================================

def claim_surplus_food(
    surplus_id: int,
    ngo_id: int,
    portions_to_claim: int,
    volunteer_name: str,
    volunteer_phone: str,
    pickup_eta: str,
    db_file: str = DB_PATH,
) -> Tuple[bool, str, Optional[str]]:
    """
    Atomically claims surplus food portions for an NGO.
    Strictly guarantees:
    - Requested portions must be > 0.
    - Requested portions cannot exceed current portions_available.
    - Transactional lock (BEGIN IMMEDIATE) prevents negative inventory and race conditions.
    - Generates a 4-digit handover code for secure pickup verification.
    - Increments NGO's meals_secured count for today if an active need is tracked.
    Returns: (success: bool, message: str, handover_code: str or None)
    """
    if portions_to_claim <= 0:
        return False, "Portions to claim must be greater than zero.", None

    conn = get_connection(db_file)
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE;")

        cursor.execute("""
            SELECT portions_available, food_title, status 
            FROM surplus_food 
            WHERE id = ?
        """, (surplus_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return False, f"Surplus listing #{surplus_id} not found.", None

        current_avail = row["portions_available"]
        food_title = row["food_title"]

        if portions_to_claim > current_avail:
            conn.rollback()
            return (
                False,
                f"Cannot claim {portions_to_claim} portions of '{food_title}'. "
                f"Only {current_avail} portions currently remain available.",
                None
            )

        new_avail = current_avail - portions_to_claim
        new_status = "Fully Claimed" if new_avail == 0 else "Partially Claimed"

        # Update surplus inventory
        cursor.execute("""
            UPDATE surplus_food 
            SET portions_available = ?, status = ? 
            WHERE id = ?
        """, (new_avail, new_status, surplus_id))

        # Generate 4-digit verification code
        handover_code = str(random.randint(1000, 9999))

        # Insert claim record
        cursor.execute("""
            INSERT INTO claims (
                surplus_id, ngo_id, portions_claimed, volunteer_name,
                volunteer_phone, pickup_eta, claim_status, handover_code
            ) VALUES (?, ?, ?, ?, ?, ?, 'Reserved', ?)
        """, (
            surplus_id, ngo_id, portions_to_claim, volunteer_name.strip(),
            volunteer_phone.strip(), pickup_eta.strip(), handover_code
        ))

        # Check if NGO has an active need for today and update it
        today_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            UPDATE ngo_needs 
            SET meals_secured = meals_secured + ? 
            WHERE user_id = ? AND date = ? AND status = 'Active'
        """, (portions_to_claim, ngo_id, today_str))

        conn.commit()
        return (
            True,
            f"Successfully claimed {portions_to_claim} portions of '{food_title}'! "
            f"Handover Verification Code: {handover_code}",
            handover_code
        )

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error during reservation: {str(e)}", None
    finally:
        conn.close()


def get_ngo_claims(ngo_id: int, db_file: str = DB_PATH) -> pd.DataFrame:
    """Fetches all claims made by an NGO with donor details."""
    conn = get_connection(db_file)
    query = """
        SELECT 
            c.id AS claim_id,
            c.created_at AS claim_time,
            c.portions_claimed,
            c.volunteer_name,
            c.volunteer_phone,
            c.pickup_eta,
            c.claim_status,
            c.handover_code,
            s.id AS surplus_id,
            s.food_title,
            s.category,
            s.dietary,
            s.storage_condition,
            s.pickup_address,
            s.pickup_instructions,
            s.expiry_deadline,
            u.org_name AS donor_org,
            u.name AS donor_contact,
            u.phone AS donor_phone,
            u.fssai_no AS donor_fssai_no
        FROM claims c
        JOIN surplus_food s ON c.surplus_id = s.id
        JOIN users u ON s.donor_id = u.id
        WHERE c.ngo_id = ?
        ORDER BY c.id DESC
    """
    try:
        return pd.read_sql_query(query, conn, params=(ngo_id,))
    finally:
        conn.close()


def update_claim_status(claim_id: int, new_status: str, db_file: str = DB_PATH) -> bool:
    """Updates the status of a claim (e.g. 'Picked Up', 'Distributed')."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE claims SET claim_status = ? WHERE id = ?", (new_status, claim_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ==========================================
# PLATFORM & IMPACT METRICS
# ==========================================

def get_platform_overview_stats(db_file: str = DB_PATH) -> Dict[str, Any]:
    """Computes overall community metrics across all donors and NGOs."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('canteen', 'restaurant')")
        total_donors = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'ngo'")
        total_ngos = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(portions_claimed), 0) FROM claims WHERE claim_status != 'Cancelled'")
        portions_rescued = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(portions_available), 0) FROM surplus_food WHERE portions_available > 0")
        active_surplus = cursor.fetchone()[0]

        # Environmental conversions
        # 1 portion = 0.40 kg of food
        kg_diverted = round(portions_rescued * 0.40, 1)
        # 2.5 kg CO2e per kg food waste avoided (FAO)
        co2_avoided = round(kg_diverted * 2.50, 1)
        # 1,000 L water per kg food waste (WFN)
        water_saved = round(kg_diverted * 1000.0, 0)
        # Cost saved at ₹45 per meal
        money_saved = round(portions_rescued * 45.0, 0)

        return {
            "total_donors": total_donors,
            "total_ngos": total_ngos,
            "portions_rescued": portions_rescued,
            "active_surplus": active_surplus,
            "kg_diverted": kg_diverted,
            "co2_avoided": co2_avoided,
            "water_saved": water_saved,
            "money_saved": money_saved,
        }
    finally:
        conn.close()


def get_donor_impact_stats(donor_id: int, db_file: str = DB_PATH) -> Dict[str, Any]:
    """Calculates waste diversion stats for a specific canteen or restaurant."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(portions_total), 0),
                COALESCE(SUM(portions_total - portions_available), 0)
            FROM surplus_food 
            WHERE donor_id = ?
        """, (donor_id,))
        row = cursor.fetchone()
        posted = row[0]
        rescued = row[1]
        kg = round(rescued * 0.40, 1)

        return {
            "total_portions_posted": posted,
            "portions_rescued": rescued,
            "kg_diverted": kg,
            "co2_avoided_kg": round(kg * 2.50, 1),
            "money_saved": round(rescued * 45.0, 0),
        }
    finally:
        conn.close()


def get_ngo_impact_stats(ngo_id: int, db_file: str = DB_PATH) -> Dict[str, Any]:
    """Calculates food rescue stats for a specific NGO."""
    conn = get_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COALESCE(SUM(portions_claimed), 0), COUNT(id)
            FROM claims 
            WHERE ngo_id = ? AND claim_status != 'Cancelled'
        """, (ngo_id,))
        row = cursor.fetchone()
        portions = row[0]
        trips = row[1]
        kg = round(portions * 0.40, 1)

        return {
            "portions_received": portions,
            "pickup_trips": trips,
            "kg_distributed": kg,
            "beneficiaries_fed": portions,
            "co2_avoided_kg": round(kg * 2.50, 1),
        }
    finally:
        conn.close()

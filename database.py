import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Таблица отзывов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            rating INTEGER,
            comment TEXT
        )
    """)
    
    # Таблица бронирований
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            phone TEXT,
            hall TEXT,
            date_time TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_review(user_name, rating, comment):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reviews (user_name, rating, comment) VALUES (?, ?, ?)", (user_name, rating, comment))
    conn.commit()
    conn.close()

def get_reviews_stat():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(rating), COUNT(id) FROM reviews")
    avg_rating, count = cursor.fetchone()
    conn.close()
    if not avg_rating:
        return 5.0, 0
    return round(avg_rating, 1), count

def add_booking(user_name, phone, hall, date_time):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (user_name, phone, hall, date_time) VALUES (?, ?, ?, ?)", (user_name, phone, hall, date_time))
    conn.commit()
    conn.close()
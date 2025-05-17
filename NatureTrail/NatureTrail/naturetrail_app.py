"""
NatureTrail - A Nature Exploration Platform
Main application file implementing core functionality with OOP principles
"""

import streamlit as st
import sqlite3
import hashlib
import uuid
import datetime
import json
import os
from abc import ABC, abstractmethod
from PIL import Image
import pandas as pd
import numpy as np
import requests
from io import BytesIO

# Abstract Base Classes
class User(ABC):
    """Abstract base class for all user types"""
    def __init__(self, user_id, username, email):
        self.user_id = user_id
        self.username = username
        self.email = email
        self._last_login = None
    
    @abstractmethod
    def get_permissions(self):
        """Return list of permissions for this user type"""
        pass
    
    def record_login(self):
        """Record the current login time"""
        self._last_login = datetime.datetime.now()
        
    def get_last_login(self):
        """Get the last login time"""
        return self._last_login


class StandardUser(User):
    """Standard user with basic permissions"""
    def __init__(self, user_id, username, email):
        super().__init__(user_id, username, email)
        self.trail_history = []
        self.sightings = []
        self.badges = []
        
    def get_permissions(self):
        return ["view_trails", "log_sightings", "view_own_history"]
    
    def add_trail_to_history(self, trail_id, completion_date):
        """Add a completed trail to user history"""
        self.trail_history.append({
            "trail_id": trail_id,
            "completion_date": completion_date
        })
        return len(self.trail_history)


class PremiumUser(StandardUser):
    """Premium user with additional features"""
    def __init__(self, user_id, username, email, subscription_level="basic"):
        super().__init__(user_id, username, email)
        self.subscription_level = subscription_level
        self.subscription_expiry = datetime.datetime.now() + datetime.timedelta(days=30)
        
    def get_permissions(self):
        permissions = super().get_permissions()
        premium_permissions = [
            "download_trail_maps",
            "advanced_analytics",
            "ad_free_experience",
            "exclusive_content"
        ]
        return permissions + premium_permissions
    
    def renew_subscription(self, days=30):
        """Renew subscription for specified number of days"""
        self.subscription_expiry = datetime.datetime.now() + datetime.timedelta(days=days)
        return self.subscription_expiry


# Database Models
class Database:
    """Database connection and operations manager"""
    def __init__(self, db_path="naturetrail.db"):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables if they don't exist"""
        cursor = self.connection.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            salt TEXT,
            user_type TEXT,
            created_at TEXT,
            last_login TEXT
        )
        ''')
        
        # Trails table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trails (
            trail_id TEXT PRIMARY KEY,
            name TEXT,
            location TEXT,
            difficulty TEXT,
            length REAL,
            elevation_gain REAL,
            description TEXT,
            features TEXT,
            created_by TEXT,
            created_at TEXT,
            last_updated TEXT,
            image_url TEXT
        )
        ''')
        
        # Wildlife sightings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sightings (
            sighting_id TEXT PRIMARY KEY,
            user_id TEXT,
            trail_id TEXT,
            species TEXT,
            quantity INTEGER,
            latitude REAL,
            longitude REAL,
            sighting_date TEXT,
            description TEXT,
            image_url TEXT,
            verified BOOLEAN,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (trail_id) REFERENCES trails (trail_id)
        )
        ''')
        
        # User trail history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trail_history (
            history_id TEXT PRIMARY KEY,
            user_id TEXT,
            trail_id TEXT,
            completion_date TEXT,
            duration INTEGER,
            rating INTEGER,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (trail_id) REFERENCES trails (trail_id)
        )
        ''')
        
        # Badges table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            badge_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            category TEXT,
            image_url TEXT
        )
        ''')
        
        # User badges table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            user_id TEXT,
            badge_id TEXT,
            earned_date TEXT,
            PRIMARY KEY (user_id, badge_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (badge_id) REFERENCES badges (badge_id)
        )
        ''')
        
        # Subscriptions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id TEXT PRIMARY KEY,
            user_id TEXT,
            plan_type TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            payment_method TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        self.connection.commit()
        self._populate_initial_data()
    
    def _populate_initial_data(self):
        """Add some initial data to the database if empty"""
        cursor = self.connection.cursor()
        
        # Check if trails table is empty
        cursor.execute("SELECT COUNT(*) FROM trails")
        trail_count = cursor.fetchone()[0]
        
        if trail_count == 0:
            # Add some sample trails
            sample_trails = [
                {
                    "trail_id": str(uuid.uuid4()),
                    "name": "Emerald Lake Loop",
                    "location": "Rocky Mountain National Park, Colorado",
                    "difficulty": "Moderate",
                    "length": 3.2,
                    "elevation_gain": 650,
                    "description": "Beautiful alpine lake surrounded by mountains. Great for wildlife viewing.",
                    "features": json.dumps(["lake", "forest", "wildlife", "mountain_views"]),
                    "created_by": "system",
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "image_url": "https://example.com/emerald_lake.jpg"
                },
                {
                    "trail_id": str(uuid.uuid4()),
                    "name": "Coastal Redwood Path",
                    "location": "Redwood National Park, California",
                    "difficulty": "Easy",
                    "length": 2.5,
                    "elevation_gain": 120,
                    "description": "Walk among ancient redwood trees on this peaceful forest trail.",
                    "features": json.dumps(["old_growth", "forest", "shade", "family_friendly"]),
                    "created_by": "system",
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "image_url": "https://example.com/redwood_path.jpg"
                }
            ]
            
            for trail in sample_trails:
                cursor.execute(
                    """
                    INSERT INTO trails VALUES 
                    (:trail_id, :name, :location, :difficulty, :length, :elevation_gain, 
                    :description, :features, :created_by, :created_at, :last_updated, :image_url)
                    """, 
                    trail
                )
        
        # Check if badges table is empty
        cursor.execute("SELECT COUNT(*) FROM badges")
        badge_count = cursor.fetchone()[0]
        
        if badge_count == 0:
            # Add some sample badges
            sample_badges = [
                {
                    "badge_id": str(uuid.uuid4()),
                    "name": "Trail Pioneer",
                    "description": "Complete your first trail",
                    "category": "achievements",
                    "image_url": "https://example.com/pioneer_badge.png"
                },
                {
                    "badge_id": str(uuid.uuid4()),
                    "name": "Wildlife Spotter",
                    "description": "Record 5 different wildlife sightings",
                    "category": "wildlife",
                    "image_url": "https://example.com/wildlife_badge.png"
                },
                {
                    "badge_id": str(uuid.uuid4()),
                    "name": "Mountain Goat",
                    "description": "Complete a difficult trail with over 1000ft elevation gain",
                    "category": "achievements",
                    "image_url": "https://example.com/mountain_badge.png"
                }
            ]
            
            for badge in sample_badges:
                cursor.execute(
                    """
                    INSERT INTO badges VALUES 
                    (:badge_id, :name, :description, :category, :image_url)
                    """, 
                    badge
                )
        
        self.connection.commit()
    
    def get_cursor(self):
        """Get database cursor"""
        return self.connection.cursor()
    
    def commit(self):
        """Commit changes to database"""
        self.connection.commit()
    
    def close(self):
        """Close database connection"""
        self.connection.close()


# Authentication System
class AuthenticationManager:
    """Handles user authentication and registration"""
    def __init__(self, db_connection):
        self.db = db_connection
        self.current_user = None
    
    def _hash_password(self, password, salt=None):
        """Hash password with salt for secure storage"""
        if salt is None:
            salt = os.urandom(32).hex()
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
        return password_hash, salt
    
    def register_user(self, username, email, password, user_type="standard"):
        """Register a new user"""
        try:
            # Check if username or email already exists
            cursor = self.db.get_cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", 
                          (username, email))
            if cursor.fetchone():
                return False, "Username or email already exists"
            
            # Hash password and create user
            user_id = str(uuid.uuid4())
            password_hash, salt = self._hash_password(password)
            created_at = datetime.datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                (user_id, username, email, password_hash, salt, user_type, created_at)
            )
            self.db.commit()
            return True, user_id
        except Exception as e:
            return False, str(e)
    
    def authenticate(self, username, password):
        """Authenticate a user with username and password"""
        try:
            cursor = self.db.get_cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()
            
            if not user_data:
                return False, "Invalid username or password"
            
            # Unpack user data
            user_id, db_username, email, stored_hash, salt, user_type, created_at, _ = user_data
            
            # Verify password
            calculated_hash, _ = self._hash_password(password, salt)
            if calculated_hash != stored_hash:
                return False, "Invalid username or password"
            
            # Update last login time
            last_login = datetime.datetime.now().isoformat()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE user_id = ?",
                (last_login, user_id)
            )
            self.db.commit()
            
            # Create appropriate user object
            if user_type == "premium":
                self.current_user = PremiumUser(user_id, username, email)
            else:
                self.current_user = StandardUser(user_id, username, email)
            
            self.current_user.record_login()
            return True, self.current_user
        except Exception as e:
            return False, str(e)
    
    def logout(self):
        """Log out the current user"""
        self.current_user = None
        return True


# Trail Management System
class Trail:
    """Trail class representing a hiking trail"""
    def __init__(self, trail_id, name, location, difficulty, length, 
                 elevation_gain, description, features=None, image_url=None):
        self.trail_id = trail_id
        self.name = name
        self.location = location
        self.difficulty = difficulty
        self.length = length  # miles
        self.elevation_gain = elevation_gain  # feet
        self.description = description
        self.features = features or []
        self.image_url = image_url
        self.sightings = []
    
    def to_dict(self):
        """Convert trail to dictionary"""
        return {
            "trail_id": self.trail_id,
            "name": self.name,
            "location": self.location,
            "difficulty": self.difficulty,
            "length": self.length,
            "elevation_gain": self.elevation_gain,
            "description": self.description,
            "features": self.features,
            "image_url": self.image_url
        }


class TrailManager:
    """Manages trail operations"""
    def __init__(self, database):
        self.db = database
    
    def add_trail(self, trail, created_by):
        """Add a new trail to the database"""
        cursor = self.db.get_cursor()
        
        # Convert features list to JSON string if it's a list
        features_json = json.dumps(trail.features) if isinstance(trail.features, list) else trail.features
        
        now = datetime.datetime.now().isoformat()
        
        cursor.execute(
            """
            INSERT INTO trails VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trail.trail_id, trail.name, trail.location, trail.difficulty,
                trail.length, trail.elevation_gain, trail.description,
                features_json, created_by, now, now, trail.image_url
            )
        )
        
        self.db.commit()
        return trail.trail_id
    
    def get_trail(self, trail_id):
        """Get trail by ID"""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM trails WHERE trail_id = ?", (trail_id,))
        trail_data = cursor.fetchone()
        
        if not trail_data:
            return None
        
        # Parse features from JSON
        features = json.loads(trail_data["features"]) if trail_data["features"] else []
        
        return Trail(
            trail_data["trail_id"],
            trail_data["name"],
            trail_data["location"],
            trail_data["difficulty"],
            trail_data["length"],
            trail_data["elevation_gain"],
            trail_data["description"],
            features,
            trail_data["image_url"]
        )
    
    def get_all_trails(self, filters=None):
        """Get all trails with optional filtering"""
        cursor = self.db.get_cursor()
        
        query = "SELECT * FROM trails"
        params = []
        
        if filters:
            conditions = []
            
            if "difficulty" in filters:
                conditions.append("difficulty = ?")
                params.append(filters["difficulty"])
                
            if "min_length" in filters:
                conditions.append("length >= ?")
                params.append(filters["min_length"])
                
            if "max_length" in filters:
                conditions.append("length <= ?")
                params.append(filters["max_length"])
                
            if "location" in filters:
                conditions.append("location LIKE ?")
                params.append(f"%{filters['location']}%")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        trail_rows = cursor.fetchall()
        
        trails = []
        for row in trail_rows:
            features = json.loads(row["features"]) if row["features"] else []
            
            trail = Trail(
                row["trail_id"],
                row["name"],
                row["location"],
                row["difficulty"],
                row["length"],
                row["elevation_gain"],
                row["description"],
                features,
                row["image_url"]
            )
            trails.append(trail)
            
        return trails
    
    def update_trail(self, trail_id, updates):
        """Update trail information"""
        if not updates:
            return False
        
        cursor = self.db.get_cursor()
        
        # Get current trail data
        cursor.execute("SELECT * FROM trails WHERE trail_id = ?", (trail_id,))
        trail_data = cursor.fetchone()
        
        if not trail_data:
            return False
        
        # Prepare update query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in ["name", "location", "difficulty", "length", 
                      "elevation_gain", "description", "image_url"]:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            elif key == "features" and isinstance(value, list):
                set_clauses.append("features = ?")
                params.append(json.dumps(value))
        
        if not set_clauses:
            return False
        
        # Add last_updated timestamp
        set_clauses.append("last_updated = ?")
        params.append(datetime.datetime.now().isoformat())
        
        # Add trail_id to params
        params.append(trail_id)
        
        # Execute update
        cursor.execute(
            f"UPDATE trails SET {', '.join(set_clauses)} WHERE trail_id = ?",
            params
        )
        
        self.db.commit()
        return True
    
    def delete_trail(self, trail_id):
        """Delete a trail"""
        cursor = self.db.get_cursor()
        cursor.execute("DELETE FROM trails WHERE trail_id = ?", (trail_id,))
        self.db.commit()
        return cursor.rowcount > 0


# Wildlife Sighting System
class WildlifeSighting:
    """Class representing a wildlife sighting"""
    def __init__(self, sighting_id, user_id, trail_id, species, quantity, 
                 latitude, longitude, sighting_date, description=None, image_url=None):
        self.sighting_id = sighting_id
        self.user_id = user_id
        self.trail_id = trail_id
        self.species = species
        self.quantity = quantity
        self.latitude = latitude
        self.longitude = longitude
        self.sighting_date = sighting_date
        self.description = description
        self.image_url = image_url
        self.verified = False
    
    def to_dict(self):
        """Convert sighting to dictionary"""
        return {
            "sighting_id": self.sighting_id,
            "user_id": self.user_id,
            "trail_id": self.trail_id,
            "species": self.species,
            "quantity": self.quantity,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "sighting_date": self.sighting_date,
            "description": self.description,
            "image_url": self.image_url,
            "verified": self.verified
        }


class SightingManager:
    """Manages wildlife sighting operations"""
    def __init__(self, database):
        self.db = database
    
    def add_sighting(self, sighting):
        """Add a new wildlife sighting"""
        cursor = self.db.get_cursor()
        
        cursor.execute(
            """
            INSERT INTO sightings VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sighting.sighting_id, sighting.user_id, sighting.trail_id,
                sighting.species, sighting.quantity, sighting.latitude,
                sighting.longitude, sighting.sighting_date, sighting.description,
                sighting.image_url, sighting.verified
            )
        )
        
        self.db.commit()
        return sighting.sighting_id
    
    def get_sightings_by_trail(self, trail_id):
        """Get all sightings for a specific trail"""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM sightings WHERE trail_id = ?", (trail_id,))
        sighting_rows = cursor.fetchall()
        
        sightings = []
        for row in sighting_rows:
            sighting = WildlifeSighting(
                row["sighting_id"],
                row["user_id"],
                row["trail_id"],
                row["species"],
                row["quantity"],
                row["latitude"],
                row["longitude"],
                row["sighting_date"],
                row["description"],
                row["image_url"]
            )
            sighting.verified = row["verified"]
            sightings.append(sighting)
            
        return sightings
    
    def get_user_sightings(self, user_id):
        """Get all sightings logged by a specific user"""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM sightings WHERE user_id = ?", (user_id,))
        sighting_rows = cursor.fetchall()
        
        sightings = []
        for row in sighting_rows:
            sighting = WildlifeSighting(
                row["sighting_id"],
                row["user_id"],
                row["trail_id"],
                row["species"],
                row["quantity"],
                row["latitude"],
                row["longitude"],
                row["sighting_date"],
                row["description"],
                row["image_url"]
            )
            sighting.verified = row["verified"]
            sightings.append(sighting)
            
        return sightings


# Badge and Achievement System
class BadgeManager:
    """Manages badges and achievements"""
    def __init__(self, database):
        self.db = database
    
    def get_all_badges(self):
        """Get all available badges"""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM badges")
        badge_rows = cursor.fetchall()
        
        badges = []
        for row in badge_rows:
            badge = {
                "badge_id": row["badge_id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "image_url": row["image_url"]
            }
            badges.append(badge)
            
        return badges
    
    def get_user_badges(self, user_id):
        """Get all badges earned by a specific user"""
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT b.*, ub.earned_date 
            FROM badges b
            JOIN user_badges ub ON b.badge_id = ub.badge_id
            WHERE ub.user_id = ?
        """, (user_id,))
        
        badge_rows = cursor.fetchall()
        
        badges = []
        for row in badge_rows:
            badge = {
                "badge_id": row["badge_id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "image_url": row["image_url"],
                "earned_date": row["earned_date"]
            }
            badges.append(badge)
            
        return badges
    
    def award_badge(self, user_id, badge_id):
        """Award a badge to a user"""
        cursor = self.db.get_cursor()
        
        # Check if user already has this badge
        cursor.execute(
            "SELECT * FROM user_badges WHERE user_id = ? AND badge_id = ?",
            (user_id, badge_id)
        )
        
        if cursor.fetchone():
            return False  # Badge already awarded
        
        # Award the badge
        earned_date = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO user_badges VALUES (?, ?, ?)",
            (user_id, badge_id, earned_date)
        )
        
        self.db.commit()
        return True
    
    def check_badge_eligibility(self, user_id):
        """Check if user is eligible for any new badges"""
        cursor = self.db.get_cursor()
        
        # Get user's trail history count
        cursor.execute(
            "SELECT COUNT(*) FROM trail_history WHERE user_id = ?",
            (user_id,)
        )
        trail_count = cursor.fetchone()[0]
        
        # Get user's sightings count
        cursor.execute(
            "SELECT COUNT(*) FROM sightings WHERE user_id = ?",
            (user_id,)
        )
        sighting_count = cursor.fetchone()[0]
        
        # Get user's sightings species count
        cursor.execute(
            "SELECT COUNT(DISTINCT species) FROM sightings WHERE user_id = ?",
            (user_id,)
        )
        species_count = cursor.fetchone()[0]
        
        # Check for challenging trails completed
        cursor.execute("""
            SELECT COUNT(*) FROM trail_history th
            JOIN trails t ON th.trail_id = t.trail_id
            WHERE th.user_id = ? AND t.difficulty = 'Hard' AND t.elevation_gain > 1000
        """, (user_id,))
        hard_trail_count = cursor.fetchone()[0]
        
        # Award badges based on achievements
        awarded_badges = []
        
        # Trail Pioneer badge
        if trail_count >= 1:
            cursor.execute(
                "SELECT badge_id FROM badges WHERE name = 'Trail Pioneer'"
            )
            badge_id = cursor.fetchone()["badge_id"]
            if self.award_badge(user_id, badge_id):
                awarded_badges.append("Trail Pioneer")
        
        # Wildlife Spotter badge
        if species_count >= 5:
            cursor.execute(
                "SELECT badge_id FROM badges WHERE name = 'Wildlife Spotter'"
            )
            badge_id = cursor.fetchone()["badge_id"]
            if self.award_badge(user_id, badge_id):
                awarded_badges.append("Wildlife Spotter")
        
        # Mountain Goat badge
        if hard_trail_count >= 1:
            cursor.execute(
                "SELECT badge_id FROM badges WHERE name = 'Mountain Goat'"
            )
            badge_id = cursor.fetchone()["badge_id"]
            if self.award_badge(user_id, badge_id):
                awarded_badges.append("Mountain Goat")
        
        return awarded_badges


# Payment and Subscription System
class PaymentManager:
    """Manages payments and subscriptions"""
    def __init__(self, database):
        self.db = database
        self.subscription_plans = {
            "monthly": {
                "name": "Monthly Premium",
                "price": 4.99,
                "duration_days": 30,
                "stripe_price_id": "price_monthly_premium"
            },
            "annual": {
                "name": "Annual Premium",
                "price": 49.99,
                "duration_days": 365,
                "stripe_price_id": "price_annual_premium"
            }
        }
    
    def get_subscription_plans(self):
        """Get available subscription plans"""
        return self.subscription_plans
    
    def create_payment_session(self, user_id, plan_type):
        """Create a payment session for subscription"""
        try:
            if plan_type not in self.subscription_plans:
                return False, "Invalid plan type"
            
            plan = self.subscription_plans[plan_type]
            
            # In a real application, we would create a Stripe checkout session
            # For demo purposes, simulate a successful checkout
            checkout_session = {
                "id": f"cs_{uuid.uuid4().hex}",
                "url": "#demo-checkout-url",  # In real app, this would be a Stripe URL
                "payment_status": "unpaid"
            }
            
            return True, checkout_session
        except Exception as e:
            return False, str(e)
    
    def process_successful_payment(self, user_id, plan_type, payment_method="card"):
        """Process a successful payment and create subscription"""
        try:
            cursor = self.db.get_cursor()
            
            if plan_type not in self.subscription_plans:
                return False, "Invalid plan type"
            
            plan = self.subscription_plans[plan_type]
            
            # Create subscription
            subscription_id = str(uuid.uuid4())
            start_date = datetime.datetime.now().isoformat()
            end_date = (datetime.datetime.now() + datetime.timedelta(days=plan["duration_days"])).isoformat()
            
            cursor.execute(
                """
                INSERT INTO subscriptions VALUES 
                (?, ?, ?, ?, ?, ?, ?)
                """,
                (subscription_id, user_id, plan_type, start_date, end_date, "active", payment_method)
            )
            
            # Update user type to premium
            cursor.execute(
                "UPDATE users SET user_type = 'premium' WHERE user_id = ?",
                (user_id,)
            )
            
            self.db.commit()
            return True, subscription_id
        except Exception as e:
            # Rollback any changes in case of error
            self.db.connection.rollback()
            return False, f"Payment processing failed: {str(e)}"

    def cancel_subscription(self, subscription_id):
        """Cancel an active subscription"""
        try:
            cursor = self.db.get_cursor()
            
            # Update subscription status
            cursor.execute(
                "UPDATE subscriptions SET status = 'cancelled' WHERE subscription_id = ?",
                (subscription_id,)
            )
            
            # Get user_id from subscription
            cursor.execute(
                "SELECT user_id FROM subscriptions WHERE subscription_id = ?",
                (subscription_id,)
            )
            result = cursor.fetchone()
            
            if result:
                user_id = result[0]
                # Update user type back to standard
                cursor.execute(
                    "UPDATE users SET user_type = 'standard' WHERE user_id = ?",
                    (user_id,)
                )
            
            self.db.commit()
            return True, "Subscription cancelled successfully"
        except Exception as e:
            self.db.connection.rollback()
            return False, f"Failed to cancel subscription: {str(e)}"

    def get_subscription_status(self, subscription_id):
        """Get the current status of a subscription"""
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT s.*, u.username 
                FROM subscriptions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.subscription_id = ?
                """,
                (subscription_id,)
            )
            subscription = cursor.fetchone()
            
            if not subscription:
                return False, "Subscription not found"
            
            return True, {
                "subscription_id": subscription["subscription_id"],
                "user_id": subscription["user_id"],
                "username": subscription["username"],
                "plan_type": subscription["plan_type"],
                "start_date": subscription["start_date"],
                "end_date": subscription["end_date"],
                "status": subscription["status"],
                "payment_method": subscription["payment_method"]
            }
        except Exception as e:
            return False, f"Failed to get subscription status: {str(e)}"


# Main application class
class NatureTrailApp:
    """Main application class that ties everything together"""
    def __init__(self):
        try:
            self.db = Database()
            self.auth_manager = AuthenticationManager(self.db)
            self.trail_manager = TrailManager(self.db)
            self.sighting_manager = SightingManager(self.db)
            self.badge_manager = BadgeManager(self.db)
            self.payment_manager = PaymentManager(self.db)
        except Exception as e:
            st.error(f"Failed to initialize application: {str(e)}")
            raise
    
    def _validate_input(self, text, min_length=3, max_length=50):
        """Validate user input"""
        if not text or not isinstance(text, str):
            return False
        return min_length <= len(text.strip()) <= max_length
    
    def _validate_email(self, email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def run(self):
        """Run the application"""
        try:
            st.title("NatureTrail - Nature Exploration Platform")
            
            # Initialize session state
            if 'user' not in st.session_state:
                st.session_state.user = None
            
            # Sidebar for authentication
            with st.sidebar:
                st.header("Authentication")
                if st.session_state.user is None:
                    # Login/Register form
                    auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])
                    
                    with auth_tab1:
                        username = st.text_input("Username")
                        password = st.text_input("Password", type="password")
                        if st.button("Login"):
                            if not self._validate_input(username):
                                st.error("Invalid username format")
                            elif not self._validate_input(password, min_length=6):
                                st.error("Password must be at least 6 characters")
                            else:
                                success, result = self.auth_manager.authenticate(username, password)
                                if success:
                                    st.session_state.user = result
                                    st.success("Login successful!")
                                    st.rerun()
                                else:
                                    st.error(result)
                    
                    with auth_tab2:
                        new_username = st.text_input("New Username")
                        new_email = st.text_input("New Email")
                        new_password = st.text_input("New Password", type="password")
                        if st.button("Register"):
                            if not self._validate_input(new_username):
                                st.error("Username must be 3-50 characters")
                            elif not self._validate_email(new_email):
                                st.error("Invalid email format")
                            elif not self._validate_input(new_password, min_length=6):
                                st.error("Password must be at least 6 characters")
                            else:
                                success, result = self.auth_manager.register_user(
                                    new_username, new_email, new_password
                                )
                                if success:
                                    st.success("Registration successful! Please login.")
                                else:
                                    st.error(result)
                else:
                    st.write(f"Welcome, {st.session_state.user.username}!")
                    if st.button("Logout"):
                        self.auth_manager.logout()
                        st.session_state.user = None
                        st.rerun()
            
            # Main content
            if st.session_state.user is None:
                st.info("Please login or register to access the application.")
            else:
                # Main navigation
                tab1, tab2, tab3, tab4 = st.tabs([
                    "Trails", "Wildlife Sightings", "Badges", "Subscription"
                ])
                
                with tab1:
                    st.header("Trails")
                    try:
                        trails = self.trail_manager.get_all_trails()
                        if not trails:
                            st.info("No trails available.")
                        else:
                            for trail in trails:
                                with st.expander(trail.name):
                                    st.write(f"Location: {trail.location}")
                                    st.write(f"Difficulty: {trail.difficulty}")
                                    st.write(f"Length: {trail.length} miles")
                                    st.write(f"Elevation Gain: {trail.elevation_gain} feet")
                                    st.write(f"Description: {trail.description}")
                                    if trail.image_url:
                                        try:
                                            st.image(trail.image_url)
                                        except Exception as e:
                                            st.warning(f"Could not load trail image: {str(e)}")
                    except Exception as e:
                        st.error(f"Error loading trails: {str(e)}")
                
                with tab2:
                    st.header("Wildlife Sightings")
                    try:
                        sightings = self.sighting_manager.get_user_sightings(st.session_state.user.user_id)
                        if not sightings:
                            st.info("No wildlife sightings recorded yet.")
                        else:
                            for sighting in sightings:
                                with st.expander(f"{sighting.species} - {sighting.sighting_date}"):
                                    st.write(f"Quantity: {sighting.quantity}")
                                    st.write(f"Location: {sighting.latitude}, {sighting.longitude}")
                                    if sighting.description:
                                        st.write(f"Description: {sighting.description}")
                                    if sighting.image_url:
                                        try:
                                            st.image(sighting.image_url)
                                        except Exception as e:
                                            st.warning(f"Could not load sighting image: {str(e)}")
                    except Exception as e:
                        st.error(f"Error loading sightings: {str(e)}")
                
                with tab3:
                    st.header("Badges")
                    try:
                        badges = self.badge_manager.get_user_badges(st.session_state.user.user_id)
                        if not badges:
                            st.info("No badges earned yet.")
                        else:
                            for badge in badges:
                                st.write(f"🏆 {badge['name']}")
                                st.write(f"Description: {badge['description']}")
                                st.write(f"Earned: {badge['earned_date']}")
                    except Exception as e:
                        st.error(f"Error loading badges: {str(e)}")
                
                with tab4:
                    st.header("Subscription")
                    try:
                        if isinstance(st.session_state.user, PremiumUser):
                            st.success("You are a premium user!")
                            st.write(f"Subscription expires: {st.session_state.user.subscription_expiry}")
                        else:
                            st.info("Upgrade to premium for additional features!")
                            plans = self.payment_manager.get_subscription_plans()
                            for plan_type, plan in plans.items():
                                with st.expander(plan["name"]):
                                    st.write(f"Price: ${plan['price']}")
                                    st.write(f"Duration: {plan['duration_days']} days")
                                    if st.button(f"Subscribe to {plan['name']}"):
                                        success, result = self.payment_manager.create_payment_session(
                                            st.session_state.user.user_id, plan_type
                                        )
                                        if success:
                                            st.success("Payment session created! Redirecting to checkout...")
                                        else:
                                            st.error(result)
                    except Exception as e:
                        st.error(f"Error loading subscription information: {str(e)}")
        
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.stop()


if __name__ == "__main__":
    try:
        app = NatureTrailApp()
        app.run()
    except Exception as e:
        st.error(f"Failed to start application: {str(e)}")
        st.stop() 
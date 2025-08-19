import streamlit as st
import sqlite3
import hashlib
import time
import json
import random
import datetime
from PIL import Image
from transformers import pipeline
import matplotlib.pyplot as plt
import pandas as pd
import os
import zipfile

# ======================
# 1. CORE CONFIGURATION
# ======================
AD_PLATFORMS = {
    "start.io": {"ad_format": "banner", "min_reward": 0.02},
    "Google AdMob": {"ad_format": "interstitial", "min_reward": 0.03},
    "Unity Ads": {"ad_format": "rewarded", "min_reward": 0.04},
    "AppLovin": {"ad_format": "offerwall", "min_reward": 0.035}
}

# ======================
# 2. DATABASE SETUP
# ======================
def init_db():
    conn = sqlite3.connect('instacaption_enterprise.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP,
        caption_count INTEGER DEFAULT 0,
        ad_watched INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 0
    )''')
    
    # Ad configurations table
    c.execute('''CREATE TABLE IF NOT EXISTS ad_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform_name TEXT,
        api_key TEXT,
        priority INTEGER,
        is_active BOOLEAN DEFAULT 1,
        ads_per_use INTEGER DEFAULT 1,
        min_coins INTEGER DEFAULT 1
    )''')
    
    # Ad events table
    c.execute('''CREATE TABLE IF NOT EXISTS ad_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        platform_id INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        coins_earned INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(platform_id) REFERENCES ad_configs(id)
    )''')
    
    # Caption history
    c.execute('''CREATE TABLE IF NOT EXISTS captions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        image_hash TEXT,
        caption TEXT,
        hashtags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ======================
# 3. ENTERPRISE AD SYSTEM
# ======================
class AdMonetizationEngine:
    def __init__(self):
        self.conn = sqlite3.connect('instacaption_enterprise.db')
    
    def get_active_ad_platforms(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM ad_configs WHERE is_active=1 ORDER BY priority")
        return c.fetchall()
    
    def show_ads_to_user(self, user_id):
        platforms = self.get_active_ad_platforms()
        if not platforms:
            return False, "No active ad platforms configured"
        
        # Select highest priority platform
        platform = platforms[0]
        platform_id, platform_name, api_key, priority, is_active, ads_per_use, min_coins = platform
        
        # Simulate ad display (in real app, integrate SDK here)
        st.session_state['current_ad'] = {
            'platform': platform_name,
            'coins': min_coins,
            'start_time': time.time()
        }
        
        # Show ad container
        st.subheader(f"🔔 Ad from {platform_name}")
        with st.expander("Advertisement Content"):
            st.image("ad_placeholder.jpg", width=300)
            st.caption("Special offer for our users!")
            
            # Ad timer
            ad_duration = 5
            timer_placeholder = st.empty()
            for i in range(ad_duration, 0, -1):
                timer_placeholder.caption(f"Ad completes in: {i}s")
                time.sleep(1)
            timer_placeholder.success("✅ Ad completed! Thank you for supporting us.")
        
        # Reward user
        reward_coins = min_coins
        c = self.conn.cursor()
        c.execute("UPDATE users SET coins = coins + ?, ad_watched = ad_watched + 1 WHERE id=?", 
                 (reward_coins, user_id))
        c.execute("INSERT INTO ad_events (user_id, platform_id, coins_earned) VALUES (?, ?, ?)",
                 (user_id, platform_id, reward_coins))
        self.conn.commit()
        
        return True, f"Earned {reward_coins} coins!"

# ======================
# 4. AI CAPTION ENGINE
# ======================
class CaptionGenerator:
    def __init__(self):
        self.model = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
    
    def generate_caption(self, image, style="🤩 Smart"):
        result = self.model(image)[0]['generated_text']
        
        styles = {
            "🤩 Smart": result.capitalize(),
            "😂 Funny": f"LOL when I {result.split(' ', 1)[1]} 😂",
            "💬 Inspirational": f"In this moment: {result}. Cherish the journey. ✨",
            "➖ Minimalist": result.split(',')[0],
            "💼 Professional": f"High-quality image showing: {result}",
            "🎭 Dramatic": f"OMG! You won't BELIEVE what happens when {result}!!!"
        }
        
        final_caption = styles.get(style, styles["🤩 Smart"])
        
        # Generate hashtags
        keywords = [word for word in result.split() if len(word) > 3][:5]
        hashtags = " ".join([f"#{word}" for word in keywords]) 
        hashtags += " #InstaAI #SocialMedia"
        
        return final_caption, hashtags

# ======================
# 5. ENTERPRISE ADMIN DASHBOARD
# ======================
def enterprise_admin_dashboard():
    st.title("🚀 InstaCaption AI Enterprise Dashboard")
    st.subheader("Business Intelligence & Monetization Control Center")
    
    # Security
    admin_pass = st.sidebar.text_input("Admin Password", type="password", key="admin_pass")
    if admin_pass != os.getenv("ADMIN_PASSWORD", "admin123"):
        st.error("Unauthorized access")
        return
    
    # Dashboard tabs - FIXED INDENTATION
    tabs = st.tabs(["📊 Analytics", "💰 Ad Monetization", "👥 User Management", "⚙ Settings"])
    
    with tabs[0]:  # Analytics
        conn = sqlite3.connect('instacaption_enterprise.db')
        
        # Real-time metrics
        col1, col2, col3 = st.columns(3)
        total_users = pd.read_sql("SELECT COUNT(*) FROM users", conn).iloc[0,0]
        active_today = pd.read_sql("SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-1 day')", conn).iloc[0,0]
        total_ads = pd.read_sql("SELECT SUM(ad_watched) FROM users", conn).iloc[0,0]
        
        col1.metric("Total Users", total_users)
        col2.metric("Active Today", active_today)
        col3.metric("Ads Watched", total_ads)
        
        # User growth chart
        st.subheader("User Acquisition")
        user_growth = pd.read_sql('''SELECT DATE(created_at) as date, COUNT(*) as new_users 
                                  FROM users GROUP BY date''', conn)
        st.line_chart(user_growth.set_index('date'))
        
        # Revenue projection
        st.subheader("Revenue Forecast")
        ad_revenue = pd.read_sql('''SELECT a.platform_name, COUNT(e.id) as ad_count 
                                 FROM ad_events e 
                                 JOIN ad_configs a ON e.platform_id = a.id 
                                 GROUP BY a.platform_name''', conn)
        
        if not ad_revenue.empty:
            ad_revenue['revenue'] = ad_revenue['ad_count'] * ad_revenue['platform_name'].map(
                lambda x: AD_PLATFORMS.get(x, {}).get('min_reward', 0.02)
            )
            st.bar_chart(ad_revenue.set_index('platform_name')['revenue'])
        
        conn.close()
    
    with tabs[1]:  # Ad Monetization
        st.subheader("Ad Platform Integration")
        
        # Add new ad platform
        with st.form("new_ad_platform"):
            st.write("Configure New Ad Platform")
            platform = st.selectbox("Platform", list(AD_PLATFORMS.keys()))
            api_key = st.text_input("API Key")
            priority = st.slider("Priority (1=highest)", 1, 5, 3)
            ads_per_use = st.slider("Ads required per use", 0, 5, 1)
            min_coins = st.slider("Coins per ad", 1, 10, 3)
            is_active = st.checkbox("Activate Platform", True)
            
            if st.form_submit_button("Save Configuration"):
                conn = sqlite3.connect('instacaption_enterprise.db')
                c = conn.cursor()
                c.execute('''INSERT INTO ad_configs 
                          (platform_name, api_key, priority, is_active, ads_per_use, min_coins) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                         (platform, api_key, priority, int(is_active), ads_per_use, min_coins))
                conn.commit()
                conn.close()
                st.success(f"{platform} configuration saved!")
        
        # Current configurations
        st.subheader("Active Ad Platforms")
        conn = sqlite3.connect('instacaption_enterprise.db')
        configs = pd.read_sql("SELECT * FROM ad_configs ORDER BY priority", conn)
        
        if not configs.empty:
            # Show as interactive table
            edited_configs = st.data_editor(configs[['id', 'platform_name', 'priority', 
                                                    'is_active', 'ads_per_use', 'min_coins']],
                                          hide_index=True)
            
            # Save edits
            if st.button("Save Changes"):
                for _, row in edited_configs.iterrows():
                    c = conn.cursor()
                    c.execute('''UPDATE ad_configs 
                              SET priority=?, is_active=?, ads_per_use=?, min_coins=? 
                              WHERE id=?''',
                             (row['priority'], row['is_active'], row['ads_per_use'], 
                              row['min_coins'], row['id']))
                conn.commit()
                st.success("Configurations updated!")
        else:
            st.warning("No ad platforms configured yet")
        
        conn.close()
    
    with tabs[2]:  # User Management
        st.subheader("User Management")
        conn = sqlite3.connect('instacaption_enterprise.db')
        
        # User search
        search_term = st.text_input("Search users by device ID")
        if search_term:
            users = pd.read_sql(f"SELECT * FROM users WHERE device_id LIKE '%{search_term}%'", conn)
        else:
            users = pd.read_sql("SELECT * FROM users ORDER BY last_active DESC LIMIT 100", conn)
        
        if not users.empty:
            st.dataframe(users)
            
            # User actions
            user_id = st.selectbox("Select user for actions", users['id'])
            action = st.selectbox("Action", ["Add coins", "Reset password", "Export data"])
            
            if action == "Add coins":
                coins = st.number_input("Coins to add", min_value=1, max_value=100, value=10)
                if st.button("Apply"):
                    c = conn.cursor()
                    c.execute("UPDATE users SET coins = coins + ? WHERE id=?", (coins, user_id))
                    conn.commit()
                    st.success(f"Added {coins} coins to user {user_id}")
            
            if st.button("Export All User Data"):
                # Create ZIP with all data
                users = pd.read_sql("SELECT * FROM users", conn)
                captions = pd.read_sql("SELECT * FROM captions", conn)
                
                with zipfile.ZipFile('user_data_export.zip', 'w') as zipf:
                    users.to_csv('users.csv', index=False)
                    captions.to_csv('captions.csv', index=False)
                    zipf.write('users.csv')
                    zipf.write('captions.csv')
                
                with open('user_data_export.zip', 'rb') as f:
                    st.download_button("Download Export", f, file_name="user_data_export.zip")
        else:
            st.info("No users found")
        
        conn.close()
    
    with tabs[3]:  # Settings
        st.subheader("System Configuration")
        
        # Business settings
        with st.form("business_settings"):
            st.write("Monetization Strategy")
            free_tier_ads = st.slider("Free tier ads required", 0, 5, 1)
            premium_price = st.number_input("Premium subscription price ($)", min_value=0.99, max_value=99.99, value=4.99)
            premium_benefits = st.text_area("Premium benefits", 
                                          "✅ No ads\n✅ Priority processing\n✅ Advanced styles")
            
            if st.form_submit_button("Save Business Settings"):
                # Save to config file
                with open('business_config.json', 'w') as f:
                    json.dump({
                        "free_tier_ads": free_tier_ads,
                        "premium_price": premium_price,
                        "premium_benefits": premium_benefits
                    }, f)
                st.success("Business settings saved!")
        
        # System management
        st.subheader("System Management")
        if st.button("Backup Database"):
            conn = sqlite3.connect('instacaption_enterprise.db')
            with open('backup.sql', 'w') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
            with open('backup.sql', 'rb') as f:
                st.download_button("Download Backup", f, file_name="backup.sql")
        
        if st.button("Clear Cache"):
            st.cache_resource.clear()
            st.success("Cache cleared!")

# ======================
# 6. MAIN USER APP
# ======================
def main_user_app():
    st.title("📸 InstaCaption AI Pro")
    st.caption("Upload a photo → Get viral Instagram captions")
    
    # Initialize session
    if 'device_id' not in st.session_state:
        st.session_state.device_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        st.session_state.coins = 0
        st.session_state.caption_count = 0
        st.session_state.ads_watched = 0
        
        # Register new user
        conn = sqlite3.connect('instacaption_enterprise.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (device_id) VALUES (?)", (st.session_state.device_id,))
        conn.commit()
        conn.close()
    
    # User status bar
    with st.container():
        col1, col2 = st.columns([3,1])
        with col1:
            st.progress(st.session_state.caption_count % 10 / 10, text="Caption progress")
        with col2:
            st.metric("Coins", st.session_state.coins)
    
    # Upload section
    uploaded_file = st.file_uploader("Upload Instagram Photo", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, width=300)
        
        # Style selection
        style = st.radio("Caption Style:", 
                        ["🤩 Smart", "😂 Funny", "💬 Inspirational", "➖ Minimalist", "💼 Professional", "🎭 Dramatic"])
        
        # Ad requirement check
        conn = sqlite3.connect('instacaption_enterprise.db')
        c = conn.cursor()
        c.execute("SELECT ads_per_use FROM ad_configs WHERE is_active=1 ORDER BY priority LIMIT 1")
        ad_req = c.fetchone()
        ads_required = ad_req[0] if ad_req else 1
        conn.close()
        
        # Check if user needs to watch ads
        if st.session_state.caption_count > 0 and st.session_state.caption_count % 3 == 0:
            st.warning(f"Watch {ads_required} ad(s) to unlock this caption")
            ad_engine = AdMonetizationEngine()
            
            for i in range(ads_required):
                if st.button(f"Watch Ad {i+1}/{ads_required}"):
                    success, message = ad_engine.show_ads_to_user(st.session_state.user_id)
                    if success:
                        st.session_state.coins += st.session_state['current_ad']['coins']
                        st.session_state.ads_watched += 1
                        st.rerun()
        
        # Generate caption
        if st.button("✨ Generate Caption", disabled=st.session_state.caption_count % 3 == 0 and st.session_state.ads_watched < ads_required):
            with st.spinner("Creating your perfect caption..."):
                # Generate caption
                generator = CaptionGenerator()
                caption, hashtags = generator.generate_caption(img, style)
                
                # Save to history
                img_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
                conn = sqlite3.connect('instacaption_enterprise.db')
                c = conn.cursor()
                c.execute("INSERT INTO captions (user_id, image_hash, caption, hashtags) VALUES (?, ?, ?, ?)",
                         (st.session_state.user_id, img_hash, caption, hashtags))
                c.execute("UPDATE users SET caption_count = caption_count + 1, last_active = ? WHERE device_id = ?",
                         (datetime.datetime.now(), st.session_state.device_id))
                conn.commit()
                conn.close()
                
                # Update session
                st.session_state.caption_count += 1
                
                # Display results
                st.subheader("Your Caption")
                st.success(caption)
                st.subheader("Hashtags")
                st.code(hashtags)
                
                # Copy to clipboard
                st.download_button("📋 Copy to Clipboard", 
                                  f"{caption}\n\n{hashtags}", 
                                  "insta_caption.txt")

# ======================
# 7. APP ENTRY POINT
# ======================
def main():
    st.sidebar.title("InstaCaption AI")
    
    # Navigation
    app_mode = st.sidebar.selectbox("Navigation", ["📱 Main App", "🚀 Enterprise Dashboard"])
    
    if app_mode == "📱 Main App":
        main_user_app()
    else:
        enterprise_admin_dashboard()

if __name__ == "__main__":
    main()            is_active = st.checkbox("Activate Platform", True)
            
            if st.form_submit_button("Save Configuration"):
                conn = sqlite3.connect('instacaption_enterprise.db')
                c = conn.cursor()
                c.execute('''INSERT INTO ad_configs 
                          (platform_name, api_key, priority, is_active, ads_per_use, min_coins) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                         (platform, api_key, priority, int(is_active), ads_per_use, min_coins))
                conn.commit()
                conn.close()
                st.success(f"{platform} configuration saved!")
        
        # Current configurations
        st.subheader("Active Ad Platforms")
        conn = sqlite3.connect('instacaption_enterprise.db')
        configs = pd.read_sql("SELECT * FROM ad_configs ORDER BY priority", conn)
        
        if not configs.empty:
            # Show as interactive table
            edited_configs = st.data_editor(configs[['id', 'platform_name', 'priority', 
                                                    'is_active', 'ads_per_use', 'min_coins']],
                                          hide_index=True)
            
            # Save edits
            if st.button("Save Changes"):
                for _, row in edited_configs.iterrows():
                    c = conn.cursor()
                    c.execute('''UPDATE ad_configs 
                              SET priority=?, is_active=?, ads_per_use=?, min_coins=? 
                              WHERE id=?''',
                             (row['priority'], row['is_active'], row['ads_per_use'], 
                              row['min_coins'], row['id']))
                conn.commit()
                st.success("Configurations updated!")
        else:
            st.warning("No ad platforms configured yet")
        
        conn.close()
    
    with tabs[2]:  # User Management
        st.subheader("User Management")
        conn = sqlite3.connect('instacaption_enterprise.db')
        
        # User search
        search_term = st.text_input("Search users by device ID")
        if search_term:
            users = pd.read_sql(f"SELECT * FROM users WHERE device_id LIKE '%{search_term}%'", conn)
        else:
            users = pd.read_sql("SELECT * FROM users ORDER BY last_active DESC LIMIT 100", conn)
        
        if not users.empty:
            st.dataframe(users)
            
            # User actions
            user_id = st.selectbox("Select user for actions", users['id'])
            action = st.selectbox("Action", ["Add coins", "Reset password", "Export data"])
            
            if action == "Add coins":
                coins = st.number_input("Coins to add", min_value=1, max_value=100, value=10)
                if st.button("Apply"):
                    c = conn.cursor()
                    c.execute("UPDATE users SET coins = coins + ? WHERE id=?", (coins, user_id))
                    conn.commit()
                    st.success(f"Added {coins} coins to user {user_id}")
            
            if st.button("Export All User Data"):
                # Create ZIP with all data
                users = pd.read_sql("SELECT * FROM users", conn)
                captions = pd.read_sql("SELECT * FROM captions", conn)
                
                with zipfile.ZipFile('user_data_export.zip', 'w') as zipf:
                    users.to_csv('users.csv', index=False)
                    captions.to_csv('captions.csv', index=False)
                    zipf.write('users.csv')
                    zipf.write('captions.csv')
                
                with open('user_data_export.zip', 'rb') as f:
                    st.download_button("Download Export", f, file_name="user_data_export.zip")
        else:
            st.info("No users found")
        
        conn.close()
    
    with tabs[3]:  # Settings
        st.subheader("System Configuration")
        
        # Business settings
        with st.form("business_settings"):
            st.write("Monetization Strategy")
            free_tier_ads = st.slider("Free tier ads required", 0, 5, 1)
            premium_price = st.number_input("Premium subscription price ($)", min_value=0.99, max_value=99.99, value=4.99)
            premium_benefits = st.text_area("Premium benefits", 
                                          "✅ No ads\n✅ Priority processing\n✅ Advanced styles")
            
            if st.form_submit_button("Save Business Settings"):
                # Save to config file
                with open('business_config.json', 'w') as f:
                    json.dump({
                        "free_tier_ads": free_tier_ads,
                        "premium_price": premium_price,
                        "premium_benefits": premium_benefits
                    }, f)
                st.success("Business settings saved!")
        
        # System management
        st.subheader("System Management")
        if st.button("Backup Database"):
            conn = sqlite3.connect('instacaption_enterprise.db')
            with open('backup.sql', 'w') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
            with open('backup.sql', 'rb') as f:
                st.download_button("Download Backup", f, file_name="backup.sql")
        
        if st.button("Clear Cache"):
            st.cache_resource.clear()
            st.success("Cache cleared!")

# ======================
# 6. MAIN USER APP
# ======================
def main_user_app():
    st.title("📸 InstaCaption AI Pro")
    st.caption("Upload a photo → Get viral Instagram captions")
    
    # Initialize session
    if 'device_id' not in st.session_state:
        st.session_state.device_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        st.session_state.coins = 0
        st.session_state.caption_count = 0
        st.session_state.ads_watched = 0
        
        # Register new user
        conn = sqlite3.connect('instacaption_enterprise.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (device_id) VALUES (?)", (st.session_state.device_id,))
        conn.commit()
        conn.close()
    
    # User status bar
    with st.container():
        col1, col2 = st.columns([3,1])
        with col1:
            st.progress(st.session_state.caption_count % 10 / 10, text="Caption progress")
        with col2:
            st.metric("Coins", st.session_state.coins)
    
    # Upload section
    uploaded_file = st.file_uploader("Upload Instagram Photo", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, width=300)
        
        # Style selection
        style = st.radio("Caption Style:", 
                        ["🤩 Smart", "😂 Funny", "💬 Inspirational", "➖ Minimalist", "💼 Professional", "🎭 Dramatic"])
        
        # Ad requirement check
        conn = sqlite3.connect('instacaption_enterprise.db')
        c = conn.cursor()
        c.execute("SELECT ads_per_use FROM ad_configs WHERE is_active=1 ORDER BY priority LIMIT 1")
        ad_req = c.fetchone()
        ads_required = ad_req[0] if ad_req else 1
        conn.close()
        
        # Check if user needs to watch ads
        if st.session_state.caption_count > 0 and st.session_state.caption_count % 3 == 0:
            st.warning(f"Watch {ads_required} ad(s) to unlock this caption")
            ad_engine = AdMonetizationEngine()
            
            for i in range(ads_required):
                if st.button(f"Watch Ad {i+1}/{ads_required}"):
                    success, message = ad_engine.show_ads_to_user(st.session_state.user_id)
                    if success:
                        st.session_state.coins += st.session_state['current_ad']['coins']
                        st.session_state.ads_watched += 1
                        st.rerun()
        
        # Generate caption
        if st.button("✨ Generate Caption", disabled=st.session_state.caption_count % 3 == 0 and st.session_state.ads_watched < ads_required):
            with st.spinner("Creating your perfect caption..."):
                # Generate caption
                generator = CaptionGenerator()
                caption, hashtags = generator.generate_caption(img, style)
                
                # Save to history
                img_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
                conn = sqlite3.connect('instacaption_enterprise.db')
                c = conn.cursor()
                c.execute("INSERT INTO captions (user_id, image_hash, caption, hashtags) VALUES (?, ?, ?, ?)",
                         (st.session_state.user_id, img_hash, caption, hashtags))
                c.execute("UPDATE users SET caption_count = caption_count + 1, last_active = ? WHERE device_id = ?",
                         (datetime.datetime.now(), st.session_state.device_id))
                conn.commit()
                conn.close()
                
                # Update session
                st.session_state.caption_count += 1
                
                # Display results
                st.subheader("Your Caption")
                st.success(caption)
                st.subheader("Hashtags")
                st.code(hashtags)
                
                # Copy to clipboard
                st.download_button("📋 Copy to Clipboard", 
                                  f"{caption}\n\n{hashtags}", 
                                  "insta_caption.txt")

# ======================
# 7. APP ENTRY POINT
# ======================
def main():
    st.sidebar.title("InstaCaption AI")
    
    # Navigation
    app_mode = st.sidebar.selectbox("Navigation", ["📱 Main App", "🚀 Enterprise Dashboard"])
    
    if app_mode == "📱 Main App":
        main_user_app()
    else:
        enterprise_admin_dashboard()

if __name__ == "__main__":
    main() else:
            st.warning("No ad platforms configured yet")
        
        conn.close()
    
    with tabs[2]:  # User Management
        st.subheader("User Management")
        conn = sqlite3.connect('instacaption_enterprise.db')
        
        # User search
        search_term = st.text_input("Search users by device ID")
        if search_term:
            users = pd.read_sql(f"SELECT * FROM users WHERE device_id LIKE '%{search_term}%'", conn)
        else:
            users = pd.read_sql("SELECT * FROM users ORDER BY last_active DESC LIMIT 100", conn)
        
        if not users.empty:
            st.dataframe(users)
            
            # User actions
            user_id = st.selectbox("Select user for actions", users['id'])
            action = st.selectbox("Action", ["Add coins", "Reset password", "Export data"])
            
            if action == "Add coins":
                coins = st.number_input("Coins to add", min_value=1, max_value=100, value=10)
                if st.button("Apply"):
                    c = conn.cursor()
                    c.execute("UPDATE users SET coins = coins + ? WHERE id=?", (coins, user_id))
                    conn.commit()
                    st.success(f"Added {coins} coins to user {user_id}")
            
            if st.button("Export All User Data"):
                # Create ZIP with all data
                users = pd.read_sql("SELECT * FROM users", conn)
                captions = pd.read_sql("SELECT * FROM captions", conn)
                
                with zipfile.ZipFile('user_data_export.zip', 'w') as zipf:
                    users.to_csv('users.csv', index=False)
                    captions.to_csv('captions.csv', index=False)
                    zipf.write('users.csv')
                    zipf.write('captions.csv')
                
                with open('user_data_export.zip', 'rb') as f:
                    st.download_button("Download Export", f, file_name="user_data_export.zip")
        else:
            st.info("No users found")
        
        conn.close()
    
    with tabs[3]:  # Settings
        st.subheader("System Configuration")
        
        # Business settings
        with st.form("business_settings"):
            st.write("Monetization Strategy")
            free_tier_ads = st.slider("Free tier ads required", 0, 5, 1)
            premium_price = st.number_input("Premium subscription price ($)", min_value=0.99, max_value=99.99, value=4.99)
            premium_benefits = st.text_area("Premium benefits", 
                                          "✅ No ads\n✅ Priority processing\n✅ Advanced styles")
            
            if st.form_submit_button("Save Business Settings"):
                # Save to config file
                with open('business_config.json', 'w') as f:
                    json.dump({
                        "free_tier_ads": free_tier_ads,
                        "premium_price": premium_price,
                        "premium_benefits": premium_benefits
                    }, f)
                st.success("Business settings saved!")
        
        # System management
        st.subheader("System Management")
        if st.button("Backup Database"):
            conn = sqlite3.connect('instacaption_enterprise.db')
            with open('backup.sql', 'w') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
            with open('backup.sql', 'rb') as f:
                st.download_button("Download Backup", f, file_name="backup.sql")
        
        if st.button("Clear Cache"):
            st.cache_resource.clear()
            st.success("Cache cleared!")

# ======================
# 6. MAIN USER APP
# ======================
def main_user_app():
    st.title("📸 InstaCaption AI Pro")
    st.caption("Upload a photo → Get viral Instagram captions")
    
    # Initialize session
    if 'device_id' not in st.session_state:
        st.session_state.device_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        st.session_state.coins = 0
        st.session_state.caption_count = 0
        st.session_state.ads_watched = 0
        
        # Register new user
        conn = sqlite3.connect('instacaption_enterprise.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (device_id) VALUES (?)", (st.session_state.device_id,))
        conn.commit()
        conn.close()
    
    # User status bar
    with st.container():
        col1, col2 = st.columns([3,1])
        with col1:
            st.progress(st.session_state.caption_count % 10 / 10, text="Caption progress")
        with col2:
            st.metric("Coins", st.session_state.coins)
    
    # Upload section
    uploaded_file = st.file_uploader("Upload Instagram Photo", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, width=300)
        
        # Style selection
        style = st.radio("Caption Style:", 
                        ["🤩 Smart", "😂 Funny", "💬 Inspirational", "➖ Minimalist", "💼 Professional", "🎭 Dramatic"])
        
        # Ad requirement check
        conn = sqlite3.connect('instacaption_enterprise.db')
        c = conn.cursor()
        c.execute("SELECT ads_per_use FROM ad_configs WHERE is_active=1 ORDER BY priority LIMIT 1")
        ad_req = c.fetchone()
        ads_required = ad_req[0] if ad_req else 1
        conn.close()
        
        # Check if user needs to watch ads
        if st.session_state.caption_count > 0 and st.session_state.caption_count % 3 == 0:
            st.warning(f"Watch {ads_required} ad(s) to unlock this caption")
            ad_engine = AdMonetizationEngine()
            
            for i in range(ads_required):
                if st.button(f"Watch Ad {i+1}/{ads_required}"):
                    success, message = ad_engine.show_ads_to_user(st.session_state.user_id)
                    if success:
                        st.session_state.coins += st.session_state['current_ad']['coins']
                        st.session_state.ads_watched += 1
                        st.rerun()
        
        # Generate caption
        if st.button("✨ Generate Caption", disabled=st.session_state.caption_count % 3 == 0 and st.session_state.ads_watched < ads_required):
            with st.spinner("Creating your perfect caption..."):
                # Generate caption
                generator = CaptionGenerator()
                caption, hashtags = generator.generate_caption(img, style)
                
                # Save to history
                img_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
                conn = sqlite3.connect('instacaption_enterprise.db')
                c = conn.cursor()
                c.execute("INSERT INTO captions (user_id, image_hash, caption, hashtags) VALUES (?, ?, ?, ?)",
                         (st.session_state.user_id, img_hash, caption, hashtags))
                c.execute("UPDATE users SET caption_count = caption_count + 1, last_active = ? WHERE device_id = ?",
                         (datetime.datetime.now(), st.session_state.device_id))
                conn.commit()
                conn.close()
                
                # Update session
                st.session_state.caption_count += 1
                
                # Display results
                st.subheader("Your Caption")
                st.success(caption)
                st.subheader("Hashtags")
                st.code(hashtags)
                
                # Copy to clipboard
                st.download_button("📋 Copy to Clipboard", 
                                  f"{caption}\n\n{hashtags}", 
                                  "insta_caption.txt")

# ======================
# 7. APP ENTRY POINT
# ======================
def main():
    st.sidebar.title("InstaCaption AI")
    
    # Navigation
    app_mode = st.sidebar.selectbox("Navigation", ["📱 Main App", "🚀 Enterprise Dashboard"])
    
    if app_mode == "📱 Main App":
        main_user_app()
    else:
        enterprise_admin_dashboard()

if __name__ == "__main__":
    main()

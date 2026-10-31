# 🍲 SmartFood — Stop Food Waste & Feed People

A simple, friendly website that connects **College Canteens, Mess Halls, and Restaurants** with **Local Charities, Night Shelters, and Orphanages**.

Canteens and restaurants can track their daily cooking and quickly give away fresh extra food. Charities can see what food is available nearby, book what they need, and pick it up using a simple 4-digit code.

---

## 🌟 How It Works

### 👨‍🍳 For Canteens & Restaurants:
1. **Daily Food Planner:** Enter how many plates you cooked today and how many people ate. If you cooked too much, the system shows how many extra plates you have left.
2. **Share Extra Food:** Post your extra fresh food in 1 minute. Add dish name, how many plates you have, when it was cooked, and how to store it (hot or cold).
3. **Pickups & Secret Codes:** When a local charity books your food, you will see their volunteer's name and phone number. When the volunteer arrives, ask for their **4-digit secret code** before handing over the food.
4. **Food & Money Saved:** See clear numbers on how many plates you saved from the dustbin and how much food value you rescued.

### 🤝 For Charities & Shelters (NGOs):
1. **How Many People Need Food Today:** Enter how many people you need to feed today (e.g. 150 plates). A progress meter shows how many plates you have collected so far and how many you still need.
2. **Available Extra Food:** See fresh food posted by canteens and restaurants near you. Filter by Veg/Non-Veg.
3. **Book Food in 1 Click:** Pick how many plates you want, enter the volunteer's name who is going to collect it, and click book. You will immediately get a **4-digit secret code**.
4. **Pickup & Feed People:** The volunteer goes to the canteen, shows the 4-digit code to the cook, picks up the food, and feeds hungry people!

---

## ⚡ Try It Right Now (Quick Test Accounts)

You can click any of the **1-Click Demo Login** buttons on the login page:

| Role | Email | Password | What You Can Test |
| :--- | :--- | :--- | :--- |
| **Canteen Cook** | `canteen@campus.edu` | `password123` | Log cooked food and post extra meals |
| **Restaurant Chef** | `chef@urbanbistro.com` | `password123` | Post buffet meals and check pickup codes |
| **Charity Volunteer** | `volunteer@robinhood.org` | `password123` | See available food and book meals |
| **Night Shelter** | `shelter@hopehome.org` | `password123` | Track daily people to feed |

*You can also click **Create New Account** to sign up with your own email.*

---

## 💻 How to Run on Your Computer

1. Open your terminal and go to the project folder:
```bash
cd /Users/akshay/.gemini/antigravity/scratch/smart-food-platform
```

2. Install the simple requirements:
```bash
pip install -r requirements.txt
```

3. Run the website:
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🚀 How to Deploy to a Public Website

### Method 1: Streamlit Cloud (Free & Easiest)
1. Upload this folder to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Select your repository and choose `app.py`.
4. Click **Deploy**. Your website will be live on the internet!

### Method 2: Render or Railway
This project includes a ready `Procfile`.
Just connect your GitHub repository to [Render](https://render.com) or [Railway](https://railway.app), and it runs automatically.

### Method 3: Docker
This project includes a ready `Dockerfile`:
```bash
docker build -t smartfood .
docker run -d -p 8501:8501 smartfood
```

---

## 🧪 Tests
Run tests anytime to check that booking and inventory work properly:
```bash
pytest -v
```
All 8 tests check user login, inventory booking, and food calculation.

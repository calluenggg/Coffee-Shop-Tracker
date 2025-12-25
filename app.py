import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Cafe POS", page_icon="☕")

# --- 1. MENU SETTINGS (Edit this anytime!) ---
MENU = {
    "Espresso": 120, "Americano": 120, "Latte": 150, "Cappuccino": 150,
    "Spanish Latte": 170, "Cold Brew": 160, "Pourover": 180, "Cookie": 80
}

# --- 2. CONNECT TO GOOGLE SHEETS ---
# Streamlit manages secrets securely. We will set this up in Step 3.
def get_google_sheet():
    # Load credentials from Streamlit Secrets
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Coffee Tracker")
    return sheet

try:
    sheet = get_google_sheet()
    # Check/Create Sales Tab
    try: ws_sales = sheet.worksheet("Sales")
    except: 
        ws_sales = sheet.add_worksheet(title="Sales", rows=1000, cols=5)
        ws_sales.append_row(["Date", "Item", "Qty", "Price", "Total"])
        
    # Check/Create Expenses Tab
    try: ws_expenses = sheet.worksheet("Expenses")
    except: 
        ws_expenses = sheet.add_worksheet(title="Expenses", rows=1000, cols=4)
        ws_expenses.append_row(["Date", "Category", "Item", "Cost"])
        
    st.success("✅ System Online")
except Exception as e:
    st.error(f"❌ Connection Error: {e}")
    st.stop()

# --- 3. SIDEBAR: NAVIGATION ---
st.sidebar.title("☕ Cafe Manager")
page = st.sidebar.radio("Go to", ["New Order", "Log Expense", "Dashboard"])

# --- PAGE: NEW ORDER ---
if page == "New Order":
    st.header("☕ New Order")
    
    # Inputs
    item_name = st.selectbox("Select Item", options=MENU.keys())
    
    # Auto-update price based on selection
    default_price = MENU[item_name]
    
    col1, col2 = st.columns(2)
    with col1:
        qty = st.number_input("Quantity", min_value=1, value=1)
    with col2:
        price = st.number_input("Price", value=default_price)
    
    # Live Total Calculation
    total = qty * price
    st.metric(label="Total to Charge", value=f"P{total:,.2f}")
    
    if st.button("Record Sale", type="primary", use_container_width=True):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            ws_sales.append_row([timestamp, item_name, qty, price, total])
            st.toast(f"✅ Sold: {qty}x {item_name} for P{total}!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- PAGE: LOG EXPENSE ---
elif page == "Log Expense":
    st.header("📉 Log Expense")
    
    cat = st.selectbox("Category", ["Beans", "Milk", "Ice", "Cups", "Other"])
    item = st.text_input("Item Description")
    cost = st.number_input("Total Cost", min_value=0.0, step=10.0)
    
    if st.button("Save Expense", type="primary", use_container_width=True):
        if item and cost > 0:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                ws_expenses.append_row([timestamp, cat, item, cost])
                st.toast(f"✅ Saved Expense: {item}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please fill in item name and cost.")

# --- PAGE: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Profit Dashboard")
    
    if st.button("Refresh Data"):
        st.cache_data.clear() # Clears cache to force reload
    
    # Fetch Data
    df_s = pd.DataFrame(ws_sales.get_all_records())
    df_e = pd.DataFrame(ws_expenses.get_all_records())
    
    # Date Filtering (Current Month)
    current_month = datetime.now().strftime("%Y-%m")
    
    sales_total = 0
    if not df_s.empty:
        # Convert date column to string ensuring format matches
        df_s['Date'] = df_s['Date'].astype(str)
        sales_total = df_s[df_s['Date'].str.contains(current_month, na=False)]['Total'].sum()

    exp_total = 0
    if not df_e.empty:
        df_e['Date'] = df_e['Date'].astype(str)
        exp_total = df_e[df_e['Date'].str.contains(current_month, na=False)]['Cost'].sum()
        
    net = sales_total - exp_total
    
    # Scorecard
    col1, col2, col3 = st.columns(3)
    col1.metric("Sales (Month)", f"P{sales_total:,.2f}")
    col2.metric("Expenses (Month)", f"P{exp_total:,.2f}")
    col3.metric("Net Profit", f"P{net:,.2f}", delta_color="normal")
    
    st.divider()
    
    # Last 5 Transactions
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Last 5 Sales")
        if not df_s.empty:
            st.dataframe(df_s[['Date', 'Item', 'Total']].tail(5).iloc[::-1], hide_index=True)
            
    with c2:
        st.subheader("Last 5 Expenses")
        if not df_e.empty:
            st.dataframe(df_e[['Date', 'Item', 'Cost']].tail(5).iloc[::-1], hide_index=True)
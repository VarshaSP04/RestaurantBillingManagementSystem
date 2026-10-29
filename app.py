"""Restaurant Web Portal & Digital Receipt Server
Connects to Restaurant.db and serves real digital receipts and web ordering.
"""

import os
import sqlite3
import datetime
import qrcode
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_file

app = Flask(__name__)
DB_NAME = "Restaurant.db"
PORT = 8000

MENU = {
    1: {"item": "Pizza", "price": 240.0, "icon": "🍕"},
    2: {"item": "Burger", "price": 125.0, "icon": "🍔"},
    3: {"item": "Ice cream", "price": 80.0, "icon": "🍨"},
    4: {"item": "Drinks", "price": 60.0, "icon": "🥤"},
}

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Restaurantrecords (
            ordno TEXT PRIMARY KEY,
            piz TEXT,
            bur TEXT,
            ice TEXT,
            dr TEXT,
            ct TEXT,
            sb TEXT,
            tax TEXT,
            sr TEXT,
            tot TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CustomerOrders (
            order_no TEXT PRIMARY KEY,
            customer_phone TEXT,
            order_time TEXT,
            items_summary TEXT,
            cost_of_meal REAL,
            tax REAL,
            service_charge REAL,
            grand_total REAL,
            qr_file TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

RECEIPT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Receipt - Order #{{ order.ordno }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #f97316;
            --primary-dark: #ea580c;
            --bg: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.95);
            --border: rgba(255, 255, 255, 0.1);
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, var(--bg) 70%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }

        .receipt-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 20px;
            max-width: 440px;
            width: 100%;
            padding: 32px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 40px rgba(249, 115, 22, 0.15);
            backdrop-filter: blur(16px);
            position: relative;
        }

        .header {
            text-align: center;
            border-bottom: 2px dashed rgba(255, 255, 255, 0.15);
            padding-bottom: 20px;
            margin-bottom: 20px;
        }

        .badge-verified {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(34, 197, 94, 0.15);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
        }

        .restaurant-title {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #fff 40%, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .order-meta {
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 12px;
            font-family: 'Space Mono', monospace;
        }

        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }

        .items-table th {
            text-align: left;
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 600;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .items-table td {
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .items-table .text-right {
            text-align: right;
            font-family: 'Space Mono', monospace;
        }

        .totals {
            border-top: 2px dashed rgba(255, 255, 255, 0.15);
            padding-top: 16px;
            margin-top: 10px;
            font-size: 14px;
        }

        .totals-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: var(--text-muted);
        }

        .grand-total {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            font-size: 20px;
            font-weight: 800;
            color: #fff;
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }

        .grand-total .amount {
            color: var(--primary);
            font-family: 'Space Mono', monospace;
            font-size: 24px;
        }

        .qr-section {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            margin-top: 24px;
            text-align: center;
        }

        .qr-img {
            width: 150px;
            height: 150px;
            border-radius: 10px;
            background: #fff;
            padding: 8px;
            margin-bottom: 10px;
        }

        .qr-help {
            font-size: 12px;
            color: var(--text-muted);
        }

        .actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 24px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 18px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            border: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            box-shadow: 0 4px 15px rgba(249, 115, 22, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(249, 115, 22, 0.4);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-main);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }

        .nav-link {
            display: block;
            text-align: center;
            margin-top: 16px;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 13px;
        }

        .nav-link:hover {
            color: #fff;
        }

        @media print {
            body {
                background: white;
                color: black;
            }
            .receipt-card {
                border: none;
                box-shadow: none;
                background: white;
                color: black;
            }
            .actions, .nav-link {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="receipt-card">
        <div class="header">
            <div class="badge-verified">✓ Verified Transaction</div>
            <h1 class="restaurant-title">Varsha's Kitchen</h1>
            <p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Authentic Dining & Cafe</p>
            <div class="order-meta">
                <span>ORDER: <strong>#{{ order.ordno }}</strong></span>
                <span>{{ order.order_time or "Today" }}</span>
            </div>
            {% if order.customer_phone %}
            <div class="order-meta" style="margin-top: 4px;">
                <span>CUSTOMER:</span>
                <span>+91 {{ order.customer_phone }}</span>
            </div>
            {% endif %}
        </div>

        <table class="items-table">
            <thead>
                <tr>
                    <th>Item</th>
                    <th style="text-align: center;">Qty</th>
                    <th class="text-right">Price</th>
                    <th class="text-right">Total</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td><strong>{{ item.name }}</strong></td>
                    <td style="text-align: center;">{{ item.qty }}</td>
                    <td class="text-right">Rs. {{ "%.2f"|format(item.price) }}</td>
                    <td class="text-right">Rs. {{ "%.2f"|format(item.total) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="totals">
            <div class="totals-row">
                <span>Cost of Meal</span>
                <span style="font-family: 'Space Mono';">Rs. {{ "%.2f"|format(order.cost_of_meal) }}</span>
            </div>
            <div class="totals-row">
                <span>GST / Tax (18%)</span>
                <span style="font-family: 'Space Mono';">Rs. {{ "%.2f"|format(order.tax) }}</span>
            </div>
            <div class="totals-row">
                <span>Service Charge</span>
                <span style="font-family: 'Space Mono';">Rs. {{ "%.2f"|format(order.service_charge) }}</span>
            </div>
            <div class="grand-total">
                <span>Grand Total</span>
                <span class="amount">Rs. {{ "%.2f"|format(order.grand_total) }}</span>
            </div>
        </div>

        <div class="qr-section">
            <img class="qr-img" src="/qr/{{ order.ordno }}" alt="Receipt QR Code">
            <p class="qr-help">Scan to verify receipt or pay directly via UPI</p>
        </div>

        <div class="actions">
            <button class="btn btn-secondary" onclick="window.print()">🖨️ Print Bill</button>
            <a class="btn btn-primary" href="upi://pay?pa=varsha@upi&pn=VarshasKitchen&am={{ order.grand_total }}&cu=INR&tn=Order_{{ order.ordno }}">💳 Pay via UPI</a>
        </div>

        <a class="nav-link" href="/">← Back to Restaurant Ordering Counter</a>
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restaurant Smart POS & Billing Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #f97316;
            --primary-dark: #ea580c;
            --bg: #090d16;
            --surface: #111827;
            --surface-card: #1f2937;
            --border: rgba(255, 255, 255, 0.1);
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at top right, #1e1b4b 0%, var(--bg) 60%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 36px;
            flex-wrap: wrap;
            gap: 16px;
        }

        .header-title h1 {
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -1px;
            background: linear-gradient(135deg, #fff 30%, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-title p {
            color: var(--text-muted);
            font-size: 14px;
            margin-top: 4px;
        }

        .lookup-box {
            display: flex;
            gap: 8px;
            background: var(--surface);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid var(--border);
        }

        .lookup-input {
            background: transparent;
            border: none;
            padding: 8px 14px;
            color: #fff;
            font-size: 14px;
            outline: none;
        }

        .lookup-btn {
            background: var(--primary);
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }

        .lookup-btn:hover {
            background: var(--primary-dark);
        }

        .grid {
            display: grid;
            grid-template-columns: 1.6fr 1.2fr;
            gap: 28px;
        }

        @media (max-width: 860px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }

        .card-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .menu-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 16px;
        }

        .menu-item {
            background: var(--surface-card);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s, border-color 0.2s;
        }

        .menu-item:hover {
            transform: translateY(-3px);
            border-color: rgba(249, 115, 22, 0.4);
        }

        .item-icon {
            font-size: 32px;
            margin-bottom: 12px;
        }

        .item-name {
            font-weight: 700;
            font-size: 16px;
        }

        .item-price {
            color: var(--primary);
            font-family: 'Space Mono', monospace;
            font-weight: 700;
            margin: 6px 0 14px 0;
            font-size: 15px;
        }

        .item-controls {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 4px 8px;
        }

        .qty-btn {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border: none;
            width: 28px;
            height: 28px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .qty-btn:hover {
            background: var(--primary);
        }

        .qty-display {
            font-family: 'Space Mono', monospace;
            font-weight: 700;
            width: 28px;
            text-align: center;
        }

        .cart-items {
            max-height: 240px;
            overflow-y: auto;
            margin-bottom: 20px;
        }

        .cart-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 14px;
        }

        .phone-input {
            width: 100%;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border);
            padding: 12px 16px;
            border-radius: 10px;
            color: #fff;
            font-size: 15px;
            margin-bottom: 18px;
            outline: none;
        }

        .phone-input:focus {
            border-color: var(--primary);
        }

        .bill-summary {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .summary-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: var(--text-muted);
        }

        .summary-total {
            display: flex;
            justify-content: space-between;
            font-size: 18px;
            font-weight: 800;
            color: #fff;
            border-top: 1px solid var(--border);
            padding-top: 10px;
            margin-top: 10px;
        }

        .btn-checkout {
            width: 100%;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 14px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            box-shadow: 0 6px 20px rgba(249, 115, 22, 0.35);
            transition: 0.2s;
        }

        .btn-checkout:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(249, 115, 22, 0.5);
        }

        .orders-section {
            margin-top: 40px;
        }

        .orders-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 16px;
        }

        .orders-table th {
            text-align: left;
            padding: 12px;
            background: var(--surface-card);
            color: var(--text-muted);
            font-size: 12px;
            text-transform: uppercase;
        }

        .orders-table td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .badge-ord {
            background: rgba(249, 115, 22, 0.15);
            color: var(--primary);
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-family: 'Space Mono', monospace;
        }

        .link-receipt {
            color: #38bdf8;
            text-decoration: none;
            font-weight: 600;
        }

        .link-receipt:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>🍽️ Varsha's Kitchen</h1>
                <p>Smart POS & Digital Billing System</p>
            </div>
            <form class="lookup-box" onsubmit="event.preventDefault(); viewReceipt();">
                <input class="lookup-input" id="lookupId" type="text" placeholder="Enter Order # or Mobile">
                <button class="lookup-btn" type="submit">View Receipt</button>
            </form>
        </div>

        <div class="grid">
            <!-- Menu Card -->
            <div class="card">
                <h2 class="card-title">📖 Menu Selection</h2>
                <div class="menu-grid">
                    {% for id, item in menu.items() %}
                    <div class="menu-item">
                        <div>
                            <div class="item-icon">{{ item.icon }}</div>
                            <div class="item-name">{{ item.item }}</div>
                            <div class="item-price">Rs. {{ "%.2f"|format(item.price) }}</div>
                        </div>
                        <div class="item-controls">
                            <button class="qty-btn" onclick="updateQty({{ id }}, -1)">-</button>
                            <span class="qty-display" id="qty-{{ id }}">0</span>
                            <button class="qty-btn" onclick="updateQty({{ id }}, 1)">+</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Cart & Billing -->
            <div class="card">
                <h2 class="card-title">🛒 Order Summary</h2>
                <div class="cart-items" id="cartContainer">
                    <p style="color: var(--text-muted); text-align: center; padding: 20px;">No items selected.</p>
                </div>

                <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 6px; display: block;">Customer Mobile Number</label>
                <input class="phone-input" id="customerPhone" type="tel" placeholder="e.g. 9876543210" maxlength="10">

                <div class="bill-summary">
                    <div class="summary-row">
                        <span>Cost of Meal</span>
                        <span id="subtotalTxt">Rs. 0.00</span>
                    </div>
                    <div class="summary-row">
                        <span>GST (18%)</span>
                        <span id="taxTxt">Rs. 0.00</span>
                    </div>
                    <div class="summary-row">
                        <span>Service Charge</span>
                        <span id="serviceTxt">Rs. 0.00</span>
                    </div>
                    <div class="summary-total">
                        <span>Total Due</span>
                        <span style="color: var(--primary);" id="totalTxt">Rs. 0.00</span>
                    </div>
                </div>

                <button class="btn-checkout" onclick="placeOrder()">⚡ Generate Bill & QR Receipt</button>
            </div>
        </div>

        <!-- Recent Orders -->
        <div class="card orders-section">
            <h2 class="card-title">📋 Recent Orders in Restaurant.db</h2>
            <table class="orders-table">
                <thead>
                    <tr>
                        <th>Order</th>
                        <th>Pizza</th>
                        <th>Burger</th>
                        <th>Ice Cream</th>
                        <th>Drinks</th>
                        <th>Total</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in recent_orders %}
                    <tr>
                        <td><span class="badge-ord">#{{ order.ordno }}</span></td>
                        <td>{{ order.piz }}</td>
                        <td>{{ order.bur }}</td>
                        <td>{{ order.ice }}</td>
                        <td>{{ order.dr }}</td>
                        <td style="font-family: 'Space Mono'; font-weight: 700;">Rs. {{ order.tot }}</td>
                        <td><a class="link-receipt" href="/receipt/{{ order.ordno }}">Open Receipt ↗</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const menu = {{ menu_json|safe }};
        const cart = { 1: 0, 2: 0, 3: 0, 4: 0 };

        function updateQty(id, delta) {
            cart[id] = Math.max(0, (cart[id] || 0) + delta);
            document.getElementById('qty-' + id).innerText = cart[id];
            renderCart();
        }

        function renderCart() {
            const container = document.getElementById('cartContainer');
            let hasItems = false;
            let cost = 0;
            let html = '';

            for (let id in cart) {
                const qty = cart[id];
                if (qty > 0) {
                    hasItems = true;
                    const item = menu[id];
                    const line = item.price * qty;
                    cost += line;
                    html += `
                        <div class="cart-row">
                            <span>${item.icon} ${item.item} × ${qty}</span>
                            <span style="font-family: 'Space Mono'">Rs. ${line.toFixed(2)}</span>
                        </div>
                    `;
                }
            }

            container.innerHTML = hasItems ? html : '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No items selected.</p>';

            const tax = cost * 0.18;
            const service = cost > 0 ? (cost / 99) : 0;
            const total = cost + tax + service;

            document.getElementById('subtotalTxt').innerText = 'Rs. ' + cost.toFixed(2);
            document.getElementById('taxTxt').innerText = 'Rs. ' + tax.toFixed(2);
            document.getElementById('serviceTxt').innerText = 'Rs. ' + service.toFixed(2);
            document.getElementById('totalTxt').innerText = 'Rs. ' + total.toFixed(2);
        }

        async function placeOrder() {
            const phone = document.getElementById('customerPhone').value.trim();
            if (!/^[0-9]{10}$/.test(phone)) {
                alert('Please enter a valid 10-digit mobile number!');
                return;
            }

            const totalQty = Object.values(cart).reduce((a, b) => a + b, 0);
            if (totalQty === 0) {
                alert('Please select at least one item from the menu!');
                return;
            }

            const res = await fetch('/api/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cart: cart, phone: phone })
            });

            const data = await res.json();
            if (data.success) {
                window.location.href = data.receipt_url;
            } else {
                alert('Error placing order: ' + (data.error || 'Unknown'));
            }
        }

        function viewReceipt() {
            const query = document.getElementById('lookupId').value.trim();
            if (query) {
                window.location.href = '/receipt/' + query;
            }
        }
    </script>
</body>
</html>
"""

def parse_order_row(row):
    """Formats a database row into an order dictionary and items list."""
    ordno = str(row["ordno"])
    piz = int(row["piz"] or 0)
    bur = int(row["bur"] or 0)
    ice = int(row["ice"] or 0)
    dr = int(row["dr"] or 0)

    cost_of_meal = float(row["ct"] or 0.0)
    tax = float(row["tax"] or 0.0)
    service_charge = float(row["sr"] or 0.0)
    grand_total = float(row["tot"] or 0.0)

    items = []
    if piz > 0:
        items.append({"name": "Pizza", "qty": piz, "price": 240.0, "total": piz * 240.0})
    if bur > 0:
        items.append({"name": "Burger", "qty": bur, "price": 125.0, "total": bur * 125.0})
    if ice > 0:
        items.append({"name": "Ice cream", "qty": ice, "price": 80.0, "total": ice * 80.0})
    if dr > 0:
        items.append({"name": "Drinks", "qty": dr, "price": 60.0, "total": dr * 60.0})

    # Fetch customer phone & timestamp if available in CustomerOrders
    conn = get_db()
    c_order = conn.execute("SELECT * FROM CustomerOrders WHERE order_no = ?", (ordno,)).fetchone()
    conn.close()

    customer_phone = c_order["customer_phone"] if c_order else None
    order_time = c_order["order_time"] if c_order else None

    order = {
        "ordno": ordno,
        "cost_of_meal": cost_of_meal,
        "tax": tax,
        "service_charge": service_charge,
        "grand_total": grand_total,
        "customer_phone": customer_phone,
        "order_time": order_time,
    }
    return order, items


@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Restaurantrecords ORDER BY CAST(ordno AS INTEGER) DESC LIMIT 10")
    recent_orders = cursor.fetchall()
    conn.close()

    menu_json = {k: {"item": v["item"], "price": v["price"], "icon": v["icon"]} for k, v in MENU.items()}
    import json
    return render_template_string(INDEX_TEMPLATE, menu=MENU, menu_json=json.dumps(menu_json), recent_orders=recent_orders)


@app.route("/receipt/<identifier>")
@app.route("/<identifier>")
def receipt(identifier):
    # Lookup by ordno or by customer_phone
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM Restaurantrecords WHERE ordno = ?", (identifier,)).fetchone()

    if not row:
        # Check CustomerOrders table by phone or order_no
        c_order = cursor.execute(
            "SELECT order_no FROM CustomerOrders WHERE customer_phone = ? OR order_no = ? ORDER BY order_time DESC LIMIT 1",
            (identifier, identifier),
        ).fetchone()
        if c_order:
            row = cursor.execute("SELECT * FROM Restaurantrecords WHERE ordno = ?", (c_order["order_no"],)).fetchone()

    conn.close()

    if not row:
        # Default to highest order if none specified
        conn = get_db()
        row = conn.execute("SELECT * FROM Restaurantrecords ORDER BY CAST(ordno AS INTEGER) DESC LIMIT 1").fetchone()
        conn.close()

    if not row:
        return "No orders found in database.", 404

    order, items = parse_order_row(row)
    return render_template_string(RECEIPT_TEMPLATE, order=order, items=items)


@app.route("/qr/<order_no>")
def get_qr(order_no):
    receipt_url = f"http://localhost:{PORT}/receipt/{order_no}"
    upi_link = f"upi://pay?pa=varsha@upi&pn=VarshasKitchen&am=0&cu=INR&tn=Order_{order_no}"
    data = f"{receipt_url}\n{upi_link}"

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img_path = f"qr_order_{order_no}.png"
    img.save(img_path)
    return send_file(img_path, mimetype="image/png")


@app.route("/api/order", methods=["POST"])
def api_order():
    data = request.get_json() or {}
    cart = data.get("cart", {})
    phone = data.get("phone", "").strip()

    piz = int(cart.get("1", 0))
    bur = int(cart.get("2", 0))
    ice = int(cart.get("3", 0))
    dr = int(cart.get("4", 0))

    cost_of_meal = (piz * 240.0) + (bur * 125.0) + (ice * 80.0) + (dr * 60.0)
    if cost_of_meal <= 0:
        return jsonify({"success": False, "error": "Order cannot be empty"}), 400

    tax = round(cost_of_meal * 0.18, 2)
    service_charge = round(cost_of_meal / 99, 2)
    grand_total = round(cost_of_meal + tax + service_charge, 2)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ordno FROM Restaurantrecords")
    numeric_ids = [int(r[0]) for r in cursor.fetchall() if r[0] and str(r[0]).strip().isdigit()]
    next_ordno = str(max(numeric_ids, default=0) + 1)

    cursor.execute(
        """
        INSERT INTO Restaurantrecords (ordno, piz, bur, ice, dr, ct, sb, tax, sr, tot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (next_ordno, str(piz), str(bur), str(ice), str(dr), str(cost_of_meal), str(cost_of_meal), str(tax), str(service_charge), str(grand_total)),
    )

    items_summary = f"Pizza x{piz}, Burger x{bur}, Ice cream x{ice}, Drinks x{dr}"
    order_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT OR REPLACE INTO CustomerOrders
        (order_no, customer_phone, order_time, items_summary, cost_of_meal, tax, service_charge, grand_total, qr_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (next_ordno, phone, order_time, items_summary, cost_of_meal, tax, service_charge, grand_total, f"qr_order_{next_ordno}.png"),
    )

    conn.commit()
    conn.close()

    receipt_url = f"/receipt/{next_ordno}"
    return jsonify({"success": True, "order_no": next_ordno, "receipt_url": receipt_url})


import threading
import webbrowser

def open_browser():
    try:
        webbrowser.open_new(f"http://localhost:{PORT}")
    except Exception as e:
        print(f"Could not open browser automatically: {e}")

if __name__ == "__main__":
    print(f"\n=======================================================")
    print(f"  VARSHA'S KITCHEN - WEB PORTAL & DIGITAL RECEIPTS")
    print(f"  Opening browser at: http://localhost:{PORT}")
    print(f"=======================================================\n")
    threading.Timer(1.2, open_browser).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)


"""Restaurant Billing System
Enhanced with:
- Item quantity support & cart management
- Tax (18% GST) & Service charge calculation
- SQLite persistence in Restaurant.db (compatible with Restaurant Management GUI)
- Detailed customer order history tracking
- QR code generation (Receipt summary & UPI payment link)
- Phone number validation and simulated SMS receipt
"""

import os
import sys
import sqlite3
import datetime
import qrcode

# Ensure safe UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class RestaurantBillingSystem:
    DB_NAME = "Restaurant.db"
    CURRENCY = "Rs. "

    def __init__(self):
        # Menu configuration: id -> (name, price, short_code)
        self.menu = {
            1: {"item": "Pizza", "price": 240.0, "code": "piz"},
            2: {"item": "Burger", "price": 125.0, "code": "bur"},
            3: {"item": "Ice cream", "price": 80.0, "code": "ice"},
            4: {"item": "Drinks", "price": 60.0, "code": "dr"},
        }
        # order maps item_id -> quantity
        self.order = {}
        self.init_database()

    def init_database(self):
        """Initializes database tables if they do not exist."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            # Compatible with the Tkinter GUI's Restaurantrecords table
            cursor.execute(
                """
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
                """
            )
            # Detailed customer orders table
            cursor.execute(
                """
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
                """
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"[Database Error]: Could not initialize tables: {e}")

    def get_next_order_number(self):
        """Calculates the next sequential order number from Restaurant.db."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT ordno FROM Restaurantrecords")
            rows = cursor.fetchall()
            conn.close()

            numeric_ids = []
            for (ordno,) in rows:
                if ordno and ordno.strip().isdigit():
                    numeric_ids.append(int(ordno.strip()))

            return str(max(numeric_ids, default=0) + 1)
        except sqlite3.Error:
            return "1"

    def display_menu(self):
        """Displays the menu in a clean formatted box."""
        print("\n" + "=" * 38)
        print("         VARSHA'S KITCHEN MENU")
        print("=" * 38)
        print(f" {'ID':<4} {'Item Name':<16} {'Price':>12}")
        print("-" * 38)
        for key, value in self.menu.items():
            print(f" [{key}]  {value['item']:<16} {self.CURRENCY}{value['price']:>7.2f}")
        print("=" * 38)

    def display_cart(self):
        """Displays currently selected items and total."""
        if not self.order:
            print("\nCart is currently empty.")
            return

        print("\n--- Current Cart ---")
        subtotal = 0.0
        for item_id, qty in self.order.items():
            item = self.menu[item_id]
            line_cost = item["price"] * qty
            subtotal += line_cost
            print(f"• {item['item']} x {qty} = {self.CURRENCY}{line_cost:.2f}")
        print(f"Subtotal: {self.CURRENCY}{subtotal:.2f}")

    def take_order(self):
        """Interactive loop to select items and quantities."""
        self.order = {}
        while True:
            self.display_menu()
            if self.order:
                self.display_cart()

            choice = input("\nEnter item number to order (or 'done' to finish, 'clear' to reset): ").strip().lower()

            if choice == "done":
                if not self.order:
                    print("Cart is empty! Please select at least one item before finishing.")
                    continue
                break
            elif choice == "clear":
                self.order.clear()
                print("Cart cleared.")
                continue

            if choice.isdigit() and int(choice) in self.menu:
                item_id = int(choice)
                item = self.menu[item_id]

                qty_str = input(f"Enter quantity for {item['item']} (default 1): ").strip()
                if qty_str == "":
                    quantity = 1
                elif qty_str.isdigit() and int(qty_str) > 0:
                    quantity = int(qty_str)
                else:
                    print("Invalid quantity. Added 1 by default.")
                    quantity = 1

                self.order[item_id] = self.order.get(item_id, 0) + quantity
                print(f"Added {quantity}x {item['item']} to cart.")
            else:
                print("Invalid selection. Please enter a valid item number from the menu.")

    def calculate_bill(self):
        """Computes cost of meal, 18% tax, service charge, and grand total."""
        cost_of_meal = sum(
            self.menu[item_id]["price"] * qty for item_id, qty in self.order.items()
        )
        tax = round(cost_of_meal * 0.18, 2)  # 18% GST
        service_charge = round(cost_of_meal / 99, 2) if cost_of_meal > 0 else 0.0
        grand_total = round(cost_of_meal + tax + service_charge, 2)

        return {
            "cost_of_meal": cost_of_meal,
            "tax": tax,
            "service_charge": service_charge,
            "grand_total": grand_total,
        }

    def save_to_database(self, order_no, customer_number, bill, qr_filename):
        """Saves bill details into SQLite Restaurant.db."""
        piz_qty = str(self.order.get(1, 0))
        bur_qty = str(self.order.get(2, 0))
        ice_qty = str(self.order.get(3, 0))
        dr_qty = str(self.order.get(4, 0))

        cost_str = str(bill["cost_of_meal"])
        sub_str = str(bill["cost_of_meal"])
        tax_str = str(bill["tax"])
        service_str = str(bill["service_charge"])
        tot_str = str(bill["grand_total"])

        items_summary = ", ".join(
            f"{self.menu[i]['item']} x{q}" for i, q in self.order.items()
        )
        order_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()

            # Insert into Restaurantrecords (compatible with Tkinter restaurantmanage.py)
            cursor.execute(
                """
                INSERT OR REPLACE INTO Restaurantrecords 
                (ordno, piz, bur, ice, dr, ct, sb, tax, sr, tot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order_no, piz_qty, bur_qty, ice_qty, dr_qty, cost_str, sub_str, tax_str, service_str, tot_str),
            )

            # Insert into CustomerOrders
            cursor.execute(
                """
                INSERT OR REPLACE INTO CustomerOrders
                (order_no, customer_phone, order_time, items_summary, cost_of_meal, tax, service_charge, grand_total, qr_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_no,
                    customer_number,
                    order_time,
                    items_summary,
                    bill["cost_of_meal"],
                    bill["tax"],
                    bill["service_charge"],
                    bill["grand_total"],
                    qr_filename,
                ),
            )

            conn.commit()
            conn.close()
            print(f"Order #{order_no} successfully saved to database '{self.DB_NAME}'.")
        except sqlite3.Error as e:
            print(f"[Database Error]: Failed to save order: {e}")

    def generate_receipt(self, order_no, customer_number, bill):
        """Generates formatted text receipt and QR code."""
        timestamp = datetime.datetime.now().strftime("%d-%b-%Y %I:%M %p")
        receipt_lines = [
            "=" * 44,
            "         VARSHA'S KITCHEN RECEIPT           ",
            "=" * 44,
            f"Order No : #{order_no}",
            f"Date/Time: {timestamp}",
            f"Customer : {customer_number}",
            "-" * 44,
            f"{'Item':<14} {'Qty':>4} {'Price':>10} {'Total':>12}",
            "-" * 44,
        ]

        for item_id, qty in self.order.items():
            item = self.menu[item_id]
            line_cost = item["price"] * qty
            receipt_lines.append(
                f"{item['item']:<14} {qty:>4} {self.CURRENCY}{item['price']:>7.2f} {self.CURRENCY}{line_cost:>8.2f}"
            )

        receipt_lines.extend([
            "-" * 44,
            f"Cost of Meal:             {self.CURRENCY}{bill['cost_of_meal']:>10.2f}",
            f"GST (18%):                {self.CURRENCY}{bill['tax']:>10.2f}",
            f"Service Charge:           {self.CURRENCY}{bill['service_charge']:>10.2f}",
            "=" * 44,
            f"GRAND TOTAL:              {self.CURRENCY}{bill['grand_total']:>10.2f}",
            "=" * 44,
            "       Thank you for dining with us!        ",
            "=" * 44,
        ])

        receipt_text = "\n".join(receipt_lines)
        print("\n" + receipt_text)

        # Generate QR code containing the live receipt URL + UPI payment payload
        receipt_web_url = f"http://localhost:8000/receipt/{order_no}"
        upi_pay_link = (
            f"upi://pay?pa=varsha@upi&pn=VarshasKitchen"
            f"&am={bill['grand_total']:.2f}&cu=INR&tn=Order_{order_no}"
        )
        qr_payload = f"Digital Receipt URL:\n{receipt_web_url}\n\nUPI Payment:\n{upi_pay_link}"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_filename = "receipt_qr.png"
        qr_img.save(qr_filename)

        print(f"\nReceipt & Payment QR Code generated and saved as '{qr_filename}'.")
        return receipt_text, qr_filename

    def send_receipt(self, customer_number, order_no, bill):
        """Simulates dispatching receipt SMS link to customer."""
        simulated_link = f"http://localhost:8000/receipt/{order_no}"
        print("\n" + "~" * 44)
        print("            SMS RECEIPT DISPATCH            ")
        print("~" * 44)
        print(f"Recipient Mobile: +91 {customer_number}")
        print(f"Message Content : Dear customer, thank you for visiting! Your bill for Order #{order_no} is {self.CURRENCY}{bill['grand_total']:.2f}.")
        print(f"Digital Receipt : {simulated_link}")
        print("Status          : Sent successfully (Simulated)")
        print("~" * 44)

    def view_past_orders(self):
        """Displays past orders from the database."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ordno, piz, bur, ice, dr, ct, sb, tax, sr, tot 
                FROM Restaurantrecords 
                ORDER BY CAST(ordno AS INTEGER) DESC LIMIT 10
                """
            )
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                print("\nNo past orders found in database.")
                return

            print("\n" + "=" * 70)
            print("                 RECENT ORDERS (Restaurant.db)")
            print("=" * 70)
            print(f"{'Order':<7} {'Pizza':<6} {'Burger':<7} {'IceCream':<9} {'Drinks':<7} {'Subtotal':<10} {'Total':<10}")
            print("-" * 70)
            for row in rows:
                ordno, piz, bur, ice, dr, ct, sb, tax, sr, tot = row
                print(f"#{ordno:<6} {piz:<6} {bur:<7} {ice:<9} {dr:<7} {sb:<10} {tot:<10}")
            print("=" * 70)
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")

    def run(self):
        """Main system loop."""
        print("\n==============================================")
        print("   WELCOME TO VARSHA'S KITCHEN BILLING        ")
        print("==============================================")

        while True:
            print("\nMAIN MENU:")
            print(" 1. Create New Order & Bill")
            print(" 2. View Menu Card")
            print(" 3. View Recent Orders (from Database)")
            print(" 4. Open Web Portal & Digital Receipts in Browser")
            print(" 5. Exit")

            opt = input("\nEnter your choice (1-5): ").strip()

            if opt == "1":
                self.take_order()
                bill = self.calculate_bill()
                order_no = self.get_next_order_number()

                while True:
                    customer_number = input("\nEnter customer 10-digit mobile number: ").strip()
                    if customer_number.isdigit() and len(customer_number) == 10:
                        break
                    print("Invalid mobile number. Please enter exactly 10 digits (e.g. 9876543210).")

                _, qr_filename = self.generate_receipt(order_no, customer_number, bill)
                self.save_to_database(order_no, customer_number, bill, qr_filename)
                self.send_receipt(customer_number, order_no, bill)

                open_now = input("\nOpen digital receipt in web browser? (Y/n): ").strip().lower()
                if open_now in ("", "y", "yes"):
                    import webbrowser
                    webbrowser.open(f"http://localhost:8000/receipt/{order_no}")

            elif opt == "2":
                self.display_menu()

            elif opt == "3":
                self.view_past_orders()

            elif opt == "4":
                import webbrowser, subprocess, urllib.request
                try:
                    urllib.request.urlopen("http://localhost:8000", timeout=1)
                except Exception:
                    subprocess.Popen(["python", "app.py"])
                webbrowser.open("http://localhost:8000")
                print("Opening http://localhost:8000 in your browser...")

            elif opt == "5":
                print("\nThank you for dining at Varsha's Kitchen. Goodbye!")
                break
            else:
                print("Invalid option. Please choose between 1 and 5.")


if __name__ == "__main__":
    system = RestaurantBillingSystem()
    system.run()
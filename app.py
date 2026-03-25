from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import json

app = Flask(__name__)

DB_NAME = "finance.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS finance_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            income REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS savings_goal (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            target REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT
        )
    """)

    cur.execute("INSERT OR IGNORE INTO finance_state (id, income) VALUES (1, 0)")
    cur.execute("INSERT OR IGNORE INTO savings_goal (id, target) VALUES (1, 0)")

    conn.commit()
    conn.close()


def get_income():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT income FROM finance_state WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return float(row["income"] if row else 0)


def set_income(amount):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE finance_state SET income = ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()


def get_savings_goal():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT target FROM savings_goal WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return float(row["target"] if row else 0)


def set_savings_goal(value):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE savings_goal SET target = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()


def add_expense(category, amount, description):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (category, amount, description) VALUES (?, ?, ?)",
        (category, amount, description)
    )
    conn.commit()
    conn.close()


def update_expense(expense_id, category, amount, description):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE expenses
        SET category = ?, amount = ?, description = ?
        WHERE id = ?
    """, (category, amount, description, expense_id))
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def reset_all_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE finance_state SET income = 0 WHERE id = 1")
    cur.execute("UPDATE savings_goal SET target = 0 WHERE id = 1")
    cur.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()


def get_expenses():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_total_expense(expenses):
    return round(sum(float(row["amount"]) for row in expenses), 2)


def get_category_totals(expenses):
    category_map = {}
    for row in expenses:
        category = row["category"]
        amount = float(row["amount"])
        category_map[category] = category_map.get(category, 0) + amount

    return sorted(category_map.items(), key=lambda x: x[1], reverse=True)


def get_highest_spending_category(category_totals):
    if not category_totals:
        return "No expenses yet"
    return category_totals[0][0]


def get_health_score(income, total_expense):
    if income <= 0:
        return 0

    ratio = total_expense / income

    if ratio <= 0.40:
        return 95
    elif ratio <= 0.55:
        return 85
    elif ratio <= 0.70:
        return 70
    elif ratio <= 0.85:
        return 50
    elif ratio <= 1.00:
        return 30
    else:
        return 10


def get_spending_personality(income, total_expense, category_totals):
    if income <= 0 or total_expense == 0:
        return "No Data"

    ratio = total_expense / income
    category_dict = dict(category_totals)

    shopping = category_dict.get("Shopping", 0)
    entertainment = category_dict.get("Entertainment", 0)

    if ratio <= 0.50:
        return "Controlled Saver"
    elif shopping + entertainment > income * 0.25:
        return "Impulsive Spender"
    elif ratio > 1.00:
        return "Risky Spender"
    return "Balanced Spender"


def detect_unusual_expenses(expenses):
    if len(expenses) < 3:
        return []

    amounts = [float(row["amount"]) for row in expenses]
    avg = sum(amounts) / len(amounts)
    threshold = avg * 1.4

    unusual = [row for row in expenses if float(row["amount"]) >= threshold]
    unusual = sorted(unusual, key=lambda x: float(x["amount"]), reverse=True)

    return unusual[:5]


def get_risk_levels(income, category_totals):
    if income <= 0:
        return []

    limits = {
        "Food": 0.25,
        "Travel": 0.12,
        "Shopping": 0.15,
        "Bills": 0.25,
        "Entertainment": 0.10,
        "Health": 0.12,
        "Education": 0.12,
        "Other": 0.08
    }

    risks = []

    for category, amount in category_totals:
        ratio = amount / income
        limit = limits.get(category, 0.10)

        if ratio >= limit:
            status = "High"
        elif ratio >= limit * 0.75:
            status = "Medium"
        else:
            status = "Low"

        risks.append({
            "category": category,
            "amount": round(amount, 2),
            "status": status
        })

    return risks


def get_budget_rules(income):
    if income <= 20000:
        return {
            "Food": 0.30,
            "Travel": 0.10,
            "Shopping": 0.05,
            "Bills": 0.30,
            "Entertainment": 0.05,
            "Health": 0.10,
            "Education": 0.05,
            "Other": 0.05
        }
    elif income <= 50000:
        return {
            "Food": 0.25,
            "Travel": 0.10,
            "Shopping": 0.08,
            "Bills": 0.25,
            "Entertainment": 0.07,
            "Health": 0.10,
            "Education": 0.10,
            "Other": 0.05
        }
    else:
        return {
            "Food": 0.20,
            "Travel": 0.10,
            "Shopping": 0.10,
            "Bills": 0.20,
            "Entertainment": 0.10,
            "Health": 0.10,
            "Education": 0.10,
            "Other": 0.10
        }


def get_budget_comparison(income, category_totals):
    rules = get_budget_rules(income)
    comparison = []
    category_dict = dict(category_totals)

    for category, ratio in rules.items():
        rec_amount = income * ratio
        actual = category_dict.get(category, 0)
        percent = 0 if rec_amount == 0 else (actual / rec_amount) * 100

        if percent > 120:
            status = "Over"
        elif percent > 80:
            status = "Near"
        else:
            status = "Good"

        comparison.append({
            "category": category,
            "actual": round(actual, 2),
            "recommended": round(rec_amount, 2),
            "percent": round(percent, 1),
            "status": status
        })

    return comparison


def get_savings_potential(income, total_expense):
    if income <= 0:
        return 0
    return round(income - total_expense, 2)


def get_suggestions(income, total_expense, category_totals, unusual_expenses):
    tips = []

    if income <= 0:
        return ["Add your income first to unlock analysis."]

    savings = income - total_expense
    spend_ratio = total_expense / income
    category_dict = dict(category_totals)

    if spend_ratio >= 1.0:
        tips.append("Critical alert: your total expenses are greater than your income.")
    elif spend_ratio >= 0.85:
        tips.append("Warning: you have already used more than 85% of your income.")
    elif spend_ratio >= 0.70:
        tips.append("Caution: your expenses are above 70% of income. Monitor spending carefully.")

    if category_dict.get("Shopping", 0) > income * 0.15:
        tips.append("Shopping expenses are high. Consider setting a strict shopping cap.")

    if category_dict.get("Food", 0) > income * 0.25:
        tips.append("Food spending is above the recommended level.")

    if category_dict.get("Entertainment", 0) > income * 0.10:
        tips.append("Entertainment expenses are high compared to a healthy budget range.")

    if category_dict.get("Travel", 0) > income * 0.12:
        tips.append("Travel spending is becoming high for your income level.")

    if category_dict.get("Bills", 0) > income * 0.25:
        tips.append("Bills are taking a large part of your income.")

    if savings < income * 0.10:
        tips.append("Your savings are below 10% of income. Try keeping a minimum savings target.")

    if savings <= 0:
        tips.append("You currently have no savings buffer left.")

    if unusual_expenses:
        tips.append("Unusual large expenses were detected. Review those transactions carefully.")

    if not tips:
        if spend_ratio <= 0.60:
            tips.append("Your spending pattern looks healthy and balanced.")
        else:
            tips.append("Your finances are stable, but there is room to improve savings.")

    return tips


@app.route("/", methods=["GET", "POST"])
def index():
    init_db()

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "set_income":
            income = request.form.get("income", "0").strip()
            try:
                set_income(float(income))
            except ValueError:
                pass

        elif action == "set_goal":
            value = request.form.get("goal", "0").strip()
            try:
                set_savings_goal(float(value))
            except ValueError:
                pass

        elif action == "add_expense":
            category = request.form.get("category", "").strip()
            amount = request.form.get("amount", "").strip()
            description = request.form.get("description", "").strip()

            if category and amount:
                try:
                    add_expense(category, float(amount), description)
                except ValueError:
                    pass

        elif action == "edit_expense":
            expense_id = request.form.get("id", "").strip()
            category = request.form.get("category", "").strip()
            amount = request.form.get("amount", "").strip()
            description = request.form.get("description", "").strip()

            try:
                update_expense(int(expense_id), category, float(amount), description)
            except ValueError:
                pass

        elif action == "reset":
            reset_all_data()

        return redirect(url_for("index"))

    income = get_income()
    goal = get_savings_goal()
    expenses = get_expenses()
    total_expense = get_total_expense(expenses)
    balance = round(income - total_expense, 2)
    category_totals = get_category_totals(expenses)
    highest_category = get_highest_spending_category(category_totals)
    health_score = get_health_score(income, total_expense)
    personality = get_spending_personality(income, total_expense, category_totals)
    unusual_expenses = detect_unusual_expenses(expenses)
    risk_levels = get_risk_levels(income, category_totals)
    savings_potential = get_savings_potential(income, total_expense)
    suggestions = get_suggestions(income, total_expense, category_totals, unusual_expenses)
    budget_comparison = get_budget_comparison(income, category_totals)

    goal_progress = 0
    if goal > 0:
        goal_progress = min((savings_potential / goal) * 100, 100)

    category_labels = [item[0] for item in category_totals]
    category_values = [round(item[1], 2) for item in category_totals]

    return render_template(
        "index.html",
        income=income,
        goal=goal,
        goal_progress=round(goal_progress, 1),
        expenses=expenses,
        total_expense=total_expense,
        balance=balance,
        highest_category=highest_category,
        health_score=health_score,
        personality=personality,
        unusual_expenses=unusual_expenses,
        risk_levels=risk_levels,
        budget_comparison=budget_comparison,
        savings_potential=savings_potential,
        suggestions=suggestions,
        category_labels=json.dumps(category_labels),
        category_values=json.dumps(category_values)
    )


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_item(expense_id):
    delete_expense(expense_id)
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
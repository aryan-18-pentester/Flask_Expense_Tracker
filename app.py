from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import json as jsonify

# ── Setup ──────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_BINDS'] = {
    'users_db' : 'sqlite:///users.db',    # first database  → users.db
    'data_db'  : 'sqlite:///data.db',     # second database → data.db
}
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ── User model ─────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# ── Entry model → saved in data.db ────────────────────────────────────────────
class Entry(db.Model):
    __bind_key__ = 'data_db'              # tells SQLAlchemy: put this table in data.db
 
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, nullable=False)   # links to User.id in users.db
 
    # two string fields -- rename to match your data
    category = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200), nullable=False)
 
    # one number field -- rename to match your data
    amount = db.Column(db.Float, nullable=False)
 
    # add more columns here if needed

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Register ───────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


# ── Login ──────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html')


# ── Logout ─────────────────────────────────────────────────────────────────────
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



#------DashBoard---------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    
     entries = Entry.query.filter_by(user_id=current_user.id).all()
 
    # calculate stats from the number_one column for this user only
     stats = db.session.query(
        func.count(Entry.amount),    # total count of entries
        func.sum(Entry.amount),      # sum of all numbers
        func.avg(Entry.amount),      # average
        func.max(Entry.amount),      # highest
        func.min(Entry.amount),      # lowest
    ).filter(Entry.user_id == current_user.id).one()
 
    # unpack into named variables -- if no entries yet all values will be None
     total_count  = stats[0] or 0
     total_sum    = round(stats[1], 2) if stats[1] else 0
     average      = round(stats[2], 2) if stats[2] else 0
     highest      = stats[3] or 0
     lowest       = stats[4] or 0
     return render_template('dashboard.html', entries=entries,
                           total_count=total_count,
                           total_sum=total_sum,
                           average=average,
                           highest=highest,
                           lowest=lowest ,active='dashboard')
 
 
@app.route('/expenses',methods=['GET', 'POST'])
@login_required
def expenses():                     
    #return render_template('expenses.html', active='expenses')
    if request.method == 'POST':
 
        # read the three fields the user typed in the form
        category = request.form['category']
        description = request.form['description']
        amount = request.form['amount']
 
        # your logic goes here before saving
        # example: validate, calculate, transform the data
 
        # save to database -- user_id links this entry to whoever is logged in
        entry = Entry(
            user_id    = current_user.id,
            category = category,
            description = description,
            amount = float(amount),   # convert string from form to number
        ) 
        db.session.add(entry)
        db.session.commit()
 
        return redirect(url_for('expenses'))
        #return render_template('expenses.html', active='expenses')
    # fetch only this user's entries
    entries = Entry.query.filter_by(user_id=current_user.id).all()
    return render_template('expenses.html', active='expenses',entries=entries)


#----------edit -------------------------------
@app.route('/expenses/edit/<int:entry_id>', methods=['GET','POST'])
@login_required
def edit_expense(entry_id):

    entry = Entry.query.get_or_404(entry_id)

    if entry.user_id != current_user.id:
        flash("Unauthorized")
        return redirect(url_for("edit_expense"))
    if request.method == "POST":
        entry.category = request.form["category"]
        entry.description = request.form["description"]
        entry.amount = float(request.form["amount"])

        db.session.commit()

        flash("Expense updated successfully.")

        return redirect(url_for("expenses"))
    return render_template("edit_expense.html", entry=entry)

#------------delete---------------
@app.route('/delete/<int:entry_id>')
@login_required
def delete(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    if entry.user_id == current_user.id:
        db.session.delete(entry)
        db.session.commit()
    return redirect(url_for('expenses'))
 

@app.route('/search', methods=['GET'])
@login_required
def search():
    # --- 1. Read all parameters (existing + new) ---
    amount = request.args.get('amount', type=int)
    category = request.args.get('category', '').strip()
    description = request.args.get('description', '').strip()
    sort_by = request.args.get('sort_by')
    sort_order = request.args.get('sort_order')
            
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)
    category_filter = request.args.get('category_filter', '').strip()
    #in_stock = request.args.get('in_stock') == '1'
    print(request.args)
    # --- 2. Build the base query ---

    query = Entry.query.filter_by(user_id=current_user.id)   # replace `Item` with your actual model name

    # --- 3. Apply existing filters ---
    if amount is not None:
        query = query.filter(Entry.amount == amount)   # adjust field name

    if category:
        query = query.filter(Entry.category.ilike(f'%{category}%'))   # adjust field

    if description:
        query = query.filter(Entry.description.ilike(f'%{description}%')) # adjust field

    # --- 4. Apply new filters ---
    if price_min is not None:
        query = query.filter(Entry.amount >= price_min)
    if price_max is not None:
        query = query.filter(Entry.amount <= price_max)
    if category_filter:
        query = query.filter(Entry.category == category_filter)  # exact match

    # --- 5. Execute query ---
    #result = query.all()

    # --- 6. Get distinct categories for the dropdown (optional) ---
    categories = db.session.query(Entry.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]  # flatten and remove None
    # --- 7. sorting
    
    # Safety check
    if sort_by not in ['amount', 'category']:
        sort_by = 'category'
    
    column = getattr(Entry, sort_by)
    
    # IF-ELSE Logic
    if sort_by == 'amount':
        if sort_order == 'asc':
            query = query.order_by(Entry.amount.asc())
        elif sort_order == 'desc':
            query = query.order_by(Entry.amount.desc())
    elif sort_by == 'category':
        if sort_order == 'asc':
            query = query.order_by(Entry.category.asc())
        elif sort_order == 'desc':
            query = query.order_by(Entry.category.desc())
    results = query.all()
    # --- 8. Render template with all values ---
    return render_template(
        'search.html',        # change to your actual template name
        results=results,
        amount=amount,
        category=category,
        description=description,
        price_min=price_min,
        price_max=price_max,
        category_filter=category_filter,
        #in_stock=in_stock,
        categories=categories
    ) 
 
@app.route('/page3')
@login_required
def page3():
    return render_template('page3.html', active='page3')

#-----home-----------------------------
@app.route('/')
@login_required
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

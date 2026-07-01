from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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
    string_one = db.Column(db.String(200), nullable=False)
    string_two = db.Column(db.String(200), nullable=False)
 
    # one number field -- rename to match your data
    number_one = db.Column(db.Float, nullable=False)
 
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
    return render_template('dashboard.html', active='dashboard')
 
 
@app.route('/expenses',methods=['GET', 'POST'])
@login_required
def expenses():                     
    #return render_template('expenses.html', active='expenses')
    if request.method == 'POST':
 
        # read the three fields the user typed in the form
        string_one = request.form['string_one']
        string_two = request.form['string_two']
        number_one = request.form['number_one']
 
        # your logic goes here before saving
        # example: validate, calculate, transform the data
 
        # save to database -- user_id links this entry to whoever is logged in
        entry = Entry(
            user_id    = current_user.id,
            string_one = string_one,
            string_two = string_two,
            number_one = float(number_one),   # convert string from form to number
        ) 
        db.session.add(entry)
        db.session.commit()
 
        return redirect(url_for('dashboard'))
    return render_template('expenses.html', active='expenses')
    # fetch only this user's entries
    entries = Entry.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', entries=entries)
 
 
@app.route('/page2')
@login_required
def page2():
    return render_template('page2.html', active='page2')
 
 
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

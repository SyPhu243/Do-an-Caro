from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

LOCK_TIME = 60 
MAX_ATTEMPTS = 3


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!', 'warning')
            return render_template('register.html')

        # Kiểm tra độ mạnh mật khẩu
        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{6,12}$'
        if not re.match(password_pattern, password):
            flash('❗ Mật khẩu phải có 6-12 ký tự, gồm chữ HOA, chữ thường và ký tự đặc biệt!', 'danger')
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing = cursor.fetchone()

        if existing:
            flash('⚠️ Tên đăng nhập đã tồn tại, vui lòng chọn tên khác!', 'danger')
        else:
            hashed = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, hashed)
            )
            conn.commit()
            flash('🎉 Đăng ký thành công! Hãy đăng nhập.', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('auth.login'))

        cursor.close()
        conn.close()

    return render_template('register.html')



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))

    now = datetime.now()

  
    lock_until = session.get('lock_until')
    if lock_until:
        lock_until_dt = datetime.strptime(lock_until, '%Y-%m-%d %H:%M:%S')
        if now < lock_until_dt:
            remaining = int((lock_until_dt - now).total_seconds())
            flash(f'⚠️ Tài khoản bị khóa. Vui lòng thử lại sau {remaining} giây', 'danger')
            return render_template('login.html')
        else:
            
            session.pop('lock_until', None)
            session.pop('login_attempts', None)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Vui lòng nhập đầy đủ thông tin!', 'warning')
            return render_template('login.html')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['login_attempts'] = 0
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Xin chào {user["username"]}! 👋 Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))

        # Sai MK
        session['login_attempts'] = session.get('login_attempts', 0) + 1

        if session['login_attempts'] >= MAX_ATTEMPTS:
            session['lock_until'] = (now + timedelta(seconds=LOCK_TIME)).strftime('%Y-%m-%d %H:%M:%S')
            flash(f'⚠️ Đăng nhập sai quá nhiều lần. Tài khoản bị khóa {LOCK_TIME} giây</span>', 'danger')
        else:
            remaining_attempts = MAX_ATTEMPTS - session['login_attempts']
            flash(f'❌ Sai tài khoản hoặc mật khẩu. Còn {remaining_attempts} lần thử', 'danger')

    return render_template('login.html')


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()

        if not username:
            flash('Vui lòng nhập tên đăng nhập!', 'warning')
            return render_template('forgot_password.html')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            flash('⚠️ Không tìm thấy tài khoản với tên này!', 'danger')
            return render_template('forgot_password.html')

        session['reset_user'] = username
        return redirect(url_for('auth.reset_password'))

    return render_template('forgot_password.html')


@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    username = session.get('reset_user')

    if not username:
        flash('⚠️ Bạn chưa chọn tài khoản để đặt lại mật khẩu.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_pass = request.form.get('new_password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{6,12}$'
        if not re.match(password_pattern, new_pass):
            flash('❗ Mật khẩu phải có 6-12 ký tự, gồm chữ HOA, chữ thường và ký tự đặc biệt!', 'danger')
            return render_template('reset_password.html', username=username)

        if new_pass != confirm:
            flash('❌ Mật khẩu xác nhận không khớp!', 'danger')
            return render_template('reset_password.html', username=username)

        conn = get_db_connection()
        cursor = conn.cursor()
        hashed = generate_password_hash(new_pass)
        cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (hashed, username))
        conn.commit()
        cursor.close()
        conn.close()

        session.pop('reset_user', None)
        flash('✅ Mật khẩu đã được đặt lại thành công! Hãy đăng nhập lại.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', username=username)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('👋 Đã đăng xuất tài khoản.', 'info')
    return redirect(url_for('auth.login'))

# -*- coding: utf-8 -*-
"""二手商品交易平台 - 主应用文件"""
import os
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# ==================== 配置 ====================
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
app.secret_key = 'secondhand-platform-secret-key-2026'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
UPLOAD_FOLDER = os.path.join(STATIC_DIR, 'uploads')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_RECEIPT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# ==================== 工具函数 ====================
def load_json(filename, default=list):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default() if callable(default) else default
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default() if callable(default) else default

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def save_upload(file_obj, subfolder, allowed_exts, compress=False):
    if not file_obj or not file_obj.filename:
        return None
    filename = secure_filename(file_obj.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in allowed_exts:
        return None
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(UPLOAD_FOLDER, subfolder)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, new_filename)
    file_obj.save(filepath)
    # 图片压缩
    if compress and ext in {'jpg', 'jpeg', 'png', 'webp'}:
        compress_image(filepath)
    return f"uploads/{subfolder}/{new_filename}"

def compress_image(filepath):
    settings = load_json('settings.json')
    cfg = settings.get('image_compression', {})
    if not cfg.get('enabled', True):
        return
    try:
        img = Image.open(filepath)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb < cfg.get('threshold_mb', 2):
            return
        max_w, max_h = cfg.get('max_width', 1920), cfg.get('max_height', 1920)
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        quality = cfg.get('quality', 80)
        img.save(filepath, optimize=True, quality=quality)
    except Exception:
        pass

def generate_id():
    return uuid.uuid4().hex

def get_user(user_id):
    users = load_json('users.json')
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        return users.get(user_id)
    for u in users:
        if u.get('id') == user_id:
            return u
    return None

def get_user_by_username_or_email(username_or_email):
    users = load_json('users.json')
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        for u in users.values():
            if u.get('username') == username_or_email or u.get('email') == username_or_email:
                return u
        return None
    for u in users:
        if u.get('username') == username_or_email or u.get('email') == username_or_email:
            return u
    return None

def get_product(product_id):
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        return products.get(product_id)
    for p in products:
        if p.get('id') == product_id:
            return p
    return None

def get_products(filters=None):
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        products = list(products.values())
    if filters:
        if filters.get('status'):
            products = [p for p in products if p.get('status') == filters['status']]
        if filters.get('user_id'):
            products = [p for p in products if p.get('user_id') == filters['user_id']]
        if filters.get('category'):
            products = [p for p in products if p.get('category') == filters['category']]
        if filters.get('q'):
            q = filters['q'].lower()
            products = [p for p in products if q in p.get('title', '').lower()]
    return products

def build_comment_tree(comments, product_id):
    comments = [c for c in comments if c.get('product_id') == product_id]
    comment_map = {}
    for c in comments:
        c['children'] = []
        c['user'] = get_user(c.get('user_id'))
        c['username'] = c['user']['username'] if c['user'] else '未知'
        comment_map[c['id']] = c
    tree = []
    for c in comments:
        parent_id = c.get('parent_id')
        if parent_id and parent_id in comment_map:
            comment_map[parent_id]['children'].append(c)
        else:
            tree.append(c)
    return tree

def count_unread_messages(user_id):
    messages = load_json('messages.json')
    return len([m for m in messages if m.get('receiver_id') == user_id and not m.get('is_read', False)])

def send_notification(user_id, content, related_id=None):
    notifications = load_json('notifications.json')
    notification = {
        'id': uuid.uuid4().hex,
        'user_id': user_id,
        'content': content,
        'related_id': related_id,
        'is_read': False,
        'created_at': datetime.now().isoformat()
    }
    notifications.append(notification)
    save_json('notifications.json', notifications)

def send_message(sender_id, receiver_id, title, content, msg_type='user_message'):
    messages = load_json('messages.json')
    message = {
        'id': uuid.uuid4().hex,
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'title': title,
        'content': content,
        'is_read': False,
        'created_at': datetime.now().isoformat(),
        'message_type': msg_type
    }
    messages.append(message)
    save_json('messages.json', messages)
    send_notification(receiver_id, f'您收到新站内信: {title}', message['id'])

# ==================== 装饰器 ====================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def moderator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        role = session.get('role')
        if role not in ['moderator', 'admin']:
            flash('权限不足', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('权限不足', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ==================== 上下文处理器 ====================
@app.context_processor
@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = get_user(session['user_id'])
        unread = count_unread_messages(session['user_id']) if user else 0
        notifications = load_json('notifications.json')
        unread_notifs = len([n for n in notifications if n.get('user_id') == session['user_id'] and not n.get('is_read')])
        return {'current_user': user, 'unread_messages': unread, 'unread_notifications': unread_notifs}
    return {'current_user': None, 'unread_messages': 0, 'unread_notifications': 0}
# ==================== 公开路由 ====================

@app.route('/test_route_check')
def test_route_check():
    return "OK"


@app.route('/')
def index():
    page = int(request.args.get('page', 1))
    q = request.args.get('q', '')
    category = request.args.get('category', '')
    
    products = get_products({'status': 'approved', 'q': q, 'category': category})
    # 添加卖家信息
    for p in products:
        seller = get_user(p.get('user_id'))
        p['seller_username'] = seller['username'] if seller else '未知'
    
    per_page = 12
    total = len(products)
    total_pages = (total + per_page - 1) // per_page
    products = products[(page-1)*per_page:page*per_page]
    
    return render_template('index.html', products=products, page=page, total_pages=total_pages)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if password != confirm:
            flash('两次密码不一致', 'danger')
            return redirect(url_for('register'))
        
        if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
            flash('用户名或邮箱已被注册', 'danger')
            return redirect(url_for('register'))
        
        users = load_json('users.json')
        user = {
            'id': uuid.uuid4().hex,
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'role': 'user',
            'intro': '',
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        users.append(user)
        save_json('users.json', users)
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash('注册成功', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username_or_email'].strip()
        password = request.form['password']
        
        user = get_user_by_username_or_email(username_or_email)
        if not user or not check_password_hash(user['password'], password):
            flash('用户名或密码错误', 'danger')
            return redirect(url_for('login'))
        
        if not user.get('is_active', True):
            flash('账号已被禁用', 'danger')
            return redirect(url_for('login'))
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash('登录成功', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = get_product(product_id)
    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('index'))
    
    # 只有已审核通过的商品才公开可见
    if product['status'] != 'approved' and (not session.get('user_id') or 
        session.get('user_id') != product.get('user_id') and session.get('role') not in ['moderator', 'admin']):
        flash('商品不存在', 'danger')
        return redirect(url_for('index'))
    
    seller = get_user(product.get('user_id'))
    product['seller_username'] = seller['username'] if seller else '未知'
    
    comments = load_json('comments.json')
    comment_tree = build_comment_tree(comments, product_id)
    
    return render_template('product_detail.html', product=product, seller=seller, comments=comment_tree)

@app.route('/notices')
def notices():
    notices = load_json('notices.json')
    notices.sort(key=lambda x: x['created_at'], reverse=True)
    return render_template('notices.html', notices=notices)

@app.route('/notice/<notice_id>')
def notice_detail(notice_id):
    notices = load_json('notices.json')
    notice = next((n for n in notices if n['id'] == notice_id), None)
    if not notice:
        flash('公告不存在', 'danger')
        return redirect(url_for('notices'))
    return render_template('notice_detail.html', notice=notice)

# ==================== 登录用户路由 ====================
@app.route('/dashboard')
@login_required
def dashboard():
    products = get_products({'user_id': session['user_id']})
    for p in products:
        seller = get_user(p.get('user_id'))
        p['seller_username'] = seller['username'] if seller else '未知'
    return render_template('dashboard.html', my_products=products)

@app.route('/product/create', methods=['GET', 'POST'])
@login_required
def product_create():
    if request.method == 'POST':
        # Daily product limit check (max 10 per day)
        user_id = session.get('user_id')
        if user_id:
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            products = load_json('products.json')
            # 支持列表和字典两种格式
            if isinstance(products, dict):
                products_list = list(products.values())
            else:
                products_list = products
            user_products_today = [p for p in products_list 
                                  if p.get('user_id') == user_id 
                                  and p.get('created_at', '').startswith(today)]
            settings = load_json("settings.json")
            daily_limit = settings.get("product", {}).get("daily_limit", 10)
            if len(user_products_today) >= daily_limit:
                flash(f'今日发布已达上限（{daily_limit}件），请明天再发布', 'warning')
                return redirect(url_for('dashboard'))


        title = request.form['title'].strip()
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form.get('description', '')
        
        cover_file = request.files.get('cover_image')
        cover_image = save_upload(cover_file, 'covers', ALLOWED_IMAGE_EXTENSIONS, True)
        
        product_images = []
        images = request.files.getlist('product_images')
        for img in images:
            if img.filename:
                path = save_upload(img, 'product_images', ALLOWED_IMAGE_EXTENSIONS, True)
                if path:
                    product_images.append(path)
        
        receipt_file = request.files.get('purchase_receipt')
        purchase_receipt = save_upload(receipt_file, 'receipts', ALLOWED_RECEIPT_EXTENSIONS, False)
        
        if not cover_image or not purchase_receipt:
            flash('请上传封面图和购买票据', 'danger')
            return redirect(url_for('product_create'))
        
        products = load_json('products.json')
        product = {
            'id': uuid.uuid4().hex,
            'user_id': session['user_id'],
            'title': title,
            'description': description,
            'price': price,
            'category': category,
            'cover_image': cover_image,
            'product_images': product_images,
            'purchase_receipt': purchase_receipt,
            'status': 'pending',
            'reject_reason': None,
            'reviewed_by': None,
            'reviewed_at': None,
            'review_comment': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'archived_at': None,
            'is_deleted': False
        }
        products[product['id']] = product
        save_json('products.json', products)
        
        flash('商品已提交，等待审核', 'info')
        return redirect(url_for('dashboard'))
    return render_template('product_form.html')

@app.route('/product/<product_id>/edit', methods=['GET', 'POST'])
@login_required
def product_edit(product_id):
    product = get_product(product_id)
    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('dashboard'))
    if product['user_id'] != session['user_id']:
        flash('无权操作', 'danger')
        return redirect(url_for('dashboard'))
    if product['status'] != 'approved':
        flash('只能编辑已通过审核的商品', 'warning')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        product['title'] = request.form['title'].strip()
        product['category'] = request.form['category']
        product['price'] = float(request.form['price'])
        product['description'] = request.form.get('description', '')
        product['updated_at'] = datetime.now().isoformat()
        
        cover_file = request.files.get('cover_image')
        if cover_file and cover_file.filename:
            path = save_upload(cover_file, 'covers', ALLOWED_IMAGE_EXTENSIONS, True)
            if path:
                product['cover_image'] = path
        
        images = request.files.getlist('product_images')
        for img in images:
            if img.filename:
                path = save_upload(img, 'product_images', ALLOWED_IMAGE_EXTENSIONS, True)
                if path:
                    product['product_images'].append(path)
        
        receipt_file = request.files.get('purchase_receipt')
        if receipt_file and receipt_file.filename:
            path = save_upload(receipt_file, 'receipts', ALLOWED_RECEIPT_EXTENSIONS, False)
            if path:
                product['purchase_receipt'] = path
        
        # 重新提交审核
        product['status'] = 'pending'
        
        products = load_json('products.json')
        # 支持列表和字典两种格式
        if isinstance(products, dict):
            products[product_id] = product
        else:
            for i, p in enumerate(products):
                if p.get('id') == product_id:
                    products[i] = product
                    break
        save_json('products.json', products)
        
        flash('商品已更新，重新提交审核', 'info')
        return redirect(url_for('dashboard'))
    
    return render_template('product_form.html', product=product)

@app.route('/product/<product_id>/archive', methods=['POST'])
@login_required
def product_archive(product_id):
    product = get_product(product_id)
    if not product or product['user_id'] != session['user_id']:
        flash('无权操作', 'danger')
        return redirect(url_for('dashboard'))
    
    product['status'] = 'archived'
    product['archived_at'] = datetime.now().isoformat()
    
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        products[product_id] = product
    else:
        for i, p in enumerate(products):
            if p.get('id') == product_id:
                products[i] = product
                break
    save_json('products.json', products)
    
    flash('商品已下架', 'success')
    return redirect(url_for('dashboard'))

@app.route('/product/<product_id>/delete', methods=['POST'])
@login_required
def product_delete(product_id):
    product = get_product(product_id)
    if not product or product['user_id'] != session['user_id']:
        flash('无权操作', 'danger')
        return redirect(url_for('dashboard'))
    
    product['status'] = 'deleted'
    
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        products[product_id] = product
    else:
        for i, p in enumerate(products):
            if p.get('id') == product_id:
                products[i] = product
                break
    save_json('products.json', products)
    
    flash('商品已删除', 'success')
    return redirect(url_for('dashboard'))

@app.route('/product/<product_id>/comment', methods=['POST'])
@login_required
def product_comment(product_id):
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id') or None
    
    if not content:
        flash('评论内容不能为空', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    comments = load_json('comments.json')
    comment = {
        'id': uuid.uuid4().hex,
        'product_id': product_id,
        'user_id': session['user_id'],
        'content': content,
        'parent_id': parent_id,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'is_deleted': False
    }
    comments.append(comment)
    save_json('comments.json', comments)
    
    # 通知商品卖家
    product = get_product(product_id)
    if product and product['user_id'] != session['user_id']:
        if parent_id:
            # 回复评论通知
            parent = next((c for c in comments if c['id'] == parent_id), None)
            if parent:
                send_notification(parent['user_id'], f'有人回复了您的评论', product_id)
        else:
            send_notification(product['user_id'], '您的商品收到新评论', product_id)
    
    flash('评论成功', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/comment/<comment_id>/edit', methods=['POST'])
@login_required
def comment_edit(comment_id):
    content = request.form.get('content', '').strip()
    if not content:
        flash('评论内容不能为空', 'danger')
        return redirect(url_for('index'))
    
    comments = load_json('comments.json')
    # 支持列表和字典两种格式
    if isinstance(comments, dict):
        comments = list(comments.values())
    for c in comments:
        if c.get('id') == comment_id and c.get('user_id') == session['user_id']:
            c['content'] = content
            c['updated_at'] = datetime.now().isoformat()
            break
    save_json('comments.json', comments)
    
    flash('评论已更新', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/comment/<comment_id>/delete', methods=['POST'])
@login_required
def comment_delete(comment_id):
    comments = load_json('comments.json')
    # 支持列表和字典两种格式
    if isinstance(comments, dict):
        comments = list(comments.values())
    for c in comments:
        if c.get('id') == comment_id and c.get('user_id') == session['user_id']:
            c['is_deleted'] = True
            break
    save_json('comments.json', comments)
    
    flash('评论已删除', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/messages')
@login_required
def messages():
    user_id = session['user_id']
    all_messages = load_json('messages.json')
    messages = [m for m in all_messages if m.get('receiver_id') == user_id]
    messages.sort(key=lambda x: x['created_at'], reverse=True)
    
    for m in messages:
        sender = get_user(m.get('sender_id'))
        m['sender_username'] = sender['username'] if sender else '未知'
    
    return render_template('messages.html', messages=messages)

@app.route('/messages/send', methods=['GET', 'POST'])
@login_required
def message_send():
    receiver_id = request.args.get('receiver_id')
    
    if request.method == 'POST':
        receiver = request.form['receiver_id']
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        
        # 发送给所有人（仅管理员）
        if receiver == '__all__' and session.get('role') == 'admin':
            users = load_json('users.json')
            for user in users:
                if user['id'] != session['user_id']:
                    send_message(session['user_id'], user['id'], title, content, 'system_message')
            flash(f'消息已发送给 {len(users)-1} 位用户', 'success')
        else:
            send_message(session['user_id'], receiver, title, content)
            flash('消息已发送', 'success')
        flash('消息已发送', 'success')
        return redirect(url_for('messages'))
    
    users = load_json('users.json')
    return render_template('message_send.html', users=users, receiver_id=receiver_id)

@app.route('/messages/<message_id>')
@login_required
def message_detail(message_id):
    messages = load_json('messages.json')
    message = next((m for m in messages if m['id'] == message_id), None)
    
    if not message or message['receiver_id'] != session['user_id']:
        flash('消息不存在', 'danger')
        return redirect(url_for('messages'))
    
    if not message.get('is_read'):
        message['is_read'] = True
        message['read_at'] = datetime.now().isoformat()
        save_json('messages.json', messages)
    
    sender = get_user(message.get('sender_id'))
    message['sender_username'] = sender['username'] if sender else '未知'
    
    return render_template('message_detail.html', message=message)

@app.route('/messages/<message_id>/delete', methods=['POST'])
@login_required
def message_delete(message_id):
    messages = load_json('messages.json')
    # 支持列表和字典两种格式
    if isinstance(messages, dict):
        messages = list(messages.values())
    for m in messages:
        if m.get('id') == message_id and m.get('receiver_id') == session['user_id']:
            messages.remove(m)
            break
    save_json('messages.json', messages)
    
    flash('消息已删除', 'success')
    return redirect(url_for('messages'))

@app.route('/notifications')
@login_required
def notifications():
    user_id = session['user_id']
    all_notifications = load_json('notifications.json')
    notifications = [n for n in all_notifications if n.get('user_id') == user_id]
    notifications.sort(key=lambda x: x['created_at'], reverse=True)
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/<notification_id>/read', methods=['POST'])
@login_required
def notification_mark_read(notification_id):
    notifications = load_json('notifications.json')
    # 支持列表和字典两种格式
    if isinstance(notifications, dict):
        notifications = list(notifications.values())
    for n in notifications:
        if n.get('id') == notification_id and n.get('user_id') == session['user_id']:
            n['is_read'] = True
            break
    save_json('notifications.json', notifications)
    return redirect(request.referrer or url_for('notifications'))

@app.route('/notifications/clear_all', methods=['POST'])
@login_required
def notification_clear_all():
    notifications = load_json('notifications.json')
    if isinstance(notifications, dict):
        notifications = list(notifications.values())
    # 只删除当前用户的通知
    user_notif_ids = [n['id'] for n in notifications if n.get('user_id') == session['user_id']]
    all_notifs = load_json('notifications.json')
    if isinstance(all_notifs, dict):
        all_notifs = {k: v for k, v in all_notifs.items() if v['id'] not in user_notif_ids}
    else:
        all_notifs = [n for n in all_notifs if n['id'] not in user_notif_ids]
    save_json('notifications.json', all_notifs)
    return redirect(url_for('notifications'))

# ==================== 审核/管理员路由 ====================
@app.route('/admin')
@moderator_required
def admin_index():
    users = load_json('users.json')
    products = load_json('products.json')
    
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        products_list = list(products.values())
    else:
        products_list = products if products else []
    
    stats = {
        'total_users': len(users),
        'total_products': len(products),
        'pending_products': len([p for p in products_list if p.get('status') == 'pending']),
        'approved_products': len([p for p in products_list if p.get('status') == 'approved'])
    }
    
    pending = [p for p in products_list if p.get('status') == 'pending']
    for p in pending:
        seller = get_user(p.get('user_id'))
        p['seller_username'] = seller['username'] if seller else '未知'
    
    return render_template('admin/index.html', stats=stats, pending_products=pending[:5])

@app.route('/admin/approvals')
@moderator_required
def admin_approvals():
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        pending = [p for p in products.values() if p.get('status') == 'pending']
    else:
        pending = [p for p in products if p.get('status') == 'pending']
    for p in pending:
        seller = get_user(p.get('user_id'))
        p['seller_username'] = seller['username'] if seller else '未知'
    return render_template('admin/approvals.html', products=pending)

@app.route('/admin/product/<product_id>/approve', methods=['POST'])
@moderator_required
def admin_approve(product_id):
    products = load_json('products.json')
    product = None
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        product = products.get(product_id)
    else:
        for p in products:
            if p.get('id') == product_id:
                product = p
                break
    
    if product:
        product['status'] = 'approved'
        product['reviewed_by'] = session['user_id']
        product['reviewed_at'] = datetime.now().isoformat()
        save_json('products.json', products)
        
        # 通知卖家
        send_message(session['user_id'], product['user_id'], '商品审核通过', 
                     f'您的商品 "{product["title"]}" 已通过审核', 'review_result')
        flash('商品已通过审核', 'success')
    
    return redirect(url_for('admin_approvals'))

@app.route('/admin/product/<product_id>/reject', methods=['POST'])
@moderator_required
def admin_reject(product_id):
    products = load_json('products.json')
    product = None
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        product = products.get(product_id)
    else:
        for p in products:
            if p.get('id') == product_id:
                product = p
                break
    
    if product:
        reason = request.form.get('reason', '').strip()
        product['status'] = 'rejected'
        product['reject_reason'] = reason
        product['reviewed_by'] = session['user_id']
        product['reviewed_at'] = datetime.now().isoformat()
        save_json('products.json', products)
        
        msg = f'您的商品 "{product["title"]}" 未通过审核'
        if reason:
            msg += f'。原因: {reason}'
        send_message(session['user_id'], product['user_id'], '商品审核未通过', msg, 'review_result')
        flash('商品已拒绝', 'success')
    
    return redirect(url_for('admin_approvals'))

# ==================== 仅管理员路由 ====================
@app.route('/admin/users')
@admin_required
def admin_users():
    users = load_json('users.json')
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        users_list = list(users.values())
    else:
        users_list = users
    return render_template('admin/users.html', users=users_list)

@app.route('/admin/user/<user_id>/set-role/<role>', methods=['POST'])
@admin_required
def admin_set_role(user_id, role):
    users = load_json('users.json')
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        if user_id in users:
            users[user_id]['role'] = role
    else:
        for u in users:
            if u.get('id') == user_id:
                u['role'] = role
                break
    save_json('users.json', users)
    flash(f'已设置用户角色为 {role}', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    users = load_json('users.json')
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        users = {k: v for k, v in users.items() if k != user_id}
    else:
        users = [u for u in users if u.get('id') != user_id]
    save_json('users.json', users)
    flash('用户已删除', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/products')
@admin_required
def admin_products():
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        products_list = list(products.values())
    else:
        products_list = products
    for p in products_list:
        seller = get_user(p.get('user_id'))
        p['seller_username'] = seller['username'] if seller else '未知'
    return render_template('admin/products.html', products=products_list)

@app.route('/admin/product/<product_id>/delete', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        products = {k: v for k, v in products.items() if k != product_id}
    else:
        products = [p for p in products if p.get('id') != product_id]
    save_json('products.json', products)
    flash('商品已删除', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/notices')
@admin_required
def admin_notices():
    notices = load_json('notices.json')
    notices.sort(key=lambda x: x['created_at'], reverse=True)
    return render_template('admin/notices.html', notices=notices)

@app.route('/admin/notices/create', methods=['GET', 'POST'])
@admin_required
def admin_notice_create():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        
        notices = load_json('notices.json')
        # 支持列表和字典两种格式
        if isinstance(notices, dict):
            notices = list(notices.values())
        notice = {
            'id': uuid.uuid4().hex,
            'title': title,
            'content': content,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'created_by': session['user_id']
        }
        notices.append(notice)
        save_json('notices.json', notices)
        
        flash('公告已发布', 'success')
        return redirect(url_for('admin_notices'))
    
    return render_template('admin/notice_form.html')

@app.route('/admin/notices/<notice_id>/delete', methods=['POST'])
@admin_required
def admin_notice_delete(notice_id):
    notices = load_json('notices.json')
    # 支持列表和字典两种格式
    if isinstance(notices, dict):
        notices = {k: v for k, v in notices.items() if k != notice_id}
    else:
        notices = [n for n in notices if n.get('id') != notice_id]
    save_json('notices.json', notices)
    flash('公告已删除', 'success')
    return redirect(url_for('admin_notices'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    settings = load_json('settings.json')
    
    if request.method == 'POST':
        settings['image_compression']['enabled'] = 'compression_enabled' in request.form
        settings['image_compression']['threshold_mb'] = float(request.form.get('threshold_mb', 2))
        settings['image_compression']['quality'] = int(request.form.get('quality', 80))
        settings['image_compression']['max_width'] = int(request.form.get('max_width', 1920))
        settings['image_compression']['max_height'] = int(request.form.get('max_height', 1920))
        settings['site']['site_name'] = request.form.get('site_name', '二手商品交易平台')
        settings['site']['allow_registration'] = 'allow_registration' in request.form
        # Product settings
        if 'product' not in settings:
            settings['product'] = {}
        settings['product']['daily_limit'] = int(request.form.get('daily_limit', 10))
        save_json('settings.json', settings)
        flash('设置已保存', 'success')
    
    return render_template('admin/settings.html', settings=settings)

# ==================== 用户主页 ====================
@app.route('/user/<user_id>')
def user_profile(user_id):
    users = load_json('users.json')
    products = load_json('products.json')
    
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        if user_id not in users:
            flash('用户不存在', 'error')
            return redirect(url_for('index'))
        user = users[user_id]
    else:
        user = None
        for u in users:
            if u.get('id') == user_id:
                user = u
                break
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('index'))
    
    # Get all products by this user (including sold)
    if isinstance(products, dict):
        user_products = [p for p in products.values() if p.get('user_id') == user_id]
    else:
        user_products = [p for p in products if p.get('user_id') == user_id]
    # Sort by created_at descending
    user_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template('user_profile.html', user=user, products=user_products, user_id=user_id)


@app.route('/user/edit_intro', methods=['POST'])
@login_required
def edit_intro():
    users = load_json('users.json')
    user_id = session.get('user_id')
    
    # 支持列表和字典两种格式
    if isinstance(users, dict):
        if user_id and user_id in users:
            users[user_id]['intro'] = request.form.get('intro', '')[:500]
            save_json('users.json', users)
            flash('个人简介已更新', 'success')
    else:
        for u in users:
            if u.get('id') == user_id:
                u['intro'] = request.form.get('intro', '')[:500]
                break
        save_json('users.json', users)
        flash('个人简介已更新', 'success')
    
    return redirect(url_for('user_profile', user_id=user_id))

# ==================== 静态文件 ====================
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

# ==================== 启动 ====================


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    user = get_user(session["user_id"])
    if not user:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        user["nickname"] = request.form.get("nickname", "")
        user["intro"] = request.form.get("intro", "")
        user["gender"] = request.form.get("gender", "")
        user["location"] = request.form.get("location", "")
        
        users = load_json("users.json")
        for i, u in enumerate(users):
            if u["id"] == user["id"]:
                users[i] = user
                break
        save_json("users.json", users)
        flash("个人资料已更新", "success")
        return redirect(url_for("user_profile", user_id=user["id"]))
    return render_template("profile_edit.html", user=user)


# ==================== 学生认证 ====================

@app.route('/profile/verify', methods=['GET', 'POST'])
@login_required
def student_verify():
    user = get_user(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user['degree'] = request.form.get('degree', '')
        user['school'] = request.form.get('school', '')
        user['enrollment_year'] = request.form.get('enrollment_year', '')
        user['graduation_year'] = request.form.get('graduation_year', '')
        user['student_id_number'] = request.form.get('student_id_number', '')
        user['student_verify_status'] = 'pending'
        
        # 通知管理员有新认证申请
        admin_users = [u for u in load_json('users.json') if u.get('role') == 'admin']
        for admin in admin_users:
            send_notification(admin['id'], f'用户 {user.get("username")} 提交了学生认证申请', user['id'])
        
        if 'student_id_image' in request.files:
            file = request.files['student_id_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(BASE_DIR, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                user['student_id_image'] = filename
        
        users = load_json('users.json')
        for i, u in enumerate(users):
            if u['id'] == user['id']:
                users[i] = user
                break
        save_json('users.json', users)
        flash('学生认证申请已提交，请等待审核', 'info')
        return redirect(url_for('user_profile', user_id=user['id']))
    return render_template('student_verify.html', user=user)


@app.route('/admin/verifications')
@login_required
def admin_verifications():
    if session.get('role') != 'admin':
        flash('无权限', 'danger')
        return redirect(url_for('index'))
    users = load_json('users.json')
    verifications = [u for u in users if u.get('student_verify_status') == 'pending']
    return render_template('admin/verifications.html', verifications=verifications)


@app.route('/admin/verify/<user_id>/<action>')
@login_required
def admin_verify_user(user_id, action):
    if session.get('role') != 'admin':
        flash('无权限', 'danger')
        return redirect(url_for('index'))
    users = load_json('users.json')
    for user in users:
        if user['id'] == user_id:
            if action == 'approve':
                user['student_verify_status'] = 'approved'
                flash(f'已批准 {user.get("username")} 的学生认证', 'success')
                send_notification(user_id, '您的学生认证已通过审核！', user_id)
            elif action == 'reject':
                user['student_verify_status'] = 'rejected'
                flash(f'已拒绝 {user.get("username")} 的学生认证', 'warning')
                send_notification(user_id, '很抱歉，您的学生认证未通过审核，请重新提交', user_id)
            break
    save_json('users.json', users)
    return redirect(url_for('admin_verifications'))


if __name__ == '__main__':
    # 确保目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'covers'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'product_images'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'receipts'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'editor'), exist_ok=True)
    


@app.route('/product/<product_id>/report', methods=['POST'])
@login_required
def report_product(product_id):
    """Report a product as violating rules"""
    products = load_json('products.json')
    # 支持列表和字典两种格式
    if isinstance(products, dict):
        if product_id not in products:
            flash('商品不存在', 'error')
            return redirect(url_for('product_detail', product_id=product_id))
        product = products[product_id]
    else:
        product = None
        for p in products:
            if p.get('id') == product_id:
                product = p
                break
        if not product:
            flash('商品不存在', 'error')
            return redirect(url_for('product_detail', product_id=product_id))
    reason = request.form.get('reason', '')
    detail = request.form.get('detail', '')
    
    if not reason:
        flash('请选择举报原因', 'warning')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Create report
    reports = load_json('reports.json')
    report_id = generate_id()
    # 支持列表和字典两种格式
    if isinstance(reports, dict):
        reports[report_id] = {
            'id': report_id,
            'product_id': product_id,
            'reporter_id': session['user_id'],
            'seller_id': product.get('seller_id'),
            'reason': reason,
            'detail': detail,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
    else:
        reports = list(reports) if isinstance(reports, list) else []
        reports.append({
            'id': report_id,
            'product_id': product_id,
            'reporter_id': session['user_id'],
            'seller_id': product.get('seller_id'),
            'reason': reason,
            'detail': detail,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        })
    save_json('reports.json', reports)
    
    # Notify admin
    notifications = load_json('notifications.json')
    notif_id = generate_id()
    # 支持列表和字典两种格式
    if isinstance(notifications, dict):
        notifications[notif_id] = {
            'id': notif_id,
            'user_id': 'admin',
            'type': 'report',
            'title': '新商品举报',
            'message': f'商品 "{product.get("title", "未知")}" 收到举报，原因：{reason}',
            'read': False,
            'created_at': datetime.now().isoformat()
        }
    else:
        notifications = list(notifications) if isinstance(notifications, list) else []
        notifications.append({
            'id': notif_id,
            'user_id': 'admin',
            'type': 'report',
            'title': '新商品举报',
            'message': f'商品 "{product.get("title", "未知")}" 收到举报，原因：{reason}',
            'read': False,
            'created_at': datetime.now().isoformat()
        })
    save_json('notifications.json', notifications)
    
    flash('举报已提交，管理员将进行审核', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/admin/reports')
@login_required
def admin_reports():
    """Admin: View all reports"""
    if session.get('role') not in ['admin', 'moderator']:
        flash('无权访问', 'error')
        return redirect(url_for('index'))
    
    reports = load_json('reports.json')
    products = load_json('products.json')
    users = load_json('users.json')
    # 支持列表和字典两种格式
    if isinstance(reports, dict):
        sorted_reports = sorted(reports.values(), key=lambda x: x.get('created_at', ''), reverse=True)
    else:
        sorted_reports = sorted(reports, key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('admin/reports.html', reports=sorted_reports, products=products, users=users)

@app.route('/admin/report/<report_id>/action', methods=['POST'])
@login_required
def admin_report_action(report_id):
    """Admin: Take action on a report"""
    if session.get('role') not in ['admin', 'moderator']:
        flash('无权访问', 'error')
        return redirect(url_for('index'))
    
    reports = load_json('reports.json')
    products = load_json('products.json')
    
    if report_id not in reports:
        flash('举报不存在', 'error')
        return redirect(url_for('admin_reports'))
    
    report = reports[report_id]
    action = request.form.get('action')
    
    if action == 'valid':
        report['status'] = 'valid'
        if report['product_id'] in products:
            products[report['product_id']]['status'] = 'hidden'
            products[report['product_id']]['hidden_reason'] = report['reason']
            save_json('products.json', products)
        flash('商品已下架', 'success')
    elif action == 'ban_seller':
        users = load_json('users.json')
        seller_id = report.get('seller_id')
        if seller_id in users:
            users[seller_id]['status'] = 'banned'
            users[seller_id]['banned_at'] = datetime.now().isoformat()
            users[seller_id]['ban_reason'] = f'商品违规被举报：{report["reason"]}'
            save_json('users.json', users)
        for pid, p in products.items():
            if p.get('seller_id') == seller_id:
                p['status'] = 'hidden'
        save_json('products.json', products)
        flash('卖家已封号，商品已下架', 'success')
    elif action == 'invalid':
        report['status'] = 'invalid'
        flash('举报已标记为无效', 'info')
    
    report['reviewed_at'] = datetime.now().isoformat()
    report['reviewer_id'] = session['user_id']
    reports[report_id] = report
    save_json('reports.json', reports)
    
    return redirect(url_for('admin_reports'))


    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
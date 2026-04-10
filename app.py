from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import calendar
import os
from translations import TRANSLATIONS, Trans

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'terrain-smimou-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///terrain.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ─── Context processor ─────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    lang = session.get('lang', 'fr')
    if lang not in TRANSLATIONS:
        lang = 'fr'
    t = Trans(TRANSLATIONS[lang])
    return {
        'now': datetime.utcnow(),
        't': t,
        'lang': lang,
        'LANGS': [{'code': k, 'name': v['lang_name']} for k, v in TRANSLATIONS.items()],
        'public_user': session.get('public_user'),
    }


# ─── Language route ────────────────────────────────────────────────────────────

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


# ─── Models ────────────────────────────────────────────────────────────────────

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PublicUser(db.Model):
    __tablename__ = 'public_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    telephone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    date_reservation = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.String(10), nullable=False)
    heure_fin = db.Column(db.String(10), nullable=False)
    sport = db.Column(db.String(60), nullable=False)
    statut = db.Column(db.String(20), default='en attente')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def statut_badge(self):
        return {'confirmé': 'success', 'en attente': 'warning', 'annulé': 'danger'}.get(self.statut, 'secondary')


class TimeSlot(db.Model):
    __tablename__ = 'time_slot'
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class SiteSettings(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    weekly_limit = db.Column(db.Integer, default=2)


# ─── Init DB ───────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            admin = Admin(username='admin')
            admin.set_password('berserker2005@')
            db.session.add(admin)

        if not Reservation.query.first():
            samples = [
                Reservation(nom='Mohammed Ait Brahim', telephone='0661234567',
                            date_reservation=date(2026, 4, 1), heure_debut='08:00', heure_fin='10:00',
                            sport='Football', statut='confirmé'),
                Reservation(nom='Hassan Eddari', telephone='0672345678',
                            date_reservation=date(2026, 4, 1), heure_debut='10:00', heure_fin='12:00',
                            sport='Basketball', statut='confirmé'),
                Reservation(nom='Fatima Benali', telephone='0683456789',
                            date_reservation=date(2026, 4, 2), heure_debut='14:00', heure_fin='16:00',
                            sport='Volleyball', statut='en attente'),
                Reservation(nom='Youssef Ouzine', telephone='0694567890',
                            date_reservation=date(2026, 4, 3), heure_debut='16:00', heure_fin='18:00',
                            sport='Football', statut='en attente'),
                Reservation(nom='Aicha Moustaqim', telephone='0615678901',
                            date_reservation=date(2026, 4, 4), heure_debut='08:00', heure_fin='10:00',
                            sport='Tennis', statut='annulé', notes='Indisponibilité du terrain'),
                Reservation(nom='Rachid Bouhali', telephone='0626789012',
                            date_reservation=date(2026, 4, 5), heure_debut='10:00', heure_fin='12:00',
                            sport='Football', statut='confirmé'),
            ]
            db.session.bulk_save_objects(samples)

        if not TimeSlot.query.first():
            default_slots = [
                TimeSlot(start_time='08:00', end_time='10:00', is_active=True, sort_order=0),
                TimeSlot(start_time='10:00', end_time='12:00', is_active=True, sort_order=1),
                TimeSlot(start_time='12:00', end_time='14:00', is_active=True, sort_order=2),
                TimeSlot(start_time='14:00', end_time='16:00', is_active=True, sort_order=3),
                TimeSlot(start_time='16:00', end_time='18:00', is_active=True, sort_order=4),
                TimeSlot(start_time='18:00', end_time='20:00', is_active=True, sort_order=5),
            ]
            db.session.bulk_save_objects(default_slots)

        if not SiteSettings.query.first():
            db.session.add(SiteSettings(weekly_limit=2))

        db.session.commit()


# ─── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def get_active_slots():
    return [(s.start_time, s.end_time)
            for s in TimeSlot.query.filter_by(is_active=True).order_by(TimeSlot.sort_order).all()]


def get_weekly_limit():
    s = SiteSettings.query.first()
    return s.weekly_limit if s else 2


def count_week_reservations(telephone):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return Reservation.query.filter(
        Reservation.telephone == telephone,
        Reservation.date_reservation >= week_start,
        Reservation.date_reservation <= week_end,
        Reservation.statut.in_(['confirmé', 'en attente'])
    ).count()


# ─── Public user routes ─────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if session.get('public_user') or session.get('admin_logged_in'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        telephone = request.form.get('telephone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not all([username, telephone, password, confirm]):
            flash('Veuillez remplir tous les champs.', 'danger')
        elif password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
        elif len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
        elif PublicUser.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur est déjà pris.", 'danger')
        elif PublicUser.query.filter_by(telephone=telephone).first():
            flash('Ce numéro de téléphone est déjà utilisé.', 'danger')
        else:
            user = PublicUser(username=username, telephone=telephone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['public_user'] = {'id': user.id, 'username': user.username, 'telephone': user.telephone}
            flash(f'Bienvenue {username} ! Vous êtes maintenant inscrit.', 'success')
            return redirect(request.args.get('next') or url_for('planning'))
    return render_template('user_register.html')


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if session.get('public_user') or session.get('admin_logged_in'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = PublicUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['public_user'] = {'id': user.id, 'username': user.username, 'telephone': user.telephone}
            flash(f'Bienvenue {user.username} !', 'success')
            return redirect(request.args.get('next') or url_for('planning'))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", 'danger')
    return render_template('user_login.html')


@app.route('/logout-user')
def user_logout():
    session.pop('public_user', None)
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))


@app.route('/my-reservations')
def my_reservations():
    pub_user = session.get('public_user')
    if not pub_user:
        flash('Veuillez vous connecter pour voir vos réservations.', 'warning')
        return redirect(url_for('user_login', next=url_for('my_reservations')))
    reservations = (Reservation.query
                    .filter_by(telephone=pub_user['telephone'])
                    .order_by(Reservation.date_reservation.desc(), Reservation.heure_debut)
                    .all())
    weekly_limit = get_weekly_limit()
    weekly_used = count_week_reservations(pub_user['telephone'])
    return render_template('my_reservations.html',
                           reservations=reservations,
                           weekly_limit=weekly_limit,
                           weekly_used=weekly_used)


@app.route('/reservation/<int:rid>/attestation')
def attestation(rid):
    pub_user = session.get('public_user')
    is_admin = session.get('admin_logged_in')
    if not pub_user and not is_admin:
        flash('Veuillez vous connecter.', 'warning')
        return redirect(url_for('user_login'))
    r = Reservation.query.get_or_404(rid)
    if not is_admin and r.telephone != pub_user['telephone']:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('my_reservations'))
    if r.statut != 'confirmé':
        flash('L\'attestation n\'est disponible que pour les réservations confirmées.', 'warning')
        return redirect(url_for('my_reservations'))
    lang = session.get('lang', 'fr')
    t = Trans(TRANSLATIONS.get(lang, TRANSLATIONS['fr']))
    return render_template('attestation.html', r=r, t=t, lang=lang,
                           generated_at=datetime.now())


@app.route('/reservation/<int:rid>/cancel', methods=['POST'])
def cancel_reservation(rid):
    pub_user = session.get('public_user')
    if not pub_user:
        flash('Veuillez vous connecter.', 'warning')
        return redirect(url_for('user_login'))
    r = Reservation.query.get_or_404(rid)
    if r.telephone != pub_user['telephone']:
        flash('Vous ne pouvez pas annuler cette réservation.', 'danger')
        return redirect(url_for('my_reservations'))
    if r.statut == 'annulé':
        flash('Cette réservation est déjà annulée.', 'info')
    else:
        r.statut = 'annulé'
        db.session.commit()
        flash('Votre réservation a été annulée.', 'success')
    return redirect(url_for('my_reservations'))


# ─── Public routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    upcoming = (Reservation.query
                .filter(Reservation.date_reservation >= date.today(),
                        Reservation.statut == 'confirmé')
                .order_by(Reservation.date_reservation, Reservation.heure_debut)
                .limit(5).all())
    return render_template('index.html', upcoming=upcoming)


@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    if not session.get('public_user') and not session.get('admin_logged_in'):
        flash('Veuillez vous connecter pour faire une réservation.', 'warning')
        return redirect(url_for('user_login', next=url_for('planning')))

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        telephone = request.form.get('telephone', '').strip()
        date_str = request.form.get('date_reservation', '')
        heure_debut = request.form.get('heure_debut', '')
        heure_fin = request.form.get('heure_fin', '')
        sport = request.form.get('sport', '')
        notes = request.form.get('notes', '').strip()

        if not all([nom, telephone, date_str, heure_debut, heure_fin, sport]):
            flash('Veuillez remplir tous les champs obligatoires.', 'danger')
        else:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                if not session.get('admin_logged_in'):
                    weekly_limit = get_weekly_limit()
                    week_count = count_week_reservations(telephone)
                    if week_count >= weekly_limit:
                        flash(f'Vous avez atteint la limite de {weekly_limit} réservation(s) par semaine.', 'danger')
                        return redirect(url_for('planning'))

                conflict = Reservation.query.filter_by(
                    date_reservation=date_obj, heure_debut=heure_debut, statut='confirmé'
                ).first()
                if conflict:
                    flash('Ce créneau est déjà réservé. Veuillez choisir un autre horaire.', 'danger')
                else:
                    r = Reservation(nom=nom, telephone=telephone,
                                    date_reservation=date_obj,
                                    heure_debut=heure_debut, heure_fin=heure_fin,
                                    sport=sport, notes=notes)
                    db.session.add(r)
                    db.session.commit()
                    flash('Votre réservation a été soumise avec succès ! Nous vous contacterons pour confirmation.', 'success')
                    return redirect(url_for('planning', month=date_obj.month, year=date_obj.year))
            except ValueError:
                flash('Date invalide.', 'danger')

    return render_template('reservation.html', today=date.today().isoformat(),
                           slots=get_active_slots())


# ─── Admin routes ──────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            flash('Connexion réussie !', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", 'danger')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin', methods=['GET', 'POST'])
@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    statut_filter = request.args.get('statut', '')
    date_filter = request.args.get('date', '')
    sport_filter = request.args.get('sport', '')
    query = Reservation.query
    if statut_filter:
        query = query.filter_by(statut=statut_filter)
    if date_filter:
        try:
            query = query.filter_by(date_reservation=datetime.strptime(date_filter, '%Y-%m-%d').date())
        except ValueError:
            pass
    if sport_filter:
        query = query.filter_by(sport=sport_filter)
    reservations = query.order_by(Reservation.date_reservation.desc(), Reservation.heure_debut).all()
    stats = {
        'total': Reservation.query.count(),
        'confirmées': Reservation.query.filter_by(statut='confirmé').count(),
        'en_attente': Reservation.query.filter_by(statut='en attente').count(),
        'annulées': Reservation.query.filter_by(statut='annulé').count(),
    }
    sports = [r[0] for r in db.session.query(Reservation.sport).distinct().all()]
    weekly_limit = get_weekly_limit()

    if request.method == 'POST' and request.form.get('action') == 'set_limit':
        try:
            limit = int(request.form.get('weekly_limit', 2))
            if limit < 1:
                limit = 1
            settings = SiteSettings.query.first()
            if settings:
                settings.weekly_limit = limit
            else:
                db.session.add(SiteSettings(weekly_limit=limit))
            db.session.commit()
            flash(f'Limite hebdomadaire mise à jour : {limit} réservation(s)/semaine.', 'success')
            return redirect(url_for('admin_dashboard'))
        except ValueError:
            flash('Valeur invalide.', 'danger')

    return render_template('admin_dashboard.html', reservations=reservations,
                           stats=stats, sports=sports,
                           statut_filter=statut_filter, date_filter=date_filter,
                           sport_filter=sport_filter, weekly_limit=weekly_limit)


@app.route('/admin/reservation/<int:rid>/statut', methods=['POST'])
@login_required
def update_statut(rid):
    r = Reservation.query.get_or_404(rid)
    new_statut = request.form.get('statut')
    if new_statut in ['confirmé', 'en attente', 'annulé']:
        r.statut = new_statut
        db.session.commit()
        flash(f'Réservation #{rid} mise à jour.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reservation/<int:rid>/delete', methods=['POST'])
@login_required
def delete_reservation(rid):
    r = Reservation.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash(f'Réservation #{rid} supprimée.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reservation/new', methods=['GET', 'POST'])
@login_required
def admin_new_reservation():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        telephone = request.form.get('telephone', '').strip()
        date_str = request.form.get('date_reservation', '')
        heure_debut = request.form.get('heure_debut', '')
        heure_fin = request.form.get('heure_fin', '')
        sport = request.form.get('sport', '')
        statut = request.form.get('statut', 'en attente')
        notes = request.form.get('notes', '').strip()
        if not all([nom, telephone, date_str, heure_debut, heure_fin, sport]):
            flash('Veuillez remplir tous les champs obligatoires.', 'danger')
        else:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                r = Reservation(nom=nom, telephone=telephone, date_reservation=date_obj,
                                heure_debut=heure_debut, heure_fin=heure_fin,
                                sport=sport, statut=statut, notes=notes)
                db.session.add(r)
                db.session.commit()
                flash('Réservation ajoutée avec succès.', 'success')
                return redirect(url_for('admin_dashboard'))
            except ValueError:
                flash('Date invalide.', 'danger')
    return render_template('admin_new_reservation.html', slots=get_active_slots())


# ─── Admin settings (slots + weekly limit) ─────────────────────────────────────

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            start = request.form.get('start_time', '').strip()
            end = request.form.get('end_time', '').strip()
            if start and end:
                max_order = db.session.query(db.func.max(TimeSlot.sort_order)).scalar() or 0
                db.session.add(TimeSlot(start_time=start, end_time=end, sort_order=max_order + 1))
                db.session.commit()
                flash('Créneau ajouté.', 'success')
        elif action == 'delete':
            slot = TimeSlot.query.get(request.form.get('slot_id'))
            if slot:
                db.session.delete(slot)
                db.session.commit()
                flash('Créneau supprimé.', 'info')
        elif action == 'toggle':
            slot = TimeSlot.query.get(request.form.get('slot_id'))
            if slot:
                slot.is_active = not slot.is_active
                db.session.commit()
        elif action == 'set_limit':
            try:
                limit = int(request.form.get('weekly_limit', 2))
                if limit < 1:
                    limit = 1
                settings = SiteSettings.query.first()
                if settings:
                    settings.weekly_limit = limit
                else:
                    db.session.add(SiteSettings(weekly_limit=limit))
                db.session.commit()
                flash(f'Limite hebdomadaire mise à jour : {limit} réservation(s) par semaine.', 'success')
            except ValueError:
                flash('Valeur invalide.', 'danger')
        return redirect(url_for('admin_settings'))
    slots = TimeSlot.query.order_by(TimeSlot.sort_order).all()
    settings = SiteSettings.query.first()
    weekly_limit = settings.weekly_limit if settings else 2
    return render_template('admin_settings.html', all_slots=slots, weekly_limit=weekly_limit)


# ─── Planning ──────────────────────────────────────────────────────────────────

@app.route('/planning')
def planning():
    today = date.today()

    # Week navigation — default to current week's Monday
    week_str = request.args.get('week')
    if week_str:
        try:
            week_start = date.fromisoformat(week_str)
            # Normalize to Monday
            week_start -= timedelta(days=week_start.weekday())
        except ValueError:
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end  = week_start + timedelta(days=6)
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    slots = get_active_slots()

    reservations = Reservation.query.filter(
        Reservation.date_reservation >= week_start,
        Reservation.date_reservation <= week_end
    ).all()

    # lookup[date_obj][heure_debut] = reservation
    lookup = {}
    for r in reservations:
        lookup.setdefault(r.date_reservation, {})[r.heure_debut] = r

    is_admin    = bool(session.get('admin_logged_in'))
    is_logged_in = is_admin or bool(session.get('public_user'))

    pub_user     = session.get('public_user')
    weekly_used  = 0
    weekly_limit = get_weekly_limit()
    if pub_user and not is_admin:
        weekly_used = count_week_reservations(pub_user['telephone'])

    return render_template('planning.html',
                           week_start=week_start,
                           week_end=week_end,
                           week_days=week_days,
                           prev_week=prev_week,
                           next_week=next_week,
                           slots=slots,
                           lookup=lookup,
                           today=today,
                           is_admin=is_admin,
                           is_logged_in=is_logged_in,
                           weekly_used=weekly_used,
                           weekly_limit=weekly_limit)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

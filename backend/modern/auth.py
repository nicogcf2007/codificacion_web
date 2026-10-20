"""Database-backed browser sessions; no public registration or bearer fallback."""
from __future__ import annotations
import hashlib
import hmac
import re
import secrets
import time
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException
from sqlalchemy import select, insert, update, func, case
from sqlalchemy.exc import IntegrityError
from . import db
from .repository import identity, now, record_activity

PUBLIC_USER_FIELDS = ('id', 'email', 'name', 'role', 'active', 'must_change_password', 'created_at')
LOGIN_FAILURE = 'Correo o contraseña inválidos'
HASHER = PasswordHasher(type=Type.ID)
# Only a timing equalizer, not a credential or a usable account.
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def csrf_for(token):
    return hmac.new(token.encode('utf-8'), b'cnc-csrf-v1', hashlib.sha256).hexdigest()


def public_user(user):
    return {key: user[key] for key in PUBLIC_USER_FIELDS}


def valid_email(email):
    email = email.strip().casefold()
    if len(email) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", email):
        raise ValueError('Correo electrónico inválido')
    return email


def validate_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError('La contraseña debe tener entre 12 y 128 caracteres')


class AuthService:
    def __init__(self, engine, session_ttl_seconds=28800, clock=None):
        if not 1 <= session_ttl_seconds <= 604800:
            raise ValueError('Duración de sesión inválida')
        self.engine = engine
        self.session_ttl_seconds = session_ttl_seconds
        self.clock = clock or time.time

    def bootstrap(self, email=None, password=None, name=None):
        with self.engine.connect() as conn:
            if conn.scalar(select(func.count()).select_from(db.users)):
                return None
        if not any((email, password, name)):
            return None
        if not all((email, password, name)):
            raise ValueError('Bootstrap ADMIN requiere email, contraseña y nombre')
        email = valid_email(email)
        validate_password(password)
        name = name.strip()
        if not name or len(name) > 240:
            raise ValueError('Nombre inválido')
        user = dict(id=identity(), email=email, name=name, role='ADMIN', active=True,
                    must_change_password=False, password_hash=HASHER.hash(password), created_at=now())
        try:
            with self.engine.begin() as conn:
                # A unique durable reservation serializes simultaneous bootstraps.
                conn.execute(insert(db.bootstrap_state).values(id='initial-admin'))
                if conn.scalar(select(func.count()).select_from(db.users)):
                    return None
                conn.execute(insert(db.users).values(**user))
        except IntegrityError:
            return None
        return public_user(user)

    def get_user(self, user_id):
        with self.engine.connect() as conn:
            user = conn.execute(select(db.users).where(db.users.c.id == user_id)).mappings().first()
            if user is None:
                raise KeyError('Usuario no encontrado')
            return public_user(user)

    def list_users(self):
        with self.engine.connect() as conn:
            return [public_user(row) for row in conn.execute(select(db.users).order_by(db.users.c.created_at, db.users.c.id)).mappings()]

    def create_user(self, actor_id, email, name, password, role, must_change_password):
        actor = self.get_user(actor_id)
        if not actor['active'] or actor['must_change_password'] or actor['role'] != 'ADMIN':
            raise HTTPException(403, 'Se requiere rol ADMIN')
        validate_password(password)
        if role not in {'ADMIN', 'STANDARD'} or not isinstance(must_change_password, bool):
            raise ValueError('Rol o indicador de contraseña inválidos')
        name = name.strip()
        if not name or len(name) > 240:
            raise ValueError('Nombre inválido')
        user = dict(id=identity(), email=valid_email(email), name=name, role=role, active=True,
                    must_change_password=must_change_password, password_hash=HASHER.hash(password), created_at=now())
        try:
            with self.engine.begin() as conn:
                conn.execute(insert(db.users).values(**user))
                record_activity(conn, actor_id, 'user_created', 'user', user['id'])
        except IntegrityError:
            raise HTTPException(409, 'La cuenta ya existe') from None
        return public_user(user)

    def change_password(self, context, current_password, password):
        validate_password(password)
        user_id = context['user']['id']
        with self.engine.connect() as conn:
            user = conn.execute(select(db.users).where(db.users.c.id == user_id)).mappings().one()
        try:
            valid = HASHER.verify(user['password_hash'], current_password)
        except (VerificationError, InvalidHashError):
            valid = False
        if not valid:
            raise HTTPException(401, LOGIN_FAILURE)
        new_hash = HASHER.hash(password)
        with self.engine.begin() as conn:
            live_session = conn.scalar(select(db.sessions.c.id).where(db.sessions.c.id == context['session_id'],
                db.sessions.c.revoked.is_(False), db.sessions.c.expires_at > self.clock()))
            if not live_session:
                raise HTTPException(401, 'Sesión inválida o ausente')
            changed = conn.execute(update(db.users).where(db.users.c.id == user_id, db.users.c.active.is_(True),
                db.users.c.password_hash == user['password_hash']).values(password_hash=new_hash, must_change_password=False)).rowcount
            if not changed:
                raise HTTPException(401, LOGIN_FAILURE)
            conn.execute(update(db.sessions).where(db.sessions.c.user_id == user_id,
                db.sessions.c.id != context['session_id']).values(revoked=True))
            record_activity(conn, user_id, 'password_changed', 'user', user_id)
        return {'user': self.get_user(user_id), 'csrf_token': context['csrf_token']}

    def reserve_login_attempt(self, remote):
        # No email-address/IP plaintext retained; a shared per-peer bucket also
        # prevents rotating account identifiers from evading the limit.
        bucket, instant = digest(remote), self.clock()
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        from sqlalchemy.dialects.postgresql import insert as postgres_insert
        factory = sqlite_insert if self.engine.dialect.name == 'sqlite' else postgres_insert
        stale = db.login_attempts.c.window_start <= instant - 300
        statement = factory(db.login_attempts).values(bucket=bucket, window_start=instant, attempts=1)
        statement = statement.on_conflict_do_update(index_elements=['bucket'], set_={
            'window_start': case((stale, instant), else_=db.login_attempts.c.window_start),
            'attempts': case((stale, 1), else_=db.login_attempts.c.attempts + 1),
        }).returning(db.login_attempts.c.attempts)
        with self.engine.begin() as conn:
            attempts = conn.scalar(statement)
        if attempts > 10:
            raise HTTPException(429, LOGIN_FAILURE, headers={'Retry-After': '300'})

    def login(self, email, password, remote='local'):
        self.reserve_login_attempt(remote)
        try:
            email = valid_email(email)
        except ValueError:
            email = ''
        with self.engine.connect() as conn:
            user = conn.execute(select(db.users).where(db.users.c.email == email)).mappings().first()
        try:
            verified = HASHER.verify(user['password_hash'] if user else DUMMY_HASH, password)
        except (VerificationError, InvalidHashError):
            verified = False
        if not verified or not user or not user['active']:
            raise HTTPException(401, LOGIN_FAILURE)
        token = secrets.token_urlsafe(32)
        csrf = csrf_for(token)
        session = dict(id=identity(), user_id=user['id'], token_hash=digest(token), csrf_hash=digest(csrf),
                       expires_at=self.clock() + self.session_ttl_seconds, revoked=False, created_at=now())
        replacement = HASHER.hash(password) if HASHER.check_needs_rehash(user['password_hash']) else user['password_hash']
        with self.engine.begin() as conn:
            changed = conn.execute(update(db.users).where(db.users.c.id == user['id'],
                db.users.c.active.is_(True), db.users.c.password_hash == user['password_hash']).values(password_hash=replacement)).rowcount
            if not changed:
                raise HTTPException(401, LOGIN_FAILURE)
            conn.execute(insert(db.sessions).values(**session))
        return token, {'user': public_user(user), 'csrf_token': csrf}

    def resolve(self, token):
        if not token or len(token) > 128:
            raise HTTPException(401, 'Sesión inválida o ausente')
        with self.engine.connect() as conn:
            session = conn.execute(select(db.sessions).where(db.sessions.c.token_hash == digest(token),
                db.sessions.c.revoked.is_(False), db.sessions.c.expires_at > self.clock())).mappings().first()
            user = conn.execute(select(db.users).where(db.users.c.id == session['user_id'],
                db.users.c.active.is_(True))).mappings().first() if session else None
        csrf = csrf_for(token)
        if not session or not user or not hmac.compare_digest(session['csrf_hash'], digest(csrf)):
            raise HTTPException(401, 'Sesión inválida o ausente')
        return {'session_id': session['id'], 'user': public_user(user), 'csrf_token': csrf}

    def logout(self, session_id):
        with self.engine.begin() as conn:
            conn.execute(update(db.sessions).where(db.sessions.c.id == session_id).values(revoked=True))

    def check_csrf(self, request, context):
        expected = context['csrf_token']
        header = request.headers.get('x-csrf-token', '')
        cookie = request.cookies.get('cnc_csrf', '')
        if not hmac.compare_digest(header.encode('utf-8'), expected.encode('utf-8')) or not hmac.compare_digest(cookie.encode('utf-8'), expected.encode('utf-8')):
            raise HTTPException(403, 'Token CSRF inválido o ausente')

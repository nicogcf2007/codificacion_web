"""Provision the first administrator from server environment, without a web API.
Never prints identifiers, passwords, connection strings or raw exceptions.
"""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    from modern.auth import AuthService
    from modern.db import database
    url = os.getenv('DATABASE_URL') or 'sqlite:///' + (ROOT / 'backend/data/modern.sqlite3').as_posix()
    engine = None
    try:
        engine = database(url)
        auth = AuthService(engine)
        if auth.list_users():
            print('Ya existen cuentas. No se modificaron usuarios ni contrasenas.')
            return 0
        email, password, name = (os.getenv(key) for key in ('CNC_ADMIN_EMAIL', 'CNC_ADMIN_PASSWORD', 'CNC_ADMIN_NAME'))
        if not email or not password or not name:
            print('Faltan las variables de provisionamiento del servidor.', file=sys.stderr)
            return 1
        created = auth.bootstrap(email, password, name)
        if created and auth.get_user(created['id'])['role'] == 'ADMIN':
            print('Administrador inicial creado y verificado. Puedes iniciar sesion.')
        else:
            print('El administrador ya fue provisionado por otro proceso. No se modificaron cuentas.')
        return 0
    except Exception:
        print('No fue posible provisionar el administrador. Comprueba los datos y el entorno del servidor.', file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())

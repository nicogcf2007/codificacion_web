"""Static regression for the public local launcher; no secret or server access."""
from pathlib import Path
from contextlib import closing
import os
import secrets
import sqlite3
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class SessionLauncherTests(unittest.TestCase):
    def test_first_admin_bootstrap_uses_masked_input_and_server_env(self):
        script=(ROOT/'scripts/run-local.ps1').read_text(encoding='utf-8')
        self.assertIn('BootstrapAdmin',script)
        self.assertIn('CNC_ADMIN_EMAIL',script)
        self.assertIn('CNC_ADMIN_PASSWORD',script)
        self.assertIn('-AsSecureString',script)
        self.assertIn('ZeroFreeBSTR',script)
        self.assertNotIn('APP_ACCESS_TOKEN',script)

    def test_proxy_preserves_origin_port_for_cookie_sessions(self):
        nginx=(ROOT/'frontend/nginx.conf').read_text(encoding='utf-8')
        self.assertIn('proxy_set_header Host $http_host;',nginx)
        self.assertNotIn('proxy_set_header Host $host;',nginx)

    def test_offline_first_admin_setup_can_run_while_web_server_is_running(self):
        script=(ROOT/'scripts/create-admin.ps1').read_text(encoding='utf-8')
        self.assertIn('-AsSecureString',script)
        self.assertIn('ZeroFreeBSTR',script)
        self.assertIn('provision-admin.py',script)
        self.assertNotIn('uvicorn',script)

    def test_offline_provisioning_creates_one_admin_and_never_resets_password(self):
        scratch=Path.home()/'AppData/Local/hermes/cache/scratch'
        with tempfile.TemporaryDirectory(prefix='cnc-admin-cli-',dir=scratch) as directory:
            db_path=Path(directory)/'synthetic.sqlite3'
            env=os.environ.copy()
            env.update(DATABASE_URL='sqlite:///'+db_path.as_posix(),CNC_ADMIN_EMAIL='cli-admin@example.test',CNC_ADMIN_PASSWORD=secrets.token_urlsafe(24),CNC_ADMIN_NAME='QA sintético')
            def run():
                return subprocess.run([str(ROOT/'backend/venv/Scripts/python.exe'),str(ROOT/'scripts/provision-admin.py')],cwd=ROOT,env=env,text=True,capture_output=True)
            created=run()
            self.assertEqual(created.returncode,0)
            self.assertIn('creado y verificado',created.stdout)
            with closing(sqlite3.connect(db_path)) as conn:
                table=next(name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'") if name.endswith('users'))
                first=conn.execute(f'SELECT password_hash,role FROM "{table}"').fetchall()
            self.assertEqual(len(first),1)
            self.assertEqual(first[0][1],'ADMIN')
            env['CNC_ADMIN_PASSWORD']=secrets.token_urlsafe(24)
            existing=run()
            self.assertEqual(existing.returncode,0)
            self.assertIn('No se modificaron',existing.stdout)
            with closing(sqlite3.connect(db_path)) as conn:
                self.assertEqual(first,conn.execute(f'SELECT password_hash,role FROM "{table}"').fetchall())
            self.assertNotIn(env['CNC_ADMIN_PASSWORD'],created.stdout+existing.stdout+created.stderr+existing.stderr)


if __name__=='__main__':unittest.main()

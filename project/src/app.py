"""Bootstrap: inicializa proteção local antes de carregar qualquer sessão."""
import asyncio
import logging
import os
from cryptography.fernet import Fernet
import flet as ft


def windows_key(path):
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    def protect(data, decrypt=False):
        buffer = ctypes.create_string_buffer(data)
        source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
        target = Blob()
        function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(target.data, target.size)
        finally:
            ctypes.windll.kernel32.LocalFree(target.data)
    if path.exists():
        return protect(path.read_bytes(), True)
    key = Fernet.generate_key()
    path.write_bytes(protect(key))
    return key


async def bootstrap(page: ft.Page):
    from cloud import storage_dir, SESSION_PATH, CACHE_PATH
    from services.privacy import Vault
    from main import NexGranaCloud
    page.add(ft.Text('Preparando seu NexGrana…'))
    try:
        if os.name == 'nt':
            key = windows_key(storage_dir()/'device-key.dpapi')
        else:
            import flet_secure_storage as fss
            secure = fss.SecureStorage()
            page.services.append(secure)
            page.update()
            key = await asyncio.wait_for(secure.get('nexgrana.device-key.v1'), 15)
            if not key:
                key = Fernet.generate_key().decode()
                await asyncio.wait_for(secure.set('nexgrana.device-key.v1',key),15)
        vault = Vault(storage_dir()/'vault',key)
    except Exception as exc:
        logging.getLogger(__name__).warning('secure_storage_bootstrap_failed kind=%s',type(exc).__name__)
        page.clean()
        page.add(ft.Text('Não foi possível abrir o armazenamento protegido deste dispositivo. Reinicie o aplicativo. Nenhuma sessão foi gravada sem proteção.'))
        return

    try:
        # Migra somente uma sessão plaintext antiga; o arquivo é apagado mesmo
        # quando a migração falha para não perpetuar credenciais desprotegidas.
        if SESSION_PATH.exists():
            import json
            try:
                old=json.loads(SESSION_PATH.read_text(encoding='utf-8'))
                if old.get('access_token') and old.get('refresh_token'):
                    vault.write(SESSION_PATH.name,old)
            finally:
                SESSION_PATH.unlink(missing_ok=True)
        CACHE_PATH.unlink(missing_ok=True)
        # Controles Flet são criados no loop principal; rede pesada é tratada
        # pelos próprios serviços/handlers.
        NexGranaCloud(page,vault)
    except Exception as exc:
        logging.getLogger(__name__).warning('app_bootstrap_failed kind=%s',type(exc).__name__)
        page.clean()
        page.add(ft.Text('O armazenamento seguro abriu, mas o NexGrana não conseguiu carregar a interface/conta. Tente novamente e, se persistir, verifique a conexão e as migrações do banco.'))


if __name__ == '__main__':
    ft.run(bootstrap)

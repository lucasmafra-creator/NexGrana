"""Cofre cifrado; chave mestra fornecida pelo armazenamento seguro do SO."""
import hashlib
import json
import os
import threading
from contextlib import closing
from pathlib import Path
from cryptography.fernet import Fernet

POLICY_VERSION = '2026-09-13.1'
POLICY_TEXT = 'NexGrana — resumo de privacidade (versão 2026-09-13.1)\n\nO NexGrana trata os dados que você e os integrantes autorizados registram para organizar receitas, despesas, rateios, metas, aquisições, compras de mercado, trilhas e preferências do espaço familiar. O perfil ativo personaliza a experiência; a identidade e permissões continuam vinculadas à conta autenticada.\n\nFinalidades principais: fornecer o serviço financeiro solicitado; sincronizar dados entre dispositivos; calcular saldos e projeções; permitir exportação/backup; manter segurança e integridade; e exibir recursos opcionais quando houver consentimento. Recomendações não movimentam dinheiro automaticamente.\n\nArmazenamento e fornecedores: autenticação e banco usam Supabase. Sessão, preferências pessoais e cache local são protegidos no dispositivo. Conversa local não é enviada a provedor externo de IA nesta versão. Caso IA externa seja adicionada, deverá existir backend seguro, minimização de contexto e consentimento/aviso apropriado antes do envio.\n\nFotos de notas ficam temporariamente na memória durante a conferência manual e não são enviadas a OCR externo nesta versão. Links de afiliado são opcionais e externos; o NexGrana não acrescenta saldo, despesas, renda, metas ou histórico financeiro ao link. Personalização de ofertas a partir de dados financeiros permanece desativada sem consentimento específico.\n\nCompartilhamento familiar: integrantes autorizados do mesmo espaço podem visualizar os dados permitidos pelas regras do produto. O acesso é protegido por autenticação e RLS no banco. Nunca informe senha bancária, PIN, CVV ou número completo de cartão ao app.\n\nSeus controles: você pode corrigir registros, exportar uma cópia dos dados, revogar consentimentos opcionais e limpar dados locais ao sair. Exclusão integral de conta/espaço e portabilidade pública exigem fluxo administrativo seguro antes do lançamento comercial; o app não deve fingir que executou exclusão quando esse backend não estiver disponível.\n\nRetenção: dados financeiros permanecem enquanto o espaço/conta existir ou conforme necessidade legítima do serviço e obrigações aplicáveis. Prazos formais de retenção, controlador, contato de privacidade, bases legais e lista final de suboperadores devem ser publicados e revisados juridicamente antes do lançamento público.\n\nEsta tela é uma medida de transparência do produto e não substitui revisão jurídica da política de privacidade/LGPD antes da publicação comercial.'


class Vault:
    def __init__(self, root, key):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(key)
        self.lock = threading.RLock()

    def _path(self, name):
        return self.root / (hashlib.sha256(name.encode()).hexdigest() + '.enc')

    def read(self, name, default=None):
        with self.lock:
            p = self._path(name)
            if not p.exists():
                return default
            return json.loads(self.cipher.decrypt(p.read_bytes()))

    def write(self, name, value):
        with self.lock:
            p = self._path(name)
            temp = p.with_suffix('.tmp')
            temp.write_bytes(self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode()))
            os.replace(temp, p)

    def remove(self, name):
        self._path(name).unlink(missing_ok=True)

    def clear(self):
        with self.lock:
            for p in self.root.glob('*.enc'):
                p.unlink()

    def clear_keys(self, names):
        with self.lock:
            for name in names:
                self.remove(name)


def export_snapshot(cloud):
    tables = ('income','expenses','expense_shares','acquisitions','financial_goals',
              'wallet_accounts','semester_summaries','market_trips','market_items',
              'goal_contributions','nex_journeys','privacy_consents')
    result = {'format':'nexgrana-snapshot', 'version':1, 'household':cloud.household,
              'members':cloud.list_members(), 'tables':{}}
    for table in tables:
        if table == 'expense_shares':
            result['tables'][table] = [s for e in cloud.all_expenses_full() for s in e.get('expense_shares', [])]
        else:
            result['tables'][table] = cloud.fetch_all(table)
    return result


def write_backup(path, payload):
    import sqlite3
    with closing(sqlite3.connect(path)) as db:
        db.execute('create table snapshot (id integer primary key check(id=1), payload text not null)')
        db.execute('insert into snapshot values (1,?)', (json.dumps(payload, ensure_ascii=False),))
        db.commit()
        if db.execute('pragma integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Backup inconsistente')


def read_backup(path):
    import sqlite3
    with closing(sqlite3.connect(f'{Path(path).as_uri()}?mode=ro', uri=True)) as db:
        data = json.loads(db.execute('select payload from snapshot where id=1').fetchone()[0])
    if data.get('format') != 'nexgrana-snapshot' or data.get('version') != 1:
        raise ValueError('Formato de backup inválido')
    return data

# Segurança
Nenhum token, senha, banco operacional ou evidência pessoal bruta deve integrar este ZIP. Manifesto registra hashes dos arquivos compartilhados; originais privados ficam fora.

SQL mantém owner/household e RLS; RPCs de mensagens/orçamento/fechamento usam SECURITY INVOKER, auth.uid e escopo. Exclusão conserva tombstones, não apaga finanças; confirmação obrigatória. Testes SQL cobrem isolamento, repetição e rollback. Ainda requer teste em staging com duas contas.

Backup usa fechamento explícito e retry limitado, nunca taskkill amplo ou exclusão forçada. Runner só opera manualmente em código confiável: cópia e allowlist NÃO constituem sandbox de arquivos/rede. Não pode executar código recebido de usuários automaticamente. Registro de artefato usa endpoint loopback, sem redirects/proxy ambiente; nunca lança EXE. Relatório importado exige evidência/hash, autorização CEO e deduplicação. Stable imutável, DONE não automatizado.

RESET QA mantém autorização por UUID e workspace descartável; diagnósticos não relaxam controles. Recusa no banco ativo ainda não foi reproduzida com credenciais, portanto causa específica de staging não está confirmada. Não aplicar migrations em produção nem substituir instalação ativa sem comparar suas personalizações.

## RC7 Mercado
Novas RPCs SECURITY INVOKER com dono do registro, household e membro autorizados; nenhuma flexibilização de RLS. Vínculo de compra é único por trip e sobrevive à remoção da compra; edição/exclusão de Mercado não altera despesas anteriores. Desfazer exige estado correspondente ao resultado original e valida conflito no servidor. Ações e metadados financeiros ficam no banco protegido; nunca em logs públicos. Migrações novas somente em staging após backup/revisão.

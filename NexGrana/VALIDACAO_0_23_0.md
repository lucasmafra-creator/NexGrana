# Validação — NexGrana 0.23.0 QA RC1

## Executado nesta candidata

- `compileall` de `src`, `admin` e `gateway`: OK.
- suíte Python completa com dependências locais: **130/130 OK**.
- suíte principal sem UI: validada pelo `validate_release.py`.
- varredura de segredos e artefatos locais: OK.
- cadeia SQL/PGlite até `MIGRATION_0_23.sql`: deve permanecer obrigatória antes do pacote final.
- Golden Nex SHA-256: `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.

## Ainda exige homologação do proprietário

- abrir e revisar visualmente Home, Transações, Planejamento, Mercado, Nex, Mais e Tutorial;
- testar teclado/Voltar no Android físico;
- gerar, instalar e abrir Windows e APK 0.23.0;
- testar rede boa, mediana, offline e reconexão;
- testar gateway online somente após hospedagem HTTPS e consentimento;
- build iOS em macOS.

Build não é declarado validado antes dessas etapas.

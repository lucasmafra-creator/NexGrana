# Builds — QA RC2

O ZIP é **código-fonte**. Windows e Android não foram compilados nesta rodada:
este ambiente Linux não possui Flutter/Android SDK e não compila binário Windows.
Use os scripts `VALIDAR_0_24.cmd`, `VALIDAR_SQL_0_24.cmd`, depois
`COMPILAR_0_24_WINDOWS.cmd` e `COMPILAR_0_24_ANDROID.cmd` no Windows e
registre caminho, log e SHA-256 de cada artefato. Nenhum APK/EXE novo foi
testado no aparelho do proprietário.

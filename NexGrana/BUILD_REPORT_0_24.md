# Builds — candidata 0.24.0 QA RC1

O código foi validado em Linux; o ZIP contém fonte e scripts, **não contém
binários Windows ou Android compilados**. Nenhum build dessas plataformas
foi concluído neste ambiente. iOS requer Mac/Xcode e assinatura.

Ao extrair o ZIP no Windows, execute `VALIDAR_0_24.cmd` a partir da pasta
`project`, depois `COMPILAR_0_24_WINDOWS.cmd` ou
`COMPILAR_0_24_ANDROID.cmd`. Antes de compartilhar um APK/EXE, registre
no relatório local: versão, caminho e SHA-256 do artefato, `build-*.log`,
testes de instalação/abertura e Supabase de destino. O empacotador de fonte
relata builds como `not generated` no manifest; não convertê-los em sucesso
apenas porque o script foi iniciado.

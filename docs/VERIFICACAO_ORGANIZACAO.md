# Verificação da organização e publicação

Data: 2026-09-22.

- Núcleo: 16 testes de preservação aprovados.
- Extensão experimental: 12 testes aprovados.
- Notebooks: validação estática aprovada; saídas e contagens removidas das cópias publicadas.
- SMOKE: cadeia 01/03/02/04 aprovada em cópia isolada, sem sobrescrever resultados da pesquisa.
- Comparação com cópias anteriores: alterações no código das células limitadas aos caminhos
  locais dos notebooks 13, 25, 26, 27 e 28. Nenhuma equação alterada pela organização.
- Acervo: 24.170 arquivos em 135 ZIPs, 2.059.738.272 bytes compactados. Cada conteúdo
  foi relido e comparado com o SHA-256 do arquivo original.
- Restauração: extração, repetição idempotente, verificação sem extração e recusa de
  sobrescrever conteúdo local diferente verificadas em diretório temporário.
- Padrões comuns de credenciais: nenhum encontrado nos novos fontes publicados.

O smoke não substitui a validação científica de todas as campanhas. As ferramentas
históricas de geração de documentos não foram executadas, para preservar manuscritos abertos.

Ambientes antigos, o ZIP antigo do projeto, revisões de renderização e o formulário
administrativo foram movidos para `.local/`, fora do versionamento. A limpeza é reversível;
esses arquivos ainda ocupam espaço no computador. Os resultados brutos também permanecem
locais e estão preservados integralmente no acervo publicado.

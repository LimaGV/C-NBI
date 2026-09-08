# Relatório de verificação — CNBI 1.0.0rc2

Data: 2026-09-08. Este arquivo registra comandos e resultados da candidata; não é um hash de congelamento.

## Verificação corrente da rc2

Em `CNBI_clean_env_rc2`, Python 3.10.11 recebeu somente NumPy 1.26.4, SciPy 1.14.1 e a instalação normal, não editável, da candidata. A importação foi resolvida em `site-packages` e reportou `cnbi.__version__ == "1.0.0rc2"`.

Resultado: **16/16 testes passaram** em 12,7 s; `pip check` não encontrou dependências quebradas. A suíte cobre, além da regressão normativa, os novos limites configuráveis e o pós-processamento opcional.

`python examples/minimal_example.py` passou com 386 candidatos brutos/aceitos e 285 pontos na fronteira RSM estimada após o pós-processamento padrão. O diagnóstico manteve dimensão efetiva 3, 15.817 avaliações RSM e 3.274 avaliações de gradiente.

`pip wheel --no-deps` construiu `cnbi-1.0.0rc2-py3-none-any.whl` fora da candidata. O wheel contém 14 entradas: os nove módulos, metadados e o aviso de licença. Nenhum digest foi adotado como hash de congelamento.

A comparação controlada entre normalização local e global foi executada nas fixtures de 4, 6 e 12 objetivos. Ela mostrou diferenças nas decisões, na cardinalidade das fronteiras e em uma convergência no caso 12D. Os resultados completos estão em `provenance/NORMALIZATION_IMPACT.json`; a normalização local do notebook 03 permanece normativa.

## Escopo

Validação estrutural e numérica contra a fonte selecionada, execução do exemplo, instalação em ambiente limpo e inspeção do pacote. Modo FULL não executado.

## Histórico da rc1 — ambiente original

Python 3.10.11, NumPy 1.26.4 e SciPy 1.14.1, Windows.

Comando: `python -m unittest discover -s tests -v`.

Resultado: **13/13 testes passaram** em 11,3 s. Foram cobertos AST dos corpos extraídos, constantes, malha combinatória, base/jacobiana RSM, payoff, análise paralela/SVD, seleção, NBI, recomposição, aceitação, determinismo, dominância e checkpoint histórico v4.

Comando: `python examples/minimal_example.py`.

Resultado: passou; 386 candidatos brutos/aceitos, 309 linhas não dominadas no RSM, dimensão efetiva 3, 15.817 avaliações RSM e 3.274 avaliações de gradiente no contador do CNBI.

O SciPy emitiu `RuntimeWarning` informando que passos intermediários fora dos bounds foram recortados. A execução terminou normalmente e os resultados coincidiram exatamente com a fonte/checkpoint.

## Histórico da rc1 — primeira tentativa limpa

Em `CNBI_clean_env_rc1`, as dependências de runtime foram instaladas. A instalação editável falhou porque Setuptools 65.5.0 não encontrou `bdist_wheel`; a suíte não pôde importar o pacote. O exemplo executou apenas porque seu script adiciona a raiz local ao caminho. A falha motivou a inclusão de `wheel==0.45.1` no build-system.

## Histórico da rc1 — segunda tentativa limpa

Em `CNBI_clean_env_rc1_second`, Python 3.10.11 criou um ambiente novo. Foram instalados somente NumPy 1.26.4 e SciPy 1.14.1; o build isolado instalou as ferramentas fixadas e instalou `cnbi 1.0.0rc1` em modo editável.

Resultado: instalação passou; **13/13 testes passaram** em 13,4 s; exemplo passou com os mesmos números; import confirmou `cnbi.__version__ == "1.0.0rc1"`; `pip check` informou ausência de dependências quebradas; `compileall` passou.

## Histórico da rc1 — artefato de empacotamento

`pip wheel --no-deps` construiu com sucesso `cnbi-1.0.0rc1-py3-none-any.whl` em uma pasta externa de verificação. O wheel contém somente os nove módulos `cnbi`, metadados e `ORIGINAL_LICENSE.txt`; testes, exemplos, proveniência e documentação permanecem na distribuição-fonte. O digest impresso automaticamente pelo pip é transitório e não constitui hash de congelamento.

O wheel foi instalado no primeiro ambiente limpo, onde `cnbi` não estava presente após a falha editável. A importação veio de `site-packages`, reportou 1.0.0rc1 e **13/13 testes passaram** em 11,8 s.

## SMOKE do repositório experimental original

Comando: `python scripts/run_notebooks.py --mode SMOKE`, usando a `.venv` original.

- passaram: notebooks 01, 03, 02, 04 e 05;
- ignorado como previsto: notebook 08, que requer 90 blocos FULL;
- falhou: notebook 06, célula 4, ao tentar ler `results/synthetic/tables/smoke_method_runs.csv`;
- não alcançados depois da falha: notebook 07 e etapas posteriores da ordem.

Causa: o modo SMOKE define `run_optimizers=false`; o notebook 04 não cria `smoke_method_runs.csv`, mas o executor chama o notebook 06, que exige o arquivo. O núcleo normativo do notebook 03 já havia passado. Nenhuma tolerância, metodologia ou notebook foi alterado para contornar a falha.

## Não verificado

- outras plataformas/BLAS;
- versões diferentes das fixadas;
- equivalência à v0 aplicada;
- alinhamento com a dissertação nas divergências D01–D16;
- campanha FULL e resultados científicos completos;
- titularidade/licença institucional.
- smoke gráfico completo enquanto D16 não for resolvida.

## Histórico da rc1 — higiene da candidata

Diretórios gerados (`build`, `cnbi.egg-info`, caches bytecode e `examples/output`) foram retirados da candidata após a verificação. Para manter a operação recuperável, foram movidos para a área local `CNBI_generated_cleanup_rc1/`, que não integra o repositório. Ambientes limpos e wheel de teste também permanecem fora da candidata. O CSV do exemplo é regenerado pelo comando documentado.

Após a limpeza, a suíte foi executada com `python -B`: **13/13 testes passaram** em 11,7 s sem regenerar bytecode. Onze arquivos Python passaram por parse AST, nove JSONs foram lidos com sucesso e a busca final não encontrou caminhos pessoais no código, exemplo, teste principal ou documentação. A candidata contém 38 arquivos.

## Higiene final da rc2

Diretórios gerados pela rc2 (`build`, `cnbi.egg-info`, cache bytecode e `examples/output`) foram movidos, sem exclusão, para a área local `CNBI_generated_cleanup_rc2/`, que não integra o repositório. A candidata ficou com **39 arquivos** antes da preparação da raiz Git.

Após a limpeza, a fonte foi testada novamente com o Python do ambiente limpo e `python -B`: **16/16 testes passaram** em 11,9 s. Onze arquivos Python passaram por parse AST, dez JSONs foram lidos com sucesso e a busca final, excluindo fixtures/proveniência que registram as fontes auditadas, não encontrou caminhos pessoais. A execução não regenerou bytecode na candidata.

## Preparação da raiz Git

Os arquivos distribuíveis foram promovidos para a raiz `CNBI/`. Ambientes, builds, resultados de verificação, material editorial, ZIP e checkout experimental foram mantidos localmente e excluídos pelo `.gitignore`. Os inventários públicos foram sanitizados para substituir o prefixo do perfil pessoal por `<USER_HOME>`; cópias integrais foram preservadas na área local ignorada. O GitHub Actions foi configurado para repetir instalação, 16 testes e exemplo mínimo com Python 3.10.11.

A primeira execução do workflow em Linux aprovou 15 testes e falhou somente na igualdade binária do checkpoint histórico: diferença absoluta máxima de `2,27652813e-09`, atribuível à plataforma/BLAS. Nenhuma tolerância foi alterada. Como o checkpoint normativo foi produzido e validado em Windows, o workflow passou a usar runner Windows para conservar a comparação bit a bit. A repetição no GitHub Actions aprovou instalação, **16/16 testes** e exemplo mínimo.

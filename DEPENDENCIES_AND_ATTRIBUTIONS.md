# Dependências e atribuições

## Núcleo CNBI

Autoria oficial declarada para a implementação consolidada:

- Gabriel Victor de Lima;
- Mirelli de Castro Cesário;
- Matheus Costa Pereira;
- Anderson Paulo de Paiva.

Esta declaração registra autoria, sem atribuir percentuais de contribuição, titularidade patrimonial ou vínculo institucional específico.

Os arquivos `cnbi/core.py`, `spectral.py`, `combinations.py` e a orquestração em `nbi.py` constituem a implementação computacional selecionada do método CNBI. A afirmação se refere à organização autoral do procedimento; SVD, NBI, SLSQP, RSM, Simplex-Lattice e Pareto são métodos matemáticos preexistentes.

`cnbi/rsm.py`, `payoff.py` e `pareto.py` são componentes científicos auxiliares. Não há código de NSGA-III, MOEA/D ou VRF-NBI na candidata.

## Dependências de execução

| Componente | Versão fixada | Uso | Licença identificada |
|---|---:|---|---|
| Python | 3.10.11 | linguagem/runtime | PSF License |
| NumPy | 1.26.4 | arrays, álgebra linear, RNG, SVD | BSD modificada/BSD-3-Clause; binários podem incluir OpenBLAS e outros componentes |
| SciPy | 1.14.1 | SLSQP e `null_space` | BSD-3-Clause; distribuições binárias podem conter componentes com licenças próprias |

Fontes primárias consultadas: [NumPy informa licença BSD modificada](https://numpy.org/about/) e [SciPy informa licença BSD](https://scipy.org/faq/). Os textos e avisos efetivos da instalação devem ser obtidos nos metadados `*.dist-info/licenses` do ambiente que gerar a distribuição.

## Dependência de construção

O `pyproject.toml` fixa `setuptools==65.5.0`, versão encontrada tanto no ambiente Python 3.10 base quanto na `.venv` original, e `wheel==0.45.1`. Wheel não constava no ambiente original, mas o teste limpo demonstrou que Setuptools 65.5.0 precisa do comando `bdist_wheel`; a versão 0.45.1 requer Python ≥3.8, declara licença MIT e é compatível com Python 3.10 conforme os [metadados oficiais no PyPI](https://pypi.org/project/wheel/0.45.1/). Setuptools declara licença MIT em seu [repositório oficial](https://github.com/pypa/setuptools/blob/main/LICENSE). Essas ferramentas não são importadas pelo CNBI em execução.

## Dependências excluídas

O repositório experimental também usa pandas, matplotlib, seaborn, statsmodels, scikit-learn, factor-analyzer, pymoo, Jupyter/nbclient/nbformat, psutil, pyarrow, openpyxl, tqdm, plotly, deap, pyDOE2 e python-docx/Pillow em artefatos auxiliares. Nenhuma delas é importada pelo pacote `cnbi` ou necessária ao exemplo/testes da candidata.

## Código e métodos externos

- VRF-NBI: Pereira et al. (2025), DOI `10.1016/j.engappai.2025.112510`; excluído da candidata.
- NSGA-III e MOEA/D: implementações `pymoo` usadas somente nos benchmarks; excluídas.
- SLSQP: fornecido por SciPy; a candidata apenas formula objetivo/restrições/jacobianas.
- `numpy.linalg.svd` e `scipy.linalg.null_space`: rotinas de biblioteca, sem incorporação de seu código-fonte.

Não foi encontrado cabeçalho de proveniência indicando que os corpos extraídos do notebook 03 foram copiados de terceiros. `provenance/EXTRACTION.json` registra a origem interna exata de cada função. A autoria oficial desta candidata foi declarada posteriormente pelos responsáveis e está registrada acima e em `CITATION.cff`.

## Licença da candidata

O repositório de origem contém uma licença MIT com aviso `Copyright (c) 2026 LimaGV`, preservada integralmente em `ORIGINAL_LICENSE.txt`. A definição dos três autores não determina automaticamente o titular dos direitos patrimoniais nem confirma se esse aviso deve reger o pacote registrável. Por isso o `pyproject.toml` ainda não declara licença e nenhum novo texto jurídico foi criado.

Decisão humana ainda necessária antes do congelamento: confirmar titular(es), aviso de copyright e licença de distribuição, preservando os avisos das bibliotecas.

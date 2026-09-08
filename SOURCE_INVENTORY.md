# Inventário da candidata CNBI v1.0

## Código-fonte executável do CNBI

- `cnbi/__init__.py`
- `cnbi/config.py`
- `cnbi/rsm.py`
- `cnbi/payoff.py`
- `cnbi/spectral.py`
- `cnbi/combinations.py`
- `cnbi/nbi.py`
- `cnbi/core.py`
- `cnbi/pareto.py` — infraestrutura auxiliar de saída

## Execução, build e validação

- `pyproject.toml`, `requirements.txt`, `MANIFEST.in`, `.gitignore`, `.gitattributes`
- `.github/workflows/tests.yml` — instalação e verificação automática no GitHub
- `examples/minimal_example.py`, `examples/data/rsm_input.json`, `examples/data/README.md`
- `tests/test_preservation.py`
- `tests/fixtures/original_core.py.txt`
- `tests/fixtures/original_nondominated.py.txt`
- `tests/fixtures/m4_low_seed103.json`
- `tests/fixtures/m6_medium_seed101.json`
- `tests/fixtures/m12_high_seed101.json`
- `tests/fixtures/historical_m4_low_seed103.npz`
- `tests/fixtures/historical_m4_low_seed103.metadata.json`
- `tests/fixtures/PROVENANCE.json`

## Documentação e proveniência

- `README.md`, `CHANGELOG.md`, `TRACEABILITY.md`, `PARAMETERS.md`, `VERIFICATION_REPORT.md`
- `DEPENDENCIES_AND_ATTRIBUTIONS.md`, `AUDIT_REPORT.md`, `SUGESTOES_POS_V1.md`
- `SOURCE_INVENTORY.md`, `CITATION.cff`, `ORIGINAL_LICENSE.txt`
- `provenance/EXTRACTION.json`, `PROJECT_INVENTORY.json`, `STATIC_ANALYSIS.json`, `NORMALIZATION_IMPACT.json`

Os inventários públicos substituem apenas o prefixo absoluto do perfil local por `<USER_HOME>`. As cópias integrais anteriores à sanitização permanecem na área ignorada `CNBI_audit/private_provenance/` e não devem ser enviadas ao GitHub.

`examples/output/`, `__pycache__/`, ambientes virtuais, wheels, sdists e logs são gerados e não compõem o código-fonte a congelar. O gerador local em `CNBI_audit/` e o checkout experimental em `CNBI-Synthetic-Benchmarks/` estão excluídos pelo `.gitignore` e não integram a candidata.

O pacote final para protocolo deve ser derivado desta lista somente depois de resolver as decisões humanas registradas. Os notebooks experimentais, resultados completos, figuras, documentos Word/PDF, `tmp/`, métodos externos, diretórios de ambiente/build e ZIPs antigos não integram a candidata.

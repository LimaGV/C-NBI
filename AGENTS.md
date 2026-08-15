# Regras permanentes

- Não alterar equações, critérios, orientação de matrizes ou fluxo da v0 sem aprovação explícita.
- Preservar os deltas adaptativos CNBI da célula 1: `k=2:0.10`, `k=3:0.10`, `k=4:0.20`, `k=5:0.50`.
- Implementar somente a análise paralela legada independente; não criar uma segunda versão.
- Nunca usar as funções verdadeiras durante a otimização final.
- Manter toda metodologia científica em notebooks; scripts servem apenas para validação, sanitização e execução.
- Nunca executar o modo FULL automaticamente.
- Antes de commits: `python scripts/sanitize_notebooks.py` e `python scripts/validate_notebooks.py`.
- Smoke test: `python scripts/run_notebooks.py --mode SMOKE`.
- Máximo de três processos e nenhuma forma de paralelismo aninhado.

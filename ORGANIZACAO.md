# Organização do projeto

- `cnbi/`: pacote científico original, versão 1.0.0rc2.
- `cnbi_experiments/`: extensão, comparadores, campanhas e testes.
- `CNBI-Synthetic-Benchmarks/`: submódulo com notebooks, configurações e scripts; revisão fixada.
- `experimental_results/`: resumo geral e resultados locais restaurados.
- `research_archive/`: resultados, dados de entrada, referências numéricas, planilhas,
  figuras, checkpoints, versões históricas de campanhas e logs, em ZIPs verificados.
- `manuscript/` e `Papper/`: manuscritos, versões de seções e figuras. O nome `Papper`
  foi mantido porque há documentos abertos no Word e ferramentas que usam esse caminho.
- `tools/manuscript/`: ferramentas de montagem dos documentos.
- `tools/audit/` e `docs/history/`: ferramentas e documentos históricos, preservados
  como registro; os scripts de auditoria ainda descrevem a antiga montagem `CNBI_v1.0`.
- `provenance/`, `tests/`, `examples/`: rastreabilidade, regressão e exemplo do núcleo.
- `.local/`: material administrativo privado, ambientes antigos e revisões temporárias;
  não enviado ao GitHub. O ambiente ativo dos notebooks foi mantido em seu caminho original.

## Baixar o projeto completo

```sh
git clone --branch cnbi-v1.0 --recurse-submodules https://github.com/LimaGV/C-NBI.git
cd C-NBI
python tools/research_archive.py restore
```

`restore` verifica SHA-256 e nunca sobrescreve um arquivo local diferente. Os resultados
brutos permanecem disponíveis localmente e nos ZIPs; não é necessário repetir campanhas
para recuperar os dados. Cada ZIP é independente. `manifest.json` associa cada arquivo
original a um ZIP, seu tamanho e seu SHA-256. Use `verify` para verificar sem extrair.

As campanhas finais descritas em `experimental_results/APANHADO_GERAL_DOE_MAF.md` são:
`doe_final_unlimited_calibrated`, `maf_cnbi_unlimited` e `ablation_expanded_9_final`.
Pilotos e revisões anteriores são históricos e não substituem esses resultados.

## Limites da limpeza

A organização não altera as equações do núcleo nem executa campanhas FULL.
Dados privados e credenciais não integram a publicação. Materiais cuja utilidade
histórica é incerta foram preservados localmente, em vez de descartados.

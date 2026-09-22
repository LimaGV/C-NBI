# Extensão DOE, MaF e ablação — diagnóstico prévio

Data: 2026-09-08. Estado: levantamento concluído; implementação e piloto pendentes de decisões metodológicas. Este documento não é um relatório de piloto executado.

Atualização: após a aprovação do usuário, a extensão isolada e o piloto foram implementados. Este levantamento permanece como histórico; o estado atual está em [RELATORIO_TECNICO.md](experimental_results/pilot_verified/RELATORIO_TECNICO.md). A campanha completa permanece bloqueada pelos resultados do piloto, documentados nesse relatório.

## Base de trabalho e preservação

A base encontrada é `C:/Users/gabri/Documents/CNBI`. A pasta de trabalho inicial em `OneDrive/Documentos/CNBI` contém somente `.docx_review_1607`. O núcleo auditado está em `cnbi/`; o acervo científico está em `CNBI-Synthetic-Benchmarks/`. O status Git da base estava limpo antes deste documento. Nenhum algoritmo, resultado, notebook ou configuração foi alterado.

## Reaproveitamento identificado

| Componente | Fonte existente | Uso proposto |
|---|---|---|
| CNBI RSM, payoff, NBI local | `cnbi/core.py`, `payoff.py`, `nbi.py` | Preservar como referência numérica; reutilizar diretamente nos casos compatíveis de três variáveis |
| PA de incerteza e janela SVD | `cnbi/spectral.py` | Manter integralmente no ramo RSM |
| Pesos e ordenação | `cnbi/combinations.py` | Reutilizar; resolver explicitamente ausência de resolução para k=6 |
| Pareto e deduplicação | `cnbi/pareto.py` | Reutilizar pós-processamento com tolerâncias declaradas |
| Gerador, correlação e RSM | notebook `01_geracao_cenarios_sinteticos` | Reutilizar distância quadrática às âncoras, calibração e auditoria de correlação; generalização de dimensão exige trabalho adicional |
| VRF-NBI e checkpoints | notebook `03_pipeline_CNBI_comparacoes` | Extrair/adaptar em extensão rastreável; não executar o notebook inteiro por importação |
| NSGA-III e MOEA/D | notebook `02_calibracao_NSGAIII_MOEAD` | Reutilizar infraestrutura de calibração e orçamento após inspeção detalhada das células |
| Métricas | notebook `04_analise_resultados` | Preservar IGD existente, GD, HV QMC, Spacing e Sparsity; não substituir por IGD+ |
| Cardinalidade | notebook `08_clusterizacao_equalizacao_cardinalidade` | Reutilizar redução por representantes reais e seleção auditável; não presumir um vencedor |
| Gráficos e estatística | notebooks `14`, `17`, `18`, `20`–`24` | Aproveitar estrutura após conferir procedência; auditoria D11 impede tratar números digitados do notebook 19 como evidência |
| Resultados históricos | `results/synthetic`, `results/applied` no acervo | Usar como referência e verificação; não relabelar como novo DOE ou novas replicações |

## Conflitos concretos — parada solicitada no prompt

1. **Dimensão e domínio.** `rsm.z/dz` desempacotam três variáveis. O solver usa `v[:3]`, esfera de raio ALPHA e modelos de dez termos. `core.cnbi` enumera k=2..min(m,4). Não recebe funções arbitrárias ou domínios MaF. DOE com nx=2 ou 5 e MaF não são simples configurações da API atual. Proposta: adaptador experimental de problema com dimensão, avaliação, jacobiana, domínio e restrições explícitos, mantendo o núcleo auditado intacto e verificando equivalência no caso nx=3.

2. **Horn não determina sozinha a janela atual.** A PA existente opera na SVD das diferenças da payoff normalizada e calcula `d=max(1,sum(s>p95))`, `floor=s[d]` (ou zero) e `ceiling=s[0]/s[d-1]`. A PA pedida opera nos autovalores da correlação de uma amostra Pareto, com parada sequencial e possível posto zero. As escalas, matrizes e regras diferem. Não é legítimo inserir autovalores diretamente como piso de valores singulares de sub-CHIMs. Alternativa a avaliar: usar Horn apenas para estimar r e obter piso/teto do espectro da payoff, com regra explícita para r=0 ou r fora do espectro disponível. Isso é uma extensão metodológica proposta, não equivalência demonstrada. Outra alternativa é limitar inicialmente a execução ao ramo RSM e manter o diagnóstico MaF separado.

3. **Ablação all e degenerescência.** Remover o filtro faz chegar ao solver subconjuntos que podem ter CHIM degenerada. `null_space(E).ravel()` pressupõe nulidade unidimensional; admitir dimensionalmente um subconjunto não garante essa propriedade. Proposta: enumerar todos, registrar degenerados como não resolvidos com causa geométrica e não escolher uma normal arbitrária. A convenção deve ser decidida antes de declarar que all executa todos os subconjuntos.

4. **Resolução faltante.** Para nx=5 há subconjuntos admissíveis de tamanho 6. `DELTA_BY_K` termina em 5. É necessário definir a resolução para k=6 ou declarar um estudo restrito que não satisfaz a ablação all completa. Não extrapolar silenciosamente os deltas.

5. **Orçamento.** A auditoria D09 registra que o contador legado não inclui todas as recomposições, payoff final ou gradientes na mesma moeda. Maxiter não é um teto de avaliações. Proposta: preservar contadores históricos e acrescentar contagem experimental de todas as chamadas, por fase, com política explícita de interrupção e tratamento de subproblemas incompletos. Comparações MaF em orçamento estrito não estão demonstradas pela infraestrutura atual.

6. **Dependência controlada.** O gerador atual usa alvos 0,25/0,60/0,85 e tolerância 0,03, com geometria em três dimensões. Não há evidência de atingibilidade desses mesmos alvos em todos os novos pares (nx,m). Primeiro calibrar e auditar; cenários fora da faixa devem falhar explicitamente. Não mudar o nível nominal para acomodar resultados.

O prompt atual autoriza módulos Python, PA por permutação e benchmarks próprios, prevalecendo sobre regras antigas incompatíveis do AGENTS.md do acervo. A interrupção aqui decorre da exigência expressa do próprio prompt de documentar conflitos antes de modificar o método, não de uma exigência genérica de confirmação.

## Desenho proposto após resolução

DOE: nx={2,3,5}, delta={1,3,5}, m=nx+1+delta, dependência={baixa,média,alta}: 27 condições e 10 seeds por condição, total 270 instâncias estruturais/replicações. Separar seed de geometria, observação RSM, otimizador e diagnóstico; preservar pareamento entre métodos. A escolha entre geometria fixa por condição e recalibrada por réplica precisa ser registrada porque muda a interpretação estatística. Transição proposta: nx=3, m={3,4,5}, correspondendo a delta={-1,0,1}, dependência média. NBI clássico somente com delta<=0.

MaF: configurações solicitadas M={4,6,8,10,15} para MaF8/9 e {8,10,15} para MaF13, sujeitas à validação normativa. Não se consultou nem implementou ainda a formulação MaF; dimensionalidade, domínio, restrições, PS/PF e convenção MaF13 continuam pendentes. Consultar Cheng et al., DOI 10.1007/s40747-017-0039-7, e fontes oficiais BIMK/PlatEMO com revisão fixada antes de codificar; guardar valores independentes de validação, não testes que reproduzem a mesma implementação.

PA proposta: permutações independentes por coluna, B=1000, quantil 0,95, retenção sequencial estrita, seed explícita; guardar todos os autovalores e limiares. Amostras Pareto normativas N={250,500,1000,5000}. Não reutilizar amostras dominadas como substituto.

Ablação mínima: all versus spectral com mesmo problema e seeds; PA_unc no RSM e PA_perm no MaF após resolver a ponte espectral. Nenhuma terceira variante ou limiar arbitrário proposto.

## Piloto, validação e custo

Nenhum piloto ou teste numérico novo executado. Nenhuma equivalência MaF/PlatEMO, estabilidade PA, igualdade de orçamento/cardinalidade ou ausência de NaN/Inf foi demonstrada. Não há métricas experimentais novas a reportar.

Após as decisões: validar benchmarks antes dos otimizadores; piloto com um caso de cada MaF, três condições DOE e ambas as ablações. Guardar dados por seed, diagnósticos, tempos por fase e orçamento observado. Só depois estimar custo e produzir análises de efeitos/interações com intervalos de confiança que preservem a replicação.

O custo de campanha não pode ser estimado confiavelmente em horas sem esse piloto. A enumeração all cresce como soma de C(m,k), k=2..min(m,nx+1), multiplicada pela quantidade de pesos por k, starts, resgates e seeds. A resolução ainda indefinida de k=6 impede até fixar todos os subproblemas potenciais. A campanha completa permanece não executada.

## Arquivos criados/modificados

Criado somente `EXTENSAO_EXPERIMENTAL_DIAGNOSTICO.md`. Próximo passo recomendado: aprovar o protocolo de generalização e a ponte Horn–janela SVD; então implementar em extensão isolada com testes de preservação do núcleo.

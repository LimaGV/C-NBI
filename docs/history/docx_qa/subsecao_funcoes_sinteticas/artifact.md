# Contrato de estilo — subseção sobre funções sintéticas

## Referência

- Arquivo preservado: `C:\Users\gabri\Documents\Dissertação\01_TEXTOS\capitulos\dissertação CNBI_16.07.docx`
- SHA-256: `52a1b7c0985a61939f4be31b44cf8b10ac0d3ace4c497b16c680d5201727b172`
- Tamanho: 4.028.714 bytes
- Extensão visual: 72 páginas; 2 seções.
- Evidência estrutural: `template-style-evidence.json` e saída do `section_audit.py`.
- Evidência visual: PDF e PNGs em `reference_render`; páginas 52–54 inspecionadas em resolução original por conterem o padrão metodológico relevante.

## Sistema de página

- Formato A4, orientação retrato.
- Padrão principal da dissertação: margens superior e esquerda de 3 cm; inferior e direita de 2 cm.
- Cabeçalho vazio no padrão principal; numeração de página à direita no rodapé, em Times New Roman 10 pt.
- O novo arquivo será uma peça autônoma de inserção: uma seção A4 com a geometria principal e numeração reiniciada em 1 apenas para facilitar revisão. A dissertação de referência não será modificada.

## Tipografia e ritmo

- Texto: estilo semântico `Corpo do texto Dissertação`, Times New Roman 12 pt, preto, justificado, recuo da primeira linha de 1 cm, entrelinha 1,5, sem espaço adicional antes ou depois.
- Título da subseção: Times New Roman 12 pt, negrito, justificado, entrelinha 1,5 e 6 pt depois. O título fica sem número no arquivo autônomo para não conflitar com a numeração da dissertação; ao inserir, deve receber o nível hierárquico correto no documento principal.
- Termos estrangeiros: itálico apenas quando a prática acadêmica do texto exigir.
- Não usar cores, caixas, tabelas decorativas ou outra linguagem visual ausente no trecho metodológico de referência.

## Conteúdo e fluxo

- Um único título de subseção.
- Prosa científica contínua, didática e predominantemente narrativa.
- Sequência conceitual: finalidade do benchmark; espaço de decisão; construção das respostas por âncoras; calibração da dependência; cenários; simulação dos dados e ajuste RSM; referência verdadeira; validações.
- Evitar equações e símbolos dispensáveis. Manter apenas números, nomes de métodos e conceitos necessários à reprodutibilidade.

## Mapa de slots

- `word/document.xml/body/p[1]`: título da subseção; reescrito.
- Demais parágrafos do corpo: conteúdo metodológico novo; reescritos.
- Propriedades de seção: reproduzir a geometria principal da referência.
- Cabeçalho e rodapé: recriados de forma mínima, sem transportar conteúdo ou metadados da dissertação.
- Estilos: recriar somente os papéis necessários a partir das medidas observadas; não transportar texto, imagens, tabelas, comentários ou relacionamentos da referência.

## Preservação e desvios autorizados

- O arquivo de referência permanece byte a byte inalterado.
- Por privacidade e leveza, o novo DOCX não copiará partes opacas, imagens ou metadados da dissertação; somente a aparência observável e os estilos necessários serão reproduzidos.
- O texto novo deverá ser conferido contra o notebook 01, `configs/full.json`, `README.md` e `docs/metodologia.md` do repositório científico.

## Portões de fidelidade

- Confirmar A4 e margens 3/2 cm.
- Confirmar Times New Roman 12 pt, entrelinha 1,5, justificação e recuo de 1 cm em todos os parágrafos de corpo.
- Confirmar título em 12 pt negrito, sem numeração fixa.
- Confirmar ausência de equações, placeholders, instruções internas, comentários e alterações controladas.
- Renderizar todas as páginas do novo DOCX e inspecioná-las em resolução original.
- Verificar que o SHA-256 da referência continua idêntico ao registrado acima.

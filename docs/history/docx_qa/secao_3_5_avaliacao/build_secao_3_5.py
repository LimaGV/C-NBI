from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


HELPER_DIR = Path(r"C:\Users\gabri\Documents\CNBI\docx_qa\subsecao_funcoes_sinteticas")
sys.path.insert(0, str(HELPER_DIR))
import build_subsecao as base  # noqa: E402
import build_subsecao_equacoes as style  # noqa: E402


OUTPUT = Path(
    r"C:\Users\gabri\Documents\Dissertação\01_TEXTOS\capitulos\secao_3_5_estrategia_comparacao_avaliacao.docx"
)


EQUATIONS = {
    "normalization": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <msub><mi>z</mi><mi>j</mi></msub><mfenced><mi mathvariant="bold">f</mi></mfenced><mo>=</mo>
    <mfrac>
      <mrow><msub><mi>f</mi><mi>j</mi></msub><mo>−</mo><msubsup><mi>z</mi><mi>j</mi><mtext>ideal</mtext></msubsup></mrow>
      <mrow><msubsup><mi>z</mi><mi>j</mi><mtext>nadir</mtext></msubsup><mo>−</mo><msubsup><mi>z</mi><mi>j</mi><mtext>ideal</mtext></msubsup></mrow>
    </mfrac>
  </mrow>
</math>
""",
    "budget": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <msub><mi>B</mi><mrow><mi>p</mi><mo>,</mo><mi>s</mi></mrow></msub><mo>=</mo>
    <msubsup><mi>N</mi><mrow><mi>p</mi><mo>,</mo><mi>s</mi></mrow><mtext>payoff</mtext></msubsup>
    <mo>+</mo>
    <msubsup><mi>N</mi><mrow><mi>p</mi><mo>,</mo><mi>s</mi></mrow><mtext>CNBI</mtext></msubsup>
    <mo>,</mo><mspace width="1.5em"/>
    <msubsup><mi>N</mi><mrow><mi>p</mi><mo>,</mo><mi>s</mi></mrow><mtext>EA</mtext></msubsup>
    <mo>≤</mo><msub><mi>B</mi><mrow><mi>p</mi><mo>,</mo><mi>s</mi></mrow></msub>
  </mrow>
</math>
""",
    "cardinality": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <msubsup><mi>n</mi><mrow><mi>p</mi><mo>,</mo><mi>s</mi></mrow><mo>*</mo></msubsup><mo>=</mo>
    <munder><mi>min</mi><mrow><mi>h</mi><mo>∈</mo><mi mathvariant="script">H</mi></mrow></munder>
    <mfenced open="|" close="|"><msub><mi mathvariant="script">A</mi><mrow><mi>h</mi><mo>,</mo><mi>p</mi><mo>,</mo><mi>s</mi></mrow></msub></mfenced>
  </mrow>
</math>
""",
    "gd": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <mi>GD</mi><mfenced><mrow><mi mathvariant="script">A</mi><mo>,</mo><mi mathvariant="script">R</mi></mrow></mfenced><mo>=</mo>
    <mfrac><mn>1</mn><mfenced open="|" close="|"><mi mathvariant="script">A</mi></mfenced></mfrac>
    <munder><mo>∑</mo><mrow><mi mathvariant="bold">a</mi><mo>∈</mo><mi mathvariant="script">A</mi></mrow></munder>
    <munder><mi>min</mi><mrow><mi mathvariant="bold">r</mi><mo>∈</mo><mi mathvariant="script">R</mi></mrow></munder>
    <msub><mfenced open="‖" close="‖"><mrow><mi mathvariant="bold">a</mi><mo>−</mo><mi mathvariant="bold">r</mi></mrow></mfenced><mn>2</mn></msub>
  </mrow>
</math>
""",
    "igd": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <mi>IGD</mi><mfenced><mrow><mi mathvariant="script">A</mi><mo>,</mo><mi mathvariant="script">R</mi></mrow></mfenced><mo>=</mo>
    <mfrac><mn>1</mn><mfenced open="|" close="|"><mi mathvariant="script">R</mi></mfenced></mfrac>
    <munder><mo>∑</mo><mrow><mi mathvariant="bold">r</mi><mo>∈</mo><mi mathvariant="script">R</mi></mrow></munder>
    <munder><mi>min</mi><mrow><mi mathvariant="bold">a</mi><mo>∈</mo><mi mathvariant="script">A</mi></mrow></munder>
    <msub><mfenced open="‖" close="‖"><mrow><mi mathvariant="bold">r</mi><mo>−</mo><mi mathvariant="bold">a</mi></mrow></mfenced><mn>2</mn></msub>
  </mrow>
</math>
""",
    "hypervolume": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <mi>HV</mi><mfenced><mi mathvariant="script">A</mi></mfenced><mo>=</mo>
    <mi>λ</mi>
    <mfenced>
      <mrow>
        <munder><mo>⋃</mo><mrow><mi mathvariant="bold">a</mi><mo>∈</mo><mi mathvariant="script">A</mi></mrow></munder>
        <mfenced open="[" close="]"><mrow><mi mathvariant="bold">a</mi><mo>,</mo><msup><mi mathvariant="bold">r</mi><mtext>ref</mtext></msup></mrow></mfenced>
      </mrow>
    </mfenced>
  </mrow>
</math>
""",
    "spacing": """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <mi>S</mi><mfenced><mi mathvariant="script">A</mi></mfenced><mo>=</mo>
    <msup>
      <mfenced>
        <mrow><mfrac><mn>1</mn><mi>n</mi></mfrac><munderover><mo>∑</mo><mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow><mi>n</mi></munderover>
        <msup><mfenced><mrow><msub><mi>d</mi><mi>i</mi></msub><mo>−</mo><mover><mi>d</mi><mo>¯</mo></mover></mrow></mfenced><mn>2</mn></msup></mrow>
      </mfenced>
      <mfrac><mn>1</mn><mn>2</mn></mfrac>
    </msup>
    <mo>,</mo><mspace width="1em"/>
    <mi>Sp</mi><mfenced><mi mathvariant="script">A</mi></mfenced><mo>=</mo><mover><mi>d</mi><mo>¯</mo></mover>
    <mo>,</mo><mspace width="1em"/>
    <msub><mi>d</mi><mi>i</mi></msub><mo>=</mo>
    <munder><mi>min</mi><mrow><mi>k</mi><mo>≠</mo><mi>i</mi></mrow></munder>
    <msub><mfenced open="‖" close="‖"><mrow><msub><mi mathvariant="bold">a</mi><mi>i</mi></msub><mo>−</mo><msub><mi mathvariant="bold">a</mi><mi>k</mi></msub></mrow></mfenced><mn>2</mn></msub>
  </mrow>
</math>
""",
}


METHOD_ROWS = [
    (
        "VRF-NBI",
        "Redução das respostas por componentes principais e fatores rotacionados antes da aplicação do NBI.",
        "Compara o C-NBI com uma estratégia que reduz explicitamente a dimensão dos objetivos.",
    ),
    (
        "NSGA-III",
        "Seleção populacional por dominância, direções de referência e nichamento.",
        "Representa uma abordagem evolutiva desenvolvida para problemas com muitos objetivos.",
    ),
    (
        "MOEA/D",
        "Decomposição do problema em subproblemas escalares associados a direções e vizinhanças.",
        "Representa uma abordagem evolutiva baseada em decomposição e cooperação local.",
    ),
]


PARAMETER_ROWS = [
    ("NSGA-III", "4", "4", "0,90", "20", "30", "—"),
    ("MOEA/D", "4", "4", "0,90", "30", "20", "0,10 / 1,00"),
    ("NSGA-III", "6", "4", "0,90", "30", "20", "—"),
    ("MOEA/D", "6", "3", "0,90", "20", "30", "0,20 / 0,90"),
    ("NSGA-III", "12", "4", "0,90", "20", "30", "—"),
    ("MOEA/D", "12", "4", "0,90", "20", "30", "0,10 / 1,00"),
]


METRIC_ROWS = [
    ("GD", "Distância média da aproximação à referência.", "Menor", "Proximidade dos pontos retornados."),
    ("IGD", "Distância média da referência à aproximação.", "Menor", "Cobertura de toda a extensão da referência."),
    ("HV", "Volume dominado até o ponto de referência.", "Maior", "Convergência e cobertura em uma medida conjunta."),
    ("Spacing", "Dispersão das distâncias ao vizinho mais próximo.", "Menor", "Regularidade da distribuição dos pontos."),
    ("Sparsity", "Média das distâncias ao vizinho mais próximo.", "Menor¹", "Densidade local; deve ser lida com IGD e HV."),
    ("Factibilidade", "Proporção de soluções dentro do domínio.", "Maior", "Respeito às restrições."),
    ("Convergência", "Proporção de execuções internas declaradas convergentes.", "Maior", "Estabilidade numérica do método."),
    ("Custo", "Avaliações do RSM e tempos de parede e CPU.", "Menor²", "Esforço computacional sob qualidade comparável."),
]


def set_keep_with_next(paragraph) -> None:
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.keep_together = True


def add_heading(document: Document, text: str, level: int) -> None:
    paragraph = document.add_paragraph(style=f"Heading {level}")
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.left_indent = Cm(0)
    set_keep_with_next(paragraph)
    base.set_font(paragraph.add_run(text), bold=True)


def add_body(document: Document, text: str) -> None:
    style.add_body(document, text)


def add_caption(document: Document, text: str) -> None:
    style.add_small_paragraph(
        document,
        text,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        keep_next=True,
    )


def set_cell_text(cell, text: str, *, bold=False, size=9, align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run(text)
    base.set_font(run, bold=bold, size=size)


def add_academic_table(
    document: Document,
    caption: str,
    headers: list[str],
    rows: list[tuple[str, ...]],
    widths: list[int],
    *,
    aligns: list,
    font_size: int = 9,
    source: str,
    note: str | None = None,
) -> None:
    add_caption(document, caption)
    table = document.add_table(rows=1, cols=len(headers))
    style.set_table_geometry(table, widths)
    style.set_repeat_table_header(table.rows[0])
    for index, (cell, header) in enumerate(zip(table.rows[0].cells, headers)):
        set_cell_text(cell, header, bold=True, size=font_size, align=aligns[index])
        style.set_cell_borders(cell, top={"sz": 10}, bottom={"sz": 8})
    for values in rows:
        row = table.add_row()
        for index, (cell, value) in enumerate(zip(row.cells, values)):
            set_cell_text(cell, value, size=font_size, align=aligns[index])
    style.set_table_geometry(table, widths)
    for cell in table.rows[-1].cells:
        style.set_cell_borders(cell, bottom={"sz": 10})
    style.add_small_paragraph(document, source, align=WD_ALIGN_PARAGRAPH.CENTER)
    if note:
        style.add_small_paragraph(document, note, align=WD_ALIGN_PARAGRAPH.LEFT)


def configure_heading_styles(document: Document) -> None:
    heading3 = document.styles["Heading 3"]
    heading3.base_style = document.styles["Normal"]
    heading3.font.name = "Times New Roman"
    heading3.font.size = Pt(12)
    heading3.font.bold = True
    heading3.font.color.rgb = RGBColor(0, 0, 0)
    heading3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    heading3.paragraph_format.first_line_indent = Cm(0)
    heading3.paragraph_format.left_indent = Cm(0)
    heading3.paragraph_format.line_spacing = 1.5
    heading3.paragraph_format.space_before = Pt(6)
    heading3.paragraph_format.space_after = Pt(0)
    heading3.paragraph_format.keep_with_next = True
    heading3.paragraph_format.keep_together = True
    base.set_outline_level(heading3, 2)


def build() -> None:
    document = Document()
    style.configure_document(document)
    configure_heading_styles(document)

    add_heading(document, "3.5. Estratégia de comparação e avaliação", 2)
    add_body(
        document,
        "A comparação foi organizada para separar o efeito do método de otimização de três fontes de vantagem indevida: o modelo disponível, o número de avaliações e a quantidade de soluções retornadas. Em cada combinação entre problema e semente, todos os métodos receberam o mesmo conjunto de superfícies de resposta ajustadas. As funções verdadeiras permaneceram indisponíveis durante a busca e foram consultadas somente depois do término de cada execução, para avaliar as soluções em relação a uma referência externa comum.",
    )
    add_body(
        document,
        "O C-NBI foi tratado como método de interesse. A avaliação empregou três referências com princípios distintos: uma redução multivariada seguida de NBI, um algoritmo evolutivo guiado por direções de referência e um algoritmo evolutivo baseado em decomposição. Essa escolha evita que a conclusão dependa de um único paradigma computacional. Para cada método foram preservados os resultados completos e uma segunda versão com cardinalidade igualada, permitindo distinguir qualidade geométrica de simples vantagem decorrente de uma frente mais numerosa.",
    )

    add_heading(document, "3.5.1. Métodos de referência", 3)
    add_body(
        document,
        "O VRF-NBI segue a estratégia de redução por fatores proposta por Pereira et al. (2025). As respostas preditas pelos modelos são inicialmente padronizadas. Em seguida, aplica-se análise de componentes principais, retendo-se o menor número de componentes capaz de explicar pelo menos 90% da variância. Sobre esse subespaço é realizada análise fatorial pelo método principal, seguida de rotação Varimax. O sinal de cada fator é orientado de modo determinístico, tornando positiva sua carga de maior módulo e eliminando ambiguidades de sinal que poderiam alterar a execução sem modificar o modelo estatístico.",
    )
    add_body(
        document,
        "O NBI é então aplicado no espaço fatorial reduzido, com incremento igual a 0,10. As soluções são obtidas no espaço original de decisão e, ao final, avaliadas em todas as respostas originais. Dessa forma, a redução atua apenas como representação interna para a otimização; nenhuma resposta é descartada na comparação final. O VRF-NBI permite verificar se os ganhos do C-NBI decorrem apenas da redução da dimensão ou também da forma como as combinações de objetivos são construídas.",
    )
    add_body(
        document,
        "O NSGA-III, de Deb e Jain (2014), mantém uma população de soluções e utiliza ordenação por não dominância. Quando uma frente não cabe integralmente na geração seguinte, direções de referência e um mecanismo de nichamento favorecem regiões menos ocupadas. O método foi incluído por ser uma referência consolidada para problemas com muitos objetivos e por produzir uma aproximação populacional sem empregar a geometria NBI.",
    )
    add_body(
        document,
        "O MOEA/D, de Zhang e Li (2007), decompõe o problema multiobjetivo em vários subproblemas escalares associados a vetores de peso. Cada subproblema compartilha informação principalmente com seus vizinhos, definidos pela proximidade entre os vetores de peso. Essa estrutura oferece um contraponto relevante ao NSGA-III: ambos são evolucionários, mas o primeiro organiza a seleção por dominância e nichamento, enquanto o segundo explora uma coleção cooperativa de decomposições escalares.",
    )
    add_academic_table(
        document,
        "Quadro 1 - Síntese dos métodos empregados como referência.",
        ["Método", "Mecanismo central", "Papel na comparação"],
        METHOD_ROWS,
        [1350, 3350, 4100],
        aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=9,
        source="Fonte: Elaborado pelo autor (2026).",
    )
    add_body(
        document,
        "Os algoritmos evolucionários foram calibrados separadamente para 4, 6 e 12 objetivos. A calibração utilizou somente o problema de correlação intermediária e as sementes 1, 2 e 3, mantendo as sementes finais 101 a 110 fora desse processo. Entre os três finalistas de cada método e dimensão, a escolha foi lexicográfica: menor mediana do IGD, maior mediana do hipervolume, menor inviabilidade mediana, menor amplitude interquartil do IGD e menor tempo mediano. A configuração vencedora foi congelada antes das execuções finais.",
    )
    add_academic_table(
        document,
        "Tabela 1 - Parâmetros dos algoritmos evolucionários congelados para a campanha FULL.",
        ["Método", "m", "Divisões", "p-SBX", "η-SBX", "η-PM", "Vizinhança / acasalamento"],
        PARAMETER_ROWS,
        [1450, 550, 900, 800, 800, 800, 3500],
        aligns=[
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.CENTER,
        ],
        font_size=9,
        source="Fonte: Elaborado pelo autor a partir de results/tuning/chosen_parameters.json (2026).",
        note="Nota: p-SBX é a probabilidade de cruzamento; η-SBX e η-PM são os índices de distribuição do cruzamento SBX e da mutação polinomial. Para o MOEA/D, a última coluna apresenta, respectivamente, a fração de vizinhos e a probabilidade de acasalamento na vizinhança.",
    )

    add_heading(document, "3.5.2. Construção do conjunto de referência", 3)
    add_body(
        document,
        "A geração geométrica da região eficiente foi apresentada na seção anterior. Para a comparação, importa distinguir essa referência das aproximações produzidas pelos métodos. O conjunto de referência contém 100.000 pontos e é construído diretamente a partir da estrutura conhecida do problema, sem participação de qualquer algoritmo avaliado. Ele é representado por R, enquanto A designa a aproximação retornada por um método após a remoção de soluções inválidas e dominadas.",
    )
    add_body(
        document,
        "Antes do cálculo das métricas, os valores dos objetivos foram colocados em uma escala comum. O ideal verdadeiro é zero em cada objetivo, pois cada função atinge valor nulo em sua própria âncora. O nadir externo também é obtido analiticamente pela maior distância quadrática entre a âncora de cada objetivo e as demais âncoras. Essa normalização externa é usada somente na avaliação; a normalização interna dos métodos NBI continua baseada em sua matriz payoff.",
    )
    style.add_equation(document, EQUATIONS["normalization"])
    add_body(
        document,
        "Na expressão, o numerador desloca o valor do j-ésimo objetivo pelo ideal verdadeiro e o denominador o divide pela amplitude entre ideal e nadir. O resultado é o valor normalizado. Como todos os métodos são transformados pelos mesmos extremos, as distâncias entre pontos e o hipervolume tornam-se comparáveis entre objetivos com amplitudes diferentes e não dependem da densidade finita da amostra de referência.",
    )
    add_body(
        document,
        "Ao término de cada execução, as decisões retornadas foram avaliadas nas funções verdadeiras. Foram mantidas somente as soluções declaradas convergentes, situadas no domínio admissível e não dominadas no espaço original dos objetivos. A fronteira resultante foi então normalizada e comparada com R. Esse uso posterior das funções verdadeiras não produz vazamento de informação, porque ocorre depois que a busca foi encerrada.",
    )

    add_heading(document, "3.5.3. Controle do orçamento computacional e da cardinalidade", 3)
    add_body(
        document,
        "A unidade de custo foi uma chamada ao vetor completo de respostas preditas pelo RSM. Assim, calcular simultaneamente quatro, seis ou doze respostas contou como uma única avaliação, evitando penalizar artificialmente problemas com mais objetivos. Um contador central registrou separadamente as avaliações da construção da payoff e da busca C-NBI. A soma dessas parcelas definiu, para cada problema p e semente s, o teto aplicado aos algoritmos evolucionários.",
    )
    style.add_equation(document, EQUATIONS["budget"])
    add_body(
        document,
        "Na expressão, B representa o orçamento completo observado para o C-NBI na combinação definida pelos índices p e s. As duas parcelas correspondem às avaliações da payoff e da busca; o termo identificado por EA é o total consumido pelo NSGA-III ou pelo MOEA/D. O pareamento foi feito para o mesmo problema e a mesma semente, em vez de usar uma média global. Isso preserva variações reais de custo causadas pela dimensão reduzida e pelo número de subproblemas aceitos. Como os algoritmos evolucionários avançam por gerações, a última geração foi executada apenas quando não ultrapassava o teto.",
    )
    add_body(
        document,
        "O orçamento igual, entretanto, não garante cardinalidade igual. Uma frente com mais pontos tende a obter melhor cobertura e pode aumentar o hipervolume apenas por ser mais densa. Por essa razão, cada bloco problema-semente foi analisado em duas versões. A primeira conservou todas as soluções válidas e não dominadas. Na segunda, todos os métodos foram reduzidos à menor cardinalidade observada naquele mesmo bloco.",
    )
    style.add_equation(document, EQUATIONS["cardinality"])
    add_body(
        document,
        "Na expressão, H é o conjunto de métodos comparados e A representa a aproximação completa identificada pelo método, pelo problema e pela semente indicados nos subscritos. O alvo de cardinalidade pode mudar entre blocos, mas é comum a todos os métodos dentro de cada comparação pareada.",
    )
    add_body(
        document,
        "A redução foi realizada no espaço normalizado dos objetivos por K-Means. Cada centroide foi substituído pela solução real mais próxima pertencente ao respectivo agrupamento; portanto, nenhum ponto artificial foi introduzido. A seleção usa semente fixa 42. Esse procedimento foi escolhido após um estudo com as 90 frentes completas do C-NBI, no qual foi comparado com Farthest-Point Sampling, MiniBatch K-Means, mistura gaussiana e agrupamento hierárquico de Ward. Todos os candidatos precisavam produzir a cardinalidade exata; entre os elegíveis, priorizou-se o menor posto mediano de IGD verdadeiro por bloco, com desempate pelo IGD verdadeiro mediano, pela perda de retenção e pelo tempo. O K-Means com representante real apresentou o melhor resultado segundo essa regra.",
    )
    add_heading(document, "3.5.4. Métricas de desempenho", 3)
    add_body(
        document,
        "A qualidade das aproximações foi examinada por métricas complementares. Nenhuma delas, isoladamente, descreve simultaneamente proximidade, cobertura, uniformidade e custo. As distâncias foram calculadas no espaço normalizado com norma euclidiana.",
    )
    style.add_equation(document, EQUATIONS["gd"])
    style.add_equation(document, EQUATIONS["igd"])
    add_body(
        document,
        "A GD parte de cada ponto produzido pelo método e procura seu vizinho mais próximo na referência, enfatizando a proximidade da aproximação. O IGD inverte a consulta: parte da referência e procura a aproximação, tornando-se mais sensível a lacunas e à cobertura da região eficiente. Em ambas, valores menores indicam melhor desempenho.",
    )
    add_body(
        document,
        "O hipervolume mede a porção do espaço de objetivos que é simultaneamente dominada pela aproximação e limitada por um ponto de referência. Na escala normalizada, esse ponto foi fixado em 1,1 para todas as coordenadas.",
    )
    style.add_equation(document, EQUATIONS["hypervolume"])
    add_body(
        document,
        "O símbolo λ representa o volume e o vetor sobrescrito por “ref” é o ponto de referência. O hipervolume foi estimado por quase Monte Carlo com 1.000.000 de pontos de Sobol, usando a mesma amostra para todos os métodos de cada bloco e registrando o erro-padrão. Valores maiores indicam combinação mais favorável de convergência e cobertura.",
    )
    add_body(
        document,
        "A regularidade e a densidade local foram avaliadas pelas distâncias ao vizinho mais próximo. Na expressão seguinte, cada distância indexada liga um ponto ao vizinho mais próximo; o Spacing mede a dispersão dessas distâncias e a Sparsity, sua média.",
    )
    style.add_equation(document, EQUATIONS["spacing"])
    add_body(
        document,
        "Spacing menor indica distribuição local mais uniforme. Sparsity menor indica maior densidade, mas não garante cobertura, pois pontos concentrados também podem estar próximos. Por isso, ela foi interpretada com IGD e hipervolume, sobretudo após a equalização.",
    )
    add_academic_table(
        document,
        "Quadro 2 - Métricas utilizadas e orientação de interpretação.",
        ["Medida", "Definição operacional", "Direção", "Aspecto principal"],
        METRIC_ROWS,
        [1500, 2800, 900, 3600],
        aligns=[
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.LEFT,
        ],
        font_size=9,
        source="Fonte: Elaborado pelo autor (2026).",
        note="Notas: ¹ menor significa maior densidade local, não superioridade isolada; ² a direção de custo só é interpretada entre soluções de qualidade comparável.",
    )
    add_body(
        document,
        "Também foram registrados a fração de soluções factíveis, a fração com indicação de convergência, o número de avaliações do RSM e os tempos de parede e de CPU. Esses indicadores ajudam a distinguir perda de qualidade por limitação de orçamento, falha numérica ou dificuldade em respeitar o domínio.",
    )
    add_body(
        document,
        "Para cada problema, método e tipo de comparação, os resultados das dez sementes finais foram resumidos pela mediana e pela amplitude interquartil. A comparação inferencial preservou o pareamento das sementes. Aplicou-se inicialmente o teste de Friedman entre os métodos; as comparações do C-NBI com cada referência foram realizadas pelo teste de postos sinalizados de Wilcoxon, com correção de Holm para multiplicidade. O tamanho de efeito foi expresso pela correlação bisserial de postos, orientada de modo que valores positivos favoreçam o C-NBI.",
    )
    add_body(
        document,
        "A interpretação final considera conjuntamente as versões completa e equalizada. Uma vantagem que desaparece após a redução é atribuída principalmente à densidade da frente. Sua permanência em IGD e hipervolume após a equalização constitui evidência mais forte de melhor cobertura sob orçamento e cardinalidade comparáveis. GD, Spacing e Sparsity permanecem como diagnósticos complementares.",
    )

    section = document.sections[0]
    section.header.paragraphs[0].text = ""
    section.footer.paragraphs[0].clear()
    base.add_page_number(section.footer.paragraphs[0])

    core = document.core_properties
    core.title = "3.5. Estratégia de comparação e avaliação"
    core.subject = "Métodos de referência, conjunto de referência, orçamento, cardinalidade e métricas"
    core.author = ""
    core.last_modified_by = ""
    core.keywords = "C-NBI; VRF-NBI; NSGA-III; MOEA/D; IGD; hipervolume; cardinalidade"
    core.comments = "Peça autônoma preparada para inserção na dissertação."

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()

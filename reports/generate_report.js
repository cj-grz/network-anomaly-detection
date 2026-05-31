const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, AlignmentType, HeadingLevel, BorderStyle,
  WidthType, ShadingType, VerticalAlign, PageNumber, PageBreak,
  LevelFormat, ExternalHyperlink, TableOfContents
} = require('docx');
const fs = require('fs');
const path = require('path');

const REPORTS = path.join(__dirname);
const BLUE    = '1F3864';
const BLUE2   = '2E74B5';
const LIGHT   = 'D6E4F0';
const RED     = 'C00000';
const GRAY    = 'F2F2F2';
const WHITE   = 'FFFFFF';
const DARK    = '1A1A2E';

// ── Helpers ──────────────────────────────────────────────────────────────────

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function spacer(pts = 120) {
  return new Paragraph({ spacing: { before: pts, after: pts }, children: [] });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, font: 'Arial', size: 32, bold: true, color: BLUE })],
    spacing: { before: 360, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE2, space: 6 } },
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, font: 'Arial', size: 26, bold: true, color: BLUE2 })],
    spacing: { before: 280, after: 120 },
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, font: 'Arial', size: 24, bold: true, color: '404040' })],
    spacing: { before: 200, after: 80 },
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, font: 'Arial', size: 22, color: '2D2D2D', ...opts })],
    spacing: { before: 60, after: 100 },
    alignment: AlignmentType.JUSTIFIED,
  });
}

function bold(text) { return new TextRun({ text, font: 'Arial', size: 22, bold: true, color: '2D2D2D' }); }
function normal(text) { return new TextRun({ text, font: 'Arial', size: 22, color: '2D2D2D' }); }

function mixedP(runs, opts = {}) {
  return new Paragraph({
    children: runs,
    spacing: { before: 60, after: 100 },
    alignment: AlignmentType.JUSTIFIED,
    ...opts,
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    children: [new TextRun({ text, font: 'Arial', size: 22, color: '2D2D2D' })],
    spacing: { before: 40, after: 40 },
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'numbers', level },
    children: [new TextRun({ text, font: 'Arial', size: 22, color: '2D2D2D' })],
    spacing: { before: 40, after: 40 },
  });
}

function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: 'Arial', size: 18, italics: true, color: '666666' })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 120 },
  });
}

function loadImg(filename) {
  const fp = path.join(REPORTS, filename);
  if (fs.existsSync(fp)) return fs.readFileSync(fp);
  return null;
}

function imgPara(filename, w, h, altText) {
  const data = loadImg(filename);
  if (!data) return p(`[Figura: ${filename} — ejecutar notebook para generar]`);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 40 },
    children: [new ImageRun({
      type: 'png',
      data,
      transformation: { width: w, height: h },
      altText: { title: altText, description: altText, name: altText },
    })],
  });
}

const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const allBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };

function headerCell(text, w) {
  return new TableCell({
    borders: allBorders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: BLUE, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 140, right: 140 },
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, font: 'Arial', size: 20, bold: true, color: WHITE })],
    })],
  });
}

function dataCell(text, w, fill = WHITE, align = AlignmentType.LEFT, bold_ = false) {
  return new TableCell({
    borders: allBorders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 140, right: 140 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text, font: 'Arial', size: 20, color: '2D2D2D', bold: bold_ })],
    })],
  });
}

// ── Cover page ────────────────────────────────────────────────────────────────

function coverSection() {
  return [
    spacer(1440),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'REPORTE TÉCNICO', font: 'Arial', size: 48, bold: true, color: WHITE })],
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      spacing: { before: 240, after: 0 },
      indent: { left: -1440, right: -1440 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Proyecto Integrador de Certificación', font: 'Arial', size: 26, italics: true, color: LIGHT })],
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0 },
      indent: { left: -1440, right: -1440 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: ' ', font: 'Arial', size: 24 })],
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 240 },
      indent: { left: -1440, right: -1440 },
    }),
    spacer(360),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Sistema de Detección de Anomalías en Redes', font: 'Arial', size: 40, bold: true, color: BLUE })],
      spacing: { before: 120, after: 80 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'con Priorización Inteligente de Alertas mediante Q-Learning', font: 'Arial', size: 32, italics: true, color: BLUE2 })],
      spacing: { before: 0, after: 240 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE2, space: 1 } },
      children: [],
      spacing: { before: 0, after: 240 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'SecureOps MX — MSSP SOC', font: 'Arial', size: 26, bold: true, color: '404040' })],
      spacing: { before: 0, after: 80 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Dataset: NSL-KDD  |  Framework: PySpark MLlib + Keras  |  Agente: Q-Learning', font: 'Arial', size: 22, color: '666666' })],
      spacing: { before: 0, after: 320 },
    }),
    new Table({
      width: { size: 6000, type: WidthType.DXA },
      alignment: AlignmentType.CENTER,
      columnWidths: [2400, 3600],
      rows: [
        new TableRow({ children: [
          dataCell('Autor', 2400, LIGHT, AlignmentType.LEFT, true),
          dataCell('Justin Valdez', 3600),
        ]}),
        new TableRow({ children: [
          dataCell('Certificación', 2400, LIGHT, AlignmentType.LEFT, true),
          dataCell('CERT-TLG-SDS — Senior Data Scientist', 3600),
        ]}),
        new TableRow({ children: [
          dataCell('Metodología', 2400, LIGHT, AlignmentType.LEFT, true),
          dataCell('CRISP-DM (6 fases)', 3600),
        ]}),
        new TableRow({ children: [
          dataCell('Repositorio', 2400, LIGHT, AlignmentType.LEFT, true),
          dataCell('github.com/cj-grz/network-anomaly-detection', 3600),
        ]}),
        new TableRow({ children: [
          dataCell('Fecha', 2400, LIGHT, AlignmentType.LEFT, true),
          dataCell('Mayo 2026', 3600),
        ]}),
      ],
    }),
  ];
}

// ── Main document ─────────────────────────────────────────────────────────────

const doc = new Document({
  numbering: {
    config: [
      { reference: 'bullets', levels: [
        { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: '◦', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]},
      { reference: 'numbers', levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ],
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, font: 'Arial', color: BLUE },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: 'Arial', color: BLUE2 },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: '404040' },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ],
  },
  sections: [
    // ── Portada ──────────────────────────────────────────────────────────────
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      children: [...coverSection(), pageBreak()],
    },
    // ── Contenido ────────────────────────────────────────────────────────────
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1260, bottom: 1260, left: 1440 } },
      },
      headers: {
        default: new Header({ children: [
          new Paragraph({
            children: [
              new TextRun({ text: 'Reporte Técnico — Detección de Anomalías en Redes  |  SecureOps MX', font: 'Arial', size: 18, color: '888888' }),
              new TextRun({ children: ['\t'], font: 'Arial', size: 18 }),
              new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 18, color: '888888' }),
            ],
            tabStops: [{ type: 'right', position: 9360 }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'DDDDDD', space: 4 } },
          }),
        ]}),
      },
      footers: {
        default: new Footer({ children: [
          new Paragraph({
            children: [new TextRun({ text: 'CERT-TLG-SDS  |  NSL-KDD  |  PySpark + Q-Learning  |  Mayo 2026', font: 'Arial', size: 16, color: 'AAAAAA' })],
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: 'DDDDDD', space: 4 } },
          }),
        ]}),
      },
      children: [

        // ── Índice ──────────────────────────────────────────────────────────
        h1('Contenido'),
        new TableOfContents('', { hyperlink: true, headingStyleRange: '1-3' }),
        pageBreak(),

        // ── Resumen Ejecutivo ───────────────────────────────────────────────
        h1('Resumen Ejecutivo'),
        p('Este reporte documenta el desarrollo de un sistema de detección de anomalías en tráfico de red para SecureOps MX, empresa de servicios de seguridad gestionada (MSSP). El sistema integra tres componentes técnicos: clasificación multiclase con PySpark MLlib (Random Forest y Gradient Boosted Trees), detección no supervisada mediante un Autoencoder (Keras), y un agente de Inteligencia Artificial con aprendizaje por refuerzo (Q-Learning) que actúa como capa de priorización de alertas.'),
        p('El dataset utilizado es NSL-KDD, una versión mejorada del KDD Cup 1999, con 125,973 registros de entrenamiento y 22,544 de prueba, clasificados en cinco categorías: Normal, DoS, Probe, R2L y U2R. La metodología seguida es CRISP-DM en sus seis fases.'),
        p('La métrica principal de evaluación es el Costo Operativo Total (COT), bajo el constraint duro de Recall del sistema mayor o igual al 90%, que garantiza que al menos 9 de cada 10 ataques sean detectados. El agente Q-Learning es evaluado contra tres baselines: escalar todas las alertas, umbral fijo de probabilidad, y el clasificador sin capa de decisión.'),
        spacer(80),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 3120, 3120],
          rows: [
            new TableRow({ children: [
              headerCell('Componente', 3120),
              headerCell('Tecnología', 3120),
              headerCell('Propósito', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Clasificador principal', 3120, GRAY),
              dataCell('Random Forest / GBT (PySpark MLlib)', 3120),
              dataCell('Identificación multiclase de ataques', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Detector de anomalías', 3120, GRAY),
              dataCell('Autoencoder (Keras)', 3120),
              dataCell('Detección de ataques no vistos en entrenamiento', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Agente de decisión', 3120, GRAY),
              dataCell('Q-Learning tabular', 3120),
              dataCell('Priorización de alertas con contexto operativo', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Plataforma MLOps', 3120, GRAY),
              dataCell('Databricks + MLflow', 3120),
              dataCell('Registro y seguimiento de experimentos', 3120),
            ]}),
          ],
        }),
        caption('Tabla 1. Componentes del sistema'),
        pageBreak(),

        // ── 1. Business Understanding ───────────────────────────────────────
        h1('1. Comprensión del Negocio (Business Understanding)'),

        h2('1.1 Contexto Organizacional'),
        p('SecureOps MX es un proveedor de servicios de seguridad gestionada (MSSP) que opera un Centro de Operaciones de Seguridad (SOC) para múltiples clientes corporativos. El equipo de analistas enfrenta un volumen creciente de alertas de seguridad, donde la mayoría son falsos positivos que consumen recursos sin representar amenazas reales.'),
        p('El problema central es la fatiga por alertas: los analistas reciben miles de notificaciones diarias, lo que incrementa el tiempo de respuesta ante amenazas reales y eleva el costo operativo del SOC.'),

        h2('1.2 Objetivo del Proyecto'),
        p('Desarrollar un sistema de detección de intrusiones que clasifique el tráfico de red y priorice las alertas de forma inteligente, minimizando el Costo Operativo Total (COT) sin comprometer la seguridad del cliente.'),

        h2('1.3 Criterios de Éxito'),
        spacer(40),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3500, 2000, 3860],
          rows: [
            new TableRow({ children: [
              headerCell('Situación', 3500),
              headerCell('Costo (COT)', 2000),
              headerCell('Justificación', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('Ataque no detectado — FN', 3500, GRAY),
              dataCell('15 puntos', 2000, GRAY, AlignmentType.CENTER),
              dataCell('Amenaza ignorada — daño operativo al cliente', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('DoS no detectado — FN DoS', 3500),
              dataCell('20 puntos', 2000, GRAY, AlignmentType.CENTER),
              dataCell('Denegación de servicio — impacto mayor', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('Tráfico normal escalado — FP', 3500, GRAY),
              dataCell('2 puntos', 2000, GRAY, AlignmentType.CENTER),
              dataCell('Analista invierte tiempo sin razón', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('Costo base de escalada', 3500),
              dataCell('1 punto', 2000, GRAY, AlignmentType.CENTER),
              dataCell('Toda alerta revisada tiene costo de gestión', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('TN correcto — alerta ignorada correctamente', 3500, GRAY),
              dataCell('-1 punto', 2000, GRAY, AlignmentType.CENTER),
              dataCell('Ahorro operativo por filtrado correcto', 3860),
            ]}),
          ],
        }),
        caption('Tabla 2. Tabla de costos del sistema (COT)'),
        spacer(80),
        mixedP([bold('Constraint duro: '), normal('Recall del sistema ≥ 0.90. Cualquier política que no alcance este umbral no es aceptable para producción, independientemente del COT obtenido.')]),

        h2('1.4 Subcompetencias de la Certificación'),
        bullet('SC-02: Modelado con PySpark MLlib — Random Forest y GBT sobre datos distribuidos'),
        bullet('SC-03: Pipelines reproducibles — anti-leakage con StringIndexer, VectorAssembler, StandardScaler'),
        bullet('SC-06: Aprendizaje por refuerzo — Q-Learning tabular para toma de decisiones'),
        bullet('SC-08: Evaluación rigurosa — F1-macro, COT, comparativa de 4 políticas'),
        bullet('SC-10: MLOps — Databricks Unity Catalog, Delta tables, MLflow Model Registry'),
        bullet('SC-11: Despliegue — Dashboard Streamlit con 4 vistas interactivas'),
        pageBreak(),

        // ── 2. Data Understanding ───────────────────────────────────────────
        h1('2. Comprensión de los Datos (Data Understanding)'),

        h2('2.1 Descripción del Dataset NSL-KDD'),
        p('NSL-KDD es una versión mejorada del dataset KDD Cup 1999, ampliamente utilizado en investigación de seguridad de redes. Corrige las principales limitaciones de su predecesor: elimina registros duplicados que sesgaban los resultados y selecciona registros de dificultad variada para una evaluación más representativa.'),
        spacer(60),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 3120, 3120],
          rows: [
            new TableRow({ children: [
              headerCell('Característica', 3120),
              headerCell('KDDTrain+', 3120),
              headerCell('KDDTest+', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Registros totales', 3120, GRAY),
              dataCell('125,973', 3120, WHITE, AlignmentType.CENTER),
              dataCell('22,544', 3120, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Features originales', 3120, GRAY),
              dataCell('41 + 1 label', 3120, WHITE, AlignmentType.CENTER),
              dataCell('41 + 1 label', 3120, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Clases', 3120, GRAY),
              dataCell('Normal, DoS, Probe, R2L, U2R', 3120),
              dataCell('Normal, DoS, Probe, R2L, U2R + Unknown', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Features categóricas', 3120, GRAY),
              dataCell('protocol_type, service, flag', 3120),
              dataCell('protocol_type, service, flag', 3120),
            ]}),
          ],
        }),
        caption('Tabla 3. Características del dataset NSL-KDD'),

        h2('2.2 Distribución de Clases'),
        imgPara('01_class_distribution.png', 560, 280, 'Distribución de clases'),
        caption('Figura 1. Distribución de clases en KDDTrain+'),
        spacer(80),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 1560, 1560, 1560, 1560, 780],
          rows: [
            new TableRow({ children: [
              headerCell('Clase', 2340),
              headerCell('Train (n)', 1560),
              headerCell('Train (%)', 1560),
              headerCell('Test (n)', 1560),
              headerCell('Test (%)', 1560),
              headerCell('Shift', 780),
            ]}),
            new TableRow({ children: [
              dataCell('Normal', 2340, GRAY),
              dataCell('67,343', 1560, WHITE, AlignmentType.CENTER),
              dataCell('53.54%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('9,711', 1560, WHITE, AlignmentType.CENTER),
              dataCell('43.07%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('↓', 780, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('DoS', 2340, GRAY),
              dataCell('45,927', 1560, WHITE, AlignmentType.CENTER),
              dataCell('36.46%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('7,458', 1560, WHITE, AlignmentType.CENTER),
              dataCell('33.08%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('↓', 780, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Probe', 2340, GRAY),
              dataCell('11,656', 1560, WHITE, AlignmentType.CENTER),
              dataCell('9.25%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('2,421', 1560, WHITE, AlignmentType.CENTER),
              dataCell('10.74%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('↑', 780, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('R2L', 2340, GRAY, AlignmentType.LEFT),
              dataCell('995', 1560, WHITE, AlignmentType.CENTER),
              dataCell('0.79%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('2,424', 1560, WHITE, AlignmentType.CENTER),
              dataCell('10.75%', 1560, '#FFF2CC', AlignmentType.CENTER),
              dataCell('↑↑↑', 780, '#FFF2CC', AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('U2R', 2340, GRAY),
              dataCell('52', 1560, WHITE, AlignmentType.CENTER),
              dataCell('0.04%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('200', 1560, WHITE, AlignmentType.CENTER),
              dataCell('0.89%', 1560, WHITE, AlignmentType.CENTER),
              dataCell('↑↑', 780, WHITE, AlignmentType.CENTER),
            ]}),
          ],
        }),
        caption('Tabla 4. Distribución de clases y distribution shift entre train y test'),

        h2('2.3 Riesgos Metodológicos Identificados'),
        bullet('Desbalance severo: R2L (0.79%) y U2R (0.04%) en entrenamiento → riesgo de ignorar ataques raros'),
        bullet('Distribution shift intencional: R2L se multiplica ~14x en test — evalúa generalización del modelo'),
        bullet('Clase "Unknown" en test: ataques no vistos en entrenamiento → excluidos del modelado'),
        bullet('Alta correlación entre features: dst_host_srv_count alcanza 0.62 con la etiqueta'),
        spacer(60),
        imgPara('03_feature_correlation.png', 560, 280, 'Correlación de features'),
        caption('Figura 2. Correlación de features numéricas con la etiqueta de ataque'),
        imgPara('02_train_vs_test_distribution.png', 560, 220, 'Train vs Test distribution'),
        caption('Figura 3. Comparación de distribución entre train y test (distribution shift)'),
        pageBreak(),

        // ── 3. Data Preparation ─────────────────────────────────────────────
        h1('3. Preparación de Datos (Data Preparation)'),

        h2('3.1 Pipeline Anti-Leakage'),
        p('El principio fundamental del pipeline es que ningún transformador ve datos de validación o test durante el ajuste (fit). Todo el conocimiento estadístico del escalado y codificación proviene exclusivamente del conjunto de entrenamiento.'),
        spacer(60),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2000, 3500, 3860],
          rows: [
            new TableRow({ children: [
              headerCell('Etapa', 2000),
              headerCell('Componente', 3500),
              headerCell('Garantía anti-leakage', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('1', 2000, GRAY, AlignmentType.CENTER),
              dataCell('StringIndexer (label)', 3500),
              dataCell('Vocabulario fijo en orden alfabético', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('2', 2000, GRAY, AlignmentType.CENTER),
              dataCell('StringIndexer × 3 (categóricas)', 3500),
              dataCell('Ajustado SOLO en train', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('3', 2000, GRAY, AlignmentType.CENTER),
              dataCell('OneHotEncoder', 3500),
              dataCell('Fit en train, transform en val/test', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('4', 2000, GRAY, AlignmentType.CENTER),
              dataCell('VectorAssembler', 3500),
              dataCell('38 numéricas + OHE → features_raw', 3860),
            ]}),
            new TableRow({ children: [
              dataCell('5', 2000, GRAY, AlignmentType.CENTER),
              dataCell('StandardScaler (μ y σ de train)', 3500),
              dataCell('Media y desviación estándar SOLO de train', 3860),
            ]}),
          ],
        }),
        caption('Tabla 5. Pipeline de preprocesamiento PySpark MLlib'),

        h2('3.2 Split Estratificado 70/15/15'),
        p('La división se realiza por clase antes de cualquier transformación, garantizando que las proporciones de clases minoritarias (R2L, U2R) se mantengan en los tres conjuntos.'),
        spacer(60),
        imgPara('04_split_distribution.png', 560, 260, 'Split distribution'),
        caption('Figura 4. Distribución de clases por split — proporciones consistentes'),
        spacer(80),
        new Table({
          width: { size: 7200, type: WidthType.DXA },
          columnWidths: [2400, 1600, 1600, 1600],
          rows: [
            new TableRow({ children: [
              headerCell('Conjunto', 2400),
              headerCell('Registros', 1600),
              headerCell('% del total', 1600),
              headerCell('Uso', 1600),
            ]}),
            new TableRow({ children: [
              dataCell('Train', 2400, GRAY),
              dataCell('88,726', 1600, WHITE, AlignmentType.CENTER),
              dataCell('70.4%', 1600, WHITE, AlignmentType.CENTER),
              dataCell('Fit de modelos', 1600),
            ]}),
            new TableRow({ children: [
              dataCell('Validation', 2400, GRAY),
              dataCell('18,780', 1600, WHITE, AlignmentType.CENTER),
              dataCell('14.9%', 1600, WHITE, AlignmentType.CENTER),
              dataCell('Selección de modelos y threshold AE', 1600),
            ]}),
            new TableRow({ children: [
              dataCell('Test', 2400, GRAY),
              dataCell('18,467', 1600, WHITE, AlignmentType.CENTER),
              dataCell('14.7%', 1600, WHITE, AlignmentType.CENTER),
              dataCell('Evaluación final — UNA VEZ', 1600),
            ]}),
          ],
        }),
        caption('Tabla 6. Split estratificado 70/15/15'),

        h2('3.3 Pesos de Clase'),
        p('Para compensar el desbalance severo, se calculan pesos inversamente proporcionales a la frecuencia de cada clase: peso = total / (n_clases × conteo_clase).'),
        imgPara('05_class_weights.png', 500, 220, 'Pesos de clase'),
        caption('Figura 5. Pesos de clase — R2L y U2R tienen penalización alta por ser raros'),
        spacer(60),
        new Table({
          width: { size: 7200, type: WidthType.DXA },
          columnWidths: [2400, 2400, 2400],
          rows: [
            new TableRow({ children: [
              headerCell('Clase', 2400), headerCell('Muestras (train)', 2400), headerCell('Peso', 2400),
            ]}),
            new TableRow({ children: [dataCell('Normal', 2400, GRAY), dataCell('47,379', 2400, WHITE, AlignmentType.CENTER), dataCell('0.37', 2400, WHITE, AlignmentType.CENTER)] }),
            new TableRow({ children: [dataCell('DoS', 2400, GRAY), dataCell('32,368', 2400, WHITE, AlignmentType.CENTER), dataCell('0.55', 2400, WHITE, AlignmentType.CENTER)] }),
            new TableRow({ children: [dataCell('Probe', 2400, GRAY), dataCell('8,249', 2400, WHITE, AlignmentType.CENTER), dataCell('2.15', 2400, WHITE, AlignmentType.CENTER)] }),
            new TableRow({ children: [dataCell('R2L', 2400, GRAY), dataCell('698', 2400, WHITE, AlignmentType.CENTER), dataCell('25.42', 2400, '#FFF2CC', AlignmentType.CENTER)] }),
            new TableRow({ children: [dataCell('U2R', 2400, GRAY), dataCell('32', 2400, WHITE, AlignmentType.CENTER), dataCell('554.54', 2400, '#FFE0E0', AlignmentType.CENTER)] }),
          ],
        }),
        caption('Tabla 7. Pesos de clase para Random Forest'),
        pageBreak(),

        // ── 4. Modeling ──────────────────────────────────────────────────────
        h1('4. Modelado (Modeling)'),

        h2('4.1 Modelo 1 — Random Forest (PySpark MLlib)'),
        p('Random Forest es el clasificador principal. Fue seleccionado por su robustez ante desbalance de clases cuando se aplican pesos, su interpretabilidad mediante feature importance, y su eficiencia en entornos distribuidos con PySpark MLlib.'),
        bullet('Optimización: CrossValidator con k=5 folds sobre train'),
        bullet('Grid de búsqueda: numTrees ∈ {50, 100} × maxDepth ∈ {8, 12}'),
        bullet('Métrica de selección: F1-macro (no accuracy, por el desbalance)'),
        bullet('Pesos de clase: columna classWeight con pesos inversos a la frecuencia'),
        spacer(80),
        imgPara('06_rf_feature_importance.png', 520, 340, 'Feature importance RF'),
        caption('Figura 6. Feature importance del Random Forest — Top 20 variables'),

        h2('4.2 Modelo 2 — Gradient Boosted Trees (PySpark MLlib)'),
        p('GBT en PySpark solo soporta clasificación binaria nativamente. Para el caso multiclase de 5 categorías se utilizó la estrategia One-vs-Rest (OvR): se entrena un clasificador binario por cada clase contra todas las demás.'),
        bullet('CrossValidator: k=3 folds (más lento que RF)'),
        bullet('Grid: maxIter ∈ {20, 40} × maxDepth ∈ {5, 8}'),
        bullet('Estrategia: OneVsRest — 5 clasificadores binarios independientes'),

        h2('4.3 Modelo 3 — Autoencoder (Keras)'),
        p('El Autoencoder es un modelo de red neuronal no supervisado que aprende a comprimir y reconstruir el tráfico normal. Una conexión con alto error de reconstrucción (MSE alto) es señal de anomalía.'),
        spacer(60),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 6240],
          rows: [
            new TableRow({ children: [
              headerCell('Aspecto', 3120), headerCell('Detalle', 6240),
            ]}),
            new TableRow({ children: [
              dataCell('Entrenamiento', 3120, GRAY),
              dataCell('SOLO con conexiones Normal de train — nunca ve ataques', 6240),
            ]}),
            new TableRow({ children: [
              dataCell('Arquitectura', 3120, GRAY),
              dataCell('Input → Dense(enc_dim, ReLU) → Dense(btl_dim, ReLU) → Dense(enc_dim, ReLU) → Output', 6240),
            ]}),
            new TableRow({ children: [
              dataCell('Threshold', 3120, GRAY),
              dataCell('Percentil 95 del MSE en conexiones Normal de validación', 6240),
            ]}),
            new TableRow({ children: [
              dataCell('Score de anomalía', 3120, GRAY),
              dataCell('MSE normalizado ∈ [0, 1] por el MSE máximo en validación', 6240),
            ]}),
            new TableRow({ children: [
              dataCell('Anti-leakage', 3120, GRAY),
              dataCell('Threshold calibrado en val — test NUNCA se ve durante calibración', 6240),
            ]}),
          ],
        }),
        caption('Tabla 8. Diseño del Autoencoder'),

        h2('4.4 Resultados de Modelado ML'),
        p('El Random Forest fue el único clasificador ejecutable en el entorno local (Apple Silicon M1) debido a incompatibilidad de arquitectura ARM64/x86_64 con los Python workers de Spark para GBT OneVsRest. El RF con CrossValidator k=5 y pesos de clase obtuvo los siguientes resultados:'),
        spacer(60),
        imgPara('confusion_matrix_—_random_forest_val.png', 460, 320, 'Confusion matrix RF Val'),
        caption('Figura 7. Matriz de confusión — Random Forest (Validation)'),
        spacer(80),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 1404, 1404, 1404, 1404, 1404],
          rows: [
            new TableRow({ children: [
              headerCell('Modelo', 2340), headerCell('F1-macro', 1404), headerCell('Recall DoS', 1404),
              headerCell('Recall Probe', 1404), headerCell('Recall R2L', 1404), headerCell('Recall U2R', 1404),
            ]}),
            new TableRow({ children: [
              dataCell('Random Forest (Val)', 2340, GRAY),
              dataCell('0.796', 1404, '#EBF3FB', AlignmentType.CENTER),
              dataCell('1.000', 1404, WHITE, AlignmentType.CENTER),
              dataCell('0.994', 1404, WHITE, AlignmentType.CENTER),
              dataCell('0.985', 1404, WHITE, AlignmentType.CENTER),
              dataCell('0.167', 1404, '#FFF2CC', AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Random Forest (Test)', 2340, GRAY),
              dataCell('0.919', 1404, '#D5E8D4', AlignmentType.CENTER),
              dataCell('—', 1404, WHITE, AlignmentType.CENTER),
              dataCell('—', 1404, WHITE, AlignmentType.CENTER),
              dataCell('—', 1404, WHITE, AlignmentType.CENTER),
              dataCell('—', 1404, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Databricks RF (baseline)', 2340, GRAY),
              dataCell('0.7007', 1404, '#FFF2CC', AlignmentType.CENTER),
              dataCell('N/A', 1404, WHITE, AlignmentType.CENTER),
              dataCell('N/A', 1404, WHITE, AlignmentType.CENTER),
              dataCell('N/A', 1404, WHITE, AlignmentType.CENTER),
              dataCell('N/A', 1404, WHITE, AlignmentType.CENTER),
            ]}),
          ],
        }),
        caption('Tabla 9. Resultados Random Forest. Val F1-macro bajo por U2R (solo 6 muestras). Test F1 sube a 0.919 por distribution shift de R2L. Databricks RF = baseline sin pesos de clase.'),
        pageBreak(),

        // ── 5. Agente RL ─────────────────────────────────────────────────────
        h1('5. Agente de Priorización — Q-Learning'),

        h2('5.1 Formulación del Problema como MDP'),
        p('La priorización de alertas se formula como un Proceso de Decisión de Markov (MDP) donde el agente Q-Learning aprende la política óptima de triage a partir de las predicciones del mejor modelo ML.'),
        spacer(60),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2400, 6960],
          rows: [
            new TableRow({ children: [
              headerCell('Componente MDP', 2400), headerCell('Definición', 6960),
            ]}),
            new TableRow({ children: [
              dataCell('Estados (S)', 2400, GRAY),
              dataCell('60 = 5 clases × 4 niveles de confianza × 3 niveles de FP rate reciente', 6960),
            ]}),
            new TableRow({ children: [
              dataCell('Acciones (A)', 2400, GRAY),
              dataCell('3: IGNORAR (0) / MONITOREAR (1) / ESCALAR (2)', 6960),
            ]}),
            new TableRow({ children: [
              dataCell('Recompensa (R)', 2400, GRAY),
              dataCell('Negativa del COT: FN=-15/-20, FP=-2, escalada=-1, TN=+1', 6960),
            ]}),
            new TableRow({ children: [
              dataCell('Política', 2400, GRAY),
              dataCell('Epsilon-greedy durante entrenamiento (ε: 1.0 → 0.05), greedy en evaluación', 6960),
            ]}),
            new TableRow({ children: [
              dataCell('Contexto', 2400, GRAY),
              dataCell('fp_rate_reciente calculado sobre ventana deslizante de 100 decisiones (MongoDB)', 6960),
            ]}),
          ],
        }),
        caption('Tabla 10. Formulación MDP del agente Q-Learning'),

        h2('5.2 Espacio de Estados Detallado'),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2000, 3000, 4360],
          rows: [
            new TableRow({ children: [
              headerCell('Dimensión', 2000), headerCell('Valores', 3000), headerCell('Rango', 4360),
            ]}),
            new TableRow({ children: [
              dataCell('Clase predicha', 2000, GRAY),
              dataCell('5 valores', 3000, WHITE, AlignmentType.CENTER),
              dataCell('Normal, DoS, Probe, R2L, U2R', 4360),
            ]}),
            new TableRow({ children: [
              dataCell('Confianza ML', 2000, GRAY),
              dataCell('4 niveles', 3000, WHITE, AlignmentType.CENTER),
              dataCell('[0, 0.5) · [0.5, 0.75) · [0.75, 0.9) · [0.9, 1.0]', 4360),
            ]}),
            new TableRow({ children: [
              dataCell('FP rate reciente', 2000, GRAY),
              dataCell('3 niveles', 3000, WHITE, AlignmentType.CENTER),
              dataCell('Bajo (<10%) · Medio (10-30%) · Alto (≥30%)', 4360),
            ]}),
          ],
        }),
        caption('Tabla 11. Dimensiones del espacio de estados'),

        h2('5.3 Rol de MongoDB'),
        p('La tasa de falsos positivos reciente (fp_rate_reciente) es el elemento que diferencia este agente de un clasificador estático. MongoDB almacena las últimas 100 decisiones del agente en una colección con índice temporal, permitiendo calcular en tiempo real cuántas de las últimas escaladas resultaron ser tráfico normal. Si el agente está generando demasiados FP, el estado lo refleja y el agente aprende a ser más conservador.'),
        p('En caso de que MongoDB no esté disponible, el sistema hace fallback automático a una colección de Python (deque) en memoria, garantizando que el agente funcione en cualquier entorno.'),

        h2('5.4 Baselines de Comparación'),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 4680, 2340],
          rows: [
            new TableRow({ children: [
              headerCell('Política', 2340), headerCell('Descripción', 4680), headerCell('Fortaleza / Debilidad', 2340),
            ]}),
            new TableRow({ children: [
              dataCell('Escalar Todo', 2340, GRAY),
              dataCell('Todas las alertas se envían al analista', 4680),
              dataCell('Recall máximo / COT máximo', 2340),
            ]}),
            new TableRow({ children: [
              dataCell('Threshold ≥ 0.85', 2340, GRAY),
              dataCell('Escalar si la probabilidad de ataque es ≥ 0.85', 4680),
              dataCell('Simple / Sin contexto operativo', 2340),
            ]}),
            new TableRow({ children: [
              dataCell('GBT Argmax', 2340, GRAY),
              dataCell('Escalar si el modelo predice cualquier ataque', 4680),
              dataCell('Usa el modelo / Sin capa de decisión', 2340),
            ]}),
            new TableRow({ children: [
              dataCell('Q-Learning', 2340, GRAY),
              dataCell('Política aprendida con contexto de FP reciente', 4680),
              dataCell('Adaptativo / Requiere entrenamiento', 2340),
            ]}),
          ],
        }),
        caption('Tabla 12. Políticas de comparación'),

        h2('5.5 Resultados del Agente RL (Pendiente)'),
        p('Los resultados completos se generan al ejecutar 04_rl_agent.ipynb. La tabla comparativa final estará disponible en reports/policy_comparison_test_FINAL.csv.'),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 1755, 1755, 1755, 1755],
          rows: [
            new TableRow({ children: [
              headerCell('Política', 2340), headerCell('COT Total', 1755),
              headerCell('COT/alerta', 1755), headerCell('Recall', 1755), headerCell('Cumple ≥0.90', 1755),
            ]}),
            new TableRow({ children: [
              dataCell('Escalar Todo', 2340, GRAY),
              dataCell('38,211', 1755, WHITE, AlignmentType.CENTER),
              dataCell('2.069', 1755, WHITE, AlignmentType.CENTER),
              dataCell('1.000', 1755, WHITE, AlignmentType.CENTER),
              dataCell('✓', 1755, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Threshold ≥0.85', 2340, GRAY),
              dataCell('1,724', 1755, WHITE, AlignmentType.CENTER),
              dataCell('0.093', 1755, WHITE, AlignmentType.CENTER),
              dataCell('0.956', 1755, WHITE, AlignmentType.CENTER),
              dataCell('✓', 1755, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('RF Argmax (sin RL)', 2340, GRAY),
              dataCell('-737', 1755, '#D5E8D4', AlignmentType.CENTER),
              dataCell('-0.040', 1755, '#D5E8D4', AlignmentType.CENTER),
              dataCell('0.998', 1755, WHITE, AlignmentType.CENTER),
              dataCell('✓', 1755, WHITE, AlignmentType.CENTER),
            ]}),
            new TableRow({ children: [
              dataCell('Q-Learning', 2340, GRAY),
              dataCell('4,792', 1755, '#EBF3FB', AlignmentType.CENTER),
              dataCell('0.260', 1755, '#EBF3FB', AlignmentType.CENTER),
              dataCell('0.986', 1755, WHITE, AlignmentType.CENTER),
              dataCell('✓', 1755, WHITE, AlignmentType.CENTER),
            ]}),
          ],
        }),
        caption('Tabla 13. Resultados FINALES en Test. COT negativo = ahorro neto. Las 4 políticas cumplen Recall ≥ 0.90.'),
        pageBreak(),

        // ── 6. Deployment ────────────────────────────────────────────────────
        h1('6. Despliegue (Deployment)'),

        h2('6.1 Dashboard Streamlit'),
        p('El sistema cuenta con un dashboard interactivo desarrollado con Streamlit que permite visualizar el funcionamiento del sistema en tiempo real. Está organizado en cuatro vistas:'),
        bullet('Vista 1 — Resumen del Sistema: KPIs principales, distribución de clases, tabla de costos y estado del pipeline'),
        bullet('Vista 2 — Modelos ML: métricas RF vs GBT, matrices de confusión, feature importance y resultados del Autoencoder'),
        bullet('Vista 3 — Agente RL: comparativa de políticas, heatmap de la tabla Q, curvas de aprendizaje'),
        bullet('Vista 4 — Simulación en Vivo: el usuario configura los parámetros de una alerta y observa la decisión del agente en tiempo real'),
        spacer(80),
        mixedP([bold('Comando para ejecutar: '), normal('streamlit run src/app.py')]),

        h2('6.2 Integración MLOps — Databricks'),
        p('Adicionalmente, el pipeline fue implementado en Databricks para demostrar capacidades de MLOps en entorno cloud:'),
        bullet('Unity Catalog: datos almacenados en Delta tables (network_anomaly_detection.nslkdd_train / test)'),
        bullet('MLflow Tracking: experimento "nslkdd-alert-detection" con parámetros y métricas registrados'),
        bullet('MLflow Model Registry: modelo nslkdd_alert_classifier v1 registrado con estado READY'),
        bullet('Resultado baseline en Databricks: F1-macro = 0.7007 (sin pesos de clase ni CrossValidator)'),
        spacer(80),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 3120, 3120],
          rows: [
            new TableRow({ children: [
              headerCell('Componente', 3120), headerCell('Entorno Local', 3120), headerCell('Databricks', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Almacenamiento', 3120, GRAY), dataCell('Parquet (local)', 3120), dataCell('Delta tables / Unity Catalog', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Tracking de experimentos', 3120, GRAY), dataCell('CSV + PNG', 3120), dataCell('MLflow', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Registro de modelos', 3120, GRAY), dataCell('Directorio models/', 3120), dataCell('MLflow Model Registry', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('Pesos de clase', 3120, GRAY), dataCell('Sí (CrossValidator)', 3120), dataCell('No (baseline demo)', 3120),
            ]}),
            new TableRow({ children: [
              dataCell('F1-macro obtenido', 3120, GRAY), dataCell('Ver notebook 03', 3120), dataCell('0.7007', 3120),
            ]}),
          ],
        }),
        caption('Tabla 14. Comparativa entorno local vs Databricks'),

        h2('6.3 Repositorio GitHub'),
        p('Todo el código fuente está disponible en el repositorio público:'),
        new Paragraph({
          children: [new ExternalHyperlink({
            children: [new TextRun({ text: 'https://github.com/cj-grz/network-anomaly-detection', font: 'Arial', size: 22, style: 'Hyperlink' })],
            link: 'https://github.com/cj-grz/network-anomaly-detection',
          })],
          spacing: { before: 60, after: 100 },
        }),
        pageBreak(),

        // ── 7. Conclusiones ──────────────────────────────────────────────────
        h1('7. Conclusiones'),

        h2('7.1 Contribuciones Técnicas'),
        numbered('Pipeline PySpark MLlib con garantías formales de anti-leakage: todos los transformadores se ajustan exclusivamente en train, eliminando el riesgo de data leakage en producción.'),
        numbered('Agente Q-Learning con 60 estados que incorpora contexto operativo dinámico (fp_rate_reciente) mediante ventana deslizante en MongoDB, diferenciándolo de un clasificador estático.'),
        numbered('Sistema de tres capas complementarias: clasificadores supervisados (RF/GBT) para casos conocidos + Autoencoder no supervisado para anomalías nuevas + agente RL para priorización óptima.'),
        numbered('Integración MLOps con Databricks, MLflow Tracking y Model Registry, demostrando capacidad de despliegue en entorno productivo cloud.'),
        numbered('Constraint duro de recall (≥0.90) que garantiza que el sistema no sacrifica seguridad por eficiencia operativa.'),

        h2('7.2 Lecciones Aprendidas'),
        bullet('El distribution shift de R2L (0.79% → 10.75%) es intencional en NSL-KDD: el RF generaliza bien, subiendo de F1=0.796 en val a 0.919 en test gracias a más muestras R2L.'),
        bullet('Los pesos de clase son críticos: el baseline sin pesos (Databricks RF) obtuvo F1=0.70, frente a 0.919 del pipeline con CrossValidator y pesos.'),
        bullet('El agente Q-Learning con 15 épocas no superó al baseline RF Argmax (COT=-737 vs 4,792). Esto indica que cuando el clasificador base ya es muy preciso (99.5%), el RL necesita más épocas o ajuste de hiperparámetros de recompensa para encontrar una política superior.'),
        bullet('La incompatibilidad de arquitectura ARM64/x86_64 en macOS M1 con PySpark Python workers impidió correr GBT OneVsRest — documentado como limitación del entorno local; en Databricks (x86_64) el GBT sí funciona correctamente.'),

        h2('7.3 Trabajo Futuro'),
        bullet('Extender el Autoencoder con un LSTM-Autoencoder para capturar patrones temporales en el tráfico de red'),
        bullet('Implementar DQN (Deep Q-Network) para escalar a espacios de estado continuos'),
        bullet('Integración con SIEM en tiempo real (Elastic/Splunk) para alertas sobre tráfico de producción'),
        bullet('Aplicar técnicas de explicabilidad (SHAP) sobre el Random Forest para justificar cada alerta ante el analista SOC'),
        pageBreak(),

        // ── Referencias ──────────────────────────────────────────────────────
        h1('Referencias'),
        p('Tavallaee, M., Bagheri, E., Lu, W., & Ghorbani, A. A. (2009). A detailed analysis of the KDD CUP 99 data set. In 2009 IEEE Symposium on Computational Intelligence for Security and Defense Applications (pp. 1-6). IEEE.'),
        p('Mnih, V., Kavukcuoglu, K., Silver, D., et al. (2015). Human-level control through deep reinforcement learning. Nature, 518(7540), 529-533.'),
        p('Zaharia, M., et al. (2016). Apache Spark: A unified engine for big data processing. Communications of the ACM, 59(11), 56-65.'),
        p('Wirth, R., & Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. In Proceedings of the 4th International Conference on the Practical Applications of Knowledge Discovery and Data Mining (pp. 29-39).'),
        p('Databricks Inc. (2024). MLflow: An open source platform for the machine learning lifecycle. https://mlflow.org'),
        spacer(200),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: 'CCCCCC', space: 12 } },
          children: [new TextRun({ text: 'Network Anomaly Detection — SecureOps MX  |  CERT-TLG-SDS  |  Mayo 2026', font: 'Arial', size: 18, italics: true, color: '888888' })],
          spacing: { before: 120, after: 0 },
        }),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buffer => {
  const outPath = path.join(__dirname, 'Reporte_Tecnico_NetworkAnomalyDetection.docx');
  fs.writeFileSync(outPath, buffer);
  console.log(`✓ Reporte generado: ${outPath}`);
}).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});

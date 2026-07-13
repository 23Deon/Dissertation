import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outputDir = path.join(root, "outputs", "appendix_tables");
const dataPath = path.join(outputDir, "appendix_tables_data.json");
const workbookPath = path.join(outputDir, "appendix_results_tables.xlsx");

const theme = {
  navy: "#1F3A5F",
  blue: "#DCE6F2",
  blue2: "#EDF3F9",
  line: "#C7D2E0",
  text: "#22313F",
  green: "#E8F3EC",
  amber: "#FFF4E5",
  red: "#FBEAEA",
};

function formatHeader(range) {
  range.format = {
    fill: theme.navy,
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
}

function addTitle(sheet, title, subtitle, spanLetters) {
  const headerRange = `A1:${spanLetters}1`;
  const subtitleRange = `A2:${spanLetters}2`;
  sheet.getRange(headerRange).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    font: { bold: true, size: 16, color: theme.text },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  sheet.getRange(subtitleRange).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format = {
    font: { italic: true, color: "#4B5D70" },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  sheet.getRange("A1:A2").format.rowHeightPx = 26;
}

function writeTable(sheet, startCell, headers, rows, options = {}) {
  const [colLetters, rowStr] = startCell.match(/^([A-Z]+)(\d+)$/).slice(1);
  const startRow = Number(rowStr) - 1;
  const startCol = lettersToIndex(colLetters);
  const matrix = [headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))];
  const range = sheet.getRangeByIndexes(startRow, startCol, matrix.length, headers.length);
  range.values = matrix;

  formatHeader(sheet.getRangeByIndexes(startRow, startCol, 1, headers.length));
  const dataRange = sheet.getRangeByIndexes(startRow + 1, startCol, Math.max(matrix.length - 1, 1), headers.length);
  dataRange.format = {
    wrapText: true,
    verticalAlignment: "top",
    borders: {
      top: { style: "Continuous", color: theme.line },
      bottom: { style: "Continuous", color: theme.line },
      left: { style: "Continuous", color: theme.line },
      right: { style: "Continuous", color: theme.line },
    },
  };

  if (options.numberFormats) {
    for (const [header, fmt] of Object.entries(options.numberFormats)) {
      const idx = headers.indexOf(header);
      if (idx >= 0) {
        sheet.getRangeByIndexes(startRow + 1, startCol + idx, Math.max(matrix.length - 1, 1), 1).format.numberFormat = fmt;
      }
    }
  }

  if (options.addTable !== false) {
    const endCol = indexToLetters(startCol + headers.length - 1);
    const endRow = startRow + matrix.length;
    sheet.tables.add(`${colLetters}${startRow + 1}:${endCol}${endRow}`, true, options.tableName);
  }
}

function lettersToIndex(letters) {
  let idx = 0;
  for (const ch of letters) {
    idx = idx * 26 + (ch.charCodeAt(0) - 64);
  }
  return idx - 1;
}

function indexToLetters(index) {
  let n = index + 1;
  let out = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    out = String.fromCharCode(65 + rem) + out;
    n = Math.floor((n - 1) / 26);
  }
  return out;
}

const payload = JSON.parse(await fs.readFile(dataPath, "utf8"));
const workbook = Workbook.create();

const overview = workbook.worksheets.add("Overview");
overview.showGridLines = false;
addTitle(
  overview,
  "Appendix Results Tables",
  "Detailed per-version, per-scenario, and final-version benchmark tables for dissertation appendices.",
  "B",
);
overview.getRange("A4:B11").values = [
  ["Sheet", "Purpose"],
  ["Per Version", "All controller versions with success rate, average steps, and transition note."],
  ["Final Versions", "Final version table for each approach with solved scenarios listed."],
  ["Scenario Metadata", "Benchmark scenario identifiers, geometry, start/goal, and obstacle details."],
  ["GPT PDD Matrix", "Scenario outcomes for all GPT PDD versions."],
  ["GPT SDD Matrix", "Scenario outcomes for all GPT SDD versions."],
  ["Opus PDD Matrix", "Scenario outcomes for all Opus PDD versions."],
  ["Opus SDD Matrix", "Scenario outcomes for all Opus SDD versions."],
];
formatHeader(overview.getRange("A4:B4"));
overview.getRange("A14:B18").values = [
  ["Cell codes", "Meaning"],
  ["S (n)", "Scenario solved in n steps"],
  ["T (n)", "Timeout or unsuccessful run recorded at n steps"],
  ["I", "Invalid controller"],
  ["initial / improved / regressed / drifted / same", "Version-to-version qualitative note"],
];
formatHeader(overview.getRange("A14:B14"));
overview.getRange("A1:B18").format.autofitColumns();

const perVersion = workbook.worksheets.add("Per Version");
addTitle(
  perVersion,
  "Per-Version Results",
  "All controller versions across GPT, Opus, and baseline families.",
  "J",
);
writeTable(
  perVersion,
  "A4",
  [
    "approach",
    "version",
    "scenarios",
    "success_count",
    "success_rate",
    "collision_count",
    "timeout_count",
    "invalid_count",
    "average_steps",
    "outcome_note",
  ],
  payload.per_version_rows,
  {
    tableName: "PerVersionTable",
    numberFormats: { success_rate: "0.0%", average_steps: "0.00" },
  },
);
perVersion.getRange("A:K").format.autofitColumns();

const finalVersions = workbook.worksheets.add("Final Versions");
addTitle(
  finalVersions,
  "Final-Version Comparison",
  "Final version for each approach, including solved scenarios.",
  "G",
);
writeTable(
  finalVersions,
  "A4",
  [
    "approach",
    "version",
    "success_count",
    "scenarios",
    "success_rate",
    "average_steps",
    "solved_scenarios",
  ],
  payload.final_version_rows,
  {
    tableName: "FinalVersionsTable",
    numberFormats: { success_rate: "0.0%", average_steps: "0.00" },
  },
);
finalVersions.getRange("A:G").format.autofitColumns();
finalVersions.getRange("G:G").format.columnWidthPx = 380;

const metadata = workbook.worksheets.add("Scenario Metadata");
addTitle(
  metadata,
  "Benchmark Scenario Metadata",
  "Canonical scenario definitions used by the evaluation testbed.",
  "I",
);
writeTable(
  metadata,
  "A4",
  [
    "scenario_id",
    "scenario_name",
    "difficulty",
    "challenge_type",
    "grid_size",
    "start",
    "goal",
    "step_budget",
    "obstacles",
  ],
  payload.scenario_metadata_rows,
  {
    tableName: "ScenarioMetadataTable",
  },
);
metadata.getRange("A:I").format.autofitColumns();
metadata.getRange("I:I").format.columnWidthPx = 420;

const matrixSpecs = [
  ["GPT PDD Matrix", "gpt_pdd", "Scenario outcome matrix for all GPT PDD chains."],
  ["GPT SDD Matrix", "gpt_sdd", "Scenario outcome matrix for all GPT SDD chains."],
  ["Opus PDD Matrix", "opus_pdd", "Scenario outcome matrix for all Opus PDD chains."],
  ["Opus SDD Matrix", "opus_sdd", "Scenario outcome matrix for all Opus SDD chains."],
];

for (const [sheetName, key, subtitle] of matrixSpecs) {
  const sheet = workbook.worksheets.add(sheetName);
  const matrix = payload.scenario_matrices[key];
  addTitle(sheet, sheetName, subtitle, indexToLetters(matrix.columns.length - 1));
  writeTable(sheet, "A4", matrix.columns, matrix.rows, {
    tableName: `${key.replace(/[^A-Za-z0-9]/g, "")}MatrixTable`,
    addTable: false,
  });
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(4);
  sheet.getRange("A:AZ").format.autofitColumns();
  const outcomeColumnsStart = 4;
  const dataRowStart = 4;
  for (let r = 0; r < matrix.rows.length; r += 1) {
    for (let c = outcomeColumnsStart; c < matrix.columns.length; c += 1) {
      const value = matrix.rows[r][matrix.columns[c]] ?? "";
      const cell = sheet.getRangeByIndexes(dataRowStart + r, c, 1, 1);
      cell.format.horizontalAlignment = "center";
      if (typeof value === "string" && value.startsWith("S")) {
        cell.format.fill = theme.green;
      } else if (typeof value === "string" && value.startsWith("T")) {
        cell.format.fill = theme.amber;
      } else if (value === "I") {
        cell.format.fill = theme.red;
      }
    }
  }
}

for (const name of workbook.worksheets.items.map((ws) => ws.name)) {
  const sheet = workbook.worksheets.getItem(name);
  const used = sheet.getUsedRange(true);
  if (used) {
    used.format.wrapText = true;
  }
}

await fs.mkdir(outputDir, { recursive: true });
const out = await SpreadsheetFile.exportXlsx(workbook);
await out.save(workbookPath);
console.log(workbookPath);

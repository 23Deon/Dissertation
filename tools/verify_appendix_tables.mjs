import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const workbookPath = path.join(root, "outputs", "appendix_tables", "appendix_results_tables.xlsx");

const blob = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(blob);

const sheets = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 3000,
});
console.log("=== SHEETS ===");
console.log(sheets.ndjson);

const finalVersions = await workbook.inspect({
  kind: "table",
  range: "Final Versions!A1:G12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 7,
});
console.log("=== FINAL VERSIONS ===");
console.log(finalVersions.ndjson);

const metadata = await workbook.inspect({
  kind: "table",
  range: "Scenario Metadata!A1:I8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 9,
});
console.log("=== SCENARIO METADATA ===");
console.log(metadata.ndjson);

const preview = await workbook.render({
  sheetName: "Overview",
  range: "A1:B18",
  scale: 2,
  format: "png",
});
const previewBytes = new Uint8Array(await preview.arrayBuffer());
const previewPath = path.join(root, "outputs", "appendix_tables", "appendix_results_tables_overview.png");
await fs.writeFile(previewPath, previewBytes);
console.log("=== PREVIEW ===");
console.log(previewPath);

for (const [sheetName, range, fileName] of [
  ["Per Version", "A1:J20", "appendix_results_tables_per_version.png"],
  ["Final Versions", "A1:G18", "appendix_results_tables_final_versions.png"],
  ["Scenario Metadata", "A1:I12", "appendix_results_tables_metadata.png"],
]) {
  const image = await workbook.render({
    sheetName,
    range,
    scale: 2,
    format: "png",
  });
  const bytes = new Uint8Array(await image.arrayBuffer());
  const filePath = path.join(root, "outputs", "appendix_tables", fileName);
  await fs.writeFile(filePath, bytes);
  console.log(filePath);
}

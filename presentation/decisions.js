/**
 * How many judgement calls are in the decision log.
 *
 * Read from results/decision_log.csv rather than typed into the deck, for the
 * same reason every number in the report is generated: the log grows, and a
 * hand-typed count goes stale silently. It already did once -- the slide said
 * 49 the moment a fiftieth decision was added.
 *
 * Counted a row at a time rather than by splitting on newlines, because a
 * quoted CSV field is allowed to contain one.
 */

const fs = require("fs");
const path = require("path");

const LF = 10;
const QUOTE = 34;

function countDecisions(csvPath) {
  const csv = fs.readFileSync(csvPath, "utf8");
  let rows = 0;
  let inQuotes = false;

  for (let i = 0; i < csv.length; i++) {
    const code = csv.charCodeAt(i);
    if (code === QUOTE) inQuotes = !inQuotes;
    else if (code === LF && !inQuotes) rows++;
  }
  // A final row with no trailing newline still counts.
  if (csv.length > 0 && csv.charCodeAt(csv.length - 1) !== LF) rows++;

  return rows - 1; // minus the header
}

module.exports = {
  countDecisions,
  DECISIONS: countDecisions(
    path.join(__dirname, "..", "results", "decision_log.csv")),
};

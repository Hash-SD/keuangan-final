const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.join(__dirname, "..", "portal", "index.html"), "utf8");

assert(html.includes("Konteks Periode Data"), "frontend must rename the period panel");
assert(!html.includes("Periode Data Opsional"), "frontend must not use Opsional in the period title");
assert(!html.includes("Simpan Periode"), "frontend must not expose a manual save-period button");
assert(!html.includes("Simpan Sesi Upload"), "frontend must not expose a manual save-session button");
assert(html.includes('apiPost("/api/upload/session/context"'), "frontend must autosave context through the session context endpoint");
assert(html.includes('apiPost("/api/upload/session/file", formData)'), "frontend must stage files through the session file endpoint");
assert(html.includes('apiDelete("/api/upload/session/file"'), "frontend must support removing staged files");
assert(html.includes('apiPost("/api/upload/session/commit", {})'), "frontend must commit through the session commit endpoint");
assert(html.includes('formData.append("upload_type", type)'), "frontend must identify the upload type for staged files");
assert(html.includes('formData.append("file", file)'), "frontend must append selected files for staging");
assert(html.includes('const canCommit = readiness.can_commit === true && session.status !== "committed"'), "commit button must depend on backend readiness");
assert(!html.includes('apiPost("/api/upload/pdf"'), "frontend must not use legacy PDF upload endpoint");
assert(!html.includes('apiPost("/api/upload/csv"'), "frontend must not use legacy CSV upload endpoint");
assert(!html.includes('apiPost("/api/upload/excel"'), "frontend must not use legacy Excel upload endpoint");

console.log("frontend upload session state checks passed");

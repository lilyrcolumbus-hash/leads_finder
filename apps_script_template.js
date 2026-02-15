/**
 * Google Apps Script - Lead Receiver
 *
 * Paste this code into your Google Apps Script project (script.google.com).
 * It receives leads via POST from the Lead Generation App and writes them
 * to the active spreadsheet.
 *
 * Setup:
 * 1. Open your Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Delete any existing code and paste this entire file
 * 4. Click Deploy > New deployment
 * 5. Select type: "Web app"
 * 6. Set "Execute as": Me
 * 7. Set "Who has access": Anyone
 * 8. Click Deploy and copy the URL
 * 9. Paste the URL in your .env as GOOGLE_SHEETS_WEBHOOK_URL
 */

// Column headers (must match the data sent from the Python app)
var HEADERS = [
  "Nombre", "Email", "Telefono", "Empresa", "Website", "Direccion",
  "Industria", "Rating", "Fuente", "URL", "Pain Score", "AI Score",
  "Software Needs", "Gemini Analysis", "Has Website", "Has Social Media", "Fecha"
];

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    // Create headers if sheet is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      // Bold headers and freeze first row
      sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight("bold");
      sheet.setFrozenRows(1);
    }

    var data = JSON.parse(e.postData.contents);
    var leads = data.leads || [];
    var count = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];
      sheet.appendRow([
        lead.nombre || "",
        lead.email || "",
        lead.telefono || "",
        lead.empresa || "",
        lead.website || "",
        lead.direccion || "",
        lead.industria || "",
        lead.rating || "",
        lead.fuente || "",
        lead.url || "",
        lead.pain_score || "",
        lead.ai_score || 0,
        lead.software_needs || "",
        lead.gemini_analysis || "",
        lead.has_website || "",
        lead.has_social_media || "",
        new Date().toLocaleString()
      ]);
      count++;
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok", count: count }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ status: "ok", message: "Lead receiver is running" }))
    .setMimeType(ContentService.MimeType.JSON);
}

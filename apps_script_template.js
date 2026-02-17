/**
 * Google Apps Script - Lead Receiver
 *
 * Paste this code into your Google Apps Script project (script.google.com).
 * It receives leads via POST from the Lead Generation App and writes them
 * to named sheet tabs (auto-created per industry).
 *
 * Features:
 * - Auto-creates sheet tabs by industry (e.g., "Plumbers", "Dentists")
 * - Adds formatted column headers automatically
 * - Includes Ciudad (city) column for multi-location filtering
 * - Falls back to "Leads" tab if no sheet_name provided
 *
 * Setup:
 * 1. Open your Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Delete any existing code and paste this entire file
 * 4. Click Deploy > New deployment (or Manage deployments > Edit)
 * 5. Select type: "Web app"
 * 6. Set "Execute as": Me
 * 7. Set "Who has access": Anyone
 * 8. Click Deploy and copy the URL
 * 9. Paste the URL in your .env as GOOGLE_SHEETS_WEBHOOK_URL
 */

// Column headers (must match the data sent from the Python app)
var HEADERS = [
  "Negocio", "Telefono", "Email", "Website", "Direccion", "Ciudad",
  "Rating", "Reviews", "Tipo de Negocio", "Pain Score", "Pain Summary",
  "AI Score", "Fuente", "URL", "Fecha"
];

/**
 * Get or create a sheet tab by name.
 * If the tab doesn't exist, creates it with formatted headers.
 */
function getOrCreateSheet(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);

  if (!sheet) {
    sheet = ss.insertSheet(name);
    // Add headers
    sheet.appendRow(HEADERS);
    // Format header row
    var headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#4285f4");
    headerRange.setFontColor("#ffffff");
    sheet.setFrozenRows(1);
    // Set column widths for readability
    sheet.setColumnWidth(1, 200);  // Negocio
    sheet.setColumnWidth(2, 130);  // Telefono
    sheet.setColumnWidth(3, 200);  // Email
    sheet.setColumnWidth(4, 200);  // Website
    sheet.setColumnWidth(5, 250);  // Direccion
    sheet.setColumnWidth(6, 130);  // Ciudad
    sheet.setColumnWidth(7, 70);   // Rating
    sheet.setColumnWidth(8, 70);   // Reviews
    sheet.setColumnWidth(9, 130);  // Tipo de Negocio
    sheet.setColumnWidth(10, 90);  // Pain Score
    sheet.setColumnWidth(11, 250); // Pain Summary
    sheet.setColumnWidth(12, 80);  // AI Score
    sheet.setColumnWidth(13, 110); // Fuente
    sheet.setColumnWidth(14, 250); // URL
    sheet.setColumnWidth(15, 150); // Fecha
  }

  return sheet;
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var leads = data.leads || [];
    var sheetName = data.sheet_name || "Leads";

    var sheet = getOrCreateSheet(sheetName);

    // If sheet exists but has no headers (legacy), add them
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      var headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
      headerRange.setFontWeight("bold");
      headerRange.setBackground("#4285f4");
      headerRange.setFontColor("#ffffff");
      sheet.setFrozenRows(1);
    }

    var count = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];
      sheet.appendRow([
        lead.negocio || "",
        lead.telefono || "",
        lead.email || "",
        lead.website || "",
        lead.direccion || "",
        lead.ciudad || "",
        lead.rating || "",
        lead.reviews || "",
        lead.tipo_negocio || "",
        lead.pain_score || "",
        lead.pain_summary || "",
        lead.ai_score || "",
        lead.fuente || "",
        lead.url || "",
        new Date().toLocaleString()
      ]);
      count++;
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok", count: count, sheet: sheetName }))
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

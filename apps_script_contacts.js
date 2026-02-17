/**
 * Google Apps Script - Business Contacts Receiver
 *
 * Template optimizado para recibir contactos de negocios buscados por industria
 * y ciudad desde la Lead Generation App.
 *
 * Caracteristicas:
 *   - Headers con formato profesional
 *   - Deduplicacion automatica por telefono/nombre de empresa
 *   - Formato condicional para Pain Score (rojo = dolor detectado)
 *   - Columnas con ancho automatico
 *   - Hoja "Contactos" creada automaticamente
 *   - Timestamps por cada entrada
 *
 * Configuracion:
 * 1. Crea o abre un Google Sheet
 * 2. Ve a Extensions > Apps Script
 * 3. Borra el codigo existente y pega este archivo completo
 * 4. Click en Deploy > New deployment
 * 5. Selecciona tipo: "Web app"
 * 6. "Execute as": Me
 * 7. "Who has access": Anyone
 * 8. Click Deploy y copia la URL
 * 9. Pega la URL en tu .env como GOOGLE_SHEETS_WEBHOOK_URL
 *
 * Uso desde la app:
 *   python main.py → Opcion [8] → Selecciona industria y ciudad
 */

// Column headers matching the Python app's _lead_to_row() output
var HEADERS = [
  "Nombre", "Email", "Telefono", "Empresa", "Website", "Direccion",
  "Industria", "Rating", "Fuente", "URL", "Pain Score", "AI Score",
  "Software Needs", "Gemini Analysis", "Has Website", "Has Social Media", "Fecha"
];

// Column widths (pixels) for better readability
var COLUMN_WIDTHS = [180, 220, 140, 200, 220, 250, 120, 70, 100, 200, 90, 80, 200, 300, 90, 110, 150];

/**
 * Get or create the "Contactos" sheet with headers and formatting.
 */
function getContactsSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Contactos");

  if (!sheet) {
    sheet = ss.insertSheet("Contactos");
    setupHeaders(sheet);
  } else if (sheet.getLastRow() === 0) {
    setupHeaders(sheet);
  }

  return sheet;
}

/**
 * Set up header row with formatting.
 */
function setupHeaders(sheet) {
  sheet.appendRow(HEADERS);

  var headerRange = sheet.getRange(1, 1, 1, HEADERS.length);

  // Bold white text on dark blue background
  headerRange.setFontWeight("bold");
  headerRange.setFontColor("#FFFFFF");
  headerRange.setBackground("#1a73e8");
  headerRange.setHorizontalAlignment("center");

  // Freeze header row
  sheet.setFrozenRows(1);

  // Set column widths
  for (var i = 0; i < COLUMN_WIDTHS.length; i++) {
    sheet.setColumnWidth(i + 1, COLUMN_WIDTHS[i]);
  }

  // Add conditional formatting for Pain Score column (column 11)
  var painScoreCol = 11;
  var maxRows = 1000;
  var painRange = sheet.getRange(2, painScoreCol, maxRows, 1);

  // Red background when Pain Score > 0 (pain detected)
  var rule = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberGreaterThan(0)
    .setBackground("#fce4ec")
    .setFontColor("#c62828")
    .setRanges([painRange])
    .build();

  var rules = sheet.getConditionalFormatRules();
  rules.push(rule);
  sheet.setConditionalFormatRules(rules);
}

/**
 * Check if a lead already exists in the sheet (by phone or company name).
 * Returns true if duplicate found.
 */
function isDuplicate(sheet, lead) {
  var lastRow = sheet.getLastRow();
  if (lastRow <= 1) return false;

  var phone = (lead.telefono || "").trim();
  var empresa = (lead.empresa || "").trim().toLowerCase();

  // Skip check if both are empty
  if (!phone && !empresa) return false;

  // Get existing phone numbers (col 3) and company names (col 4)
  var data = sheet.getRange(2, 1, lastRow - 1, 4).getValues();

  for (var i = 0; i < data.length; i++) {
    var existingPhone = (data[i][2] || "").toString().trim();
    var existingEmpresa = (data[i][3] || "").toString().trim().toLowerCase();

    // Match by phone number (if both have phone)
    if (phone && existingPhone && phone === existingPhone) {
      return true;
    }

    // Match by company name (if both have company name and same industry/location)
    if (empresa && existingEmpresa && empresa === existingEmpresa) {
      return true;
    }
  }

  return false;
}

/**
 * POST handler - receives leads from the Python app.
 */
function doPost(e) {
  try {
    var sheet = getContactsSheet();
    var data = JSON.parse(e.postData.contents);
    var leads = data.leads || [];
    var added = 0;
    var skipped = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];

      // Deduplication check
      if (isDuplicate(sheet, lead)) {
        skipped++;
        continue;
      }

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

      added++;
    }

    return ContentService
      .createTextOutput(JSON.stringify({
        status: "ok",
        count: added,
        skipped: skipped,
        message: added + " added, " + skipped + " duplicates skipped"
      }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * GET handler - health check.
 */
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: "ok",
      message: "Business contacts receiver is running"
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Google Apps Script - Business Contacts Receiver (Simplified)
 *
 * Template simplificado para recibir datos basicos de contacto de negocios.
 * Optimizado para busquedas por industria + ciudad con datos de contacto esenciales.
 *
 * Columnas: Negocio | Email | Telefono | Website | Direccion | Rating | Reviews | Industria | Fecha
 *
 * Caracteristicas:
 *   - Solo datos basicos de contacto (sin AI scores ni analisis)
 *   - Headers con formato profesional
 *   - Deduplicacion automatica por telefono/nombre de negocio
 *   - Columnas con ancho optimizado
 *   - Hoja "Contactos" creada automaticamente
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
 *   python main.py → Opcion [8] → Selecciona industria, ciudad y radio
 */

// Basic contact columns
var HEADERS = [
  "Negocio", "Email", "Telefono", "Website",
  "Direccion", "Rating", "Reviews", "Industria", "Fecha"
];

// Column widths (pixels)
var COLUMN_WIDTHS = [200, 220, 140, 200, 250, 70, 80, 120, 150];

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
  headerRange.setFontWeight("bold");
  headerRange.setFontColor("#FFFFFF");
  headerRange.setBackground("#1a73e8");
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);

  for (var i = 0; i < COLUMN_WIDTHS.length; i++) {
    sheet.setColumnWidth(i + 1, COLUMN_WIDTHS[i]);
  }

  // Green highlight for rows with email (column 2)
  var emailRange = sheet.getRange(2, 2, 1000, 1);
  var rule = SpreadsheetApp.newConditionalFormatRule()
    .whenTextContains("@")
    .setBackground("#e8f5e9")
    .setRanges([emailRange])
    .build();

  var rules = sheet.getConditionalFormatRules();
  rules.push(rule);
  sheet.setConditionalFormatRules(rules);
}

/**
 * Check if a contact already exists (by phone or business name).
 */
function isDuplicate(sheet, lead) {
  var lastRow = sheet.getLastRow();
  if (lastRow <= 1) return false;

  var phone = (lead.telefono || "").trim();
  var negocio = (lead.negocio || "").trim().toLowerCase();

  if (!phone && !negocio) return false;

  // Columns: Negocio(1), Email(2), Telefono(3)
  var data = sheet.getRange(2, 1, lastRow - 1, 3).getValues();

  for (var i = 0; i < data.length; i++) {
    var existingNegocio = (data[i][0] || "").toString().trim().toLowerCase();
    var existingPhone = (data[i][2] || "").toString().trim();

    if (phone && existingPhone && phone === existingPhone) return true;
    if (negocio && existingNegocio && negocio === existingNegocio) return true;
  }

  return false;
}

/**
 * POST handler - receives contacts from the Python app.
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

      if (isDuplicate(sheet, lead)) {
        skipped++;
        continue;
      }

      sheet.appendRow([
        lead.negocio || "",
        lead.email || "",
        lead.telefono || "",
        lead.website || "",
        lead.direccion || "",
        lead.rating || "",
        lead.reviews || "",
        lead.industria || "",
        new Date().toLocaleString()
      ]);

      added++;
    }

    return ContentService
      .createTextOutput(JSON.stringify({
        status: "ok",
        count: added,
        skipped: skipped,
        message: added + " contactos agregados, " + skipped + " duplicados omitidos"
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
      message: "Contact sheet receiver is running"
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

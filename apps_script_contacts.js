/**
 * Google Apps Script - Business Contacts Receiver
 *
 * Receives business contact data from the Lead Generation App via POST.
 * Compatible with both full lead data and basic contact searches.
 *
 * Columns: Name | Email | Phone | Company | Website | Address |
 *          Industry | Rating | Source | URL | Pain Score | AI Score | Date
 *
 * Features:
 *   - Auto-creates headers with formatting on first POST
 *   - Duplicate detection by phone number or company name
 *   - Green highlight on rows with email
 *   - doGet() health check for connection verification
 *   - Error handling with JSON error responses
 *
 * Setup:
 * 1. Open your Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Delete existing code and paste this entire file
 * 4. Click Deploy > New deployment
 * 5. Select type: "Web app"
 * 6. Set "Execute as": Me
 * 7. Set "Who has access": Anyone
 * 8. Click Deploy and copy the URL
 * 9. Paste the URL in your .env as GOOGLE_SHEETS_WEBHOOK_URL
 *
 * Usage from the app:
 *   python main.py → Option [8] → Select industry, city, and radius
 */

// Column headers (English)
var HEADERS = [
  "Name", "Email", "Phone", "Company", "Website", "Address",
  "Industry", "Rating", "Source", "URL", "Pain Score", "AI Score", "Date"
];

// Column widths (pixels)
var COLUMN_WIDTHS = [180, 220, 140, 200, 220, 250, 120, 70, 100, 200, 90, 80, 150];

/**
 * Set up header row with formatting on the active sheet.
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
 * Check if a contact already exists (by phone or company name).
 * Returns true if duplicate found.
 */
function isDuplicate(sheet, lead) {
  var lastRow = sheet.getLastRow();
  if (lastRow <= 1) return false;

  var phone = (lead.phone || "").trim();
  var company = (lead.company || lead.name || "").trim().toLowerCase();

  if (!phone && !company) return false;

  // Columns: Name(1), Email(2), Phone(3), Company(4)
  var data = sheet.getRange(2, 1, lastRow - 1, 4).getValues();

  for (var i = 0; i < data.length; i++) {
    var existingPhone = (data[i][2] || "").toString().trim();
    var existingCompany = (data[i][3] || data[i][0] || "").toString().trim().toLowerCase();

    if (phone && existingPhone && phone === existingPhone) return true;
    if (company && existingCompany && company === existingCompany) return true;
  }

  return false;
}

/**
 * POST handler - receives leads/contacts from the Python app.
 *
 * Expects JSON body: { "leads": [ { name, email, phone, company, ... }, ... ] }
 * Field names match Python _lead_to_contact_row() output.
 */
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    // Create headers if sheet is empty
    if (sheet.getLastRow() === 0) {
      setupHeaders(sheet);
    }

    var data = JSON.parse(e.postData.contents);
    var leads = data.leads || [];
    var added = 0;
    var skipped = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];

      // Duplicate check
      if (isDuplicate(sheet, lead)) {
        skipped++;
        continue;
      }

      sheet.appendRow([
        lead.name || "",
        lead.email || "",
        lead.phone || "",
        lead.company || "",
        lead.website || "",
        lead.address || "",
        lead.industry || "",
        lead.rating || "",
        lead.source || "",
        lead.url || "",
        lead.pain_score || "",
        lead.ai_score || "",
        new Date().toLocaleString()
      ]);

      added++;
    }

    return ContentService
      .createTextOutput(JSON.stringify({
        status: "ok",
        count: added,
        skipped: skipped,
        message: added + " contacts added, " + skipped + " duplicates skipped"
      }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * GET handler - health check for connection verification.
 */
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: "ok",
      message: "Lead receiver is running"
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Google Apps Script - Lead Receiver
 *
 * Paste this code into your Google Apps Script project (script.google.com).
 * It receives leads via POST from the Lead Generation App and writes them
 * to named sheet tabs (auto-created per industry).
 *
 * Features:
 * - Auto-creates sheet tabs by name (e.g., "Plumbers", "Dentists")
 * - Adds formatted column headers automatically on every new tab
 * - Duplicate detection by business name + phone/email (skips duplicates)
 * - Dropdown filter arrows on all header columns
 * - Green row highlighting for leads that have an email address
 * - Custom menu to create tabs and re-apply formatting manually
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

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// Column headers (must match the data sent from the Python app)
var HEADERS = [
  "Business", "Phone", "Email", "Website", "Address", "City",
  "Rating", "Reviews", "Business Type", "Pain Score", "Pain Summary",
  "AI Score", "Source", "URL", "Date"
];

// Column index constants (1-based) for readability
var COL_BUSINESS = 1;
var COL_PHONE    = 2;
var COL_EMAIL    = 3;
var COL_WEBSITE  = 4;
var COL_ADDRESS  = 5;
var COL_CITY     = 6;
var COL_DATE     = 15;

// Green highlight for rows with email
var EMAIL_HIGHLIGHT_COLOR = "#d9ead3";

// Header style
var HEADER_BG_COLOR   = "#4285f4";
var HEADER_FONT_COLOR = "#ffffff";

// ---------------------------------------------------------------------------
// Menu (runs when the spreadsheet is opened)
// ---------------------------------------------------------------------------

/**
 * Adds a custom "Leads" menu to the spreadsheet toolbar.
 * Allows users to create new tabs and re-apply formatting manually.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Leads")
    .addItem("Create new tab...", "menuCreateTab")
    .addItem("Re-apply formatting (current tab)", "menuReformat")
    .addItem("Highlight rows with email (current tab)", "menuHighlightEmails")
    .addToUi();
}

/**
 * Menu action: prompts for a tab name and creates it with headers.
 */
function menuCreateTab() {
  var ui = SpreadsheetApp.getUi();
  var response = ui.prompt(
    "Create New Lead Tab",
    "Enter the tab name (e.g., Plumbers, Dentists):",
    ui.ButtonSet.OK_CANCEL
  );
  if (response.getSelectedButton() !== ui.Button.OK) return;

  var name = response.getResponseText().trim();
  if (!name) {
    ui.alert("Tab name cannot be empty.");
    return;
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss.getSheetByName(name)) {
    ui.alert('Tab "' + name + '" already exists.');
    return;
  }

  getOrCreateSheet(name);
  ui.alert('Tab "' + name + '" created with headers and filters.');
}

/**
 * Menu action: re-applies headers, formatting, and filters on the active tab.
 */
function menuReformat() {
  var sheet = SpreadsheetApp.getActiveSheet();
  applyHeaderFormatting_(sheet);
  applyFilters_(sheet);
  highlightRowsWithEmail_(sheet);
  SpreadsheetApp.getUi().alert("Formatting re-applied to "" + sheet.getName() + "".");
}

/**
 * Menu action: highlights rows that have an email in the active tab.
 */
function menuHighlightEmails() {
  var sheet = SpreadsheetApp.getActiveSheet();
  highlightRowsWithEmail_(sheet);
  SpreadsheetApp.getUi().alert("Email highlighting applied.");
}

// ---------------------------------------------------------------------------
// Sheet creation & formatting helpers
// ---------------------------------------------------------------------------

/**
 * Get or create a sheet tab by name.
 * If the tab doesn't exist, creates it with formatted headers and filters.
 *
 * @param {string} name - The tab name.
 * @param {string[]} [customHeaders] - Optional custom headers. Falls back to HEADERS.
 * @return {Sheet} The existing or newly created sheet.
 */
function getOrCreateSheet(name, customHeaders) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);
  var headers = customHeaders || HEADERS;

  if (!sheet) {
    sheet = ss.insertSheet(name);
    // Write headers in the first row
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    applyHeaderFormatting_(sheet, headers.length);
    applyColumnWidths_(sheet, headers.length);
    applyFilters_(sheet, headers.length);
  }

  return sheet;
}

/**
 * Format the header row: bold, colored background, frozen.
 *
 * @param {Sheet} sheet - The sheet to format.
 * @param {number} [numCols] - Number of columns. Defaults to HEADERS.length.
 */
function applyHeaderFormatting_(sheet, numCols) {
  numCols = numCols || HEADERS.length;

  // Ensure headers exist
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, numCols).setValues([HEADERS.slice(0, numCols)]);
  }

  var headerRange = sheet.getRange(1, 1, 1, numCols);
  headerRange.setFontWeight("bold");
  headerRange.setBackground(HEADER_BG_COLOR);
  headerRange.setFontColor(HEADER_FONT_COLOR);
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);
}

/**
 * Set column widths for readability.
 *
 * @param {Sheet} sheet - The sheet to format.
 * @param {number} [numCols] - Number of columns. Defaults to HEADERS.length.
 */
function applyColumnWidths_(sheet, numCols) {
  numCols = numCols || HEADERS.length;

  // Default widths per column index (for legacy HEADERS)
  var defaultWidths = [200, 130, 200, 200, 250, 130, 70, 70, 130, 90, 250, 80, 110, 250, 150];

  for (var i = 0; i < numCols; i++) {
    var width = (i < defaultWidths.length) ? defaultWidths[i] : 150;
    sheet.setColumnWidth(i + 1, width);
  }
}

/**
 * Enable (or re-enable) dropdown filter arrows on the header row.
 * Removes existing filter first to avoid conflicts, then creates a new one
 * covering all data rows.
 *
 * @param {Sheet} sheet - The sheet to apply filters to.
 * @param {number} [numCols] - Number of columns. Defaults to HEADERS.length.
 */
function applyFilters_(sheet, numCols) {
  numCols = numCols || HEADERS.length;

  // Remove any existing filter
  var existingFilter = sheet.getFilter();
  if (existingFilter) {
    existingFilter.remove();
  }

  var lastRow = Math.max(sheet.getLastRow(), 1);
  var filterRange = sheet.getRange(1, 1, lastRow, numCols);
  filterRange.createFilter();
}

// ---------------------------------------------------------------------------
// Duplicate detection
// ---------------------------------------------------------------------------

/**
 * Build a Set of duplicate keys from existing data in the sheet.
 * Key = lowercase(business) + "|" + phone_or_email
 *
 * This allows fast O(1) lookups when inserting new leads.
 *
 * @param {Sheet} sheet - The sheet to scan.
 * @param {number} [bizCol]   - 0-based column index for business name. Default 0.
 * @param {number} [phoneCol] - 0-based column index for phone. Default 1.
 * @param {number} [emailCol] - 0-based column index for email. Default 2.
 * @return {Object} A plain object used as a Set (keys = duplicate strings).
 */
function buildDuplicateIndex_(sheet, bizCol, phoneCol, emailCol) {
  bizCol   = (bizCol   != null) ? bizCol   : 0;
  phoneCol = (phoneCol != null) ? phoneCol : 1;
  emailCol = (emailCol != null) ? emailCol : 2;

  var index = {};
  var lastRow = sheet.getLastRow();
  if (lastRow <= 1) return index; // Only headers or empty

  // Read all columns to support dynamic positions
  var maxCol = Math.max(bizCol, phoneCol, emailCol) + 1;
  var data = sheet.getRange(2, 1, lastRow - 1, maxCol).getValues();

  for (var i = 0; i < data.length; i++) {
    var business = String(data[i][bizCol]).toLowerCase().trim();
    var phone    = String(data[i][phoneCol]).trim();
    var email    = String(data[i][emailCol]).toLowerCase().trim();

    // Key by business+phone
    if (business && phone) {
      index[business + "|" + phone] = true;
    }
    // Key by business+email
    if (business && email) {
      index[business + "|" + email] = true;
    }
    // Key by phone alone (if present)
    if (phone) {
      index["phone|" + phone] = true;
    }
    // Key by email alone (if present)
    if (email) {
      index["email|" + email] = true;
    }
  }

  return index;
}

/**
 * Check if a lead already exists in the duplicate index.
 *
 * @param {Object} index - The duplicate index from buildDuplicateIndex_().
 * @param {string} business - Business name.
 * @param {string} phone - Phone number.
 * @param {string} email - Email address.
 * @return {boolean} True if duplicate, false if new.
 */
function isDuplicate_(index, business, phone, email) {
  business = String(business).toLowerCase().trim();
  phone    = String(phone).trim();
  email    = String(email).toLowerCase().trim();

  // Match by business+phone
  if (business && phone && index[business + "|" + phone]) {
    return true;
  }
  // Match by business+email
  if (business && email && index[business + "|" + email]) {
    return true;
  }
  // Match by phone alone
  if (phone && index["phone|" + phone]) {
    return true;
  }
  // Match by email alone
  if (email && index["email|" + email]) {
    return true;
  }

  return false;
}

/**
 * Add a lead's keys to the duplicate index (after insertion).
 */
function addToIndex_(index, business, phone, email) {
  business = String(business).toLowerCase().trim();
  phone    = String(phone).trim();
  email    = String(email).toLowerCase().trim();

  if (business && phone)  index[business + "|" + phone] = true;
  if (business && email)  index[business + "|" + email] = true;
  if (phone)              index["phone|" + phone] = true;
  if (email)              index["email|" + email] = true;
}

// ---------------------------------------------------------------------------
// Email highlighting
// ---------------------------------------------------------------------------

/**
 * Highlight all data rows that have an email address with a green background.
 * Rows without email keep a white background.
 *
 * Detects the email column dynamically by reading the header row.
 *
 * @param {Sheet} sheet - The sheet to process.
 */
function highlightRowsWithEmail_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow <= 1) return; // No data rows

  // Find the email column dynamically from the header row
  var numCols = sheet.getLastColumn();
  if (numCols === 0) return;
  var headerValues = sheet.getRange(1, 1, 1, numCols).getValues()[0];
  var emailColIdx = -1;
  for (var h = 0; h < headerValues.length; h++) {
    if (String(headerValues[h]).toLowerCase().trim() === "email") {
      emailColIdx = h + 1; // 1-based
      break;
    }
  }
  if (emailColIdx < 0) return; // No Email column found

  var numRows = lastRow - 1;
  var emailValues = sheet.getRange(2, emailColIdx, numRows, 1).getValues();
  var fullRange   = sheet.getRange(2, 1, numRows, numCols);
  var backgrounds = fullRange.getBackgrounds();

  for (var i = 0; i < numRows; i++) {
    var email = String(emailValues[i][0]).trim();
    var color = (email && email !== "") ? EMAIL_HIGHLIGHT_COLOR : "#ffffff";
    for (var j = 0; j < numCols; j++) {
      backgrounds[i][j] = color;
    }
  }

  fullRange.setBackgrounds(backgrounds);
}

// ---------------------------------------------------------------------------
// Webhook handlers
// ---------------------------------------------------------------------------

/**
 * Handle POST requests from the Python Lead Generation App.
 *
 * Expected JSON payload:
 *   { "leads": [...], "sheet_name": "Plumbers" }
 *
 * Each lead object fields:
 *   business, phone, email, website, address, city, rating, reviews,
 *   business_type, pain_score, pain_summary, ai_score, source, url
 */
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var leads = data.leads || [];
    var sheetName = data.sheet_name || "Leads";

    // Support custom headers and column keys from Python
    var customHeaders = data.headers || null;
    var columnKeys    = data.column_keys || null;
    var headers       = customHeaders || HEADERS;
    var numCols       = headers.length;

    var sheet = getOrCreateSheet(sheetName, customHeaders);

    // If sheet exists but has no rows (legacy empty), add headers
    if (sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, numCols).setValues([headers]);
      applyHeaderFormatting_(sheet, numCols);
    }

    // Determine which fields to use for duplicate detection
    // For custom column_keys, find indices of business/name, phone, email
    var bizKey   = "business";
    var phoneKey = "phone";
    var emailKey = "email";
    if (columnKeys) {
      // Spreadsheet format uses "business_name" instead of "business"
      if (columnKeys.indexOf("business_name") >= 0) bizKey = "business_name";
    }

    // Build duplicate index from existing data
    // Find the column positions for duplicate detection in the sheet
    var bizCol   = columnKeys ? columnKeys.indexOf(bizKey) : 0;
    var phoneCol = columnKeys ? columnKeys.indexOf(phoneKey) : 1;
    var emailCol = columnKeys ? columnKeys.indexOf(emailKey) : 2;
    var dupIndex = buildDuplicateIndex_(sheet, bizCol, phoneCol, emailCol);

    var added = 0;
    var skipped = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];
      var business = lead[bizKey] || "";
      var phone    = lead[phoneKey] || "";
      var email    = lead[emailKey] || "";

      // Skip duplicates
      if (isDuplicate_(dupIndex, business, phone, email)) {
        skipped++;
        continue;
      }

      var row;
      if (columnKeys) {
        // Dynamic column mapping: build row from column_keys order
        row = [];
        for (var j = 0; j < columnKeys.length; j++) {
          row.push(lead[columnKeys[j]] || "");
        }
      } else {
        // Legacy format: fixed column order
        row = [
          business,
          phone,
          email,
          lead.website || "",
          lead.address || "",
          lead.city || "",
          lead.rating || "",
          lead.reviews || "",
          lead.business_type || "",
          lead.pain_score || "",
          lead.pain_summary || "",
          lead.ai_score || "",
          lead.source || "",
          lead.url || "",
          new Date().toLocaleString()
        ];
      }

      sheet.appendRow(row);

      // Highlight green if lead has email
      if (email) {
        var newRow = sheet.getLastRow();
        sheet.getRange(newRow, 1, 1, numCols).setBackground(EMAIL_HIGHLIGHT_COLOR);
      }

      // Update the duplicate index for subsequent leads in this batch
      addToIndex_(dupIndex, business, phone, email);
      added++;
    }

    // Re-apply filters to include new rows
    if (added > 0) {
      applyFilters_(sheet, numCols);
    }

    return ContentService
      .createTextOutput(JSON.stringify({
        status: "ok",
        count: added,
        duplicates_skipped: skipped,
        sheet: sheetName
      }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handle GET requests (health check).
 */
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: "ok",
      message: "Lead receiver is running",
      features: ["tabs_by_name", "auto_headers", "duplicate_detection", "dropdown_filters", "email_highlighting"]
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

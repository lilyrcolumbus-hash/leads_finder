/**
 * Google Apps Script - Business Leads Finder (v5 - RapidAPI)
 *
 * Busca negocios usando RapidAPI Local Business Data directamente desde tu Google Sheet.
 * Crea una pestana nueva por cada busqueda (industria + ciudad).
 *
 * NUEVO en v5:
 *   - Usa RapidAPI "Local Business Data" en vez de Google Places API
 *   - Emails y redes sociales incluidos automaticamente (no scraping)
 *   - Hasta 500 resultados por busqueda (vs 60 de Google Places)
 *   - Reviews completas via /business-reviews (no limitado a 5)
 *   - Mas rapido: una sola llamada trae nombre, telefono, email, website, etc.
 *
 * Uso desde terminal:
 *   curl "TU_DEPLOYMENT_URL?industry=plumber&location=Lima,OH&max=3"
 *
 * SETUP:
 *   1. En tu Google Sheet: Extensiones -> Apps Script
 *   2. Pega todo este codigo
 *   3. En la linea de RAPIDAPI_KEY abajo, pon tu RapidAPI Key
 *   4. Guarda (Ctrl+S)
 *   5. Implementar -> Nueva implementacion -> Aplicacion web
 *      - Ejecutar como: Tu cuenta
 *      - Quien tiene acceso: Cualquier persona
 *   6. Copia la URL del deployment
 *   7. Desde terminal: curl -L "URL?industry=plumber&location=Lima,OH&max=3"
 */

// ============================================================
// CONFIGURACION
// ============================================================
const RAPIDAPI_KEY = "18d4566812mshfbf9f44e3b77292p10acbfjsn8b3b6e383c60";
const RAPIDAPI_HOST = "local-business-data.p.rapidapi.com";

// Maximo de negocios a buscar por busqueda (max 500)
const MAX_RESULTS = 60;

// Limite de tiempo: 5 min (deja 1 min de buffer antes del limite duro de 6 min)
const MAX_RUNTIME_MS = 5 * 60 * 1000;

// Cada cuantas filas hacer flush() para guardar datos parciales
const FLUSH_EVERY_N_ROWS = 5;

// Maximo de reviews a pedir por negocio para pain analysis
const MAX_REVIEWS_PER_BUSINESS = 20;

// Palabras clave de dolor en reviews (comunicacion, telefono, servicio)
const PAIN_KEYWORDS = [
  "never answers", "no one picks up", "can't get through",
  "went to voicemail", "left message", "hard to reach",
  "impossible to contact", "no response", "waited forever",
  "rude receptionist", "couldn't schedule", "missed appointment",
  "no confirmation", "terrible communication", "never returned",
  "phone just rings", "always busy", "no call back",
  "poor customer service", "ignored my calls", "don't answer",
  "never called back", "unreachable", "no reply",
  "unprofessional", "rude staff", "worst experience",
  // Espanol
  "no contestan", "no responden", "mala atencion",
  "pesimo servicio", "no devuelven llamada", "imposible comunicarse"
];

// Headers de la tabla (14 columnas)
const HEADERS = [
  "Negocio",                // col 1
  "Email",                  // col 2
  "Telefono",               // col 3
  "Direccion",              // col 4
  "Website",                // col 5
  "Rating",                 // col 6
  "Reviews",                // col 7
  "Tipo de Negocio",        // col 8
  "Pain Score",             // col 9
  "Resumen de Pain Points", // col 10
  "Reviews con Dolor",      // col 11
  "Redes Sociales",         // col 12
  "Google Maps URL",        // col 13
  "Place ID"                // col 14
];

// ============================================================
// MENU PERSONALIZADO
// ============================================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🔍 Lead Finder")
    .addItem("Buscar Negocios", "showSearchDialog")
    .addSeparator()
    .addItem("Buscar Dentistas - Miami", "searchDentistsMiami")
    .addItem("Buscar Plomeros - Houston", "searchPlumbersHouston")
    .addItem("Buscar HVAC - Phoenix", "searchHvacPhoenix")
    .addSeparator()
    .addItem("Busqueda Rapida (sin reviews)", "showQuickSearchDialog")
    .addToUi();
}

// ============================================================
// WEB APP ENDPOINT (para llamar desde terminal con curl)
// ============================================================

/**
 * Maneja requests GET desde terminal/curl.
 *
 * Parametros URL:
 *   ?industry=plumber       (requerido) Tipo de negocio
 *   &location=Lima,OH       (requerido) Ciudad, Estado
 *   &max=3                  (opcional)  Maximo de resultados (default: 60)
 *   &reviews=true           (opcional)  Analizar reviews (default: true)
 *
 * @param {Object} e - Event object con parametros
 * @returns {TextOutput} JSON con resultados
 */
function doGet(e) {
  try {
    var params = e ? e.parameter : {};
    var industry = params.industry || "";
    var location = params.location || "";
    var maxResults = parseInt(params.max) || MAX_RESULTS;
    var analyzeReviews = params.reviews !== "false";

    if (!industry || !location) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Faltan parametros. Uso: ?industry=plumber&location=Lima,OH&max=3",
        example: "?industry=plumber&location=Lima,OH&max=3&reviews=true"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    if (!RAPIDAPI_KEY || RAPIDAPI_KEY === "TU_RAPIDAPI_KEY_AQUI") {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "RAPIDAPI_KEY no configurada. Edita el script y pon tu RapidAPI Key."
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var result = searchAndWriteHeadless(industry, location, analyzeReviews, maxResults);

    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.message
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Version headless (sin UI) para llamadas via curl/web.
 */
function searchAndWriteHeadless(industry, location, analyzeReviews, maxPlaces) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var startTime = new Date().getTime();

  // Paso 1: Buscar negocios via RapidAPI
  var searchResult = searchBusinesses(industry, location, maxPlaces);

  if (searchResult.error) {
    return {
      status: "error",
      message: "No se encontraron negocios para '" + industry + "' en '" + location + "'",
      api_error: searchResult.error,
      leads: 0
    };
  }

  var businesses = searchResult.results;
  if (businesses.length === 0) {
    return {
      status: "ok",
      message: "No se encontraron negocios para '" + industry + "' en '" + location + "'",
      leads: 0
    };
  }

  // Paso 2: Crear pestana
  var tabName = capitalizeFirst(industry) + " - " + location;
  tabName = sanitizeTabName(tabName);
  var sheet = getOrCreateTab(ss, tabName);
  writeHeaders(sheet);
  SpreadsheetApp.flush();

  // Paso 3: Procesar cada negocio
  var currentRow = 2;
  var emailCount = 0;
  var phoneCount = 0;
  var painCount = 0;
  var leadsData = [];

  for (var i = 0; i < businesses.length; i++) {
    var elapsed = new Date().getTime() - startTime;
    if (elapsed > MAX_RUNTIME_MS) break;

    var biz = businesses[i];
    var lead = mapBusinessToLead(biz);

    // Analizar reviews si se pidio y hay tiempo
    if (analyzeReviews && biz.business_id) {
      var timeRemaining = MAX_RUNTIME_MS - elapsed;
      if (timeRemaining > 30000) {
        var reviews = getBusinessReviews(biz.business_id);
        if (reviews.length > 0) {
          var painResult = analyzeReviewsForPain(reviews);
          lead.painScore = painResult.score;
          lead.painSummary = painResult.summary;
          lead.painReviews = painResult.painReviews.join(" | ");
        }
      }
    }

    writeLeadRow(sheet, currentRow, lead);

    if (lead.email) emailCount++;
    if (lead.phone) phoneCount++;
    if (lead.painScore > 0) painCount++;

    leadsData.push({
      name: lead.name,
      email: lead.email,
      phone: lead.phone,
      address: lead.address,
      website: lead.website,
      rating: lead.rating,
      reviews: lead.reviewCount
    });

    currentRow++;

    if ((currentRow - 2) % FLUSH_EVERY_N_ROWS === 0) {
      SpreadsheetApp.flush();
    }

    // Pausa entre reviews calls para rate limits
    if (analyzeReviews && i % 3 === 2) {
      Utilities.sleep(300);
    }
  }

  // Paso 4: Sort y formato
  var totalLeads = currentRow - 2;
  if (totalLeads > 1) {
    var elapsed = new Date().getTime() - startTime;
    if (elapsed < MAX_RUNTIME_MS - 10000) {
      sortAndFormatSheet(sheet, totalLeads);
    } else {
      formatSheet(sheet, totalLeads);
    }
  } else if (totalLeads === 1) {
    formatSheet(sheet, totalLeads);
  }
  SpreadsheetApp.flush();

  return {
    status: "ok",
    message: "Busqueda completada",
    tab: tabName,
    spreadsheet: ss.getUrl(),
    total_leads: totalLeads,
    with_email: emailCount,
    with_phone: phoneCount,
    with_pain: painCount,
    leads: leadsData
  };
}

// ============================================================
// DIALOGOS DE BUSQUEDA
// ============================================================

function showSearchDialog() {
  var ui = SpreadsheetApp.getUi();

  var industryResponse = ui.prompt(
    "🔍 Buscar Negocios",
    "Industria (ej: dentist, plumber, lawyer, hvac, restaurant):",
    ui.ButtonSet.OK_CANCEL
  );
  if (industryResponse.getSelectedButton() !== ui.Button.OK) return;
  var industry = industryResponse.getResponseText().trim();
  if (!industry) { ui.alert("Industria no puede estar vacia"); return; }

  var locationResponse = ui.prompt(
    "🔍 Buscar Negocios",
    "Ciudad / Estado (ej: Miami, FL):",
    ui.ButtonSet.OK_CANCEL
  );
  if (locationResponse.getSelectedButton() !== ui.Button.OK) return;
  var location = locationResponse.getResponseText().trim();
  if (!location) { ui.alert("Ciudad no puede estar vacia"); return; }

  searchAndWrite(industry, location, true);
}

function showQuickSearchDialog() {
  var ui = SpreadsheetApp.getUi();

  var industryResponse = ui.prompt(
    "⚡ Busqueda Rapida",
    "Industria (ej: dentist, plumber, lawyer):",
    ui.ButtonSet.OK_CANCEL
  );
  if (industryResponse.getSelectedButton() !== ui.Button.OK) return;
  var industry = industryResponse.getResponseText().trim();
  if (!industry) { ui.alert("Industria no puede estar vacia"); return; }

  var locationResponse = ui.prompt(
    "⚡ Busqueda Rapida",
    "Ciudad / Estado (ej: Miami, FL):",
    ui.ButtonSet.OK_CANCEL
  );
  if (locationResponse.getSelectedButton() !== ui.Button.OK) return;
  var location = locationResponse.getResponseText().trim();
  if (!location) { ui.alert("Ciudad no puede estar vacia"); return; }

  searchAndWrite(industry, location, false);
}

// ============================================================
// BUSQUEDAS RAPIDAS PRE-CONFIGURADAS
// ============================================================

function searchDentistsMiami() { searchAndWrite("dentist", "Miami, FL", true); }
function searchPlumbersHouston() { searchAndWrite("plumber", "Houston, TX", true); }
function searchHvacPhoenix() { searchAndWrite("hvac", "Phoenix, AZ", true); }

// ============================================================
// LOGICA PRINCIPAL (con UI)
// ============================================================

function searchAndWrite(industry, location, analyzeReviews) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var startTime = new Date().getTime();

  var ui = null;
  try {
    ui = SpreadsheetApp.getUi();
  } catch (e) {
    return searchAndWriteHeadless(industry, location, analyzeReviews, MAX_RESULTS);
  }

  if (!RAPIDAPI_KEY || RAPIDAPI_KEY === "TU_RAPIDAPI_KEY_AQUI") {
    ui.alert("⚠️ Error", "Configura tu RAPIDAPI_KEY en el codigo del script.", ui.ButtonSet.OK);
    return;
  }

  ss.toast("Buscando " + industry + " en " + location + " via RapidAPI...", "🔍 Buscando", -1);

  // Paso 1: Buscar negocios
  var searchResult = searchBusinesses(industry, location, MAX_RESULTS);

  if (searchResult.error) {
    ui.alert("Error de API: " + searchResult.error);
    return;
  }

  var businesses = searchResult.results;
  if (businesses.length === 0) {
    ui.alert("No se encontraron negocios para '" + industry + "' en '" + location + "'");
    return;
  }

  ss.toast("Encontrados " + businesses.length + " negocios. Preparando hoja...", "📋 Procesando", -1);

  // Paso 2: Crear pestana
  var tabName = capitalizeFirst(industry) + " - " + location;
  tabName = sanitizeTabName(tabName);
  var sheet = getOrCreateTab(ss, tabName);
  writeHeaders(sheet);
  ss.setActiveSheet(sheet);
  SpreadsheetApp.flush();

  // Paso 3: Procesar cada negocio
  var currentRow = 2;
  var emailCount = 0;
  var phoneCount = 0;
  var painCount = 0;
  var stoppedEarly = false;

  for (var i = 0; i < businesses.length; i++) {
    var elapsed = new Date().getTime() - startTime;

    if (elapsed > MAX_RUNTIME_MS) {
      stoppedEarly = true;
      break;
    }

    var biz = businesses[i];
    var lead = mapBusinessToLead(biz);

    ss.toast(
      "Procesando " + (i + 1) + " de " + businesses.length +
      " | " + Math.round(elapsed / 1000) + "s",
      "📋 Detalles", -1
    );

    // Analizar reviews si se pidio
    if (analyzeReviews && biz.business_id) {
      var timeRemaining = MAX_RUNTIME_MS - elapsed;
      if (timeRemaining > 30000) {
        var reviews = getBusinessReviews(biz.business_id);
        if (reviews.length > 0) {
          var painResult = analyzeReviewsForPain(reviews);
          lead.painScore = painResult.score;
          lead.painSummary = painResult.summary;
          lead.painReviews = painResult.painReviews.join(" | ");
        }
      }
    }

    writeLeadRow(sheet, currentRow, lead);

    if (lead.email) emailCount++;
    if (lead.phone) phoneCount++;
    if (lead.painScore > 0) painCount++;
    currentRow++;

    if ((currentRow - 2) % FLUSH_EVERY_N_ROWS === 0) {
      SpreadsheetApp.flush();
    }

    if (analyzeReviews && i % 3 === 2) {
      Utilities.sleep(300);
    }
  }

  // Paso 4: Sort y formato
  var totalLeads = currentRow - 2;
  if (totalLeads > 1) {
    var elapsed = new Date().getTime() - startTime;
    if (elapsed < MAX_RUNTIME_MS - 10000) {
      ss.toast("Ordenando resultados...", "📊 Ordenando", -1);
      sortAndFormatSheet(sheet, totalLeads);
    } else {
      formatSheet(sheet, totalLeads);
    }
  } else if (totalLeads === 1) {
    formatSheet(sheet, totalLeads);
  }
  SpreadsheetApp.flush();

  // Paso 5: Resumen
  ss.toast("", "✅ Completado", 1);

  var summaryMsg =
    "Pestana: " + tabName + "\n" +
    "Negocios procesados: " + totalLeads + " de " + businesses.length + "\n" +
    "Con email: " + emailCount + "\n" +
    "Con telefono: " + phoneCount + "\n";

  if (analyzeReviews) {
    summaryMsg += "Con pain points: " + painCount + "\n";
  }

  if (stoppedEarly) {
    summaryMsg += "\n⏱️ Se detuvo antes del limite de tiempo.\n" +
      "Los " + totalLeads + " negocios procesados ya estan guardados.";
  }

  ui.alert("✅ Busqueda Completada", summaryMsg, ui.ButtonSet.OK);
}

// ============================================================
// RAPIDAPI - LOCAL BUSINESS DATA
// ============================================================

/**
 * Busca negocios usando RapidAPI Local Business Data /search endpoint.
 * Una sola llamada devuelve: nombre, telefono, email, website, rating, direccion, etc.
 *
 * @param {string} industry - Tipo de negocio
 * @param {string} location - Ciudad, Estado
 * @param {number} limit - Maximo de resultados
 * @returns {{ results: Array, error: string|null }}
 */
function searchBusinesses(industry, location, limit) {
  var query = industry + " in " + location;
  var url = "https://" + RAPIDAPI_HOST + "/search"
    + "?query=" + encodeURIComponent(query)
    + "&limit=" + (limit || MAX_RESULTS)
    + "&extract_emails_and_contacts=true"
    + "&language=en"
    + "&region=us";

  try {
    var response = UrlFetchApp.fetch(url, {
      method: "get",
      headers: {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
      },
      muteHttpExceptions: true
    });

    var httpCode = response.getResponseCode();

    if (httpCode === 403) {
      return { results: [], error: "RapidAPI Key rechazada (403). Verifica que tu key es valida y que estas suscrito a 'Local Business Data' en rapidapi.com" };
    }

    if (httpCode === 429) {
      return { results: [], error: "Rate limit excedido (429). Espera un momento e intenta de nuevo." };
    }

    if (httpCode !== 200) {
      var body = response.getContentText().substring(0, 500);
      return { results: [], error: "HTTP " + httpCode + ": " + body };
    }

    var data = JSON.parse(response.getContentText());

    if (data.status === "OK" && data.data && data.data.length > 0) {
      return { results: data.data, error: null };
    }

    if (data.status && data.status !== "OK") {
      return { results: [], error: "API devolvio status: " + data.status + " - " + (data.message || "") };
    }

    // Status OK pero sin data
    return { results: [], error: null };

  } catch (e) {
    return { results: [], error: "Error de conexion: " + e.message };
  }
}

/**
 * Obtiene reviews de un negocio via RapidAPI /business-reviews endpoint.
 *
 * @param {string} businessId - Business ID del resultado de search
 * @returns {Array} Lista de reviews
 */
function getBusinessReviews(businessId) {
  var url = "https://" + RAPIDAPI_HOST + "/business-reviews"
    + "?business_id=" + encodeURIComponent(businessId)
    + "&limit=" + MAX_REVIEWS_PER_BUSINESS
    + "&sort_by=most_relevant"
    + "&region=us"
    + "&language=en";

  try {
    var response = UrlFetchApp.fetch(url, {
      method: "get",
      headers: {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
      },
      muteHttpExceptions: true
    });

    if (response.getResponseCode() !== 200) {
      return [];
    }

    var data = JSON.parse(response.getContentText());

    if (data.status === "OK" && data.data && data.data.length > 0) {
      return data.data;
    }

    return [];

  } catch (e) {
    Logger.log("Error getting reviews for " + businessId + ": " + e.message);
    return [];
  }
}

/**
 * Mapea un resultado de RapidAPI search a nuestro formato de lead.
 *
 * @param {Object} biz - Objeto de negocio de RapidAPI
 * @returns {Object} Lead formateado
 */
function mapBusinessToLead(biz) {
  // Extraer primer email valido
  var email = "";
  if (biz.emails_and_contacts && biz.emails_and_contacts.emails) {
    var emails = biz.emails_and_contacts.emails;
    if (emails.length > 0) {
      email = emails[0];
    }
  }

  // Extraer redes sociales
  var socialLinks = [];
  if (biz.emails_and_contacts) {
    var ec = biz.emails_and_contacts;
    if (ec.facebook) socialLinks.push("FB: " + ec.facebook);
    if (ec.instagram) socialLinks.push("IG: " + ec.instagram);
    if (ec.linkedin) socialLinks.push("LI: " + ec.linkedin);
    if (ec.twitter) socialLinks.push("TW: " + ec.twitter);
  }

  // Detectar tipo de negocio
  var businessType = "";
  if (biz.subtypes && biz.subtypes.length > 0) {
    businessType = biz.subtypes[0];
  } else if (biz.types && biz.types.length > 0) {
    businessType = biz.types[0];
  } else if (biz.type) {
    businessType = biz.type;
  }

  return {
    name: biz.name || "",
    email: email,
    phone: biz.phone_number || "",
    address: biz.full_address || "",
    website: biz.website || "",
    rating: biz.rating || 0,
    reviewCount: biz.review_count || 0,
    businessType: businessType,
    painScore: 0,
    painSummary: "",
    painReviews: "",
    socialLinks: socialLinks.join(" | "),
    mapsUrl: biz.place_link || "",
    placeId: biz.place_id || biz.business_id || ""
  };
}

// ============================================================
// ANALISIS DE PAIN POINTS EN REVIEWS
// ============================================================

/**
 * Analiza reviews buscando keywords de dolor/mala comunicacion.
 * Usa las reviews completas de RapidAPI (no limitado a 5 como Google Places).
 */
function analyzeReviewsForPain(reviews) {
  var painReviews = [];
  var keywordCounts = {};
  var totalNegativeReviews = 0;

  for (var i = 0; i < reviews.length; i++) {
    var reviewText = (reviews[i].review_text || reviews[i].text || "").toLowerCase();
    var reviewRating = reviews[i].rating || 5;

    if (reviewRating > 3) continue;
    totalNegativeReviews++;

    var foundKeywords = [];
    for (var j = 0; j < PAIN_KEYWORDS.length; j++) {
      if (reviewText.indexOf(PAIN_KEYWORDS[j].toLowerCase()) >= 0) {
        foundKeywords.push(PAIN_KEYWORDS[j]);
        keywordCounts[PAIN_KEYWORDS[j]] = (keywordCounts[PAIN_KEYWORDS[j]] || 0) + 1;
      }
    }

    if (foundKeywords.length > 0) {
      var rawText = reviews[i].review_text || reviews[i].text || "";
      var snippet = rawText.substring(0, 100);
      if (rawText.length > 100) snippet += "...";
      painReviews.push("⭐" + reviewRating + ": " + snippet);
    }
  }

  var totalReviews = reviews.length;
  var painCount = painReviews.length;
  var score = 0;

  if (totalReviews > 0 && painCount > 0) {
    var uniqueKeywords = Object.keys(keywordCounts).length;
    var baseScore = totalNegativeReviews > 0 ? painCount / totalNegativeReviews : 0;
    var diversityBonus = Math.min(0.2, uniqueKeywords * 0.05);
    // RapidAPI da mas reviews, asi que el penalty es menor
    var samplePenalty = totalReviews < 10 ? 0.85 : 1.0;

    score = Math.min(1, (baseScore * 0.6 + diversityBonus + painCount * 0.05) * samplePenalty);
    score = Math.round(score * 100) / 100;
  }

  var summary = "";
  if (painCount > 0) {
    var topKeywords = Object.keys(keywordCounts)
      .sort(function(a, b) { return keywordCounts[b] - keywordCounts[a]; })
      .slice(0, 3);
    summary = painCount + "/" + totalReviews + " reviews con quejas: " + topKeywords.join(", ");
  }

  return {
    score: score,
    summary: summary,
    painReviews: painReviews.slice(0, 5)
  };
}

// ============================================================
// ESCRITURA EN SHEET (INCREMENTAL + SORT)
// ============================================================

function getOrCreateTab(spreadsheet, tabName) {
  var sheet = spreadsheet.getSheetByName(tabName);

  if (sheet) {
    sheet.clear();
  } else {
    sheet = spreadsheet.insertSheet(tabName);
  }

  return sheet;
}

function writeHeaders(sheet) {
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);

  var headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
  headerRange.setFontWeight("bold");
  headerRange.setBackground("#1a73e8");
  headerRange.setFontColor("#ffffff");
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);
}

/**
 * Escribe UN lead en una fila.
 * Verde si tiene email, amarillo si pain alto.
 */
function writeLeadRow(sheet, row, lead) {
  var rowData = [
    lead.name,
    lead.email,
    lead.phone,
    lead.address,
    lead.website,
    lead.rating ? lead.rating.toFixed(1) : "",
    lead.reviewCount || "",
    lead.businessType,
    lead.painScore ? lead.painScore.toFixed(2) : "",
    lead.painSummary,
    lead.painReviews,
    lead.socialLinks || "",
    lead.mapsUrl,
    lead.placeId
  ];

  sheet.getRange(row, 1, 1, HEADERS.length).setValues([rowData]);

  if (lead.email) {
    sheet.getRange(row, 1, 1, HEADERS.length).setBackground("#e6f4ea");
  }

  if (lead.painScore >= 0.3) {
    sheet.getRange(row, 9).setBackground("#fef7e0");
    sheet.getRange(row, 9).setFontWeight("bold");
  }
}

/**
 * Ordena: emails primero, luego por rating.
 */
function sortAndFormatSheet(sheet, totalLeads) {
  var numCols = HEADERS.length;
  var dataRange = sheet.getRange(2, 1, totalLeads, numCols);

  dataRange.sort([
    {column: 2, ascending: false},
    {column: 6, ascending: false}
  ]);

  var values = dataRange.getValues();
  var backgrounds = [];
  var painWeights = [];

  for (var i = 0; i < values.length; i++) {
    var rowBg = [];
    for (var j = 0; j < numCols; j++) {
      rowBg.push("#ffffff");
    }

    var email = values[i][1];
    var painScoreStr = values[i][8];

    if (email) {
      for (var j = 0; j < numCols; j++) {
        rowBg[j] = "#e6f4ea";
      }
    }

    if (painScoreStr) {
      var pv = parseFloat(painScoreStr);
      if (pv >= 0.3) {
        rowBg[8] = "#fef7e0";
      }
    }

    backgrounds.push(rowBg);

    if (painScoreStr && parseFloat(painScoreStr) >= 0.3) {
      painWeights.push(["bold"]);
    } else {
      painWeights.push(["normal"]);
    }
  }

  dataRange.setBackgrounds(backgrounds);
  sheet.getRange(2, 9, totalLeads, 1).setFontWeights(painWeights);

  sheet.autoResizeColumns(1, 8);
  sheet.setColumnWidth(10, 250);
  sheet.setColumnWidth(11, 200);
  sheet.setColumnWidth(12, 250);
  sheet.setColumnWidth(13, 200);
}

function formatSheet(sheet, totalRows) {
  try {
    sheet.autoResizeColumns(1, 8);
    sheet.setColumnWidth(10, 250);
    sheet.setColumnWidth(11, 200);
    sheet.setColumnWidth(12, 250);
    sheet.setColumnWidth(13, 200);
  } catch (e) {
    Logger.log("Error formatting sheet: " + e.message);
  }
}

// ============================================================
// UTILIDADES
// ============================================================

function sanitizeTabName(name) {
  return name.replace(/[\[\]*\/?:\\]/g, "").substring(0, 100).trim();
}

function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Google Apps Script - Business Leads Finder
 *
 * Busca negocios usando Google Places API directamente desde tu Google Sheet.
 * Crea una pestana nueva por cada busqueda (industria + ciudad).
 *
 * SETUP:
 *   1. En tu Google Sheet: Extensiones -> Apps Script
 *   2. Pega todo este codigo
 *   3. En la linea de API_KEY abajo, pon tu Google Places API Key
 *   4. Guarda (Ctrl+S)
 *   5. Regresa a la Sheet -> veras el menu "Lead Finder" arriba
 *   6. La primera vez te pedira permisos - acepta todo
 *
 * IMPORTANTE: Tu API Key debe tener habilitado "Places API" en Google Cloud Console
 */

// ============================================================
// CONFIGURACION - Cambia esto
// ============================================================
const API_KEY = "TU_GOOGLE_PLACES_API_KEY_AQUI";

// Maximo de negocios a buscar por busqueda (max 60, va de 20 en 20)
const MAX_RESULTS = 60;

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

// Headers de la tabla
const HEADERS = [
  "Negocio",
  "Email",
  "Telefono",
  "Direccion",
  "Website",
  "Rating",
  "Reviews",
  "Tipo de Negocio",
  "Pain Score",
  "Resumen de Pain Points",
  "Reviews con Dolor",
  "Google Maps URL",
  "Place ID"
];

// ============================================================
// MENU PERSONALIZADO
// ============================================================

/**
 * Crea el menu "Lead Finder" cuando abres la Sheet
 */
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
// DIALOGOS DE BUSQUEDA
// ============================================================

/**
 * Muestra el popup para que el usuario escriba industria y ciudad
 */
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

/**
 * Busqueda rapida sin analisis de reviews (mas rapido, menos API calls)
 */
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
// LOGICA PRINCIPAL
// ============================================================

/**
 * Busca negocios y los escribe en una pestana nueva
 *
 * @param {string} industry - Tipo de negocio
 * @param {string} location - Ciudad, Estado
 * @param {boolean} analyzeReviews - Si analizar reviews para pain points
 */
function searchAndWrite(industry, location, analyzeReviews) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ui = SpreadsheetApp.getUi();

  // Verificar API Key
  if (API_KEY === "TU_GOOGLE_PLACES_API_KEY_AQUI" || !API_KEY) {
    ui.alert("⚠️ Error", "Configura tu API_KEY en el codigo del script.\n\nExtensiones -> Apps Script -> Cambia la linea de API_KEY", ui.ButtonSet.OK);
    return;
  }

  ss.toast("Buscando " + industry + " en " + location + "...", "🔍 Buscando", -1);

  // Paso 1: Buscar negocios
  var places = searchPlaces(industry, location);

  if (places.length === 0) {
    ui.alert("No se encontraron negocios para '" + industry + "' en '" + location + "'");
    return;
  }

  ss.toast("Encontrados " + places.length + " negocios. Obteniendo detalles...", "📋 Procesando", -1);

  // Paso 2: Obtener detalles de cada negocio
  var leads = [];
  for (var i = 0; i < places.length; i++) {
    ss.toast("Procesando " + (i + 1) + " de " + places.length + "...", "📋 Detalles", -1);

    var details = getPlaceDetails(places[i].place_id, analyzeReviews);
    if (details) {
      leads.push(details);
    }

    // Pausa para no exceder rate limits
    if (i % 10 === 9) {
      Utilities.sleep(1000);
    }
  }

  if (leads.length === 0) {
    ui.alert("No se pudieron obtener detalles de los negocios");
    return;
  }

  // Paso 3: Ordenar - los que tienen email primero, luego por rating
  leads.sort(function(a, b) {
    if (a.email && !b.email) return -1;
    if (!a.email && b.email) return 1;
    return (b.rating || 0) - (a.rating || 0);
  });

  // Paso 4: Escribir en nueva pestana
  var tabName = capitalizeFirst(industry) + " - " + location;
  tabName = sanitizeTabName(tabName);

  var sheet = getOrCreateTab(ss, tabName);
  writeLeadsToSheet(sheet, leads);

  // Activar la pestana nueva
  ss.setActiveSheet(sheet);

  // Resumen
  var emailCount = leads.filter(function(l) { return l.email; }).length;
  var phoneCount = leads.filter(function(l) { return l.phone; }).length;
  var painCount = leads.filter(function(l) { return l.painScore > 0; }).length;

  ss.toast("", "✅ Completado", 1);
  ui.alert(
    "✅ Busqueda Completada",
    "Pestana: " + tabName + "\n" +
    "Negocios: " + leads.length + "\n" +
    "Con email: " + emailCount + "\n" +
    "Con telefono: " + phoneCount + "\n" +
    (analyzeReviews ? "Con pain points: " + painCount + "\n" : "") +
    "\nLos resultados estan en la pestana '" + tabName + "'",
    ui.ButtonSet.OK
  );
}

// ============================================================
// GOOGLE PLACES API
// ============================================================

/**
 * Busca negocios usando Places Text Search API
 * Devuelve hasta MAX_RESULTS resultados (paginado de 20 en 20)
 */
function searchPlaces(industry, location) {
  var allResults = [];
  var query = industry + " in " + location;
  var url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    + "?query=" + encodeURIComponent(query)
    + "&key=" + API_KEY;

  try {
    // Primera pagina (hasta 20 resultados)
    var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    var data = JSON.parse(response.getContentText());

    if (data.status !== "OK") {
      Logger.log("Places API error: " + data.status + " - " + (data.error_message || ""));
      if (data.status === "REQUEST_DENIED") {
        SpreadsheetApp.getUi().alert(
          "⚠️ API Error",
          "Tu API Key no tiene acceso a Places API.\n\n" +
          "Ve a Google Cloud Console -> APIs & Services -> Enable 'Places API'",
          SpreadsheetApp.getUi().ButtonSet.OK
        );
      }
      return [];
    }

    allResults = allResults.concat(data.results);

    // Paginas 2 y 3 (hasta 60 total)
    var nextPageToken = data.next_page_token;
    var page = 1;

    while (nextPageToken && allResults.length < MAX_RESULTS && page < 3) {
      // Google requiere ~2 segundos entre paginas
      Utilities.sleep(2000);

      var nextUrl = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        + "?pagetoken=" + nextPageToken
        + "&key=" + API_KEY;

      var nextResponse = UrlFetchApp.fetch(nextUrl, { muteHttpExceptions: true });
      var nextData = JSON.parse(nextResponse.getContentText());

      if (nextData.status === "OK") {
        allResults = allResults.concat(nextData.results);
        nextPageToken = nextData.next_page_token;
      } else {
        break;
      }
      page++;
    }

  } catch (e) {
    Logger.log("Error searching places: " + e.message);
  }

  return allResults;
}

/**
 * Obtiene detalles completos de un negocio por Place ID
 * Incluye: telefono, website, email (del website), reviews
 */
function getPlaceDetails(placeId, analyzeReviews) {
  var fields = "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,url,types,business_status";
  if (analyzeReviews) {
    fields += ",reviews";
  }

  var url = "https://maps.googleapis.com/maps/api/place/details/json"
    + "?place_id=" + placeId
    + "&fields=" + fields
    + "&key=" + API_KEY;

  try {
    var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    var data = JSON.parse(response.getContentText());

    if (data.status !== "OK" || !data.result) {
      return null;
    }

    var place = data.result;

    // Saltar negocios cerrados permanentemente
    if (place.business_status === "CLOSED_PERMANENTLY") {
      return null;
    }

    // Intentar extraer email del website
    var email = "";
    if (place.website) {
      email = extractEmailFromWebsite(place.website);
    }

    // Analizar reviews para pain points
    var painScore = 0;
    var painSummary = "";
    var painReviews = [];

    if (analyzeReviews && place.reviews && place.reviews.length > 0) {
      var painResult = analyzeReviewsForPain(place.reviews);
      painScore = painResult.score;
      painSummary = painResult.summary;
      painReviews = painResult.painReviews;
    }

    // Detectar tipo de negocio desde types
    var businessType = detectBusinessType(place.types || []);

    return {
      name: place.name || "",
      email: email,
      phone: place.formatted_phone_number || "",
      address: place.formatted_address || "",
      website: place.website || "",
      rating: place.rating || 0,
      reviewCount: place.user_ratings_total || 0,
      businessType: businessType,
      painScore: painScore,
      painSummary: painSummary,
      painReviews: painReviews.join(" | "),
      mapsUrl: place.url || "",
      placeId: placeId
    };

  } catch (e) {
    Logger.log("Error getting place details: " + e.message);
    return null;
  }
}

/**
 * Intenta extraer email de un website
 * Hace fetch de la pagina y busca patrones de email
 */
function extractEmailFromWebsite(websiteUrl) {
  try {
    var response = UrlFetchApp.fetch(websiteUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      validateHttpsCertificates: false,
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; LeadFinder/1.0)"
      }
    });

    if (response.getResponseCode() !== 200) return "";

    var html = response.getContentText();

    // Buscar emails con regex
    var emailRegex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
    var matches = html.match(emailRegex);

    if (!matches || matches.length === 0) return "";

    // Filtrar emails genericos/spam y devolver el mejor
    var validEmails = matches.filter(function(email) {
      var lower = email.toLowerCase();
      // Ignorar emails de imagenes, scripts, etc
      if (lower.match(/\.(png|jpg|gif|svg|css|js)$/)) return false;
      // Ignorar emails placeholder
      if (lower.indexOf("example.com") >= 0) return false;
      if (lower.indexOf("email.com") >= 0) return false;
      if (lower.indexOf("domain.com") >= 0) return false;
      if (lower.indexOf("sentry.io") >= 0) return false;
      if (lower.indexOf("wixpress.com") >= 0) return false;
      if (lower.indexOf("wordpress") >= 0) return false;
      return true;
    });

    if (validEmails.length === 0) return "";

    // Priorizar: info@, contact@, hello@ sobre otros
    var priority = ["info@", "contact@", "hello@", "office@", "admin@"];
    for (var i = 0; i < priority.length; i++) {
      for (var j = 0; j < validEmails.length; j++) {
        if (validEmails[j].toLowerCase().indexOf(priority[i]) === 0) {
          return validEmails[j].toLowerCase();
        }
      }
    }

    return validEmails[0].toLowerCase();

  } catch (e) {
    // Timeout o error de red - no pasa nada
    return "";
  }
}

// ============================================================
// ANALISIS DE PAIN POINTS EN REVIEWS
// ============================================================

/**
 * Analiza reviews buscando keywords de dolor/mala comunicacion
 * Devuelve pain score (0-1), resumen y lista de reviews con dolor
 */
function analyzeReviewsForPain(reviews) {
  var painReviews = [];
  var keywordCounts = {};

  for (var i = 0; i < reviews.length; i++) {
    var reviewText = (reviews[i].text || "").toLowerCase();
    var reviewRating = reviews[i].rating || 5;

    // Solo analizar reviews negativas (1-3 estrellas)
    if (reviewRating > 3) continue;

    var foundKeywords = [];
    for (var j = 0; j < PAIN_KEYWORDS.length; j++) {
      if (reviewText.indexOf(PAIN_KEYWORDS[j].toLowerCase()) >= 0) {
        foundKeywords.push(PAIN_KEYWORDS[j]);
        keywordCounts[PAIN_KEYWORDS[j]] = (keywordCounts[PAIN_KEYWORDS[j]] || 0) + 1;
      }
    }

    if (foundKeywords.length > 0) {
      // Tomar primeros 100 chars de la review
      var snippet = reviews[i].text.substring(0, 100);
      if (reviews[i].text.length > 100) snippet += "...";
      painReviews.push("⭐" + reviewRating + ": " + snippet);
    }
  }

  // Calcular pain score
  var totalReviews = reviews.length;
  var painCount = painReviews.length;
  var score = 0;

  if (totalReviews > 0 && painCount > 0) {
    score = Math.min(1, painCount / totalReviews + (painCount * 0.1));
    score = Math.round(score * 100) / 100;
  }

  // Generar resumen
  var summary = "";
  if (painCount > 0) {
    var topKeywords = Object.keys(keywordCounts)
      .sort(function(a, b) { return keywordCounts[b] - keywordCounts[a]; })
      .slice(0, 3);
    summary = painCount + " reviews con quejas: " + topKeywords.join(", ");
  }

  return {
    score: score,
    summary: summary,
    painReviews: painReviews.slice(0, 5) // Max 5 reviews
  };
}

// ============================================================
// ESCRIBIR EN LA SHEET
// ============================================================

/**
 * Obtiene una pestana existente o crea una nueva
 */
function getOrCreateTab(spreadsheet, tabName) {
  var sheet = null;

  try {
    sheet = spreadsheet.getSheetByName(tabName);
  } catch (e) {
    // No existe
  }

  if (sheet) {
    // Si ya existe, limpiarla
    sheet.clear();
  } else {
    sheet = spreadsheet.insertSheet(tabName);
  }

  return sheet;
}

/**
 * Escribe los leads en la pestana con formato
 */
function writeLeadsToSheet(sheet, leads) {
  // Headers
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);

  // Formato de headers
  var headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
  headerRange.setFontWeight("bold");
  headerRange.setBackground("#1a73e8");
  headerRange.setFontColor("#ffffff");
  headerRange.setHorizontalAlignment("center");

  // Datos
  if (leads.length === 0) return;

  var rows = leads.map(function(lead) {
    return [
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
      lead.mapsUrl,
      lead.placeId
    ];
  });

  sheet.getRange(2, 1, rows.length, HEADERS.length).setValues(rows);

  // Formato condicional: resaltar filas con email en verde claro
  for (var i = 0; i < leads.length; i++) {
    if (leads[i].email) {
      sheet.getRange(i + 2, 1, 1, HEADERS.length).setBackground("#e6f4ea");
    }
  }

  // Formato condicional: resaltar pain score alto en amarillo
  for (var i = 0; i < leads.length; i++) {
    if (leads[i].painScore >= 0.3) {
      sheet.getRange(i + 2, 9).setBackground("#fef7e0");
      sheet.getRange(i + 2, 9).setFontWeight("bold");
    }
  }

  // Auto-resize columnas principales
  sheet.autoResizeColumns(1, 8);

  // Congelar header
  sheet.setFrozenRows(1);

  // Ajustar ancho de columnas de texto largo
  sheet.setColumnWidth(10, 250); // Pain summary
  sheet.setColumnWidth(11, 200); // Pain reviews
  sheet.setColumnWidth(12, 200); // Maps URL
}

// ============================================================
// UTILIDADES
// ============================================================

/**
 * Limpia nombre de pestana (Google Sheets no permite ciertos caracteres)
 */
function sanitizeTabName(name) {
  return name.replace(/[\[\]*\/?:\\]/g, "").substring(0, 100).trim();
}

/**
 * Primera letra en mayuscula
 */
function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Detecta el tipo de negocio desde los types de Google Places
 */
function detectBusinessType(types) {
  var typeMap = {
    "dentist": "Dentist",
    "doctor": "Doctor",
    "lawyer": "Lawyer",
    "accounting": "Accountant",
    "plumber": "Plumber",
    "electrician": "Electrician",
    "real_estate_agency": "Real Estate",
    "car_repair": "Auto Repair",
    "veterinary_care": "Veterinarian",
    "restaurant": "Restaurant",
    "hair_care": "Salon",
    "beauty_salon": "Salon",
    "hospital": "Medical",
    "pharmacy": "Pharmacy",
    "roofing_contractor": "Roofing",
    "general_contractor": "Contractor",
    "moving_company": "Moving",
    "insurance_agency": "Insurance",
    "locksmith": "Locksmith"
  };

  for (var i = 0; i < types.length; i++) {
    if (typeMap[types[i]]) {
      return typeMap[types[i]];
    }
  }

  return types.length > 0 ? types[0].replace(/_/g, " ") : "";
}

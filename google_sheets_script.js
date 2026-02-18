/**
 * Google Apps Script - Business Leads Finder (v2 - All Issues Fixed)
 *
 * Busca negocios usando Google Places API directamente desde tu Google Sheet.
 * Crea una pestana nueva por cada busqueda (industria + ciudad).
 *
 * FIXES en v2:
 *   - Escritura incremental (no pierdes datos si se corta el script)
 *   - Control de tiempo (se detiene antes del limite de 6 min)
 *   - SpreadsheetApp.flush() periodico para guardar datos en caso de crash
 *   - Busca emails en /contact y /contact-us ademas de homepage
 *   - Filtra emails basura (noreply, hosting providers, etc.)
 *   - Busca mailto: links primero (mas confiable que regex general)
 *   - Reintento automatico en llamadas API fallidas
 *   - Pain score ajustado para la limitacion de 5 reviews de Google
 *   - Manejo de OVER_QUERY_LIMIT con backoff
 *   - Resumen final indica muestra limitada de reviews
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

// Limite de tiempo: 5 min (deja 1 min de buffer antes del limite duro de 6 min)
const MAX_RUNTIME_MS = 5 * 60 * 1000;

// Si queda menos de este tiempo, salta la extraccion de email (que es lo mas lento)
const MIN_TIME_FOR_EMAIL_MS = 90 * 1000;

// Cada cuantas filas hacer flush() para guardar datos parciales
const FLUSH_EVERY_N_ROWS = 5;

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

// Dominios de email a ignorar (hosting, plataformas, etc.)
const EMAIL_BLACKLIST_DOMAINS = [
  "wixpress.com", "wix.com", "wordpress.com", "wordpress.org",
  "squarespace.com", "godaddy.com", "googleapis.com",
  "google.com", "facebook.com", "twitter.com", "instagram.com",
  "sentry.io", "example.com", "email.com", "domain.com",
  "shopify.com", "mailchimp.com", "hubspot.com", "weebly.com",
  "jimdo.com", "website.com", "test.com", "localhost",
  "yourdomain.com", "company.com", "yourcompany.com"
];

// Prefijos de email a ignorar (no-reply, system accounts, etc.)
const EMAIL_BLACKLIST_PREFIXES = [
  "noreply", "no-reply", "no.reply",
  "donotreply", "do-not-reply", "do.not.reply",
  "mailer-daemon", "postmaster", "webmaster", "hostmaster",
  "abuse", "root", "daemon", "nobody",
  "billing@squarespace", "support@godaddy", "support@shopify",
  "support@wix", "admin@wix"
];

// Rutas de paginas de contacto a intentar si no se encuentra email en homepage
const CONTACT_PATHS = ["/contact", "/contact-us"];

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
 * Busca negocios y los escribe INCREMENTALMENTE en una pestana nueva.
 * Cada lead se escribe en la sheet inmediatamente despues de procesarse.
 * Se detiene antes del limite de 6 minutos para no perder datos.
 *
 * @param {string} industry - Tipo de negocio
 * @param {string} location - Ciudad, Estado
 * @param {boolean} analyzeReviews - Si analizar reviews para pain points
 */
function searchAndWrite(industry, location, analyzeReviews) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ui = SpreadsheetApp.getUi();
  var startTime = new Date().getTime();

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

  ss.toast("Encontrados " + places.length + " negocios. Preparando hoja...", "📋 Procesando", -1);

  // Paso 2: Crear pestana y escribir headers ANTES de procesar
  var tabName = capitalizeFirst(industry) + " - " + location;
  tabName = sanitizeTabName(tabName);
  var sheet = getOrCreateTab(ss, tabName);
  writeHeaders(sheet);
  ss.setActiveSheet(sheet);
  SpreadsheetApp.flush();

  // Paso 3: Procesar cada negocio y escribir INMEDIATAMENTE
  var currentRow = 2;
  var emailCount = 0;
  var phoneCount = 0;
  var painCount = 0;
  var skippedEmails = 0;
  var stoppedEarly = false;

  for (var i = 0; i < places.length; i++) {
    var elapsed = new Date().getTime() - startTime;

    // Si queda menos de 30 segundos, parar para no perder datos
    if (elapsed > MAX_RUNTIME_MS) {
      stoppedEarly = true;
      Logger.log("Detenido por limite de tiempo en negocio " + (i + 1) + " de " + places.length);
      break;
    }

    // Decidir si intentar extraer email (consume mucho tiempo)
    var timeRemaining = MAX_RUNTIME_MS - elapsed;
    var skipEmail = timeRemaining < MIN_TIME_FOR_EMAIL_MS;
    if (skipEmail) skippedEmails++;

    ss.toast(
      "Procesando " + (i + 1) + " de " + places.length +
      (skipEmail ? " (sin email - poco tiempo)" : "") +
      " | " + Math.round(elapsed / 1000) + "s",
      "📋 Detalles", -1
    );

    var details = getPlaceDetails(places[i].place_id, analyzeReviews, skipEmail);
    if (details) {
      // Escribir inmediatamente a la sheet
      writeLeadRow(sheet, currentRow, details);

      if (details.email) emailCount++;
      if (details.phone) phoneCount++;
      if (details.painScore > 0) painCount++;
      currentRow++;

      // Flush periodicamente para garantizar que los datos se guardan
      if ((currentRow - 2) % FLUSH_EVERY_N_ROWS === 0) {
        SpreadsheetApp.flush();
      }
    }

    // Pausa para rate limits
    if (i % 5 === 4) {
      Utilities.sleep(500);
    }
  }

  // Paso 4: Formato final
  var totalLeads = currentRow - 2;
  if (totalLeads > 0) {
    formatSheet(sheet, totalLeads);
  }
  SpreadsheetApp.flush();

  // Paso 5: Resumen
  ss.toast("", "✅ Completado", 1);

  var summaryMsg =
    "Pestana: " + tabName + "\n" +
    "Negocios procesados: " + totalLeads + " de " + places.length + "\n" +
    "Con email: " + emailCount + "\n" +
    "Con telefono: " + phoneCount + "\n";

  if (analyzeReviews) {
    summaryMsg += "Con pain points: " + painCount + "\n";
    summaryMsg += "\n⚠️ Nota: Google solo da 5 reviews por negocio.\nLos pain scores son aproximados.\n";
  }

  if (stoppedEarly) {
    summaryMsg += "\n⏱️ Se detuvo antes del limite de tiempo.\n" +
      "Los " + totalLeads + " negocios procesados ya estan guardados.\n" +
      "Puedes volver a buscar para obtener los restantes.";
  }

  if (skippedEmails > 0) {
    summaryMsg += "\n📧 " + skippedEmails + " negocios sin buscar email (por tiempo).";
  }

  ui.alert("✅ Busqueda Completada", summaryMsg, ui.ButtonSet.OK);
}

// ============================================================
// GOOGLE PLACES API
// ============================================================

/**
 * Busca negocios usando Places Text Search API.
 * Devuelve hasta MAX_RESULTS resultados (paginado de 20 en 20).
 * Incluye reintentos y manejo de OVER_QUERY_LIMIT.
 */
function searchPlaces(industry, location) {
  var allResults = [];
  var query = industry + " in " + location;
  var url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    + "?query=" + encodeURIComponent(query)
    + "&key=" + API_KEY;

  try {
    // Primera pagina (hasta 20 resultados)
    var response = fetchWithRetry(url);
    if (!response) return [];

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
      if (data.status === "OVER_QUERY_LIMIT") {
        SpreadsheetApp.getUi().alert(
          "⚠️ Rate Limit",
          "Excediste el limite de requests de Google.\n" +
          "Espera unos minutos e intenta de nuevo.",
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

      var nextResponse = fetchWithRetry(nextUrl);
      if (!nextResponse) break;

      var nextData = JSON.parse(nextResponse.getContentText());

      if (nextData.status === "OK") {
        allResults = allResults.concat(nextData.results);
        nextPageToken = nextData.next_page_token;
      } else if (nextData.status === "OVER_QUERY_LIMIT") {
        // Esperar mas y reintentar una vez
        Logger.log("Rate limit en pagina " + (page + 1) + ", esperando 5 segundos...");
        Utilities.sleep(5000);
        nextResponse = fetchWithRetry(nextUrl);
        if (nextResponse) {
          nextData = JSON.parse(nextResponse.getContentText());
          if (nextData.status === "OK") {
            allResults = allResults.concat(nextData.results);
            nextPageToken = nextData.next_page_token;
          } else {
            break;
          }
        } else {
          break;
        }
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
 * Obtiene detalles completos de un negocio por Place ID.
 * Incluye reintentos y manejo de OVER_QUERY_LIMIT.
 *
 * @param {string} placeId - Google Place ID
 * @param {boolean} analyzeReviews - Si pedir reviews
 * @param {boolean} skipEmail - Si saltar extraccion de email (por tiempo)
 */
function getPlaceDetails(placeId, analyzeReviews, skipEmail) {
  var fields = "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,url,types,business_status";
  if (analyzeReviews) {
    fields += ",reviews";
  }

  var url = "https://maps.googleapis.com/maps/api/place/details/json"
    + "?place_id=" + placeId
    + "&fields=" + fields
    + "&key=" + API_KEY;

  try {
    var response = fetchWithRetry(url);
    if (!response) return null;

    var data = JSON.parse(response.getContentText());

    // Manejo de rate limit
    if (data.status === "OVER_QUERY_LIMIT") {
      Logger.log("Rate limit en Place Details para " + placeId + ", esperando 5s...");
      Utilities.sleep(5000);
      response = fetchWithRetry(url);
      if (!response) return null;
      data = JSON.parse(response.getContentText());
    }

    if (data.status !== "OK" || !data.result) {
      return null;
    }

    var place = data.result;

    // Saltar negocios cerrados permanentemente
    if (place.business_status === "CLOSED_PERMANENTLY") {
      return null;
    }

    // Extraer email del website (si hay tiempo)
    var email = "";
    if (!skipEmail && place.website) {
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
    Logger.log("Error getting place details for " + placeId + ": " + e.message);
    return null;
  }
}

// ============================================================
// EXTRACCION DE EMAIL (MEJORADA)
// ============================================================

/**
 * Intenta extraer email de un website.
 * 1. Busca en la homepage
 * 2. Si no encuentra, busca en /contact y /contact-us
 */
function extractEmailFromWebsite(websiteUrl) {
  // Intentar homepage primero
  var email = extractEmailFromPage(websiteUrl);
  if (email) return email;

  // Si no encontro, intentar paginas de contacto
  var baseUrl = getBaseUrl(websiteUrl);
  for (var i = 0; i < CONTACT_PATHS.length; i++) {
    email = extractEmailFromPage(baseUrl + CONTACT_PATHS[i]);
    if (email) return email;
  }

  return "";
}

/**
 * Extrae email de una URL especifica.
 * Busca primero en mailto: links (mas confiable), luego regex general.
 * Filtra emails basura y prioriza emails de contacto.
 */
function extractEmailFromPage(pageUrl) {
  try {
    var response = UrlFetchApp.fetch(pageUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      validateHttpsCertificates: false,
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      }
    });

    var code = response.getResponseCode();
    if (code !== 200) return "";

    var html = response.getContentText();

    // Limitar a 500KB para no perder tiempo con paginas enormes
    if (html.length > 500000) {
      html = html.substring(0, 500000);
    }

    // Paso 1: Buscar en mailto: links (mas confiable que regex general)
    var mailtoRegex = /mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})/gi;
    var mailtoMatches = html.match(mailtoRegex);
    if (mailtoMatches) {
      for (var i = 0; i < mailtoMatches.length; i++) {
        var mailtoEmail = mailtoMatches[i].replace(/^mailto:/i, "").toLowerCase();
        if (isValidLeadEmail(mailtoEmail)) return mailtoEmail;
      }
    }

    // Paso 2: Regex general
    var emailRegex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
    var matches = html.match(emailRegex);
    if (!matches || matches.length === 0) return "";

    // Filtrar y recoger emails validos
    var validEmails = [];
    for (var i = 0; i < matches.length; i++) {
      var em = matches[i].toLowerCase();
      if (isValidLeadEmail(em) && validEmails.indexOf(em) === -1) {
        validEmails.push(em);
      }
    }

    if (validEmails.length === 0) return "";

    // Priorizar emails de contacto sobre genericos
    var priority = [
      "info@", "contact@", "hello@", "office@",
      "appointments@", "scheduling@", "front@", "reception@",
      "inquiries@", "sales@"
    ];
    for (var i = 0; i < priority.length; i++) {
      for (var j = 0; j < validEmails.length; j++) {
        if (validEmails[j].indexOf(priority[i]) === 0) {
          return validEmails[j];
        }
      }
    }

    return validEmails[0];

  } catch (e) {
    // Timeout o error de red - no pasa nada, seguir con el siguiente
    return "";
  }
}

/**
 * Valida que un email sea util para un lead (no basura/sistema/hosting)
 */
function isValidLeadEmail(email) {
  email = email.toLowerCase();

  // Ignorar extensiones de archivo que regex confunde con emails
  if (email.match(/\.(png|jpg|jpeg|gif|svg|css|js|webp|ico|woff|woff2|ttf|eot|pdf|zip)$/)) return false;

  // Ignorar dominios blacklisted
  for (var i = 0; i < EMAIL_BLACKLIST_DOMAINS.length; i++) {
    if (email.indexOf("@" + EMAIL_BLACKLIST_DOMAINS[i]) >= 0) return false;
    if (email.indexOf("." + EMAIL_BLACKLIST_DOMAINS[i]) >= 0) return false;
  }

  // Ignorar prefijos blacklisted
  for (var i = 0; i < EMAIL_BLACKLIST_PREFIXES.length; i++) {
    if (email.indexOf(EMAIL_BLACKLIST_PREFIXES[i]) === 0) return false;
  }

  // Ignorar emails auto-generados (5+ digitos antes del @)
  if (email.match(/^[0-9a-f]{5,}@/)) return false;

  // Ignorar emails que son claramente de pixeles de tracking
  if (email.match(/@.*tracking/)) return false;
  if (email.match(/@.*pixel/)) return false;

  return true;
}

/**
 * Obtiene la URL base de un website (protocolo + dominio, sin path)
 */
function getBaseUrl(url) {
  url = url.replace(/\/+$/, "");
  var match = url.match(/^(https?:\/\/[^\/]+)/);
  return match ? match[1] : url;
}

// ============================================================
// ANALISIS DE PAIN POINTS EN REVIEWS
// ============================================================

/**
 * Analiza reviews buscando keywords de dolor/mala comunicacion.
 *
 * IMPORTANTE: Google Places API solo devuelve MAX 5 reviews por negocio.
 * El pain score se ajusta para esta limitacion con un penalty de muestra pequena.
 *
 * Devuelve: { score: 0-1, summary: string, painReviews: string[] }
 */
function analyzeReviewsForPain(reviews) {
  var painReviews = [];
  var keywordCounts = {};
  var totalNegativeReviews = 0;

  for (var i = 0; i < reviews.length; i++) {
    var reviewText = (reviews[i].text || "").toLowerCase();
    var reviewRating = reviews[i].rating || 5;

    // Solo analizar reviews negativas (1-3 estrellas)
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
      var rawText = reviews[i].text || "";
      var snippet = rawText.substring(0, 100);
      if (rawText.length > 100) snippet += "...";
      painReviews.push("⭐" + reviewRating + ": " + snippet);
    }
  }

  // Calcular pain score AJUSTADO para muestra de 5 reviews
  //
  // Problema: Google solo da 5 reviews, asi que 1 pain review de 5
  // no es lo mismo que 100 pain reviews de 500.
  //
  // Formula ajustada:
  //   - Base: proporcion de pain reviews entre las NEGATIVAS (no el total)
  //   - Bonus: por variedad de keywords (mas tipos de queja = problema real)
  //   - Penalty: muestra < 10 reviews = menos confianza (x0.8)
  var totalReviews = reviews.length;
  var painCount = painReviews.length;
  var score = 0;

  if (totalReviews > 0 && painCount > 0) {
    var uniqueKeywords = Object.keys(keywordCounts).length;

    // Base: que % de reviews negativas tienen quejas de comunicacion
    var baseScore = totalNegativeReviews > 0 ? painCount / totalNegativeReviews : 0;

    // Bonus por variedad de keywords (cada keyword distinta suma 0.05, max 0.2)
    var diversityBonus = Math.min(0.2, uniqueKeywords * 0.05);

    // Penalty por muestra pequena (5 reviews es muy poco para estar seguro)
    var samplePenalty = totalReviews < 10 ? 0.8 : 1.0;

    score = Math.min(1, (baseScore * 0.6 + diversityBonus + painCount * 0.05) * samplePenalty);
    score = Math.round(score * 100) / 100;
  }

  // Resumen con nota sobre muestra limitada
  var summary = "";
  if (painCount > 0) {
    var topKeywords = Object.keys(keywordCounts)
      .sort(function(a, b) { return keywordCounts[b] - keywordCounts[a]; })
      .slice(0, 3);
    summary = painCount + "/" + totalReviews + " reviews con quejas: " + topKeywords.join(", ");
    summary += " (muestra: " + totalReviews + " de " + "max 5 reviews)";
  }

  return {
    score: score,
    summary: summary,
    painReviews: painReviews.slice(0, 5)
  };
}

// ============================================================
// ESCRITURA EN SHEET (INCREMENTAL)
// ============================================================

/**
 * Obtiene una pestana existente o crea una nueva.
 * getSheetByName devuelve null si no existe (no tira error).
 */
function getOrCreateTab(spreadsheet, tabName) {
  var sheet = spreadsheet.getSheetByName(tabName);

  if (sheet) {
    sheet.clear();
  } else {
    sheet = spreadsheet.insertSheet(tabName);
  }

  return sheet;
}

/**
 * Escribe los headers con formato en la primera fila
 */
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
 * Escribe UN lead en una fila especifica (escritura incremental).
 * Aplica colores inmediatamente: verde si tiene email, amarillo si pain alto.
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
    lead.mapsUrl,
    lead.placeId
  ];

  sheet.getRange(row, 1, 1, HEADERS.length).setValues([rowData]);

  // Verde claro si tiene email
  if (lead.email) {
    sheet.getRange(row, 1, 1, HEADERS.length).setBackground("#e6f4ea");
  }

  // Amarillo si pain score alto
  if (lead.painScore >= 0.3) {
    sheet.getRange(row, 9).setBackground("#fef7e0");
    sheet.getRange(row, 9).setFontWeight("bold");
  }
}

/**
 * Aplica formato final a la hoja (columnas, anchos)
 */
function formatSheet(sheet, totalRows) {
  try {
    sheet.autoResizeColumns(1, 8);
    sheet.setColumnWidth(10, 250); // Pain summary
    sheet.setColumnWidth(11, 200); // Pain reviews
    sheet.setColumnWidth(12, 200); // Maps URL
  } catch (e) {
    Logger.log("Error formatting sheet: " + e.message);
  }
}

// ============================================================
// UTILIDADES
// ============================================================

/**
 * HTTP fetch con reintentos automaticos.
 * Reintenta hasta 2 veces con backoff exponencial en errores de servidor (5xx).
 * No reintenta en errores de cliente (4xx) porque esos no se arreglan solos.
 *
 * @param {string} url - URL a fetch
 * @param {number} maxRetries - Numero de reintentos (default: 2)
 * @returns {HTTPResponse|null} - Respuesta o null si todos los intentos fallaron
 */
function fetchWithRetry(url, maxRetries) {
  maxRetries = maxRetries || 2;

  for (var attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
      var code = response.getResponseCode();

      // Exito o error de API (no de red/servidor) -> devolver
      if (code < 500) {
        return response;
      }

      // Error de servidor (5xx) -> reintentar
      Logger.log("HTTP " + code + " en intento " + (attempt + 1) + " para: " + url.substring(0, 80));

    } catch (e) {
      Logger.log("Error de red en intento " + (attempt + 1) + ": " + e.message);
    }

    // Esperar antes de reintentar (backoff: 2s, 4s)
    if (attempt < maxRetries) {
      Utilities.sleep(2000 * (attempt + 1));
    }
  }

  Logger.log("Todos los " + (maxRetries + 1) + " intentos fallaron para: " + url.substring(0, 80));
  return null;
}

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

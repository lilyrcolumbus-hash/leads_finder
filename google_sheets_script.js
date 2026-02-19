/**
 * Google Apps Script - Business Leads Finder (v4)
 *
 * Busca negocios usando Google Places API directamente desde tu Google Sheet.
 * Crea una pestana nueva por cada busqueda (industria + ciudad).
 *
 * NUEVO en v4:
 *   - doGet() para llamar desde terminal via curl
 *   - Parametro ?max=N para limitar resultados
 *   - Funciona tanto desde la Sheet (menu) como desde terminal (curl)
 *
 * Uso desde terminal:
 *   curl "TU_DEPLOYMENT_URL?industry=plumber&location=Lima,OH&max=3"
 *
 * v3 - Datos limpios:
 *   - Sort post-escritura: emails primero, luego por rating
 *   - Salta URLs de Social Media internamente (no pierde tiempo)
 *   - Detecta Cloudflare/bot protection internamente (no pierde tiempo)
 *   - Email en blanco si no se encuentra (sin columna de status)
 *   - Mejor mensaje de error para API Key
 *
 * v2 FIXES (incluidos):
 *   - Escritura incremental (no pierdes datos si se corta el script)
 *   - Control de tiempo (se detiene antes del limite de 6 min)
 *   - SpreadsheetApp.flush() periodico para guardar datos en caso de crash
 *   - Busca emails en /contact y /contact-us ademas de homepage
 *   - Filtra emails basura (noreply, hosting providers, etc.)
 *   - Busca mailto: links primero (mas confiable que regex general)
 *   - Reintento automatico en llamadas API fallidas
 *   - Pain score ajustado para la limitacion de 5 reviews de Google
 *   - Manejo de OVER_QUERY_LIMIT con backoff
 *
 * SETUP:
 *   1. En tu Google Sheet: Extensiones -> Apps Script
 *   2. Pega todo este codigo
 *   3. En la linea de API_KEY abajo, pon tu Google Places API Key
 *   4. Guarda (Ctrl+S)
 *   5. Implementar -> Nueva implementacion -> Aplicacion web
 *      - Ejecutar como: Tu cuenta
 *      - Quien tiene acceso: Cualquier persona
 *   6. Copia la URL del deployment
 *   7. Desde terminal: curl "URL?industry=plumber&location=Lima,OH&max=3"
 *
 * IMPORTANTE:
 *   - Tu API Key debe tener habilitado "Places API" en Google Cloud Console
 *   - La API Key NO debe tener restriccion de "HTTP referrers" (usa "None" o "IP addresses")
 */

// ============================================================
// CONFIGURACION - Cambia esto
// ============================================================
const API_KEY = "AIzaSyDkdISixRzbgHPy5Ocfx10_lglLzHZyrOM";

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

// Dominios de redes sociales / directorios (no son websites reales del negocio)
const SOCIAL_MEDIA_DOMAINS = [
  "facebook.com", "fb.com", "fb.me",
  "instagram.com",
  "twitter.com", "x.com",
  "linkedin.com",
  "youtube.com", "youtu.be",
  "tiktok.com",
  "yelp.com",
  "nextdoor.com",
  "pinterest.com",
  "tripadvisor.com",
  "bbb.org"
];

// Headers de la tabla (13 columnas)
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
  "Google Maps URL",        // col 12
  "Place ID"                // col 13
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
 * Ejemplo:
 *   curl "https://script.google.com/macros/s/.../exec?industry=plumber&location=Lima,OH&max=3"
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

    // Validar parametros
    if (!industry || !location) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Faltan parametros. Uso: ?industry=plumber&location=Lima,OH&max=3",
        example: "?industry=plumber&location=Lima,OH&max=3&reviews=true"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Verificar API Key
    if (API_KEY === "TU_GOOGLE_PLACES_API_KEY_AQUI" || !API_KEY) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "API_KEY no configurada. Edita el script y pon tu Google Places API Key en la linea de API_KEY."
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Ejecutar busqueda y escritura (version sin UI)
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
 * Version headless (sin UI) de searchAndWrite para llamadas via curl/web.
 * No usa SpreadsheetApp.getUi() - funciona en contexto web app.
 *
 * @param {string} industry - Tipo de negocio
 * @param {string} location - Ciudad, Estado
 * @param {boolean} analyzeReviews - Si analizar reviews
 * @param {number} maxPlaces - Maximo de resultados a procesar
 * @returns {Object} Resultado con estadisticas
 */
function searchAndWriteHeadless(industry, location, analyzeReviews, maxPlaces) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var startTime = new Date().getTime();

  // Paso 1: Buscar negocios
  var searchResult = searchPlaces(industry, location);
  var places = searchResult.results;

  if (places.length === 0) {
    var msg = "No se encontraron negocios para '" + industry + "' en '" + location + "'";
    if (searchResult.error) {
      return {
        status: "error",
        message: msg,
        api_error: searchResult.error,
        leads: 0
      };
    }
    return {
      status: "ok",
      message: msg,
      leads: 0
    };
  }

  // Limitar resultados si se especifico max
  if (maxPlaces && maxPlaces < places.length) {
    places = places.slice(0, maxPlaces);
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

  for (var i = 0; i < places.length; i++) {
    var elapsed = new Date().getTime() - startTime;
    if (elapsed > MAX_RUNTIME_MS) break;

    var timeRemaining = MAX_RUNTIME_MS - elapsed;
    var skipEmail = timeRemaining < MIN_TIME_FOR_EMAIL_MS;

    var details = getPlaceDetails(places[i].place_id, analyzeReviews, skipEmail);
    if (details) {
      writeLeadRow(sheet, currentRow, details);

      if (details.email) emailCount++;
      if (details.phone) phoneCount++;
      if (details.painScore > 0) painCount++;

      leadsData.push({
        name: details.name,
        email: details.email,
        phone: details.phone,
        address: details.address,
        website: details.website,
        rating: details.rating,
        reviews: details.reviewCount
      });

      currentRow++;

      if ((currentRow - 2) % FLUSH_EVERY_N_ROWS === 0) {
        SpreadsheetApp.flush();
      }
    }

    if (i % 5 === 4) Utilities.sleep(500);
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
 * Al final, ordena: emails primero, luego por rating.
 *
 * @param {string} industry - Tipo de negocio
 * @param {string} location - Ciudad, Estado
 * @param {boolean} analyzeReviews - Si analizar reviews para pain points
 */
function searchAndWrite(industry, location, analyzeReviews) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var startTime = new Date().getTime();

  // Intentar obtener UI (falla en contexto web app)
  var ui = null;
  try {
    ui = SpreadsheetApp.getUi();
  } catch (e) {
    // Sin UI - estamos en contexto web app, usar version headless
    return searchAndWriteHeadless(industry, location, analyzeReviews, MAX_RESULTS);
  }

  // Verificar API Key
  if (API_KEY === "TU_GOOGLE_PLACES_API_KEY_AQUI" || !API_KEY) {
    ui.alert("⚠️ Error", "Configura tu API_KEY en el codigo del script.\n\nExtensiones -> Apps Script -> Cambia la linea de API_KEY", ui.ButtonSet.OK);
    return;
  }

  ss.toast("Buscando " + industry + " en " + location + "...", "🔍 Buscando", -1);

  // Paso 1: Buscar negocios
  var searchResult = searchPlaces(industry, location);
  var places = searchResult.results;

  if (places.length === 0) {
    var msg = "No se encontraron negocios para '" + industry + "' en '" + location + "'";
    if (searchResult.error) {
      msg += "\n\nError de API: " + searchResult.error;
    }
    ui.alert(msg);
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

  // Paso 4: Sort y formato final (si hay tiempo y mas de 1 lead)
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
    "Negocios procesados: " + totalLeads + " de " + places.length + "\n" +
    "Con email: " + emailCount + "\n" +
    "Con telefono: " + phoneCount + "\n";

  if (analyzeReviews) {
    summaryMsg += "Con pain points: " + painCount + "\n";
  }

  if (analyzeReviews) {
    summaryMsg += "\n⚠️ Nota: Google solo da 5 reviews por negocio. Pain scores son aproximados.";
  }

  if (stoppedEarly) {
    summaryMsg += "\n\n⏱️ Se detuvo antes del limite de tiempo.\n" +
      "Los " + totalLeads + " negocios procesados ya estan guardados.";
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
    var response = fetchWithRetry(url);
    if (!response) {
      return { results: [], error: "No se pudo conectar con Google Places API (sin respuesta)" };
    }

    var httpCode = response.getResponseCode();
    var data = JSON.parse(response.getContentText());

    if (data.status !== "OK") {
      var errorMsg = "Places API devolvio: " + data.status;
      if (data.error_message) errorMsg += " - " + data.error_message;
      Logger.log(errorMsg);

      if (data.status === "REQUEST_DENIED") {
        errorMsg = "API Key RECHAZADA por Google. " +
          "Ve a Google Cloud Console → APIs & Services → habilita 'Places API'. " +
          "Tambien revisa que tu Key no tenga restriccion de 'HTTP referrers'. " +
          "Detalle: " + (data.error_message || "sin detalle");
        try {
          SpreadsheetApp.getUi().alert("⚠️ API Key Rechazada", errorMsg, SpreadsheetApp.getUi().ButtonSet.OK);
        } catch (uiErr) { /* no UI en contexto web */ }
      }
      if (data.status === "OVER_QUERY_LIMIT") {
        errorMsg = "Rate limit excedido. Espera unos minutos e intenta de nuevo.";
        try {
          SpreadsheetApp.getUi().alert("⚠️ Rate Limit", errorMsg, SpreadsheetApp.getUi().ButtonSet.OK);
        } catch (uiErr) { /* no UI en contexto web */ }
      }
      return { results: [], error: errorMsg };
    }

    allResults = allResults.concat(data.results);

    // Paginas 2 y 3 (hasta 60 total)
    var nextPageToken = data.next_page_token;
    var page = 1;

    while (nextPageToken && allResults.length < MAX_RESULTS && page < 3) {
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
    return { results: [], error: "Error de conexion: " + e.message };
  }

  return { results: allResults, error: null };
}

/**
 * Obtiene detalles completos de un negocio por Place ID.
 * Salta extraccion de email para social media y bot protection.
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

    if (place.business_status === "CLOSED_PERMANENTLY") {
      return null;
    }

    // Extraer email (salta social media y bot protection internamente)
    var email = "";

    if (!skipEmail && place.website && !isSocialMediaUrl(place.website)) {
      var emailResult = extractEmailFromWebsite(place.website);
      email = emailResult.email;
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
 *
 * @returns {{ email: string, status: string }}
 */
function extractEmailFromWebsite(websiteUrl) {
  var result = extractEmailFromPage(websiteUrl);
  if (result.email) return result;

  // Recordar si la homepage fue bloqueada
  var blockedOnHomepage = result.status === "Bloqueado";

  // Intentar paginas de contacto
  var baseUrl = getBaseUrl(websiteUrl);
  for (var i = 0; i < CONTACT_PATHS.length; i++) {
    result = extractEmailFromPage(baseUrl + CONTACT_PATHS[i]);
    if (result.email) return result;
  }

  // Si la homepage fue bloqueada, reportar eso (aunque /contact haya dado 404)
  if (blockedOnHomepage) {
    return { email: "", status: "Bloqueado" };
  }

  return { email: "", status: result.status || "No encontrado" };
}

/**
 * Extrae email de una URL especifica.
 * Busca mailto: links primero, luego regex general.
 * Detecta bot protection (Cloudflare, Captcha, etc.)
 *
 * @returns {{ email: string, status: string }}
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
    if (code === 403) return { email: "", status: "Bloqueado" };
    if (code !== 200) return { email: "", status: "No encontrado" };

    var html = response.getContentText();

    // Limitar a 500KB
    if (html.length > 500000) {
      html = html.substring(0, 500000);
    }

    // Detectar bot protection
    if (isBotProtected(html)) {
      return { email: "", status: "Bloqueado" };
    }

    // Paso 1: Buscar en mailto: links (mas confiable)
    var mailtoRegex = /mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})/gi;
    var mailtoMatches = html.match(mailtoRegex);
    if (mailtoMatches) {
      for (var i = 0; i < mailtoMatches.length; i++) {
        var mailtoEmail = mailtoMatches[i].replace(/^mailto:/i, "").toLowerCase();
        if (isValidLeadEmail(mailtoEmail)) {
          return { email: mailtoEmail, status: "Encontrado" };
        }
      }
    }

    // Paso 2: Regex general
    var emailRegex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
    var matches = html.match(emailRegex);
    if (!matches || matches.length === 0) {
      return { email: "", status: "No encontrado" };
    }

    // Filtrar y recoger emails validos
    var validEmails = [];
    for (var i = 0; i < matches.length; i++) {
      var em = matches[i].toLowerCase();
      if (isValidLeadEmail(em) && validEmails.indexOf(em) === -1) {
        validEmails.push(em);
      }
    }

    if (validEmails.length === 0) {
      return { email: "", status: "No encontrado" };
    }

    // Priorizar emails de contacto
    var priority = [
      "info@", "contact@", "hello@", "office@",
      "appointments@", "scheduling@", "front@", "reception@",
      "inquiries@", "sales@"
    ];
    for (var i = 0; i < priority.length; i++) {
      for (var j = 0; j < validEmails.length; j++) {
        if (validEmails[j].indexOf(priority[i]) === 0) {
          return { email: validEmails[j], status: "Encontrado" };
        }
      }
    }

    return { email: validEmails[0], status: "Encontrado" };

  } catch (e) {
    return { email: "", status: "Error de red" };
  }
}

/**
 * Valida que un email sea util para un lead (no basura/sistema/hosting)
 */
function isValidLeadEmail(email) {
  email = email.toLowerCase();

  if (email.match(/\.(png|jpg|jpeg|gif|svg|css|js|webp|ico|woff|woff2|ttf|eot|pdf|zip)$/)) return false;

  for (var i = 0; i < EMAIL_BLACKLIST_DOMAINS.length; i++) {
    if (email.indexOf("@" + EMAIL_BLACKLIST_DOMAINS[i]) >= 0) return false;
    if (email.indexOf("." + EMAIL_BLACKLIST_DOMAINS[i]) >= 0) return false;
  }

  for (var i = 0; i < EMAIL_BLACKLIST_PREFIXES.length; i++) {
    if (email.indexOf(EMAIL_BLACKLIST_PREFIXES[i]) === 0) return false;
  }

  if (email.match(/^[0-9a-f]{5,}@/)) return false;
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

/**
 * Detecta si una URL es de redes sociales o directorios (no website real)
 */
function isSocialMediaUrl(url) {
  var lower = url.toLowerCase();
  for (var i = 0; i < SOCIAL_MEDIA_DOMAINS.length; i++) {
    if (lower.indexOf(SOCIAL_MEDIA_DOMAINS[i]) >= 0) return true;
  }
  return false;
}

/**
 * Detecta si el HTML es una pagina de bot protection (Cloudflare, Captcha, etc.)
 * en vez de contenido real del negocio.
 */
function isBotProtected(html) {
  var lower = html.toLowerCase();

  // Senales fuertes: cualquiera de estas = bot protection seguro
  var strongSignals = [
    "cf-browser-verification",
    "challenge-platform",
    "checking your browser",
    "just a moment</title>",
    "_cf_chl_opt",
    "ddos-guard",
    "sucuri-cloudproxy"
  ];

  for (var i = 0; i < strongSignals.length; i++) {
    if (lower.indexOf(strongSignals[i]) >= 0) return true;
  }

  // Combinacion: nombre de proteccion + challenge/captcha
  var hasProtectionName = lower.indexOf("cloudflare") >= 0 ||
                          lower.indexOf("sucuri") >= 0 ||
                          lower.indexOf("incapsula") >= 0;
  var hasChallenge = lower.indexOf("challenge") >= 0 ||
                     lower.indexOf("captcha") >= 0;

  if (hasProtectionName && hasChallenge) return true;

  // Pagina muy corta con "enable javascript" = proteccion
  if (html.length < 10000) {
    if (lower.indexOf("enable javascript") >= 0 ||
        lower.indexOf("javascript is required") >= 0 ||
        lower.indexOf("please turn javascript on") >= 0) {
      return true;
    }
  }

  return false;
}

// ============================================================
// ANALISIS DE PAIN POINTS EN REVIEWS
// ============================================================

/**
 * Analiza reviews buscando keywords de dolor/mala comunicacion.
 *
 * IMPORTANTE: Google Places API solo devuelve MAX 5 reviews por negocio.
 * El pain score se ajusta para esta limitacion con un penalty de muestra pequena.
 */
function analyzeReviewsForPain(reviews) {
  var painReviews = [];
  var keywordCounts = {};
  var totalNegativeReviews = 0;

  for (var i = 0; i < reviews.length; i++) {
    var reviewText = (reviews[i].text || "").toLowerCase();
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
      var rawText = reviews[i].text || "";
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
    var samplePenalty = totalReviews < 10 ? 0.8 : 1.0;

    score = Math.min(1, (baseScore * 0.6 + diversityBonus + painCount * 0.05) * samplePenalty);
    score = Math.round(score * 100) / 100;
  }

  var summary = "";
  if (painCount > 0) {
    var topKeywords = Object.keys(keywordCounts)
      .sort(function(a, b) { return keywordCounts[b] - keywordCounts[a]; })
      .slice(0, 3);
    summary = painCount + "/" + totalReviews + " reviews con quejas: " + topKeywords.join(", ");
    summary += " (muestra: " + totalReviews + " de max 5 reviews)";
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

/**
 * Obtiene una pestana existente o crea una nueva.
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
 * Escribe UN lead en una fila (escritura incremental).
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
    lead.mapsUrl,
    lead.placeId
  ];

  sheet.getRange(row, 1, 1, HEADERS.length).setValues([rowData]);

  // Verde claro toda la fila si tiene email
  if (lead.email) {
    sheet.getRange(row, 1, 1, HEADERS.length).setBackground("#e6f4ea");
  }

  // Amarillo en Pain Score si es alto (columna 9)
  if (lead.painScore >= 0.3) {
    sheet.getRange(row, 9).setBackground("#fef7e0");
    sheet.getRange(row, 9).setFontWeight("bold");
  }
}

/**
 * Ordena los datos: emails primero, luego por rating.
 * Recalcula todos los colores despues del sort.
 */
function sortAndFormatSheet(sheet, totalLeads) {
  var numCols = HEADERS.length;
  var dataRange = sheet.getRange(2, 1, totalLeads, numCols);

  // Sort: Email (col 2) no-vacio primero, luego Rating (col 6) mas alto primero
  dataRange.sort([
    {column: 2, ascending: false},
    {column: 6, ascending: false}
  ]);

  // Leer datos ya ordenados
  var values = dataRange.getValues();

  // Construir arrays de backgrounds y font weights
  var backgrounds = [];
  var painWeights = [];

  for (var i = 0; i < values.length; i++) {
    var rowBg = [];
    for (var j = 0; j < numCols; j++) {
      rowBg.push("#ffffff");
    }

    var email = values[i][1];         // index 1 = Email
    var painScoreStr = values[i][8];  // index 8 = Pain Score

    // Fila verde si tiene email
    if (email) {
      for (var j = 0; j < numCols; j++) {
        rowBg[j] = "#e6f4ea";
      }
    }

    // Pain Score amarillo
    if (painScoreStr) {
      var pv = parseFloat(painScoreStr);
      if (pv >= 0.3) {
        rowBg[8] = "#fef7e0";
      }
    }

    backgrounds.push(rowBg);

    // Bold para pain score
    if (painScoreStr && parseFloat(painScoreStr) >= 0.3) {
      painWeights.push(["bold"]);
    } else {
      painWeights.push(["normal"]);
    }
  }

  // Aplicar backgrounds en batch
  dataRange.setBackgrounds(backgrounds);

  // Aplicar font weights para pain score en batch
  sheet.getRange(2, 9, totalLeads, 1).setFontWeights(painWeights);

  // Auto-resize columnas
  sheet.autoResizeColumns(1, 8);
  sheet.setColumnWidth(10, 250); // Pain summary
  sheet.setColumnWidth(11, 200); // Pain reviews
  sheet.setColumnWidth(12, 200); // Maps URL
}

/**
 * Formato basico sin sort (cuando no hay tiempo para sort)
 */
function formatSheet(sheet, totalRows) {
  try {
    sheet.autoResizeColumns(1, 8);
    sheet.setColumnWidth(10, 250);
    sheet.setColumnWidth(11, 200);
    sheet.setColumnWidth(12, 200);
  } catch (e) {
    Logger.log("Error formatting sheet: " + e.message);
  }
}

// ============================================================
// UTILIDADES
// ============================================================

/**
 * HTTP fetch con reintentos automaticos.
 * Reintenta hasta 2 veces con backoff en errores 5xx o de red.
 */
function fetchWithRetry(url, maxRetries) {
  maxRetries = maxRetries || 2;

  for (var attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
      var code = response.getResponseCode();

      if (code < 500) {
        return response;
      }

      Logger.log("HTTP " + code + " en intento " + (attempt + 1) + " para: " + url.substring(0, 80));

    } catch (e) {
      Logger.log("Error de red en intento " + (attempt + 1) + ": " + e.message);
    }

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

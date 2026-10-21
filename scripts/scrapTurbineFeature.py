import json
import re
import time
from bs4 import BeautifulSoup
from seleniumbase import SB

URL = "https://es.wind-turbine-models.com/"
BUSQUEDA = "Vestas 90"
# Nombre exacto de la turbina a abrir dentro de los resultados
TURBINA = "Vestas V90-3.0"


def hay_cloudflare(sb):
    # Mientras Cloudflare verifica, el título es "Just a moment..." / "Un momento..."
    titulo = sb.get_title().lower()
    return "just a moment" in titulo or "un momento" in titulo


def pasar_cloudflare(sb, intentos=3):
    for _ in range(intentos):
        if not hay_cloudflare(sb):
            return True
        # Marca la casilla "Verifique que es un ser humano" con el ratón real
        sb.uc_gui_click_captcha()
        time.sleep(3)
    print("Cloudflare no se superó")
    return not hay_cloudflare(sb)


def normalizar(texto):
    # "Vestas V90" y "Vestas 90" -> "vestas90" (quita espacios, guiones y la "v" antes del número)
    texto = re.sub(r"[\s\-]", "", texto.lower())
    return re.sub(r"v(?=\d)", "", texto)


def leer_hoja_de_datos(html):
    # La "Hoja de datos" es un acordeón: cada <h3> (De energía, Hélice, Torre...) va seguido
    # de un div.TabContent con filas col-left (campo) / col-right (valor).
    # Se usa BeautifulSoup porque las pestañas cerradas están ocultas y Selenium no leería su texto.
    soup = BeautifulSoup(html, "html.parser")
    datos = {}
    for contenido in soup.select("#datasheet .TabContent"):
        titulo = contenido.find_previous_sibling("h3")
        seccion = titulo.get_text(strip=True) if titulo else contenido.get("data-tabname")
        campos = {}
        for fila in contenido.select(".tabbox-table .row"):
            campo = fila.select_one(".col-left")
            valor = fila.select_one(".col-right")
            if campo and valor:
                campos[campo.get_text(strip=True).rstrip(":")] = valor.get_text(strip=True)
        datos[seccion] = campos
    return datos


def rechazar_cookies(sb):
    # Botón "Declinación" del banner de cookies (es un <div>, no un <button>)
    selector = "div.cc-decline-all"
    try:
        sb.wait_for_element_visible(selector, timeout=10)
        sb.click(selector)
        print("Cookies rechazadas")
        time.sleep(1)
        return True
    except Exception:
        print("No apareció el banner de cookies")
        return False


def cargar_con_reintentos(sb, accion, selector, intentos=3):
    # Ejecuta la acción (buscar, abrir turbina...) y espera a que aparezca el selector.
    # Si la página sale con error, la recarga y vuelve a intentarlo.
    for intento in range(1, intentos + 1):
        try:
            accion()
            time.sleep(3)
            pasar_cloudflare(sb)
            sb.wait_for_element_present(selector, timeout=15)
            return True
        except Exception as e:
            print(f"Intento {intento}/{intentos} falló ({type(e).__name__}), recargando...")
            try:
                sb.refresh()
                time.sleep(3)
                pasar_cloudflare(sb)
                rechazar_cookies(sb)
                # Tras recargar puede que la página ya esté bien
                sb.wait_for_element_present(selector, timeout=5)
                return True
            except Exception:
                pass
    return False


# uc=True -> Chrome no detectable; user_data_dir guarda las cookies (cf_clearance)
# para que en las siguientes ejecuciones Cloudflare ya no pregunte
with SB(uc=True, locale="es", user_data_dir="perfil_chrome") as sb:
    sb.uc_open_with_reconnect(URL, 4)
    pasar_cloudflare(sb)
    rechazar_cookies(sb)

    # Escribir en el buscador y enviar (el "\n" pulsa Enter)
    if not cargar_con_reintentos(
        sb, lambda: sb.type("input.searchbar[name='q']", BUSQUEDA + "\n"), "#turbines .panel-overview-item"
    ):
        raise SystemExit("No se pudo cargar la página de resultados")

    print("URL resultados:", sb.get_current_url())
    print("Título:", sb.get_title())

    # Tarjetas de la sección "Turbinas" de los resultados
    turbinas = []
    for tarjeta in sb.find_elements("#turbines .panel-overview-item"):
        nombre = tarjeta.find_element("css selector", ".panel-heading-content").text.strip()
        potencia = tarjeta.find_element("css selector", ".panel-heading-subtitle").text.strip()
        enlace = tarjeta.find_element("css selector", "a.overview-link").get_attribute("href")
        turbinas.append({"nombre": nombre, "potencia": potencia, "enlace": enlace})
        print(f"{nombre} ({potencia}) -> {enlace}")

    if not turbinas:
        raise SystemExit("No se encontraron turbinas para la búsqueda")

    # Elegir la turbina cuyo nombre coincide con TURBINA; si ninguna coincide, parar
    # en vez de capturar otra por error
    elegida = None
    for turbina in turbinas:
        if normalizar(turbina["nombre"]) == normalizar(TURBINA):
            elegida = turbina
            break
    if elegida is None:
        raise SystemExit(f"'{TURBINA}' no está en los resultados de '{BUSQUEDA}'")
    print("Entrando en:", elegida["nombre"], elegida["enlace"])

    if not cargar_con_reintentos(sb, lambda: sb.open(elegida["enlace"]), "#datasheet .TabContent"):
        raise SystemExit("No se pudo cargar la página de la turbina")
    print("Título:", sb.get_title())

    datos = leer_hoja_de_datos(sb.get_page_source())
    for seccion, campos in datos.items():
        print(f"\n== {seccion} ==")
        for campo, valor in campos.items():
            print(f"  {campo}: {valor}")

    resultado = {"nombre": elegida["nombre"], "enlace": elegida["enlace"], "hoja_de_datos": datos}
    with open("datos_turbina.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print("\nDatos guardados en datos_turbina.json")

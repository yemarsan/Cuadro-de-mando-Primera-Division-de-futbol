# -*- coding: utf-8 -*-
import os
import time
from io import StringIO
import logging

import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, Comment

tiempo_inicio = time.time()

# Configuración de logging para registrar la actividad del script en archivo y consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)


# Lista de temporadas objeto de estudio
temporadas = []
inicio = 2024
fin = 2017
for anyo in range (inicio, fin-1, -1):
    temporada = f"{anyo}-{anyo+1}"
    temporadas.append(temporada)

def extraer_tabla(soup, id_base):
    """Busca y extrae una tabla del HTML utilizando el ID base proporcionado.

    Args:
        soup: Objeto BeautifulSoup con el contenido HTML.
        id_base: Parte inicial del ID de la tabla a buscar.

    Returns:
        DataFrame de pandas con los datos de la tabla, o None si no se encuentra.
    """
    # Buscar tablas en HTML visible
    tabla = soup.find('table', id=lambda x: x and x.startswith(id_base))
    if tabla:
        try:
            return pd.read_html(StringIO(str(tabla)), header=1)[0]
        except Exception as e:
            logging.error(f"Error al leer la tabla (html) {id_base}:{e}")
            return None       
    return None        

def eliminar_cabeceras_extra(df):
    serie = df.iloc[:,0].astype(str) == 'RL'
    return df[~serie].reset_index(drop=True)

# Diccionario de categorías y sus identificadores para la extracción de datos
categorias= {
    "standard":{
        "subruta": "stats", 
        "id_jug": "stats_standard",
        "id_eq_for": "stats_squads_standard_for",
        "id_eq_agst": "stats_squads_standard_against"},
    "keepers":{
        "subruta": "keepers", 
        "id_jug": "stats_keeper",
        "id_eq_for": "stats_squads_keeper_for",
        "id_eq_agst": "stats_squads_keeper_against"},
    "keepers_adv":{
        "subruta": "keepersadv",
         "id_jug": "stats_keeper_adv",
         "id_eq_for": "stats_squads_keeper_adv_for",
         "id_eq_agst": "stats_squads_keeper_adv_against"},
    "shooting":{
        "subruta": "shooting", 
        "id_jug": "stats_shooting",
        "id_eq_for": "stats_squads_shooting_for",
        "id_eq_agst": "stats_squads_shooting_against"},
    "passing":{
        "subruta": "passing", 
        "id_jug": "stats_passing",
        "id_eq_for": "stats_squads_passing_for",
        "id_eq_agst": "stats_squads_passing_against"},
    "passing_types":{
        "subruta": "passing_types", 
        "id_jug": "stats_passing_types",
        "id_eq_for": "stats_squads_passing_types_for",
        "id_eq_agst": "stats_squads_passing_types_against"},
    "gca":{
        "subruta": "gca", 
        "id_jug": "stats_gca",
        "id_eq_for": "stats_squads_gca_for",
        "id_eq_agst": "stats_squads_gca_against"},
    "defense":{
        "subruta": "defense", 
        "id_jug": "stats_defense",
        "id_eq_for": "stats_squads_defense_for",
        "id_eq_agst": "stats_squads_defense_against"},
    "possession":{
        "subruta": "possession",
         "id_jug":"stats_possession",
         "id_eq_for": "stats_squads_possession_for",
         "id_eq_agst": "stats_squads_possession_against"},
    "playing_time":{
        "subruta": "playingtime", 
        "id_jug": "stats_playing_time",
        "id_eq_for": "stats_squads_playing_time_for",
        "id_eq_agst": "stats_squads_playing_time_against"},
    "misc":{
        "subruta":"misc", 
        "id_jug": "stats_misc",
        "id_eq_for": "stats_squads_misc_for",
        "id_eq_agst": "stats_squads_misc_against"}
}

# Diccionario de nombres en español para las categorías
nombres_es = {
    "standard" : "general",
    "keepers" : "porteros",
    "keepers_adv" : "porteros_avanzado",
    "shooting" : "tiros",
    "passing" : "pases",
    "passing_types" : "tipos_pase",
    "gca" : "creación_gol",
    "defense" : "defensa",
    "possession" : "posesión",
    "playing_time" : "minutos",
    "misc" : "otros"
}

for temporada in temporadas:
    
    """Procesa cada temporada: extrae la clasificación general y las estadísticas de jugadores y equipos para cada categoría,
    guardando los resultados en archivos CSV.
    """        
    logging.info(f"Procesando temporada: {temporada}")

    # Creación de las carpetas para guardar los datos de jugadores y equipos por temporada
    directorio_jugadores = os.path.join('datos_fbref', temporada, 'Jugadores')
    os.makedirs(directorio_jugadores, exist_ok=True)
    directorio_equipos = os.path.join('datos_fbref', temporada, 'Equipos')
    os.makedirs(directorio_equipos, exist_ok=True)

    # Extracción de la clasificación (url diferente a la del resto de categorías)
    if temporada == temporadas[0]:
        url_clasif = f'https://fbref.com/es/comps/12/Estadisticas-de-La-Liga'
    else:
        url_clasif = f'https://fbref.com/es/comps/12/{temporada}/Estadisticas-{temporada}-La-Liga'

    # Configuración del navegador Chrome para evitar mensajes innecesarios y controlar tiempos de espera
    chrome_options = Options()
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(options=chrome_options)
    wait   = WebDriverWait(driver, timeout=15)
    driver.set_page_load_timeout(60)
    
    try:
        driver.get(url_clasif)
        time.sleep(10)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tabla_id_clasificacion = f"results{temporada}121_overall"
        clasificacion = soup.find('table', id=tabla_id_clasificacion)

        if clasificacion is None:
            for tabla in soup.find_all('table'):
                if tabla.get('id','').startswith('results'):
                    clasificacion = tabla
                    break
        
        if clasificacion is not None:
            try:
                df_clasif = pd.read_html(StringIO(str(clasificacion)))[0]
                ruta_clasif = os.path.join(directorio_equipos, f'Equipos_clasificación_{temporada}.csv')
                df_clasif.to_csv(ruta_clasif, index=False, encoding='utf-8-sig')
                logging.info(f"Clasificación: {ruta_clasif} ({len(df_clasif)} filas guardadas)")
            except Exception as e:
                logging.error(f"Error leyendo la tabla de clasificación: {e}")
        else:
            logging.warning("No se encontró la tabla de clasificación.")
     
        for nombre_categoria, datos in categorias.items():
            """Procesa cada categoría de estadísticas: extrae y guarda datos de jugadores y equipos.
            Para cada categoría, construye la URL correspondiente, extrae la tabla de jugadores,
            la tabla de estadísticas de equipos a favor y la tabla de estadísticas en contra del equipo,
            guardando cada una en un archivo CSV.            
            """                
            subruta = datos["subruta"]
            id_jugadores = datos["id_jug"]
            id_equipos_for= datos["id_eq_for"]
            id_equipos_against= datos["id_eq_agst"]
            nombre_es = nombres_es[nombre_categoria]

            # Construir la url para la temporada actual y categoría, para la última temporada (2024-25) la url es diferente
            if temporada == temporadas[0]:
                url = f'https://fbref.com/es/comps/12/{subruta}/Estadisticas-de-La-Liga'

            else:
                url = f'https://fbref.com/es/comps/12/{temporada}/{subruta}/Estadisticas-{temporada}-La-Liga'
            
            logging.info(f"Procesando categoría: {nombre_es} - URL {url}")

            driver.get(url)
            time.sleep(10)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extraer y guardar jugadores
            tabla_jug = extraer_tabla(soup, id_jugadores)         
            if tabla_jug is not None:
                tabla_jug = eliminar_cabeceras_extra(tabla_jug)
                ruta_jug =os.path.join(directorio_jugadores, f'Jugadores_{nombre_es}_{temporada}.csv')
                tabla_jug.to_csv(ruta_jug, index=False, encoding='utf-8-sig')
                logging.info(f"Jugadores: {ruta_jug} ({len(tabla_jug)} filas guardadas)")
            else:
                logging.warning(f"No se encontró la tabla de jugadores:{nombre_es}")

            # Extraer y guardar equipos a favor
            tabla_eq_for = extraer_tabla(soup, id_equipos_for)
            if tabla_eq_for is not None:
                ruta_eq_for = os.path.join(directorio_equipos, f'Equipos_{nombre_es}_a_favor_{temporada}.csv')
                tabla_eq_for.to_csv(ruta_eq_for, index=False, encoding='utf-8-sig')
                logging.info(f"Equipos a favor: {ruta_eq_for} ({len(tabla_eq_for)} filas guardadas)")
            else:
                logging.warning(f"No se encontró la tabla de equipos a favor: {nombre_es}")

            # Extraer y guardar equipos en contra            
            tabla_eq_against = extraer_tabla(soup, id_equipos_against)
            if tabla_eq_against is not None:
                ruta_eq_against = os.path.join(directorio_equipos, f'Equipos_{nombre_es}_en_contra_{temporada}.csv')
                tabla_eq_against.to_csv(ruta_eq_against, index=False, encoding='utf-8-sig')
                logging.info(f"Equipos en contra: {ruta_eq_against} ({len(tabla_eq_against)} filas guardadas)")
            else:
                logging.warning(f"No se encontró la tabla de equipos en contra: {nombre_es}")

            time.sleep(2)

    except Exception as e:
        logging.error(f" Error al procesar {temporada}: {e}")
    finally:
        driver.quit()
        time.sleep(2)

    logging.info(f"Temporada {temporada} completada.\n")
        
    time.sleep(10)

tiempo_fin = time.time()
duracion = tiempo_fin - tiempo_inicio
minutos = int(duracion // 60)
segundos = int(duracion % 60)
logging.info(f"Tiempo total de ejecución: {minutos} minutos y {segundos} segundos")
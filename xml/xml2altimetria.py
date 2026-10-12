import xml.etree.ElementTree as ET

class GeneradorAltimetria:
    """
    Clase para la generación de archivos SVG de altimetría a partir 
    de archivos XML de etapas ciclistas, cumpliendo con la aproximación orientada a objetos.
    """
    
    def __init__(self, archivo_xml, archivo_svg):
        self.archivo_xml = archivo_xml
        self.archivo_svg = archivo_svg
        self.puntos = []
        # Definición del espacio de nombres necesario para evaluar las expresiones XPath
        self.namespace = {'uniovi': 'http://www.uniovi.es'}
        
        # Configuraciones de las dimensiones del lienzo SVG
        self.ancho_svg = 1200
        self.alto_svg = 500
        self.margen_x = 100
        self.margen_y = 100

    def extraer_datos_xpath(self):
        """
        Lee el archivo XML en memoria y extrae las distancias y altitudes
        usando exclusivamente expresiones XPath.
        """
        try:
            arbol = ET.parse(self.archivo_xml)
            raiz = arbol.getroot()

            # 1. Obtener datos de la salida (Distancia 0 por defecto)
            salida = raiz.find('.//uniovi:lugar_salida', self.namespace)
            alt_salida = float(salida.find('.//uniovi:georreferenciacion/uniovi:altitud', self.namespace).text)
            nom_salida = salida.find('uniovi:nombre', self.namespace).text
            self.puntos.append((0.0, alt_salida, nom_salida))

            # 2. Obtener datos generales para conocer la longitud total (ubicación de la meta)
            longitud_total = float(raiz.find('.//uniovi:datos_etapa/uniovi:longitud', self.namespace).text)
            
            # 3. Obtener la altitud de la meta
            meta = raiz.find('.//uniovi:lugar_meta', self.namespace)
            alt_meta = float(meta.find('.//uniovi:georreferenciacion/uniovi:altitud', self.namespace).text)
            nom_meta = meta.find('uniovi:nombre', self.namespace).text
            
            # 4. Obtener hitos intermedios usando XPath
            for hito in raiz.findall('.//uniovi:hito', self.namespace):
                dist = float(hito.find('uniovi:distancia_salida', self.namespace).text)
                alt = float(hito.find('.//uniovi:georreferenciacion/uniovi:altitud', self.namespace).text)
                tipo = hito.attrib.get('tipo', 'Hito')
                self.puntos.append((dist, alt, tipo))

            # 5. Obtener puntos de trayecto anónimos usando XPath
            for p_anonimo in raiz.findall('.//uniovi:punto_anonimo', self.namespace):
                dist = float(p_anonimo.find('uniovi:distancia_salida', self.namespace).text)
                alt = float(p_anonimo.find('.//uniovi:georreferenciacion/uniovi:altitud', self.namespace).text)
                # Al ser anónimos, no les asignamos etiqueta de texto
                self.puntos.append((dist, alt, ''))

            # 6. Añadir el punto de meta
            self.puntos.append((longitud_total, alt_meta, nom_meta))

            # Ordenar la lista secuencialmente por la distancia recorrida
            self.puntos.sort(key=lambda x: x[0])

        except Exception as e:
            print(f"Error al procesar el archivo XML mediante XPath: {e}")

    def generar_svg(self):
        """
        Orquesta la escritura del archivo final SVG usando los métodos específicos de clase.
        """
        if not self.puntos:
            print("No hay datos extraídos para generar el gráfico.")
            return

        with open(self.archivo_svg, 'w', encoding='utf-8') as archivo:
            self.escribir_cabecera_svg(archivo)
            self.escribir_polilinea(archivo)
            self.escribir_ejes_y_textos(archivo)
            self.escribir_cierre_svg(archivo)

    def escribir_cabecera_svg(self, archivo):
        """Genera las etiquetas de encabezamiento del SVG."""
        archivo.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        archivo.write(f'<svg xmlns="http://www.w3.org/2000/svg" version="2.0" width="{self.ancho_svg}" height="{self.alto_svg}">\n')
        archivo.write('  <rect width="100%" height="100%" fill="#ffffff"/>\n')
        archivo.write('  <!-- Perfil altimetrico de la etapa -->\n')

    def escribir_polilinea(self, archivo):
        """
        Escribe la polilínea incluyendo el efecto suelo mencionado en la guía.
        """
        distancia_max = max(p[0] for p in self.puntos)
        altitud_max = max(p[1] for p in self.puntos)

        ancho_dibujo = self.ancho_svg - 2 * self.margen_x
        alto_dibujo = self.alto_svg - 2 * self.margen_y

        coordenadas = []
        
        # Iniciar en la esquina inferior izquierda para el efecto "suelo"
        y_suelo = self.alto_svg - self.margen_y
        coordenadas.append(f"{self.margen_x},{y_suelo}")

        # Añadir todos los vértices mapeando distancias a X y altitudes a Y
        for dist, alt, _ in self.puntos:
            x = self.margen_x + (dist / distancia_max) * ancho_dibujo
            y = y_suelo - (alt / altitud_max) * alto_dibujo
            coordenadas.append(f"{x},{y}")

        # Cerrar la polilínea en la esquina inferior derecha
        x_fin = self.margen_x + ancho_dibujo
        coordenadas.append(f"{x_fin},{y_suelo}")

        coordenadas_str = " ".join(coordenadas)
        archivo.write(f'  <polyline points="{coordenadas_str}" \n')
        archivo.write('            style="fill:#e04631; stroke:#a11c0f; stroke-width:3" />\n')

    def escribir_ejes_y_textos(self, archivo):
        """
        Añade marcas de distancia, líneas indicativas, las altitudes, y el texto 
        vertical de los hitos principales de la ruta.
        """
        distancia_max = max(p[0] for p in self.puntos)
        altitud_max = max(p[1] for p in self.puntos)

        ancho_dibujo = self.ancho_svg - 2 * self.margen_x
        alto_dibujo = self.alto_svg - 2 * self.margen_y
        y_suelo = self.alto_svg - self.margen_y

        # Dibujar la línea de base (distancia 0 a Max)
        x_inicio = self.margen_x
        x_fin = self.margen_x + ancho_dibujo
        archivo.write(f'  <line x1="{x_inicio}" y1="{y_suelo}" x2="{x_fin}" y2="{y_suelo}" style="stroke:black; stroke-width:2" />\n')

        # Escribir información adicional para cada punto relevante (no anónimo)
        for dist, alt, nombre in self.puntos:
            if nombre:
                x = self.margen_x + (dist / distancia_max) * ancho_dibujo
                y = y_suelo - (alt / altitud_max) * alto_dibujo

                # Línea indicadora desde la base hasta la cima
                archivo.write(f'  <line x1="{x}" y1="{y_suelo}" x2="{x}" y2="{y}" style="stroke:#555555; stroke-width:1; stroke-dasharray:4" />\n')

                # Texto vertical en la base emulando el perfil oficial
                y_texto = y_suelo + 15
                archivo.write(f'  <text x="{x}" y="{y_texto}" transform="rotate(90, {x}, {y_texto})" font-family="Arial" font-size="14" fill="#333333">{nombre} / {dist} km</text>\n')
                
                # Etiqueta de la altitud en metros justo encima del perfil
                archivo.write(f'  <text x="{x}" y="{y - 10}" font-family="Arial" font-size="12" font-weight="bold" fill="black" text-anchor="middle">{alt} m</text>\n')

    def escribir_cierre_svg(self, archivo):
        """Escribe las etiquetas de cierre del archivo SVG."""
        archivo.write('</svg>\n')


# Ejecución principal del script
if __name__ == "__main__":
    # Nombres de los archivos de entrada y salida
    archivo_entrada = "etapaEsquema.xml"
    archivo_salida = "altimetria.svg"
    
    # 1. Instanciar la clase de altimetría
    perfil = GeneradorAltimetria(archivo_entrada, archivo_salida)
    
    # 2. Parsear el XML mediante métodos XPath
    perfil.extraer_datos_xpath()
    
    # 3. Generar el archivo resultante
    perfil.generar_svg()
    
    print(f"Éxito: Archivo '{archivo_salida}' generado correctamente a partir de '{archivo_entrada}'.")
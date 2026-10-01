import xml.etree.ElementTree as ET

class GeneradorKML:
    """
    Clase orientada a objetos para leer etapaEsquema.xml mediante XPath 
    y generar un archivo etapa.kml con la planimetría de la ruta.
    """
    def __init__(self, archivo_xml):
        self.archivo_xml = archivo_xml
        # Espacio de nombres (namespace) obligatorio definido en el esquema y XML
        self.espacio_nombres = {'uo': 'http://www.uniovi.es'}
        self.arbol = ET.parse(self.archivo_xml)
        self.raiz = self.arbol.getroot()
        self.kml_contenido = []

    def escribir_prologo(self):
        """Genera las etiquetas de encabezado del archivo KML y los estilos de colores."""
        self.kml_contenido.append('<?xml version="1.0" encoding="UTF-8"?>')
        self.kml_contenido.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
        self.kml_contenido.append('<Document>')
        self.kml_contenido.append('  <name>Planimetría de la Etapa</name>')
        
        # Estilos de marcadores (Formato KML: aabbggrr)
        # Rojo: Puntos de salida y meta
        self.kml_contenido.append('  <Style id="rojo"><IconStyle><color>ff0000ff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>')
        # Verde: Puertos de montaña
        self.kml_contenido.append('  <Style id="verde"><IconStyle><color>ff00ff00</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>')
        # Azul: Sprints intermedios y bonificados
        self.kml_contenido.append('  <Style id="azul"><IconStyle><color>ffff0000</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>')
        # Amarillo: Puntos anónimos
        self.kml_contenido.append('  <Style id="amarillo"><IconStyle><color>ff00ffff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>')
        # Estilo para la línea de la planimetría completa
        self.kml_contenido.append('  <Style id="linea"><LineStyle><color>ff0000ff</color><width>4</width></LineStyle></Style>')

    def escribir_epilogo(self):
        """Cierra las etiquetas del archivo KML."""
        self.kml_contenido.append('</Document>')
        self.kml_contenido.append('</kml>')

    def _obtener_coordenadas(self, elemento):
        """Método auxiliar para extraer la longitud, latitud y altitud usando XPath."""
        geo = elemento.find('.//uo:georreferenciacion', self.espacio_nombres)
        if geo is not None:
            lon = geo.find('uo:longitud', self.espacio_nombres).text
            lat = geo.find('uo:latitud', self.espacio_nombres).text
            alt = geo.find('uo:altitud', self.espacio_nombres).text
            return f"{lon},{lat},{alt}"
        return ""

    def _crear_placemark(self, nombre, descripcion, coordenadas, estilo):
        """Crea el fragmento XML para un marcador (Placemark) en el KML."""
        self.kml_contenido.append('  <Placemark>')
        self.kml_contenido.append(f'    <name>{nombre}</name>')
        self.kml_contenido.append(f'    <description>{descripcion}</description>')
        self.kml_contenido.append(f'    <styleUrl>{estilo}</styleUrl>')
        self.kml_contenido.append('    <Point>')
        self.kml_contenido.append(f'      <coordinates>{coordenadas}</coordinates>')
        self.kml_contenido.append('    </Point>')
        self.kml_contenido.append('  </Placemark>')

    def procesar_coordenadas_y_marcadores(self):
        """Extrae la información del árbol DOM utilizando expresiones XPath para los diferentes puntos y trazado."""
        puntos_ruta = [] # Lista para almacenar las coordenadas y dibujarlas como línea
        
        # 1. SALIDA (Color: Rojo)
        salida = self.raiz.find('.//uo:lugar_salida', self.espacio_nombres)
        if salida is not None:
            nombre = salida.find('uo:nombre', self.espacio_nombres).text
            coords = self._obtener_coordenadas(salida)
            self._crear_placemark(nombre, "Salida de la etapa", coords, "#rojo")
            puntos_ruta.append((0.0, coords)) # Distancia de salida es 0

        # 2. HITOS ETAPA (Color: Verde o Azul según el tipo)
        hitos = self.raiz.findall('.//uo:hitos_etapa/uo:hito', self.espacio_nombres)
        for hito in hitos:
            tipo = hito.get('tipo', '').lower()
            coords = self._obtener_coordenadas(hito)
            dist_str = hito.find('uo:distancia_salida', self.espacio_nombres).text
            distancia = float(dist_str) if dist_str else 0.0
            
            if 'puerto' in tipo:
                self._crear_placemark(tipo.title(), "Puerto de Montaña", coords, "#verde")
            elif 'sprint' in tipo:
                self._crear_placemark(tipo.title(), "Sprint Intermedio", coords, "#azul")
            
            puntos_ruta.append((distancia, coords))

        # 3. PUNTOS ANÓNIMOS (Color: Amarillo)
        anonimos = self.raiz.findall('.//uo:puntos_trayecto_anonimos/uo:punto_anonimo', self.espacio_nombres)
        for i, punto in enumerate(anonimos):
            coords = self._obtener_coordenadas(punto)
            dist_str = punto.find('uo:distancia_salida', self.espacio_nombres).text
            distancia = float(dist_str) if dist_str else 0.0
            
            self._crear_placemark(f"Punto Anónimo {i+1}", "Trayecto de etapa", coords, "#amarillo")
            puntos_ruta.append((distancia, coords))

        # 4. META (Color: Rojo)
        meta = self.raiz.find('.//uo:lugar_meta', self.espacio_nombres)
        if meta is not None:
            nombre = meta.find('uo:nombre', self.espacio_nombres).text
            coords = self._obtener_coordenadas(meta)
            self._crear_placemark(nombre, "Meta de la etapa", coords, "#rojo")
            
            # Obtener longitud de la etapa para calcular su distancia real final
            longitud = self.raiz.find('.//uo:datos_etapa/uo:longitud', self.espacio_nombres)
            if longitud is not None:
                puntos_ruta.append((float(longitud.text), coords))
            else:
                puntos_ruta.append((float('inf'), coords))

        # 5. CREACIÓN DE LA LÍNEA DEL TRAYECTO (LineString)
        # Se ordenan todos los puntos extraídos en base a su distancia_salida para dibujar un trayecto lógico
        puntos_ruta.sort(key=lambda x: x[0])
        cadena_coordenadas = " ".join([p[1] for p in puntos_ruta])
        
        self.kml_contenido.append('  <Placemark>')
        self.kml_contenido.append('    <name>Planimetría (Ruta completa)</name>')
        self.kml_contenido.append('    <styleUrl>#linea</styleUrl>')
        self.kml_contenido.append('    <LineString>')
        self.kml_contenido.append('      <tessellate>1</tessellate>')
        self.kml_contenido.append(f'      <coordinates>{cadena_coordenadas}</coordinates>')
        self.kml_contenido.append('    </LineString>')
        self.kml_contenido.append('  </Placemark>')

    def generar(self, nombre_salida):
        """Método orquestador para llamar a las partes y escribir el archivo."""
        self.escribir_prologo()
        self.procesar_coordenadas_y_marcadores()
        self.escribir_epilogo()
        
        with open(nombre_salida, 'w', encoding='utf-8') as archivo:
            archivo.write('\n'.join(self.kml_contenido))
        print(f"El archivo '{nombre_salida}' se ha generado correctamente.")

if __name__ == "__main__":
    # Se instancia la clase y se ejecuta la creación del KML
    generador = GeneradorKML("etapaEsquema.xml")
    generador.generar("etapa.kml")
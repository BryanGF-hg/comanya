hagamos un software ya sea con python o otra tecnologia como node.js donde
¿Qué le damos al software de ENTRADA?
· Web que tenga esas empresas (maps.google.com ; https://ranking-empresas.eleconomista.es/ranking_empresas_nacional.html?qSectorNorm=4662 
· CNAE (o le das un CPV)
· Provincia

¿Qué le damos al software de SALIDA?
(Excel)
· Listado de empresas con campos (nombre, email, teléfono y más si quieres)
· Listado de nombre empresas competidoras con campos
· Crecimiento/Decrecimiento

aqui tambien tienes mas informacion sobre competidores:
Cómo encontrar al competidor que el lead ya conoce
La clave no es encontrar cualquier competidor, sino el que maximiza el reconocimiento del lead. Aquí van las ideas ordenadas por proximidad geográfica, que es tu estructura natural:
https://ranking-empresas.eleconomista.es/ranking_empresas_nacional.html?qSectorNorm=4662 

🏘️ Mismo pueblo / misma ciudad
Estas son las fuentes más fiables para encontrar empresas locales conocidas:
Google Maps — búsqueda por sector + localidad, ordenado por número de reseñas (más reseñas = más conocido localmente)
Páginas Amarillas / Yelp — filtro por categoría + municipio, ordenable por valoraciones
LinkedIn — buscar empresas por sector + ciudad, fijarse en las que tienen más empleados
Registro Mercantil (BORME) — para cruzar tamaño real (facturación, empleados) con ubicación
🔑 Proxy de "tamaño visible": número de reseñas en Google + empleados en LinkedIn. Una empresa con 200 reseñas en un pueblo de 8.000 habitantes es casi seguro que todos la conocen.

🏙️ Misma provincia / nivel nacional
Aquí el criterio cambia: ya no basta con ser conocido, tiene que ser aspiracional o amenazante para el lead.
Ranking sectoriales — muchos sectores tienen rankings publicados en medios especializados o asociaciones del gremio
Trustpilot / Google — las empresas con más reseñas en ese sector a nivel nacional
Capterra / G2 (si es software o servicios digitales)
Expansion.com / El Economista — buscador de empresas con filtro por CNAE y provincia, muestra facturación
Infocif / Axesor / Einforma — bases de datos de empresas españolas con datos financieros y sector por CNAE

🤖 Cómo estructurarlo para que la IA lo scrape bien
Para que un agente de scraping encuentre al competidor correcto de forma automatizada, necesitas darle criterios objetivos y jerarquizados:
1. Mismo CNAE que el lead
2. Radio geográfico: pueblo → ciudad → provincia → nacional
3. Indicador de tamaño: empleados > X ó facturación > Y
4. Indicador de visibilidad: reseñas Google > Z
5. Que NO sea el propio lead
El competidor ideal es el más visible dentro del radio más pequeño posible que supere el umbral de tamaño. Así el lead casi siempre lo conoce.
Úsalo como lo que es: prueba social ultra-relevante, no solo “nombre famoso”.
El juego aquí es el de $100M Leads: personalización + prueba rápida = no cuelgan. [$100M Leads, Page 111]
Y el de Proof: cuanto más parecido al prospecto, más se lo cree. [$100M Playbook Proof Checklist, Page 10]
¿Qué tipo de competidor funciona mejor?
Orden de prioridad para TU caso (pymes que licitan):
Mismo sector + misma ciudad/área metropolitana + bastante más grande (3–20x)
Es el “John’s Doggy Daycare a una hora de ti” del ejemplo del libro. [$100M Leads, Page 111]
Probabilidad alta de que lo conozca, y aspiracional sin ser gigante inalcanzable.


Si no hay: mismo sector + misma provincia + bastante más grande
Sigue siendo “gente como yo, en mi zona”.


Solo si lo anterior falla: referente nacional del sector que salga en muchas licitaciones
Sirve más como autoridad que como “lo conozco personalmente”, pero sigue dando credibilidad.


Regla simple para la IA:
“Dame una empresa del mismo sector, 3–20 veces más grande que el lead, en su misma ciudad o provincia; si no hay, usa referente nacional del sector.”
¿Cómo definirlo para que la IA lo encuentre?
Para cada lead, que la IA busque:
Mismo CNAE / sector


Usar código CNAE o CPV principal del lead.
Filtrar empresas con el mismo CNAE / CPV.
Misma geografía (en este orden)


1º: mismo municipio o código postal.
2º: misma área metropolitana.
3º: misma provincia.
Tamaño “aspiracional”


Empleados o facturación aproximada 3–20x la del lead.
Si no tenéis dato del lead, usar:
microempresa → busca pequeña/mediana,
pequeña → busca mediana/grande.
Relevancia en licitaciones


Empresas con mayor nº de adjudicaciones o volumen adjudicado en los últimos 24 meses.
Eso asegura que:
a) el lead las vea como “van en serio con las licitaciones”,
b) tú tengas historia creíble tipo: “les ayudamos a estructurar su estrategia de licitaciones”.
La IA devuelve un “score” simple por empresa:
Score = (proximidad geográfica) + (tamaño relativo) + (nº adjudicaciones 24m)
Y te quedas con la de mayor score.
Fuentes de datos concretas para alimentar la IA
Ideas prácticas (no hace falta reinventar nada):
Plataformas de licitaciones / analítica de competencia


Cualquier herramienta que ya use datos del PLACSP y tenga módulo de “análisis competencia” / adjudicatarios.
Filtrar por CPV + provincia y ver quién gana más.
Registros y directorios empresariales


Directorios por CNAE + provincia (INE, cámaras de comercio, etc.).
Cruzar con tamaño (empleados / facturación si el directorio lo da).

Google Maps / búsqueda local


“ + ” → coger las 3–5 empresas más reseñadas / antiguas.
Esto mejora muchísimo el “lo conozco seguro”.


1. Filtra por CNAE
2. Aplica radio geográfico
3. Excluye lead
4. Aplica tamaño relativo
5. Ordena por score
6. Devuelve TOP 1–3
7. Devuelve SEC 4-5


para las filas del excel, tenemos los competidores y para las columnas combina los registros que me has dado (empresa,tipo,motivo, C-Email, C-Telefono, C-Web, D-Direccion, D-Municipio, D-distancia, E-CNAE, E-empleados, T-facturacion, T-score, T-Score de las reseñas  de Google, T-ranking, T-crecimiento, T-decrecimiento, T-tendencia) C- es contacto, D- son direccion, E- empleados, T- tecnico. si quieres modificalo a tu antojo. tambien coloca una nota dentro del excel para saber como se calcula el score. y creame como inicio un MVP de python contenido dentro de un 1 script ejecutable

y una posible arquitectura python a usar puede ser:
/app
 ├── main.py
 ├── scrapers/
 │   ├── google_maps.py
 │   ├── eleconomista.py
 │   ├── infocif.py
 ├── scoring/
 │   └── competitor_score.py
 ├── models/
 │   └── company.py
 ├── export/
 │   └── excel_export.py
 └── config.yaml

los datos sql:
class Company:
    def __init__(self, name, cnae, city, province):
        self.name = name
        self.cnae = cnae
        self.city = city
        self.province = province
        self.employees = None
        self.reviews = 0
        self.revenue = None
        self.licenses_won = 0

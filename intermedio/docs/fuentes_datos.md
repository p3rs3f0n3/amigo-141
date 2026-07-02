# Fuentes de Datos Abiertos — A.M.I.G.O.

**Evidencia de uso de datos abiertos — Concurso Datos al Ecosistema 2026**  
Equipo 141 | Nivel Intermedio

---

## Fuentes principales (integradas en el sistema)

### 1. Resultados Pruebas Saber 3°, 5° y 9°
- **ID Socrata:** `4h84-62xp`
- **Entidad:** ICFES
- **Endpoint:** `https://www.datos.gov.co/resource/4h84-62xp.json`
- **Portal:** https://www.datos.gov.co/dataset/Resultados-Pruebas-Saber-3-5-y-9-/4h84-62xp
- **Columnas usadas:** municipio del colegio, grado, periodo, puntaje matemáticas, puntaje lenguaje, zona, naturaleza
- **Uso en A.M.I.G.O.:** Dataset principal para construir el perfil de desempeño por municipio. Los puntajes se convierten en niveles (alto/medio/bajo/muy bajo) que determinan cómo la IA adapta el refuerzo académico.

### 2. MEN — Estadísticas en educación por municipio
- **ID Socrata:** `nudc-7mev`
- **Entidad:** Ministerio de Educación Nacional (MEN)
- **Endpoint:** `https://www.datos.gov.co/resource/nudc-7mev.json`
- **Portal:** https://www.datos.gov.co/Educaci-n/MEN_ESTADISTICAS_EN_EDUCACION_EN_PREESCOLAR-B-SICA/nudc-7mev
- **Filas:** 15.707 | **Columnas:** 41 | **Actualizado:** 2025-11-13
- **Columnas usadas:** municipio, año, tasa deserción intra-anual, tasa aprobación, tasa reprobación, cobertura neta
- **Uso en A.M.I.G.O.:** Complementa el perfil regional con indicadores de permanencia y riesgo de abandono escolar.

### 3. MEN — Estadísticas en educación por departamento
- **ID Socrata:** `ji8i-4anb`
- **Entidad:** MEN
- **Endpoint:** `https://www.datos.gov.co/resource/ji8i-4anb.json`
- **Filas:** 462 | **Columnas:** 37 | **Actualizado:** 2025-11-13
- **Uso en A.M.I.G.O.:** Respaldo cuando el municipio tiene muy pocos registros en las fuentes municipales.

### 4. DIVIPOLA — Códigos municipios geolocalizados
- **ID Socrata:** `vafm-j2df`
- **Entidad:** DANE / MinTIC
- **Endpoint:** `https://www.datos.gov.co/resource/vafm-j2df.json`
- **Filas:** 1.121 | **Columnas:** 8 | **Actualizado:** 2021-11-05
- **Uso en A.M.I.G.O.:** Llave principal de unión entre todos los datasets (código DANE de municipio) y coordenadas para el mapa de Leaflet.js.

---

## Fuentes secundarias (módulo de bienestar y mapa)

| Dataset | ID | Entidad | Uso |
|---|---|---|---|
| Encuesta Convivencia y Seguridad Ciudadana | `qawu-zaae` | DANE | Contexto de riesgo territorial |
| Directorio Único Establecimientos Educativos | `28t6-6wvz` | MEN | Mapa de colegios con Leaflet.js |
| Establecimientos Educativos Oficiales | `qnhy-zizv` | MEN | Georreferenciación instituciones |
| Batería indicadores niñez y adolescencia | `v9qk-hdcc` | Múltiples | Contexto social infantil |
| MEN Indicadores PAE | `epkg-mphw` | MEN | Alimentación escolar / vulnerabilidad |
| MinTIC Internet fijo por tecnología | `n48w-gutb` | MinTIC | Brecha digital territorial |
| Conectividad en instituciones educativas | `px6y-fznz` | MinTIC/MEN | Colegios con/sin internet |
| Población por grados — Valle del Cauca | `pvpi-9wjb` | Gobernación Valle | Contexto local Cali |

---

## Fuentes sin endpoint SODA (descarga directa)

| Fuente | Portal | Uso planificado |
|---|---|---|
| INS/SIVIGILA — Intento de suicidio | https://www.ins.gov.co/buscador-eventos | Línea base psicosocial territorial |
| ICBF — Vulneración derechos NNA | https://www.icbf.gov.co/estadisticas | Contexto maltrato infantil por municipio |
| DANE — Proyecciones de población | https://www.dane.gov.co | Denominador de tasas comparables |
| DANE — Pobreza Multidimensional | https://www.dane.gov.co | Drivers socioeconómicos del bajo desempeño |

---

## Cómo se consumen los datos

Todos los datasets con endpoint SODA se consumen vía API REST:

```
GET https://www.datos.gov.co/resource/{ID}.csv?$limit=5000
```

El módulo `src/datos_service.py` descarga, limpia y vectoriza los datos al iniciar el servidor. Ver catálogo completo de los 26 endpoints en [`endpoints_AMIGO.txt`](endpoints_AMIGO.txt).

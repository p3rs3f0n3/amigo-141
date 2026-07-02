# Diccionario de Datos — A.M.I.G.O.

## Perfil Regional (tabla consolidada por municipio)

Estructura resultante del procesamiento de los datasets de datos.gov.co.
Una fila por municipio. Llave principal: `cod_municipio` (código DANE 5 dígitos).

| Campo | Tipo | Origen | Descripción |
|---|---|---|---|
| `municipio` | texto | DIVIPOLA `vafm-j2df` | Nombre oficial del municipio |
| `cod_municipio` | texto (5) | DIVIPOLA `vafm-j2df` | Código DANE del municipio |
| `departamento` | texto | DIVIPOLA `vafm-j2df` | Nombre del departamento |
| `cod_departamento` | texto (2) | DIVIPOLA `vafm-j2df` | Código DANE del departamento |
| `latitud` | decimal | DIVIPOLA `vafm-j2df` | Latitud del centroide (mapa Leaflet) |
| `longitud` | decimal | DIVIPOLA `vafm-j2df` | Longitud del centroide (mapa Leaflet) |
| `nivel_matematicas` | categórico | Saber 3°5°9° `4h84-62xp` | alto / medio / bajo / muy bajo |
| `nivel_lectura` | categórico | Saber 3°5°9° `4h84-62xp` | alto / medio / bajo / muy bajo |
| `prom_matematicas_raw` | decimal | Saber 3°5°9° `4h84-62xp` | Promedio de puntaje en matemáticas |
| `prom_lectura_raw` | decimal | Saber 3°5°9° `4h84-62xp` | Promedio de puntaje en lenguaje |
| `area_mas_debil` | categórico | Derivado | Área con menor puntaje promedio |
| `n_registros_saber` | entero | Saber 3°5°9° `4h84-62xp` | Cantidad de estudiantes evaluados |
| `tasa_desercion` | decimal (%) | MEN municipio `nudc-7mev` | Tasa de deserción intra-anual |
| `tasa_aprobacion` | decimal (%) | MEN municipio `nudc-7mev` | Tasa de aprobación escolar |
| `fuente` | texto | Sistema | `datos_abiertos` o `fallback_local` |

---

## Variables de los datasets originales usadas en el RAG

### Saber 3°, 5° y 9° (`4h84-62xp`)

| Campo API | Descripción | Uso en A.M.I.G.O. |
|---|---|---|
| `cole_mcpio_ubicacion` | Municipio del colegio | Filtro por municipio del niño |
| `cole_depto_ubicacion` | Departamento del colegio | Contexto territorial |
| `grado` | Grado evaluado (3, 5 o 9) | Relevancia por edad |
| `periodo` | Año de la prueba | Temporal |
| `punt_matematicas` | Puntaje en matemáticas | Nivel del municipio en matemáticas |
| `punt_lenguaje` | Puntaje en lenguaje/lectura | Nivel del municipio en lectura |
| `cole_naturaleza` | Oficial / No oficial | Contexto institucional |
| `cole_area_ubicacion` | Urbana / Rural | Brecha urbano-rural |
| `fami_estratovivienda` | Estrato de la vivienda | Contexto socioeconómico |

### MEN estadísticas por municipio (`nudc-7mev`)

| Campo API | Descripción | Uso en A.M.I.G.O. |
|---|---|---|
| `entidad_territorial` / `municipio` | Nombre del municipio | Filtro por municipio |
| `anno` / `año` | Año de referencia | Temporal |
| `tasa_desercion_intraanual` | % deserción en el año | Riesgo de abandono |
| `tasa_aprobacion` | % aprobación | Permanencia escolar |
| `tasa_reprobacion` | % reprobación | Dificultad académica |
| `cobertura_neta` | % cobertura neta | Acceso al sistema educativo |

---

## Niveles de desempeño (campo derivado)

| Nivel | Rango de puntaje | Descripción |
|---|---|---|
| `alto` | ≥ 70 | Por encima del promedio nacional |
| `medio` | 50 – 69 | Promedio nacional |
| `bajo` | 35 – 49 | Por debajo del promedio |
| `muy bajo` | < 35 | Requiere refuerzo prioritario |

---

## Niveles de alerta de bienestar (módulo NLP)

| Nivel | Descripción | Acción del sistema |
|---|---|---|
| `ninguno` | Conversación normal | Responde la IA normalmente |
| `emocion` | Tristeza o preocupación leve | IA responde con empatía primero |
| `medio` | Bullying, maltrato, miedo intenso | Mensaje de apoyo directo, `escalar=true` |
| `alto` | Riesgo inmediato (ideación) | Mensaje de apoyo + Línea 106, `escalar=true` |

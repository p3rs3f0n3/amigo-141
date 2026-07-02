# Conclusiones y Próximos Pasos — A.M.I.G.O.

## Hallazgos principales

### Sobre los datos
- Los datasets de Pruebas Saber 3°, 5° y 9° del ICFES son la fuente más relevante para el público objetivo de 7-12 años — más que Saber 11, que mide grado 11.
- La API Socrata de datos.gov.co presenta intermitencia de disponibilidad; el sistema implementa un mecanismo de fallback para garantizar continuidad.
- El código DIVIPOLA es la llave de unión indispensable entre todos los datasets del Estado colombiano.
- Varios datasets clave (ICBF, SIVIGILA, DANE población) no tienen endpoint SODA público y requieren descarga directa de la entidad.

### Sobre el modelo RAG
- El enfoque TF-IDF + similitud coseno sobre documentos generados de filas reales de datos.gov.co es suficiente para un MVP de nivel intermedio sin necesidad de embeddings costosos.
- La personalización por edad (7 configs distintas) tiene impacto directo en la calidad percibida de las respuestas.
- El detector de riesgo basado en palabras clave tiene alta precisión en frases directas pero puede tener falsos negativos en lenguaje indirecto.

## Limitaciones

- Los datos de Saber 3°5°9° deben confirmarse en columnas exactas al momento de la integración (varían entre aplicaciones).
- El sistema no persiste datos entre reinicios del servidor (diseño MVP).
- El módulo de blockchain para registro de alertas está planificado para fase 2.
- El frontend React está en desarrollo.

## Próximos pasos

### Corto plazo (antes de la final — agosto 2026)
- [ ] Completar el frontend React con el chat y el mapa de Leaflet
- [ ] Ejecutar el script `explorar_endpoints_AMIGO.py` con el portal estable para confirmar columnas reales
- [ ] Integrar el perfil regional real con los datos descargados
- [ ] Generar los notebooks de EDA y limpieza con los datos reales

### Mediano plazo (fase 2)
- [ ] Integrar SIVIGILA e ICBF cuando los datos estén disponibles públicamente
- [ ] Implementar registro de alertas en blockchain (Ethereum/Sepolia)
- [ ] Agregar actualización nocturna automática de datasets
- [ ] Desplegar en servidor (VPS) con dominio público

### Largo plazo (escalabilidad nacional)
- [ ] Extender a todas las materias (ciencias, sociales, inglés)
- [ ] Agregar soporte multimodal (imágenes de tareas)
- [ ] Integrar con sistemas de información de secretarías de educación
- [ ] Módulo para docentes y padres de familia

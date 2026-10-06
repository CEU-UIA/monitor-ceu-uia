# Monitor CEU–UIA

Tablero interactivo desarrollado en Streamlit para centralizar indicadores de actividad, industria, macroeconomía, empleo, comercio exterior, mercados financieros y morosidad empresarial de la Argentina.

- Aplicación: [monitor-ceu-uia.streamlit.app](https://monitor-ceu-uia.streamlit.app/)
- Repositorio: [CEU-UIA/monitor-ceu-uia](https://github.com/CEU-UIA/monitor-ceu-uia)
- Lenguaje principal: Python 3.11

## Contenido del monitor

El punto de entrada principal es `app.py`. La aplicación usa un router propio basado en `st.session_state` y en el parámetro de URL `section`; no utiliza el sistema multipágina automático de Streamlit.

| Sección | Ruta interna | Módulo principal | Fuente o insumo principal |
|---|---|---|---|
| Inicio | `home` | `pages/home.py` | Navegación y noticias RSS |
| Producción industrial | `ipi` | `pages/ipi.py` | IPI manufacturero del INDEC |
| Actividad económica | `macro_pbi_emae` | `pages/macro_pbi_emae.py` | EMAE del INDEC y Datos Argentina |
| Macroeconomía | `macro_home` | `pages/macro_home.py` | Resumen de BCRA, INDEC y mercados |
| Tipo de cambio | `macro_fx` | `pages/macro_fx.py` | BCRA, REM, INDEC y CCL |
| Tasas, reservas y cartera | `macro_tasa` | `pages/macro_tasa.py` | BCRA |
| Precios | `macro_precios` | `pages/macro_precios.py` | IPC e IPIM del INDEC |
| Finanzas | `finanzas` | `pages/finanzas.py` | BCRA y Yahoo Finance |
| Empleo privado | `empleo` | `pages/empleo.py` | SIPA procesado localmente |
| Comercio exterior | `comex` | `pages/comex.py` | ICA del INDEC / Datos Argentina |

Todos los gráficos Plotly comparten fondo blanco, tipografía Montserrat, fechas y números en formato español, paleta institucional con color principal `#2C5378`, descarga en PNG y exportación de datos en CSV.

## Estructura del proyecto

```text
monitor-ceu-uia/
├── app.py                         # entrada principal, login y router
├── app_morosidad.py               # entrada opcional solo para morosidad
├── pages/                          # presentación y lógica de cada sección
├── services/                       # descarga, limpieza y normalización de datos
├── ui/
│   ├── charts.py                   # estándar común de gráficos y CSV
│   ├── common.py                   # navegación, formatos y logos
│   └── theme.py                    # estilos globales
├── utils/auth.py                   # autenticación por secrets.toml
├── assets/
│   ├── sipa/                       # CSV de empleo versionados
│   ├── mora_por_actividad2.xlsx    # base activa de morosidad
│   └── ...                         # logos y otros recursos
├── scripts/actualizar_sipa_assets.py
├── tests/test_market_data.py
├── requirements.txt
└── .streamlit/config.toml
```

La separación esperada es:

- `pages/`: arma la interfaz, los controles, los indicadores y las figuras.
- `services/`: obtiene y transforma los datos para entregarlos en formatos consistentes.
- `ui/`: concentra las reglas visuales compartidas.
- `assets/`: guarda imágenes y las bases que no se descargan en tiempo real.

## Fuentes y actualización de datos

La aplicación combina datos online y archivos locales versionados.

| Fuente | Uso principal | Modalidad | Caché aproximada |
|---|---|---|---|
| API de estadísticas del BCRA | Tipo de cambio, tasas, reservas y series monetarias | Online | 1 hora |
| Archivos del BCRA | REM, ITCRM, EMBI y calidad de cartera | Online | 1 a 12 horas |
| INDEC | IPI, EMAE, IPC e IPIM | Online | 1 a 12 horas |
| Datos Argentina | Comercio exterior y series de actividad | Online | 6 a 12 horas |
| ArgentinaDatos | Serie directa de CCL | Online | 1 hora |
| Yahoo Finance | Activos financieros y respaldo del CCL | Online | 6 horas |
| SIPA | Empleo total, sectorial e industrial | CSV locales | Actualización manual |
| Central de Deudores | Morosidad por sector y subsector | Excel local | Actualización manual |

Los tiempos anteriores corresponden a los decoradores `st.cache_data`. Un reinicio de la aplicación o el borrado de la caché fuerza una nueva consulta.

### CCL y brecha cambiaria

`services/market_data.py` prioriza la serie directa de contado con liquidación publicada por ArgentinaDatos. La normalización:

- utiliza venta y, si no existe un valor positivo, compra;
- elimina observaciones repetidas de fines de semana;
- conserva el valor original en `value_raw`;
- corrige únicamente un salto puntual mayor a 12% que se revierte en la rueda siguiente, siempre que los dos valores vecinos difieran 5% o menos; el reemplazo es el promedio de ambos vecinos.

Si la fuente directa falla, se usa temporalmente el cociente `YPFD.BA / YPF` de Yahoo Finance. La columna `source` permite identificar qué fuente se está mostrando.

### Actualizar los datos SIPA

La aplicación no descarga el Excel de SIPA durante cada ejecución. Lee los archivos de `assets/sipa/`, que se regeneran con:

```bash
python scripts/actualizar_sipa_assets.py
```

El script:

1. localiza la versión más reciente del Excel de trabajo registrado;
2. procesa las hojas total, sectorial y de subsectores industriales;
3. reemplaza los cinco CSV de `assets/sipa/`.

Después de ejecutarlo, hay que revisar las fechas y los cambios antes de commitear los CSV.

### Actualizar la morosidad

`pages/morosidad.py` lee la hoja `Monitor` de `assets/mora_por_actividad2.xlsx`. Este archivo no se actualiza automáticamente desde la interfaz; debe reemplazarse con una versión procesada que conserve el mismo nombre, hoja y estructura de columnas.

### Actualizar el IPI manufacturero

`services/ipi_data.py` descarga un archivo anual del INDEC. La URL contiene actualmente el año en el nombre del archivo. Cuando el INDEC publique una nueva versión anual, se debe verificar y, si corresponde, actualizar `sh_ipi_manufacturero_2026.xls` en ese servicio.


### Presentación y estilos

- Los estilos globales se aplican desde `ui/theme.py`.
- Los logos institucionales y la navegación compartida viven en `ui/common.py`.
- La fuente preferida es Montserrat, con respaldo en Segoe UI y Arial.
- Los textos visibles, ejes y nombres de columnas exportadas deben estar en español.
- En HTML enviado a `st.markdown`, el bloque debe comenzar en la primera columna para que Markdown no lo interprete como código.



## Despliegue en Streamlit Community Cloud

Configuración esperada:

- repositorio: `CEU-UIA/monitor-ceu-uia`;
- rama de producción: `main`;
- archivo principal: `app.py`;
- versión recomendada de Python: 3.11;
- secretos: copiar el contenido de `secrets.toml` en la configuración privada de la aplicación.

Los secretos nunca deben incluirse en commits, capturas o archivos compartidos. Después de modificar una fuente, un archivo de `assets` o una dependencia, conviene reiniciar la aplicación y verificar todas las secciones que consumen ese dato.


## Seguridad y alcance

- La autenticación actual sirve como control de acceso simple; no reemplaza un proveedor de identidad ni un sistema con roles y auditoría.
- Las credenciales deben administrarse únicamente mediante los secretos de Streamlit.
- Las fuentes financieras externas pueden tener demoras, revisiones o límites de consulta.
- El repositorio no incluye actualmente una licencia de software explícita. Antes de redistribuir el código fuera del ámbito acordado con CEU–UIA, definir las condiciones de uso.


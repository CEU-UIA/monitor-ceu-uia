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
| Morosidad | `morosidad` | `pages/morosidad.py` | Archivo local derivado de la Central de Deudores |

Todos los gráficos Plotly comparten fondo blanco, tipografía Montserrat, fechas y números en formato español, paleta institucional con color principal `#2C5378`, descarga en PNG y exportación de datos en CSV.

## Inicio rápido

### 1. Clonar el repositorio

```bash
git clone https://github.com/CEU-UIA/monitor-ceu-uia.git
cd monitor-ceu-uia
```

### 2. Crear el entorno virtual

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS o Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configurar usuarios locales

La aplicación principal requiere un archivo `.streamlit/secrets.toml`. Este archivo contiene credenciales y no debe subirse al repositorio.

Ejemplo mínimo:

```toml
[usuarios."1000"]
clave = "reemplazar-por-una-clave-segura"
nombre = "Usuario de desarrollo"

[usuarios."2000"]
clave = "otra-clave-segura"
nombre = "Segundo usuario"
```

El identificador escrito entre comillas funciona como número de socio. La autenticación implementada en `utils/auth.py` es deliberadamente simple y mantiene la sesión mediante `st.session_state`.

### 4. Ejecutar la aplicación

```bash
python -m streamlit run app.py
```

Streamlit abrirá, por defecto, `http://localhost:8501`.

Existe además un punto de entrada independiente para morosidad:

```bash
python -m streamlit run app_morosidad.py
```

`app_morosidad.py` no aplica actualmente el login de `app.py`. Si se publica como aplicación separada, debe evaluarse si corresponde agregar autenticación.

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

## Convenciones para desarrollar

### Navegación

Para agregar una sección nueva:

1. crear una función `render_<seccion>(go_to)` dentro de `pages/`;
2. importarla en `app.py`;
3. agregar la ruta al bloque del router;
4. incorporar el acceso desde `pages/home.py` o `pages/macro_home.py`;
5. usar `go_to("nombre_ruta")` para navegar y conservar el parámetro `section` en la URL.

Durante el desarrollo también se puede abrir una sección directamente, por ejemplo: `http://localhost:8501/?section=macro_fx`.

### Gráficos

Los gráficos nuevos deben renderizarse con el wrapper común:

```python
from ui.charts import plotly_chart

plotly_chart(
    fig,
    key="grafico_identificador_unico",
    image_filename="nombre_del_archivo",
    use_container_width=True,
)
```

No conviene llamar directamente a `st.plotly_chart`, porque se perderían el estilo institucional, la configuración en español y las descargas comunes. Si una sección ya implementa su propio CSV, puede usar `show_csv_download=False` para evitar dos botones de descarga.

### Presentación y estilos

- Los estilos globales se aplican desde `ui/theme.py`.
- Los logos institucionales y la navegación compartida viven en `ui/common.py`.
- La fuente preferida es Montserrat, con respaldo en Segoe UI y Arial.
- Los textos visibles, ejes y nombres de columnas exportadas deben estar en español.
- En HTML enviado a `st.markdown`, el bloque debe comenzar en la primera columna para que Markdown no lo interprete como código.

### Servicios y manejo de errores

- Las consultas externas deben tener `timeout`.
- Una falla de red debe producir un mensaje entendible o un `DataFrame` vacío con esquema estable.
- La descarga y limpieza de datos debe quedar en `services/`, no dentro de los componentes visuales, salvo casos heredados que todavía no fueron migrados.
- Las funciones cacheadas no deberían devolver silenciosamente datos inválidos que luego queden almacenados.
- Si cambia la estructura de un Excel oficial, revisar nombres de hojas, filas de encabezado y columnas antes de modificar la interfaz.

## Pruebas

Con el entorno virtual activo:

```bash
python -m unittest discover -s tests -v
```

Las pruebas actuales cubren principalmente la normalización y los controles de calidad de la serie directa de CCL.

Antes de abrir un pull request también se recomienda ejecutar:

```bash
python -m compileall -q app.py app_morosidad.py pages services ui utils scripts
git diff --check
```

El repositorio no tiene actualmente un flujo de integración continua que reemplace estas verificaciones locales.

## Despliegue en Streamlit Community Cloud

Configuración esperada:

- repositorio: `CEU-UIA/monitor-ceu-uia`;
- rama de producción: `main`;
- archivo principal: `app.py`;
- versión recomendada de Python: 3.11;
- secretos: copiar el contenido de `secrets.toml` en la configuración privada de la aplicación.

Los secretos nunca deben incluirse en commits, capturas o archivos compartidos. Después de modificar una fuente, un archivo de `assets` o una dependencia, conviene reiniciar la aplicación y verificar todas las secciones que consumen ese dato.

## Problemas frecuentes

### No aparece el formulario de acceso o se informa que faltan usuarios

Verificar que exista `.streamlit/secrets.toml`, que la tabla se llame `usuarios` y que cada identificador tenga `clave` y `nombre`.

### El IPI informa que INDEC devolvió HTML

Suele indicar que cambió la URL anual, que el servidor respondió con una página de error o que bloqueó temporalmente la descarga. Abrir la URL configurada en `services/ipi_data.py` y confirmar que entregue un `.xls` válido.

### Una serie online aparece vacía

Revisar primero la disponibilidad de la fuente. Luego borrar la caché de Streamlit o reiniciar la aplicación. Yahoo Finance y algunos archivos oficiales pueden responder de forma intermitente.

### Empleo muestra un período anterior

Ejecutar `scripts/actualizar_sipa_assets.py`, verificar la última fecha informada por el script y subir los CSV resultantes.

### Morosidad no refleja la última base

Confirmar que `assets/mora_por_actividad2.xlsx` fue reemplazado y que mantiene una hoja llamada `Monitor` con el esquema esperado.

## Flujo de trabajo sugerido

```bash
git switch main
git pull
git switch -c feature/nombre-del-cambio

# desarrollar y validar

git add <archivos-modificados>
git commit -m "Descripción breve del cambio"
git push -u origin feature/nombre-del-cambio
```

Abrir un pull request contra `main`, explicar qué fuente o sección se modificó y detallar cómo se validó. Para cambios de datos, incluir la última fecha disponible antes y después de la actualización.

## Seguridad y alcance

- La autenticación actual sirve como control de acceso simple; no reemplaza un proveedor de identidad ni un sistema con roles y auditoría.
- Las credenciales deben administrarse únicamente mediante los secretos de Streamlit.
- Las fuentes financieras externas pueden tener demoras, revisiones o límites de consulta.
- El repositorio no incluye actualmente una licencia de software explícita. Antes de redistribuir el código fuera del ámbito acordado con CEU–UIA, definir las condiciones de uso.

## Contacto funcional

La validación económica de indicadores, fuentes, fórmulas y textos corresponde al Centro de Estudios de la Unión Industrial Argentina (CEU–UIA). Los cambios técnicos que alteren definiciones o metodologías deberían revisarse con el equipo antes de pasar a producción.

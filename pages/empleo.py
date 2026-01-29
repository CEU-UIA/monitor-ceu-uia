import numpy as np
import pandas as pd
import streamlit as st

from services.metrics import calc_var, fmt, obtener_nombre_mes
from services.sipa_data import cargar_sipa_excel

def fmt_es(x, dec=1):
	if pd.isna(x):
		return "s/d"
	return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_empleo(go_to):
	if st.button("← Volver"):
		go_to("home")


	st.markdown(
"""
<style>
/* Wrapper panel tipo CEU */
.emp-wrap{
  background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
  border: 1px solid #dfeaf6;
  border-radius: 22px;
  padding: 14px;
  box-shadow: 0 10px 24px rgba(15, 55, 100, 0.16),
			  inset 0 0 0 1px rgba(255,255,255,0.55);
  margin-top: 8px;
}

/* Header card */
.emp-title-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin-bottom: 10px;
  padding-left: 4px;
}

.emp-title-left{
  display:flex;
  align-items:center;
  gap:12px;
}

.emp-icon-badge{
  width: 64px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(180deg, #e7eef6 0%, #dfe7f1 100%);
  border: 1px solid rgba(15,23,42,0.10);
  display:flex;
  align-items:center;
  justify-content:center;
  box-shadow: 0 8px 14px rgba(15,55,100,0.12);
  font-size: 30px;
  flex: 0 0 auto;
}

.emp-title{
  font-size: 23px;
  font-weight: 900;
  letter-spacing: -0.01em;
  color: #14324f;
  margin: 0;
  line-height: 1.0;
}

.emp-subtitle{
  font-size: 14px;
  font-weight: 800;
  color: rgba(20,50,79,0.78);
  margin-top: 2px;
}

.emp-fuente{
  font-size: 12px;
  font-weight: 800;
  color: rgba(20,50,79,0.78);
  margin-top: 2px;
}

/* Card principal*/
.emp-card{
  background: rgba(255,255,255,0.94);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 18px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10);
}

.emp-row{
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  column-gap: 14px;
}

.emp-value{
  font-size: 46px;
  font-weight: 950;
  letter-spacing: -0.02em;
  color: #14324f;
  line-height: 0.95;
}

.emp-meta{
  font-size: 16px;
  color: #2b4660;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.emp-meta .sep{ opacity: 0.40; padding: 0 6px; }

.emp-pills{
  display:flex;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
  white-space: nowrap;
}

.emp-pill{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 12px;
  border: 1px solid rgba(15,23,42,0.10);
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 6px 10px rgba(15,55,100,0.08);
}

.emp-pill .lab{ color:#2b4660; font-weight: 800; }

.emp-pill.red{
  background: linear-gradient(180deg, rgba(220,38,38,0.08) 0%, rgba(220,38,38,0.05) 100%);
}
.emp-pill.green{
  background: linear-gradient(180deg, rgba(22,163,74,0.10) 0%, rgba(22,163,74,0.06) 100%);
}
.emp-up{ color:#168a3a; font-weight: 900; }
.emp-down{ color:#cc2e2e; font-weight: 900; }

/* Badge circular con puestos (el “circulito”) */
.emp-badge{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,0.10);
  font-size: 16px;
  font-weight: 800;
  margin-top: 6px;
  width: fit-content;
}
.emp-badge.red{ background: rgba(220,38,38,0.07); }
.emp-badge.green{ background: rgba(22,163,74,0.08); }

/* Link “Informe CEU” */
.emp-report a{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid #e5e7eb;
  background:#ffffff;
  color:#0f172a;
  font-size:12px;
  font-weight:700;
  text-decoration:none;
  box-shadow:0 2px 4px rgba(0,0,0,0.06);
}

/* Responsive */
@media (max-width: 900px){
  .emp-row{ grid-template-columns: 1fr; row-gap: 10px; }
  .emp-meta{ white-space: normal; }
  .emp-pills{ justify-content: flex-start; flex-wrap: wrap; }
}
/* Grid 3 KPIs iguales */
.emp-kpi-grid{
  display:grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 26px;
  align-items: start;
  margin-top: 4px;
}

.emp-kpi .emp-meta{
  margin-bottom: 6px;
}

.emp-kpi .emp-value{
  font-size: 44px; /* igual que mensual */
}

@media (max-width: 900px){
  .emp-kpi-grid{ grid-template-columns: 1fr; gap: 14px; }
}
</style>
""",
unsafe_allow_html=True
)

	with st.spinner("Cargando SIPA..."):
		df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa = cargar_sipa_excel()

	if df_total.empty:
		st.error("No se pudieron cargar los datos SIPA desde el Excel.")
		return

	ult_f = df_total["fecha"].iloc[-1]
	target_date = pd.Timestamp("2023-08-01")
	s_orig = df_total["orig"]
	s_sa = df_total["sa"]

	# Escala: miles vs puestos
	try:
		scale = 1000 if (pd.to_numeric(s_sa.dropna()).median() < 1_000_000) else 1
	except Exception:
		scale = 1000

	# Total
	m_e = calc_var(s_sa, 1)
	m_p = s_sa.diff().iloc[-1] * scale
	i_e = calc_var(s_orig, 12)
	i_p = s_orig.diff(12).iloc[-1] * scale

	try:
		val_23 = df_total.loc[df_total["fecha"] == target_date, "sa"].iloc[0]
		v23_pct = ((s_sa.iloc[-1] / val_23) - 1) * 100 if val_23 != 0 else np.nan
		v23_p = (s_sa.iloc[-1] - val_23) * scale
	except Exception:
		v23_pct = v23_p = np.nan

	INFORME_CEU_URL = "https://uia.org.ar/centro-de-estudios/documentos/actualidad-industrial/?q=Laborales"

	# Helpers de signo para color/flecha
	def _cls(x):
		return "green" if (x is not None and not pd.isna(x) and x >= 0) else "red"
	def _arrow(x):
		return "▲" if (x is not None and not pd.isna(x) and x >= 0) else "▼"

	mes_txt = obtener_nombre_mes(ult_f)

	m_cls = _cls(m_e); i_cls = _cls(i_e); v_cls = _cls(v23_pct)

	m_pct = f"{fmt_es(m_e, 1)}%"
	m_badge = f"{fmt(m_p, 0 , True)} puestos"

	i_pct = f"{fmt_es(i_e, 1)}%"
	i_badge = f"{fmt(i_p, 0, True)} puestos"

	v_pct = f"{fmt_es(v23_pct, 1)}%"
	v_badge = f"{fmt(v23_p, 0, True)} puestos"

	
	def _cls(x):
		return "green" if (x is not None and not pd.isna(x) and x >= 0) else "red"
	def _arrow(x):
		return "▲" if (x is not None and not pd.isna(x) and x >= 0) else "▼"

	m_cls = _cls(m_e); i_cls = _cls(i_e); v_cls = _cls(v23_pct)

	m_pct = f"{fmt(m_e, 1)}%"
	m_badge = f"{fmt(m_p, 0, True)} puestos"

	i_pct = f"{fmt(i_e, 1)}%"
	i_badge = f"{fmt(i_p, 0, True)} puestos"

	v_pct = f"{fmt(v23_pct, 1)}%"
	v_badge = f"{fmt(v23_p, 0, True)} puestos"

	st.markdown(
	f"""
	<div class="emp-wrap">
	<div class="emp-title-row">
		<div class="emp-title-left">
		<div class="emp-icon-badge">💼</div>
		<div>
			<div class="emp-title">Empleo Privado registrado - {mes_txt}</div>
			<div class="emp-subtitle">Fuente: SIPA</div>
		</div>
		</div>
		<div class="emp-report">
		<a href="{INFORME_CEU_URL}" target="_blank">📄 Ver último Informe de Indicadores Laborales</a>
		</div>
	</div>

<div class="emp-card">
		<div class="emp-kpi-grid">

<div class="emp-kpi">
			<div class="emp-meta">Mensual (s.e)</div>
			<div class="emp-value">{m_pct}</div>
			<div class="emp-badge {m_cls}">{_arrow(m_e)} {m_badge}</div>
	</div>

<div class="emp-kpi">
			<div class="emp-meta">Interanual</div>
			<div class="emp-value">{i_pct}</div>
			<div class="emp-badge {i_cls}">{_arrow(i_e)} {i_badge}</div>
</div>

<div class="emp-kpi">
			<div class="emp-meta">vs Agosto 2023</div>
			<div class="emp-value">{v_pct}</div>
			<div class="emp-badge {v_cls}">{_arrow(v23_pct)} {v_badge}</div>
	</div>
<div class="emp-note" style="font-size: 12px">
			Nota: (s.e) = sin estacionalidad.
		</div>
	</div>
	</div>
	</div>
	""",
	unsafe_allow_html=True
	)


	# Sectores
	if df_sec_orig.empty or df_sec_sa.empty:
		st.warning("No se pudieron leer las hojas de sectores.")
		return

	tmp = df_sec_orig.merge(df_sec_sa, on="fecha", how="inner", suffixes=("_orig", "_sa")).sort_values("fecha")
	sectores = [c for c in df_sec_orig.columns if c != "fecha"]

	resumen = []
	ind_data = None

	for sec in sectores:
		col_o = f"{sec}_orig"
		col_s = f"{sec}_sa"
		if col_o not in tmp.columns or col_s not in tmp.columns:
			continue

		ss_orig = tmp[col_o]
		ss_sa = tmp[col_s]

		if "industria" in sec.lower():
			ind_data = {"orig": ss_orig, "sa": ss_sa, "name": sec, "tmp": tmp}

		try:
			val_23_sec = tmp.loc[tmp["fecha"] == target_date, col_s].iloc[0]
			pct_23 = ((ss_sa.iloc[-1] / val_23_sec) - 1) * 100 if val_23_sec != 0 else np.nan
			puestos_23 = (ss_sa.iloc[-1] - val_23_sec) * scale
		except Exception:
			pct_23 = puestos_23 = np.nan

		resumen.append(
			{
				"Sector": sec,
				"Mensual %": calc_var(ss_sa, 1),
				"Mensual (puestos)": ss_sa.diff().iloc[-1] * scale,
				"Interanual %": calc_var(ss_orig, 12),
				"Interanual (puestos)": ss_orig.diff(12).iloc[-1] * scale,
				"vs Ago-23 %": pct_23,
				"vs Ago-23 (puestos)": puestos_23,
			}
		)

	if resumen:
		st.write("#### Sectores Generales")
		st.dataframe(
			pd.DataFrame(resumen).style.format(
				{
					"Mensual %": lambda x: fmt_es(x,1)+"%",
					"Mensual (puestos)":  lambda x: fmt_es(x, 0),
					"Interanual %": lambda x: fmt_es(x, 1) + "%",
					"Interanual (puestos)": lambda x: fmt_es(x, 0),
					"vs Ago-23 %": lambda x: fmt_es(x, 1) + "%",
					"vs Ago-23 (puestos)": lambda x: fmt_es(x, 0),
				},
				na_rep="s/d",
			),
			width="stretch",
			hide_index=True,
		)

	# Bloque Industria
	st.divider()
	if ind_data is not None:
			# ===== cálculos (NO visuales) =====
				isa = ind_data["sa"]
				iorig = ind_data["orig"]
				tmp2 = ind_data["tmp"]

				mi_e = calc_var(isa, 1)
				mi_p = isa.diff().iloc[-1] * scale
				ii_e = calc_var(iorig, 12)
				ii_p = iorig.diff(12).iloc[-1] * scale

				try:
					ival_23 = tmp2.loc[tmp2["fecha"] == target_date, ind_data["name"] + "_sa"].iloc[0]
					iv23_pct = ((isa.iloc[-1] / ival_23) - 1) * 100 if ival_23 != 0 else np.nan
					iv23_p = (isa.iloc[-1] - ival_23) * scale
				except Exception:
					iv23_pct = iv23_p = np.nan

    # ===== render NUEVO (HTML) =====
    # helpers
				def _cls(x):
					return "green" if (x is not None and not pd.isna(x) and x >= 0) else "red"

				def _arrow(x):
					return "▲" if (x is not None and not pd.isna(x) and x >= 0) else "▼"

				mes_txt = obtener_nombre_mes(ult_f)

				mi_cls = _cls(mi_e)
				ii_cls = _cls(ii_e)
				iv_cls = _cls(iv23_pct)

				mi_pct = f"{fmt(mi_e, 1)}%"
				mi_badge = f"{fmt(mi_p, 0, True)} puestos"

				ii_pct = f"{fmt(ii_e, 1)}%"
				ii_badge = f"{fmt(ii_p, 0, True)} puestos"

				iv_pct = f"{fmt(iv23_pct, 1)}%"
				iv_badge = f"{fmt(iv23_p, 0, True)} puestos"

				st.markdown(
					f"""
					<div class="emp-wrap" style="margin-top:14px;">
					<div class="emp-title-row">
						<div class="emp-title-left">
						<div class="emp-icon-badge">🏭</div>
						<div>
							<div class="emp-title">Empleo Industrial</div>
							<div class="emp-subtitle">{mes_txt}</div>
							<div class="emp-fuente">Fuente: SIPA</div>
						</div>
						</div>
					</div>

					<div class="emp-card">
						<div class="emp-kpi-grid">

					<div class="emp-kpi">
							<div class="emp-meta">Mensual (s.e)</div>
							<div class="emp-value">{mi_pct}</div>
							<div class="emp-badge {mi_cls}">{_arrow(mi_e)} {mi_badge}</div>
					</div>

					<div class="emp-kpi">
							<div class="emp-meta">Interanual</div>
							<div class="emp-value">{ii_pct}</div>
							<div class="emp-badge {ii_cls}">{_arrow(ii_e)} {ii_badge}</div>
					</div>

					<div class="emp-kpi">
							<div class="emp-meta">vs Agosto 2023</div>
							<div class="emp-value">{iv_pct}</div>
							<div class="emp-badge {iv_cls}">{_arrow(iv23_pct)} {iv_badge}</div>
					</div>

					</div>
					</div>
					</div>
					""",
					unsafe_allow_html=True
				)
		

	# Subsectores industriales
	if df_sub_orig.empty or df_sub_sa.empty:
		st.info("No se encontraron datos de subsectores industriales (A.6.1 / A.6.2).")
		return

	st.write("#### Subsectores Industriales")
	tmpsub = df_sub_orig.merge(df_sub_sa, on="fecha", how="inner", suffixes=("_orig", "_sa")).sort_values("fecha")
	subs = [c for c in df_sub_orig.columns if c != "fecha"]

	res_sub = []
	for sb in subs:
		col_o_s = f"{sb}_orig"
		col_s_s = f"{sb}_sa"
		if col_o_s not in tmpsub.columns or col_s_s not in tmpsub.columns:
			continue

		sbs_orig = tmpsub[col_o_s]
		sbs_sa = tmpsub[col_s_s]

		try:
			v23_sb = tmpsub.loc[tmpsub["fecha"] == target_date, col_s_s].iloc[0]
			p23_sb = ((sbs_sa.iloc[-1] / v23_sb) - 1) * 100 if v23_sb != 0 else np.nan
			d23_sb = (sbs_sa.iloc[-1] - v23_sb) * scale
		except Exception:
			p23_sb = d23_sb = np.nan

		res_sub.append(
			{
				"Subsector": sb,
				"Mensual %": calc_var(sbs_sa, 1),
				"Mensual (puestos)": sbs_sa.diff().iloc[-1] * scale,
				"Interanual %": calc_var(sbs_orig, 12),
				"Interanual (puestos)": sbs_orig.diff(12).iloc[-1] * scale,
				"vs Ago-23 %": p23_sb,
				"vs Ago-23 (puestos)": d23_sb,
			}
		)

	if res_sub:
		st.dataframe(
			pd.DataFrame(res_sub).style.format(
				{
					"Mensual %": lambda x: fmt_es(x, 1) + "%",
					"Mensual (puestos)": lambda x: fmt_es(x, 0),
					"Interanual %": lambda x: fmt_es(x, 1) + "%",
					"Interanual (puestos)": lambda x: fmt_es(x, 0),
					"vs Ago-23 %": lambda x: fmt_es(x, 1) + "%",
					"vs Ago-23 (puestos)": lambda x: fmt_es(x, 0),
				},
				na_rep="s/d",
			),
			width="stretch",
			hide_index=True
		)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json

st.set_page_config(page_title="Patient Health Intelligence", page_icon="🩺", layout="wide")

# ── Load Data ────────────────────────────────────────────────────
@st.cache_data(ttl=0)
def load_data():
    df = pd.read_csv("patient_health_data.csv", parse_dates=["date_of_test"])
    summary = pd.read_csv("patient_summary.csv")
    return df, summary

df, summary = load_data()

URGENCY = ['steadily_worsening','new_problem_emerging','approaching_risk',
           'relapsing','chronically_abnormal_stable','recovering',
           'steadily_improving','stable_normal','insufficient_data']

URGENCY_COLOR = {
    'steadily_worsening': '#e74c3c',
    'new_problem_emerging': '#e67e22',
    'approaching_risk': '#f39c12',
    'relapsing': '#d35400',
    'chronically_abnormal_stable': '#8e44ad',
    'recovering': '#27ae60',
    'steadily_improving': '#2ecc71',
    'stable_normal': '#3498db',
    'insufficient_data': '#95a5a6',
}

# ── Sidebar ─────────────────────────────────────────────────────
st.sidebar.title("🩺 Health Vector PoC")
page = st.sidebar.radio("Navigate", ["Patient Explorer", "Risk Ranking", "Population Insights"])

# ── Page 1: Patient Explorer ────────────────────────────────────
if page == "Patient Explorer":
    st.title("Patient Explorer")

    patient_ids = sorted(df["patient_id"].unique())
    col1, col2 = st.columns([2, 3])
    with col1:
        selected_pid = st.selectbox("Select Patient", patient_ids)
    with col2:
        row = summary[summary["patient_id"] == selected_pid].iloc[0]
        traj_dict = json.loads(row["param_trends"])
        worst = row["worst_trajectory"]
        c = URGENCY_COLOR.get(worst, "#95a5a6")
        st.markdown(f"""
        **Gender:** {row['gender']} &nbsp;|&nbsp;
        **Age Band:** {row['age_band']} &nbsp;|&nbsp;
        **Total Visits:** {row['total_visits']} &nbsp;|&nbsp;
        **Burden Trend:** {row['burden_trend']}
        """)
        st.markdown(f'<span style="background:{c};color:white;padding:4px 12px;border-radius:8px;font-weight:bold;">Worst: {worst}</span>', unsafe_allow_html=True)

    # LLM Summary
    st.subheader("Clinical Summary")
    st.info(row["llm_summary"] if pd.notna(row["llm_summary"]) else "No summary available.")

    # Trajectory labels per parameter
    st.subheader("Parameter Trajectories")
    cols = st.columns(4)
    for i, (param, traj) in enumerate(traj_dict.items()):
        c = URGENCY_COLOR.get(traj, "#95a5a6")
        with cols[i % 4]:
            st.markdown(f"""
            <div style="border-radius:8px;padding:10px;background:{c}22;border-left:4px solid {c};margin:4px 0">
            <b>{param}</b><br><small style="color:{c}">{traj}</small>
            </div>""", unsafe_allow_html=True)

    # Trend charts per parameter
    st.subheader("Result Trends Over Time")
    patient_df = df[df["patient_id"] == selected_pid].sort_values("date_of_test")
    params = sorted(patient_df["param_name"].unique())
    ncols = 3
    chart_cols = st.columns(ncols)

    for i, param in enumerate(params):
        sub = patient_df[patient_df["param_name"] == param]
        if sub.empty:
            continue
        lo = sub["low_range"].iloc[0]
        hi = sub["high_range"].iloc[0]
        label = sub["parameter_label"].iloc[0]
        traj = traj_dict.get(param, "unknown")
        color = URGENCY_COLOR.get(traj, "#3498db")

        fig = go.Figure()
        # Normal band
        fig.add_hrect(y0=lo, y1=hi, fillcolor="rgba(46,204,113,0.10)", line_width=0, annotation_text="Normal", annotation_position="top left")
        fig.add_hline(y=lo, line_dash="dot", line_color="green", line_width=1)
        fig.add_hline(y=hi, line_dash="dot", line_color="red", line_width=1)
        fig.add_trace(go.Scatter(
            x=sub["date_of_test"], y=sub["result"],
            mode="lines+markers", name=label,
            line=dict(color=color, width=2), marker=dict(size=5)
        ))
        fig.update_layout(
            title=dict(text=f"{label} — <i>{traj}</i>", font=dict(size=12)),
            height=220, margin=dict(l=20,r=10,t=40,b=20),
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(title=sub["unit"].iloc[0] if pd.notna(sub["unit"].iloc[0]) else "")
        )
        with chart_cols[i % ncols]:
            st.plotly_chart(fig, use_container_width=True)

# ── Page 2: Risk Ranking ─────────────────────────────────────────
elif page == "Risk Ranking":
    st.title("Patient Risk Ranking")
    st.markdown("Patients sorted from most to least urgent based on trajectory and burden signals.")

    urgency_rank = {u: i for i, u in enumerate(URGENCY)}
    ranked = summary.copy()
    ranked["urgency_rank"] = ranked["worst_trajectory"].map(urgency_rank).fillna(99)
    ranked = ranked.sort_values(["urgency_rank", "burden_trend"]).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        traj_filter = st.multiselect("Filter by worst trajectory", URGENCY, default=URGENCY[:5])
    with col2:
        burden_filter = st.multiselect("Filter by burden trend", ["worsening","stable","improving"], default=["worsening","stable","improving"])

    display = ranked[ranked["worst_trajectory"].isin(traj_filter) & ranked["burden_trend"].isin(burden_filter)].copy()

    def color_row(row):
        c = URGENCY_COLOR.get(row["worst_trajectory"], "#95a5a6")
        return [f"background-color:{c}22"] * len(row)

    cols_show = ["rank","patient_id","gender","age_band","total_visits","worst_trajectory","burden_trend","current_abnormal_params"]
    st.dataframe(
        display[cols_show].style.apply(color_row, axis=1),
        use_container_width=True, height=500
    )

    st.markdown(f"**Showing {len(display)} of {len(ranked)} patients**")

# ── Page 3: Population Insights ──────────────────────────────────
elif page == "Population Insights":
    st.title("Population-Level Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Worst-Parameter Trajectory Distribution")
        wt_counts = summary["worst_trajectory"].value_counts().reindex(URGENCY).dropna()
        fig = go.Figure(go.Bar(
            x=wt_counts.values, y=wt_counts.index,
            orientation="h",
            marker_color=[URGENCY_COLOR.get(t, "#95a5a6") for t in wt_counts.index]
        ))
        fig.update_layout(height=350, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Overall Burden Trend")
        bt_counts = summary["burden_trend"].value_counts()
        fig = px.pie(values=bt_counts.values, names=bt_counts.index,
                     color_discrete_sequence=["#e74c3c","#3498db","#2ecc71","#95a5a6"])
        fig.update_layout(height=350, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Abnormality Rate per Parameter")
    from scipy import stats as scipy_stats

    def is_abnormal(result, lo, hi, param):
        if param in ('hdl', 'total_protein'):
            return result < lo
        return result < lo or result > hi

    df2 = df.copy()
    df2["abnormal"] = df2.apply(lambda r: is_abnormal(r["result"], r["low_range"], r["high_range"], r["param_name"]), axis=1)
    abn_rate = (df2.groupby("param_name")["abnormal"].mean() * 100).round(1).sort_values(ascending=False)
    fig = px.bar(x=abn_rate.index, y=abn_rate.values,
                 labels={"x":"Parameter","y":"Abnormal Results (%)"},
                 color=abn_rate.values, color_continuous_scale="RdYlGn_r")
    fig.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Parameter Co-occurrence Heatmap")
    abn_visit = df2[df2["abnormal"]][["patient_id","date_of_test","param_name"]].drop_duplicates()
    merged = abn_visit.merge(abn_visit, on=["patient_id","date_of_test"])
    merged = merged[merged["param_name_x"] < merged["param_name_y"]]
    cooccur = merged.groupby(["param_name_x","param_name_y"]).size().reset_index(name="count")

    params_list = sorted(df["param_name"].unique())
    comat = pd.DataFrame(0, index=params_list, columns=params_list)
    for _, row in cooccur.iterrows():
        comat.loc[row["param_name_x"], row["param_name_y"]] = row["count"]
        comat.loc[row["param_name_y"], row["param_name_x"]] = row["count"]

    fig = px.imshow(comat, text_auto=True, color_continuous_scale="Blues",
                    title="Co-occurrence: Both Params Abnormal on Same Visit")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

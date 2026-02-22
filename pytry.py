import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

np.random.seed(42)

# sidebar
st.set_page_config(page_title="Electricity for Bobcity", layout="wide")
st.title("Dynamic map simulation of the buildings in the city")

st.sidebar.header("Money")
base_budget = st.sidebar.number_input("Money per year)", value=100)
budget_growth = st.sidebar.number_input("Increase in money per year", value=10)

st.sidebar.header("Number of building at start")
init_apartments = st.sidebar.number_input("Flats", value=40000, step=1000)
init_houses = st.sidebar.number_input("Private mansions", value=5000, step=500)
init_public = st.sidebar.number_input("Government buildings", value=300, step=50)

st.sidebar.header("Building growth rate (per year)")
growth_apartments = st.sidebar.number_input("Flats (%)", value=2.0, step=0.5) / 100
growth_houses = st.sidebar.number_input("Private mansions (%)", value=1.5, step=0.5) / 100
growth_public = st.sidebar.number_input("Government buildings (%)", value=0.5, step=0.5) / 100

monthly_cons = [250, 400, 3000]
cat_names = ["Flats", "Private mansions", "Government buildings"]

measures = [
    {"name": "LED lightning", "cost": 15, "eff": 0.08, "stepPct": 20, "allowed": [True, True, True]},
    {"name": "Insulation", "cost": 25, "eff": 0.15, "stepPct": 10, "allowed": [True, True, True]},
    {"name": "Solar panels", "cost": 30, "eff": 0.20, "stepPct": 5, "allowed": [True, True, True]},
    {"name": "Smart-counters", "cost": 10, "eff": 0.05, "stepPct": 25, "allowed": [True, True, True]},
    {"name": "Smart house system", "cost": 6, "eff": 0.03, "stepPct": 15, "allowed": [True, True, True]}
]

# map simulation
def dynamic_simulation():
    strats = ["DP-model", "Greedy", "Expensive (max %)", "Cheap (min price)"]
    
    state = {s: {"budget": 0, "cov": [[0.0 for _ in measures] for _ in range(3)]} for s in strats}
    
    history = {s: [] for s in strats}
    buildings_history = {}
    current_counts = [init_apartments, init_houses, init_public]

    for year in range(1, 11):
        if year > 1:
            new_counts = [int(current_counts[i] * (1 + [growth_apartments, growth_houses, growth_public][i])) for i in range(3)]
            for s in strats:
                for c in range(3):
                    for m in range(len(measures)):
                        if new_counts[c] > 0:
                            state[s]["cov"][c][m] *= (current_counts[c] / new_counts[c])
            current_counts = new_counts
            
        buildings_history[year] = current_counts.copy()
        
        E0 = [current_counts[i] * monthly_cons[i] * 12 for i in range(3)]
        yearly_total_base = sum(E0)
        
        yearly_injection = base_budget + (year - 1) * budget_growth
        for s in strats:
            state[s]["budget"] += yearly_injection

        # greedy strategy

        for s in ["Greedy", "Expensive (max %)", "Cheap (min price)"]:
            B = state[s]["budget"]
            cov = [row[:] for row in state[s]["cov"]]
            spent = 0
            purchases = [[0]*len(measures) for _ in range(3)]
            
            while True:
                best_action = None
                best_score = -1e100
                
                for c in range(3):
                    for m_idx, m in enumerate(measures):
                        if not m["allowed"][c] or cov[c][m_idx] >= 0.9999 or spent + m["cost"] > B:
                            continue
                            
                        step_size = m["stepPct"] / 100.0
                        new_c = min(1.0, cov[c][m_idx] + step_size)
                        
                        f_cur = math.prod(1.0 - mx["eff"] * cov[c][i] for i, mx in enumerate(measures) if mx["allowed"][c])
                        f_new = math.prod(1.0 - mx["eff"] * (new_c if i == m_idx else cov[c][i]) for i, mx in enumerate(measures) if mx["allowed"][c])
                        
                        savings = E0[c] * (f_cur - f_new)
                        
                        if s == "Greedy": score = savings / m["cost"]
                        elif s == "Expensive (max %)": score = savings
                        else: score = -m["cost"]
                        
                        if score > best_score:
                            best_score = score
                            best_action = (c, m_idx, m)
                
                if not best_action: break
                
                c, m_idx, m = best_action
                spent += m["cost"]
                purchases[c][m_idx] += 1
                cov[c][m_idx] = min(1.0, cov[c][m_idx] + m["stepPct"] / 100.0)

            applied_texts = []
            for c in range(3):
                cat_acts = []
                for m_idx, count in enumerate(purchases[c]):
                    if count > 0:
                        added_pct = min(1.0 - state[s]["cov"][c][m_idx], count * measures[m_idx]["stepPct"] / 100.0) * 100
                        cat_acts.append(f"{measures[m_idx]['name']} (+{int(added_pct)}%)")
                if cat_acts: applied_texts.append(f"[{cat_names[c]}] " + ", ".join(cat_acts))

            state[s]["budget"] -= spent
            state[s]["cov"] = cov
            
            final_E = sum(E0[c] * math.prod(1.0 - mx["eff"] * cov[c][i] for i, mx in enumerate(measures) if mx["allowed"][c]) for c in range(3))
            history[s].append({
                "Year": year, "Money per year (st)": B, "Spent": spent, "Left": state[s]["budget"],
                "Usage (kWh-hour)": final_E, "Saved from the original": yearly_total_base - final_E,
                "Measurements (done)": "; ".join(applied_texts) if applied_texts else "-"
            })

        # DP-model

        s_dp = "DP-model"
        B = int(state[s_dp]["budget"])
        cov = [row[:] for row in state[s_dp]["cov"]]
        best_at_most = []
        allowed_lists = []

        for c in range(3):
            allowed_m = [(i, m) for i, m in enumerate(measures) if m["allowed"][c]]
            allowed_lists.append(allowed_m)
            
            f_base = math.prod(1.0 - mx["eff"] * cov[c][orig_idx] for orig_idx, mx in allowed_m)
            E_base = E0[c] * f_base
            
            best_exact = {cost: {"saved": -1e100, "k": [0]*len(allowed_m)} for cost in range(B + 1)}
            best_exact[0]["saved"] = 0.0

            def dfs(pos, cost_so_far, current_k):
                if cost_so_far > B: return
                if pos == len(allowed_m):
                    f_new = math.prod(1.0 - mx["eff"] * min(1.0, cov[c][orig_idx] + current_k[idx] * mx["stepPct"] / 100.0) 
                                      for idx, (orig_idx, mx) in enumerate(allowed_m))
                    saved = E_base - (E0[c] * f_new)
                    if saved > best_exact[cost_so_far]["saved"]:
                        best_exact[cost_so_far]["saved"] = saved
                        best_exact[cost_so_far]["k"] = list(current_k)
                    return

                orig_idx, mx = allowed_m[pos]
                rem_cov = 1.0 - cov[c][orig_idx]
                if rem_cov <= 1e-6:
                    current_k.append(0)
                    dfs(pos + 1, cost_so_far, current_k)
                    current_k.pop()
                else:
                    k_max = min(math.ceil(rem_cov * 100 / mx["stepPct"]), (B - cost_so_far) // mx["cost"] if mx["cost"] > 0 else 0)
                    for kk in range(k_max + 1):
                        current_k.append(kk)
                        dfs(pos + 1, cost_so_far + kk * mx["cost"], current_k)
                        current_k.pop()

            dfs(0, 0, [])
            
            bam = []
            cur_best = {"saved": 0.0, "k": [0]*len(allowed_m), "cost": 0}
            for cost in range(B + 1):
                if best_exact[cost]["saved"] > cur_best["saved"]:
                    cur_best = {"saved": best_exact[cost]["saved"], "k": best_exact[cost]["k"], "cost": cost}
                bam.append(cur_best)
            best_at_most.append(bam)

        best_saved, best_plan = -1.0, (0, 0, 0)
        for L0 in range(B + 1):
            for L1 in range(B - L0 + 1):
                L2 = B - L0 - L1
                saved = best_at_most[0][L0]["saved"] + best_at_most[1][L1]["saved"] + best_at_most[2][L2]["saved"]
                if saved > best_saved:
                    best_saved, best_plan = saved, (L0, L1, L2)
        
        spent_dp = sum(best_at_most[c][p]["cost"] for c, p in enumerate(best_plan))
        
        applied_texts = []
        for c, p_lim in enumerate(best_plan):
            cat_acts = []
            for idx, (orig_idx, mx) in enumerate(allowed_lists[c]):
                kk = best_at_most[c][p_lim]["k"][idx]
                if kk > 0:
                    added_cov = min(1.0 - cov[c][orig_idx], kk * mx["stepPct"] / 100.0)
                    cov[c][orig_idx] += added_cov
                    cat_acts.append(f"{mx['name']} (+{int(added_cov*100)}%)")
            if cat_acts: applied_texts.append(f"[{cat_names[c]}] " + ", ".join(cat_acts))

        state[s_dp]["budget"] -= spent_dp
        state[s_dp]["cov"] = cov
        
        final_E_dp = sum(E0[c] * math.prod(1.0 - mx["eff"] * cov[c][i] for i, mx in enumerate(measures) if mx["allowed"][c]) for c in range(3))
        
        history[s_dp].append({
            "Year": year, "Money per year (st)": B, "Spent": spent_dp, "Left": state[s_dp]["budget"],
            "Usage (kWh-hour)": final_E_dp, "Saved from the original": yearly_total_base - final_E_dp,
            "Measurements (done)": "; ".join(applied_texts) if applied_texts else "-"
        })

    return {k: pd.DataFrame(v) for k, v in history.items()}, buildings_history

# Start
with st.spinner('Simulation for 10 years'):
    results, b_history = dynamic_simulation()

scale = [100, 20, 5] 
max_dots = [int(max(b_history[y][i] for y in range(1, 11)) / scale[i]) for i in range(3)]

np.random.seed(42)
city_coordinates = []
for max_d in max_dots:
    x_coords = np.random.uniform(0, 100, max_d)
    y_coords = np.random.uniform(0, 100, max_d)
    city_coordinates.append((x_coords, y_coords))

# Visualisation
st.write("---")
st.subheader("Map of the changing city")
selected_year = st.slider("Pick a year to see how the city looked", 1, 10, 1)

fig_map, ax_map = plt.subplots(figsize=(12, 8))
colors = ["#3498db", "#2ecc71", "#e74c3c"]

for i, b_type in enumerate(cat_names):
    count = b_history[selected_year][i]
    dots_count = int(count / scale[i])
    x = city_coordinates[i][0][:dots_count]
    y = city_coordinates[i][1][:dots_count]
    ax_map.scatter(x, y, label=f"{b_type} ({count})", color=colors[i], alpha=0.7, edgecolors='w', s=100 if i==2 else 60)

ax_map.set_xlim(0, 100); ax_map.set_ylim(0, 100); ax_map.axis('off')
ax_map.legend(loc='upper right', bbox_to_anchor=(1.15, 1.05), fontsize=12)
st.pyplot(fig_map, use_container_width=True)


st.write("---")
st.subheader("Strategies graph")

fig, ax = plt.subplots(figsize=(15, 9))

plot_colors = ['#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
for (strat_name, df), color in zip(results.items(), plot_colors):
    ax.plot(df["Year"], df["Usage (kWh-hour)"], marker='o', markersize=8, label=strat_name, color=color, linewidth=2)

base_cons_line = df["Usage (kWh-hour)"] + df["Saved from the original"]
ax.plot(df["Year"], base_cons_line, color='black', linestyle='--', alpha=0.5, label='Without measurements', linewidth=2)
        
ax.set_xlabel("Year", fontsize=16)
ax.set_ylabel("Usage (kWh-hour)", fontsize=16)
ax.tick_params(axis='both', which='major', labelsize=14)
ax.legend(fontsize=14)
ax.grid(True, alpha=0.5)

st.pyplot(fig, use_container_width=True)

# Conclusion

st.write("---")
st.subheader("Conclusion: how much we saved in 10 years")

# how much we saved for each strategy

totals_data = []
for strat_name, df in results.items():
    total_saved = df["Saved from the original"].sum()
    totals_data.append({"Strategy": strat_name, "Total savings (kWh-hour)": total_saved})

df_totals = pd.DataFrame(totals_data)

# the best strategy
best_strat = df_totals.loc[df_totals["Total savings (kWh-hour)"].idxmax()]
best_name = best_strat["Strategy"]
best_score = best_strat["Total savings (kWh-hour)"]

col_table, col_winner = st.columns([1, 1])

with col_table:
    st.dataframe(df_totals.sort_values(by="Total savings (kWh-hour)", ascending=False).reset_index(drop=True), use_container_width=True)

# Constants for CO2 calculation
CO2_PER_KWH_GRAMS = 445
total_co2_tonnes = (best_score * CO2_PER_KWH_GRAMS) / 1_000_000

with col_winner:
    st.markdown(f"""
    <div style="
        border: 4px solid #a85151;
        border-radius: 15px; 
        padding: 30px; 
        text-align: center; 
        background: linear-gradient(145deg, #2c3e50, #34495e); 
        color: white;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
    ">
        <h2 style="margin-top: 0; color: #ecf0f1;">The best strategy:</h2>
        <h1 style="color: #a85151; font-size: 2.5em; margin: 10px 0;">{best_name}</h1>
        <h3 style="color: #ecf0f1; font-weight: normal;">In total we saved:</h3>
        <h1 style="color: #2ecc71; font-size: 3em; margin: 0;">{best_score:,.0f} <span style="font-size: 0.5em; color: #bdc3c7;">kWh-hour</span></h1>
        <hr style="border: 0.5px solid #bdc3c7; margin: 20px 0;">
        <h3 style="color: #ecf0f1; font-weight: normal;">CO₂ reduction:</h3>
        <h1 style="color: #3498db; font-size: 2.5em; margin: 0;">{total_co2_tonnes:,.0f} <span style="font-size: 0.5em; color: #bdc3c7;">tonnes</span></h1>
    </div>
    """, unsafe_allow_html=True)


# In details
st.write("---")
st.subheader("Details")

tab1, tab2, tab3, tab4 = st.tabs(["DP-model", "Greedy", "Expensive (max %)", "Cheap (min price)"])

with tab1:
    st.markdown("**DP-модель**")
    st.dataframe(results["DP-model"], use_container_width=True)

with tab2:
    st.markdown("**Greedy**")
    st.dataframe(results["Greedy"], use_container_width=True)

with tab3:
    st.markdown("**Expensive (max %)**")
    st.dataframe(results["Expensive (max %)"], use_container_width=True)

with tab4:
    st.markdown("**Cheap (min price)**")
    st.dataframe(results["Cheap (min price)"], use_container_width=True)

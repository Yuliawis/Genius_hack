import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

np.random.seed(42)

# --- 1. ІНТЕРФЕЙС НАЛАШТУВАНЬ (SIDEBAR) ---
st.set_page_config(page_title="Енергоефективність Міста", layout="wide")
st.title("🏙️ Динамічна симуляція енергоефективності міста")

st.sidebar.header("💰 Фінанси")
base_budget = st.sidebar.number_input("Початковий річний бюджет (у.о.)", value=100)
budget_growth = st.sidebar.number_input("Щорічний приріст бюджету (у.о.)", value=10)

st.sidebar.header("🏢 Початкова кількість будівель")
init_apartments = st.sidebar.number_input("Квартири", value=40000, step=1000)
init_houses = st.sidebar.number_input("Приватні будинки", value=5000, step=500)
init_public = st.sidebar.number_input("Громадські будівлі", value=300, step=50)

st.sidebar.header("📈 Темп зростання будівель (% щороку)")
growth_apartments = st.sidebar.number_input("Приріст квартир (%)", value=2.0, step=0.5) / 100
growth_houses = st.sidebar.number_input("Приріст приватних будинків (%)", value=1.5, step=0.5) / 100
growth_public = st.sidebar.number_input("Приріст громадських будівель (%)", value=0.5, step=0.5) / 100

monthly_cons = [250, 400, 3000] # Квартири, Будинки, Громадські
cat_names = ["Квартири", "Приватні будинки", "Громадські будівлі"]

# Оновлений список заходів з параметрами з C++ моделі
measures_dp = [
    {"name": "LED освітлення", "cost": 15, "eff": 0.08, "stepPct": 20, "allowed": [True, True, True]},
    {"name": "Утеплення", "cost": 25, "eff": 0.15, "stepPct": 10, "allowed": [True, True, False]},
    {"name": "Сонячні панелі", "cost": 30, "eff": 0.20, "stepPct": 5, "allowed": [False, True, True]},
    {"name": "Smart-лічильники", "cost": 10, "eff": 0.05, "stepPct": 25, "allowed": [True, True, True]},
    {"name": "Розумний будинок", "cost": 6, "eff": 0.03, "stepPct": 15, "allowed": [False, True, False]}
]

# --- 2. ФУНКЦІЇ ДЛЯ DP АЛГОРИТМУ (з C++ логіки) ---
def build_best_for_category(cat_idx, max_budget, E0_cat):
    allowed_m = [(i, m) for i, m in enumerate(measures_dp) if m["allowed"][cat_idx]]
    
    best_exact = {c: {"saved": -1e100, "cost": c, "k": [0]*len(allowed_m)} for c in range(max_budget + 1)}
    best_exact[0]["saved"] = 0.0
    
    def dfs(pos, cost_so_far, current_k):
        if cost_so_far > max_budget: return
        
        if pos == len(allowed_m):
            factor = 1.0
            for i, (orig_idx, m) in enumerate(allowed_m):
                kk = current_k[i]
                if kk > 0:
                    cov = min(1.0, kk * m["stepPct"] / 100.0)
                    factor *= (1.0 - m["eff"] * cov)
            
            saved = max(0.0, E0_cat - (E0_cat * factor))
            
            if saved > best_exact[cost_so_far]["saved"]:
                best_exact[cost_so_far]["saved"] = saved
                best_exact[cost_so_far]["k"] = list(current_k)
            return

        orig_idx, m = allowed_m[pos]
        k_max_cov = (100 // m["stepPct"]) if m["stepPct"] > 0 else 0
        k_max_budget = (max_budget - cost_so_far) // m["cost"] if m["cost"] > 0 else 0
        k_max = min(k_max_cov, k_max_budget)

        for kk in range(k_max + 1):
            current_k.append(kk)
            dfs(pos + 1, cost_so_far + kk * m["cost"], current_k)
            current_k.pop()

    dfs(0, 0, [])
    
    # Перетворюємо на bestAtMost (найкраще за <= cost)
    best_at_most = []
    current_best = {"saved": 0.0, "cost": 0, "k": [0]*len(allowed_m)}
    for c in range(max_budget + 1):
        if best_exact[c]["saved"] > current_best["saved"]:
            current_best = best_exact[c]
        best_at_most.append(current_best)
        
    return best_at_most, allowed_m

# --- 3. ГОЛОВНА ФУНКЦІЯ СИМУЛЯЦІЇ ---
def simulate_dynamic():
    history = { 
        "Оптимальна (Жадібна)": [], 
        "Дорогі (Макс %)": [], 
        "Дешеві (Мін ціна)": [],
        "Комплексна DP-модель": [] 
    }
    carried_over = {k: 0 for k in history.keys()}
    buildings_history = {}

    current_counts = [init_apartments, init_houses, init_public]
    growth_rates = [growth_apartments, growth_houses, growth_public]

    for year in range(1, 11):
        # Зростання міста
        if year > 1:
            for i in range(3):
                current_counts[i] += int(current_counts[i] * growth_rates[i])
                
        buildings_history[year] = current_counts.copy()
        
        # Базове споживання цього року
        E0 = [current_counts[i] * monthly_cons[i] * 12 for i in range(3)]
        yearly_total_base = sum(E0)
        
        # Бюджет цього року
        current_base_budget = base_budget + (year - 1) * budget_growth
        
        # ---------------------------------------------------------
        # АЛГОРИТМИ 1-3: ЖАДІБНІ (Лінійний ефект)
        # ---------------------------------------------------------
        actions = []
        for i, c_name in enumerate(cat_names):
            for m in measures_dp:
                if m["allowed"][i]:
                    actions.append({
                        "action_name": f"{m['name']} ({c_name})",
                        "cost": m["cost"],
                        "savings": E0[i] * m["eff"], 
                        "roi": (E0[i] * m["eff"]) / m["cost"],
                        "raw_effect": m["eff"]
                    })
        
        strategies = {
            "Оптимальна (Жадібна)": sorted(actions, key=lambda x: x["roi"], reverse=True),
            "Дорогі (Макс %)": sorted(actions, key=lambda x: x["raw_effect"], reverse=True),
            "Дешеві (Мін ціна)": sorted(actions, key=lambda x: x["cost"])
        }
        
        for strat_name, strat_actions in strategies.items():
            av_budget = current_base_budget + carried_over[strat_name]
            spent = 0
            yearly_cons = yearly_total_base
            applied = []
            
            for act in strat_actions:
                if av_budget - spent >= act["cost"]:
                    spent += act["cost"]
                    yearly_cons -= act["savings"]
                    applied.append(act["action_name"])
            
            carried_over[strat_name] = av_budget - spent
            history[strat_name].append({
                "Рік": year,
                "Бюджет (з залишком)": av_budget,
                "Витрачено": spent,
                "Залишок": av_budget - spent,
                "Споживання після заходів": yearly_cons,
                "Зекономлено": yearly_total_base - yearly_cons,
                "Заходи": ", ".join(applied)
            })

        # ---------------------------------------------------------
        # АЛГОРИТМ 4: КОМПЛЕКСНА DP-МОДЕЛЬ (ПАКЕТИ)
        # ---------------------------------------------------------
        av_budget_dp = current_base_budget + carried_over["Комплексна DP-модель"]
        B = int(av_budget_dp)
        
        best_at_most = []
        allowed_lists = []
        for i in range(3):
            bam, al_m = build_best_for_category(i, B, E0[i])
            best_at_most.append(bam)
            allowed_lists.append(al_m)

        best_saved = -1.0
        best_plan = (0, 0, 0)
        
        # Розподіл бюджету L0 + L1 + L2 <= B
        for L0 in range(B + 1):
            for L1 in range(B - L0 + 1):
                L2 = B - L0 - L1
                saved = best_at_most[0][L0]["saved"] + best_at_most[1][L1]["saved"] + best_at_most[2][L2]["saved"]
                if saved > best_saved:
                    best_saved = saved
                    best_plan = (L0, L1, L2)
        
        p0, p1, p2 = best_plan
        spent_dp = best_at_most[0][p0]["cost"] + best_at_most[1][p1]["cost"] + best_at_most[2][p2]["cost"]
        
        # Формування красивого тексту заходів
        applied_dp = []
        for i, p_lim in enumerate(best_plan):
            plan_k = best_at_most[i][p_lim]["k"]
            cat_actions = []
            for idx, (orig_idx, m) in enumerate(allowed_lists[i]):
                kk = plan_k[idx]
                if kk > 0:
                    cov_pct = min(100, kk * m["stepPct"])
                    cat_actions.append(f"{m['name']} x{kk} ({cov_pct}%)")
            if cat_actions:
                applied_dp.append(f"[{cat_names[i]}] " + ", ".join(cat_actions))

        carried_over["Комплексна DP-модель"] = av_budget_dp - spent_dp
        yearly_cons_dp = max(0.0, yearly_total_base - best_saved)
        
        history["Комплексна DP-модель"].append({
            "Рік": year,
            "Бюджет (з залишком)": av_budget_dp,
            "Витрачено": spent_dp,
            "Залишок": av_budget_dp - spent_dp,
            "Споживання після заходів": yearly_cons_dp,
            "Зекономлено": yearly_total_base - yearly_cons_dp,
            "Заходи": "; ".join(applied_dp) if applied_dp else "Немає"
        })

    for k in history:
        history[k] = pd.DataFrame(history[k])
        
    return history, buildings_history

# Запуск
with st.spinner('Симуляція 10 років...'):
    results, b_history = simulate_dynamic()

# --- 4. ВІЗУАЛІЗАЦІЯ ---
st.write("---")
col_map, col_chart = st.columns([1, 1])

with col_map:
    st.subheader("🗺️ Карта розвитку міста")
    selected_year = st.slider("Рік", 1, 10, 1)
    
    fig_map, ax_map = plt.subplots(figsize=(6, 6))
    scale = [100, 20, 5] 
    colors = ["#3498db", "#2ecc71", "#e74c3c"]
    
    for i, b_type in enumerate(cat_names):
        count = b_history[selected_year][i]
        dots_count = int(count / scale[i])
        x = np.random.uniform(0, 100, dots_count)
        y = np.random.uniform(0, 100, dots_count)
        ax_map.scatter(x, y, label=f"{b_type} ({count} шт.)", color=colors[i], alpha=0.7, edgecolors='w', s=50 if i==2 else 30)

    ax_map.set_xlim(0, 100)
    ax_map.set_ylim(0, 100)
    ax_map.axis('off')
    ax_map.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1))
    st.pyplot(fig_map)

with col_chart:
    st.subheader("📊 Порівняння 4-х стратегій")
    fig, ax = plt.subplots(figsize=(8, 5))
    
    plot_colors = ['#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
    for (strat_name, df), color in zip(results.items(), plot_colors):
        ax.plot(df["Рік"], df["Споживання після заходів"], marker='o', label=strat_name, color=color, linewidth=2)
    
    # Лінія зростаючого споживання без заходів
    base_cons_line = df["Споживання після заходів"] + df["Зекономлено"]
    ax.plot(df["Рік"], base_cons_line, color='black', linestyle='--', alpha=0.5, label='Без заходів (зростаюче місто)')
            
    ax.set_xlabel("Рік")
    ax.set_ylabel("Споживання (кВт-год)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

# --- 5. ТАБЛИЦІ (ДЕТАЛЬНИЙ ЗВІТ) ---
st.write("---")
st.subheader("📋 Детальні звіти")

tab1, tab2, tab3, tab4 = st.tabs(["Комплексна DP-модель 🏆", "Оптимальна (Жадібна)", "Дорогі (Макс %)", "Дешеві (Мін ціна)"])

with tab1:
    st.markdown("**Стратегія: Точний розподіл бюджету через Динамічне Програмування.** Ця модель дозволяє купувати заходи «пакетами» та враховує, що ефекти мультиплікуються (перемножуються), захищаючи від нереалістичної економії >100%.")
    st.dataframe(results["Комплексна DP-модель"], use_container_width=True)

with tab2:
    st.markdown("**Стратегія: Жадібний алгоритм.** (Лінійний розрахунок). Купуємо те, що дає найбільше кВт-год на 1 у.о.")
    st.dataframe(results["Оптимальна (Жадібна)"], use_container_width=True)

with tab3:
    st.dataframe(results["Дорогі (Макс %)"], use_container_width=True)

with tab4:
    st.dataframe(results["Дешеві (Мін ціна)"], use_container_width=True)

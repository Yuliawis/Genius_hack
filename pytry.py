import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

np.random.seed(42)

# --- 1. ІНТЕРФЕЙС НАЛАШТУВАНЬ (SIDEBAR) ---
st.set_page_config(page_title="Енергоефективність Міста", layout="wide")
st.title("🏙️ Динамічна симуляція енергоефективності міста")

st.sidebar.header("💰 Фінанси")
base_budget = st.sidebar.number_input("Поповнення бюджету (у.о./рік)", value=100)
budget_growth = st.sidebar.number_input("Щорічний приріст поповнення (у.о.)", value=10)

st.sidebar.header("🏢 Початкова кількість будівель")
init_apartments = st.sidebar.number_input("Квартири", value=40000, step=1000)
init_houses = st.sidebar.number_input("Приватні будинки", value=5000, step=500)
init_public = st.sidebar.number_input("Громадські будівлі", value=300, step=50)

st.sidebar.header("📈 Темп зростання будівель (% щороку)")
growth_apartments = st.sidebar.number_input("Приріст квартир (%)", value=2.0, step=0.5) / 100
growth_houses = st.sidebar.number_input("Приріст приватних будинків (%)", value=1.5, step=0.5) / 100
growth_public = st.sidebar.number_input("Приріст громадських будівель (%)", value=0.5, step=0.5) / 100

monthly_cons = [250, 400, 3000]
cat_names = ["Квартири", "Приватні будинки", "Громадські будівлі"]

measures = [
    {"name": "LED освітлення", "cost": 15, "eff": 0.08, "stepPct": 20, "allowed": [True, True, True]},
    {"name": "Утеплення", "cost": 25, "eff": 0.15, "stepPct": 10, "allowed": [True, True, False]},
    {"name": "Сонячні панелі", "cost": 30, "eff": 0.20, "stepPct": 5, "allowed": [False, True, True]},
    {"name": "Smart-лічильники", "cost": 10, "eff": 0.05, "stepPct": 25, "allowed": [True, True, True]},
    {"name": "Розумний будинок", "cost": 6, "eff": 0.03, "stepPct": 15, "allowed": [False, True, False]}
]

# --- 2. ГОЛОВНА ФУНКЦІЯ СИМУЛЯЦІЇ ---
def simulate_dynamic():
    strats = ["Комплексна DP-модель 🏆", "Оптимальна (Жадібна)", "Дорогі (Макс %)", "Дешеві (Мін ціна)"]
    
    # Глобальний стан для кожної стратегії: переносимо бюджет і покриття (0.0..1.0)
    state = {s: {"budget": 0, "cov": [[0.0 for _ in measures] for _ in range(3)]} for s in strats}
    
    history = {s: [] for s in strats}
    buildings_history = {}
    current_counts = [init_apartments, init_houses, init_public]

    for year in range(1, 11):
        # 1. Зростання міста та розбавлення покриття (Dilution)
        if year > 1:
            new_counts = [int(current_counts[i] * (1 + [growth_apartments, growth_houses, growth_public][i])) for i in range(3)]
            for s in strats:
                for c in range(3):
                    for m in range(len(measures)):
                        if new_counts[c] > 0:
                            # Старе покриття "розмазується" на більшу кількість будівель
                            state[s]["cov"][c][m] *= (current_counts[c] / new_counts[c])
            current_counts = new_counts
            
        buildings_history[year] = current_counts.copy()
        
        # Базове споживання цього року (якби нічого не впроваджували НІКОЛИ)
        E0 = [current_counts[i] * monthly_cons[i] * 12 for i in range(3)]
        yearly_total_base = sum(E0)
        
        # Поповнення бюджету
        yearly_injection = base_budget + (year - 1) * budget_growth
        for s in strats:
            state[s]["budget"] += yearly_injection

        # =========================================================
        # ЖАДІБНІ СТРАТЕГІЇ (Динамічні кроки)
        # =========================================================
        for s in ["Оптимальна (Жадібна)", "Дорогі (Макс %)", "Дешеві (Мін ціна)"]:
            B = state[s]["budget"]
            cov = [row[:] for row in state[s]["cov"]]
            spent = 0
            purchases = [[0]*len(measures) for _ in range(3)]
            
            # Динамічний пошук найкращого "кроку"
            while True:
                best_action = None
                best_score = -1e100
                
                for c in range(3):
                    for m_idx, m in enumerate(measures):
                        if not m["allowed"][c] or cov[c][m_idx] >= 0.9999 or spent + m["cost"] > B:
                            continue
                            
                        # Рахуємо маржинальну економію від 1 кроку
                        step_size = m["stepPct"] / 100.0
                        new_c = min(1.0, cov[c][m_idx] + step_size)
                        
                        f_cur = math.prod(1.0 - mx["eff"] * cov[c][i] for i, mx in enumerate(measures) if mx["allowed"][c])
                        f_new = math.prod(1.0 - mx["eff"] * (new_c if i == m_idx else cov[c][i]) for i, mx in enumerate(measures) if mx["allowed"][c])
                        
                        savings = E0[c] * (f_cur - f_new)
                        
                        if s == "Оптимальна (Жадібна)": score = savings / m["cost"] # Макс ROI
                        elif s == "Дорогі (Макс %)": score = savings                # Макс ефект у кВт
                        else: score = -m["cost"]                                    # Найдешевші
                        
                        if score > best_score:
                            best_score = score
                            best_action = (c, m_idx, m)
                
                if not best_action: break # Немає доступних або вигідних кроків
                
                c, m_idx, m = best_action
                spent += m["cost"]
                purchases[c][m_idx] += 1
                cov[c][m_idx] = min(1.0, cov[c][m_idx] + m["stepPct"] / 100.0)

            # Формуємо красивий текст і зберігаємо стан
            applied_texts = []
            for c in range(3):
                cat_acts = []
                for m_idx, count in enumerate(purchases[c]):
                    if count > 0:
                        added_pct = min(1.0 - state[s]["cov"][c][m_idx], count * measures[m_idx]["stepPct"] / 100.0) * 100
                        cat_acts.append(f"{measures[m_idx]['name']} x{count} (+{int(added_pct)}%)")
                if cat_acts: applied_texts.append(f"[{cat_names[c]}] " + ", ".join(cat_acts))

            state[s]["budget"] -= spent
            state[s]["cov"] = cov
            
            # Підсумкове споживання
            final_E = sum(E0[c] * math.prod(1.0 - mx["eff"] * cov[c][i] for i, mx in enumerate(measures) if mx["allowed"][c]) for c in range(3))
            history[s].append({
                "Рік": year, "Бюджет (поч)": B, "Витрачено": spent, "Залишок": state[s]["budget"],
                "Споживання (кВт-год)": final_E, "Зекономлено від базового": yearly_total_base - final_E,
                "Заходи (докуплено)": "; ".join(applied_texts) if applied_texts else "-"
            })

        # =========================================================
        # КОМПЛЕКСНА DP-МОДЕЛЬ
        # =========================================================
        s_dp = "Комплексна DP-модель 🏆"
        B = int(state[s_dp]["budget"])
        cov = [row[:] for row in state[s_dp]["cov"]]
        best_at_most = []
        allowed_lists = []

        for c in range(3):
            allowed_m = [(i, m) for i, m in enumerate(measures) if m["allowed"][c]]
            allowed_lists.append(allowed_m)
            
            # Поточне споживання категорії до нових інвестицій
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

        # Розподіл бюджету L0 + L1 + L2 <= B
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
                    cat_acts.append(f"{mx['name']} x{kk} (+{int(added_cov*100)}%)")
            if cat_acts: applied_texts.append(f"[{cat_names[c]}] " + ", ".join(cat_acts))

        state[s_dp]["budget"] -= spent_dp
        state[s_dp]["cov"] = cov
        
        final_E_dp = sum(E0[c] * math.prod(1.0 - mx["eff"] * cov[c][i] for i, mx in enumerate(measures) if mx["allowed"][c]) for c in range(3))
        
        history[s_dp].append({
            "Рік": year, "Бюджет (поч)": B, "Витрачено": spent_dp, "Залишок": state[s_dp]["budget"],
            "Споживання (кВт-год)": final_E_dp, "Зекономлено від базового": yearly_total_base - final_E_dp,
            "Заходи (докуплено)": "; ".join(applied_texts) if applied_texts else "-"
        })

    return {k: pd.DataFrame(v) for k, v in history.items()}, buildings_history

# Запуск
with st.spinner('Симуляція 10 років...'):
    results, b_history = simulate_dynamic()

# --- 3. ВІЗУАЛІЗАЦІЯ ---
st.write("---")

st.subheader("🗺️ Карта розвитку міста")
selected_year = st.slider("Оберіть рік для перегляду забудови", 1, 10, 1)

fig_map, ax_map = plt.subplots(figsize=(12, 12))
scale = [100, 20, 5] 
colors = ["#3498db", "#2ecc71", "#e74c3c"]

for i, b_type in enumerate(cat_names):
    count = b_history[selected_year][i]
    dots_count = int(count / scale[i])
    x = np.random.uniform(0, 100, dots_count)
    y = np.random.uniform(0, 100, dots_count)
    ax_map.scatter(x, y, label=f"{b_type} ({count} шт.)", color=colors[i], alpha=0.7, edgecolors='w', s=100 if i==2 else 60)

ax_map.set_xlim(0, 100)
ax_map.set_ylim(0, 100)
ax_map.axis('off')
ax_map.legend(loc='upper right', bbox_to_anchor=(1.15, 1.05), fontsize=12)
st.pyplot(fig_map, use_container_width=True)


# === БЛОК 2: ВЕЛИКИЙ ГРАФІК НА ВСЮ ШИРИНУ ===
st.write("---")
st.subheader("📊 Порівняння 4-х стратегій (Детальний графік)")

fig, ax = plt.subplots(figsize=(20, 15))

plot_colors = ['#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
for (strat_name, df), color in zip(results.items(), plot_colors):
    ax.plot(df["Рік"], df["Споживання (кВт-год)"], marker='o', markersize=8, label=strat_name, color=color, linewidth=2)

base_cons_line = df["Споживання (кВт-год)"] + df["Зекономлено від базового"]
ax.plot(df["Рік"], base_cons_line, color='black', linestyle='--', alpha=0.5, label='Без заходів (зростаюче місто)', linewidth=2)
        
ax.set_xlabel("Рік", fontsize=16)
ax.set_ylabel("Споживання (кВт-год)", fontsize=16)
ax.tick_params(axis='both', which='major', labelsize=14)
ax.legend(fontsize=14)
ax.grid(True, alpha=0.5)

st.pyplot(fig, use_container_width=True)

st.write("---")
st.subheader("📋 Детальні звіти (Купівля кроків та накопичення ефекту)")

tab1, tab2, tab3, tab4 = st.tabs(["Комплексна DP-модель 🏆", "Оптимальна (Жадібна)", "Дорогі (Макс %)", "Дешеві (Мін ціна)"])

with tab1:
    st.markdown("**DP-модель**: Точний пошук комбінацій. Забезпечує математично ідеальний розподіл бюджету.")
    st.dataframe(results["Комплексна DP-модель 🏆"], use_container_width=True)

with tab2:
    st.markdown("**Жадібний (Оптимальна)**: Динамічно рахує маржинальний ROI для кожного 1 кроку. Тепер змагається з DP на рівних!")
    st.dataframe(results["Оптимальна (Жадібна)"], use_container_width=True)

with tab3:
    st.dataframe(results["Дорогі (Макс %)"], use_container_width=True)

with tab4:
    st.dataframe(results["Дешеві (Мін ціна)"], use_container_width=True)

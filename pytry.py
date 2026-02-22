import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Фіксуємо генератор випадкових чисел, щоб карта не "стрибала" при кожному оновленні
np.random.seed(42)

# --- 1. ІНТЕРФЕЙС НАЛАШТУВАНЬ (SIDEBAR) ---
st.set_page_config(page_title="Енергоефективність Міста", layout="wide")
st.title("🏙️ Динамічна симуляція енергоефективності міста")

st.sidebar.header("💰 Фінанси")
base_budget = st.sidebar.number_input("Початковий річний бюджет (у.о.)", value=100)
budget_growth = st.sidebar.number_input("Щорічний приріст бюджету (у.о.)", value=10, help="На скільки збільшується бюджет щороку, починаючи з 2-го")

st.sidebar.header("🏢 Початкова кількість будівель")
init_apartments = st.sidebar.number_input("Квартири", value=40000, step=1000)
init_houses = st.sidebar.number_input("Приватні будинки", value=5000, step=500)
init_public = st.sidebar.number_input("Громадські будівлі", value=300, step=50)

st.sidebar.header("📈 Темп зростання будівель (% щороку)")
growth_apartments = st.sidebar.number_input("Приріст квартир (%)", value=2.0, step=0.5) / 100
growth_houses = st.sidebar.number_input("Приріст приватних будинків (%)", value=1.5, step=0.5) / 100
growth_public = st.sidebar.number_input("Приріст громадських будівель (%)", value=0.5, step=0.5) / 100

# Середнє місячне споживання
monthly_cons = {"Квартири": 250, "Приватні будинки": 400, "Громадські будівлі": 3000}

measures = [
    {"name": "LED освітлення", "cost": 15, "effect": 0.08},
    {"name": "Утеплення", "cost": 25, "effect": 0.15},
    {"name": "Сонячні панелі", "cost": 30, "effect": 0.20},
    {"name": "Smart-лічильники", "cost": 10, "effect": 0.05},
    {"name": "Розумний будинок", "cost": 6, "effect": 0.03}
]

# --- 2. ФУНКЦІЯ СИМУЛЯЦІЇ (Динамічна) ---
def simulate_dynamic():
    history = { "Оптимальна (ROI)": [], "Дорогі (Макс %)": [], "Дешеві (Мін ціна)": [] }
    carried_over = { "Оптимальна (ROI)": 0, "Дорогі (Макс %)": 0, "Дешеві (Мін ціна)": 0 }
    
    # Відстеження кількості будівель по роках для карти
    buildings_history = {}

    current_counts = {
        "Квартири": init_apartments,
        "Приватні будинки": init_houses,
        "Громадські будівлі": init_public
    }

    for year in range(1, 11):
        # 1. Зростання кількості будівель (з 2-го року)
        if year > 1:
            current_counts["Квартири"] += int(current_counts["Квартири"] * growth_apartments)
            current_counts["Приватні будинки"] += int(current_counts["Приватні будинки"] * growth_houses)
            current_counts["Громадські будівлі"] += int(current_counts["Громадські будівлі"] * growth_public)
        
        # Зберігаємо дані для карти
        buildings_history[year] = current_counts.copy()
        
        # 2. Розрахунок нового базового споживання для цього року
        base_consumption = {
            name: count * monthly_cons[name] * 12 
            for name, count in current_counts.items()
        }
        yearly_total_base = sum(base_consumption.values())
        
        # 3. Розрахунок бюджету на цей рік (Початковий + (рік-1)*приріст)
        current_base_budget = base_budget + (year - 1) * budget_growth
        
        # 4. Перерахунок ефективності заходів (бо споживання змінилося)
        actions = []
        for b_name, b_cons in base_consumption.items():
            for m in measures:
                actions.append({
                    "action_name": f"{m['name']} ({b_name})",
                    "cost": m["cost"],
                    "savings": b_cons * m["effect"], 
                    "roi": (b_cons * m["effect"]) / m["cost"],
                    "raw_effect": m["effect"]
                })
        
        strategies = {
            "Оптимальна (ROI)": sorted(actions, key=lambda x: x["roi"], reverse=True),
            "Дорогі (Макс %)": sorted(actions, key=lambda x: x["raw_effect"], reverse=True),
            "Дешеві (Мін ціна)": sorted(actions, key=lambda x: x["cost"])
        }
        
        # 5. Симуляція кожної стратегії
        for strat_name, strat_actions in strategies.items():
            available_budget = current_base_budget + carried_over[strat_name]
            spent = 0
            yearly_cons = yearly_total_base
            applied = []
            
            for action in strat_actions:
                if available_budget - spent >= action["cost"]:
                    spent += action["cost"]
                    yearly_cons -= action["savings"]
                    applied.append(action["action_name"])
            
            remaining = available_budget - spent
            carried_over[strat_name] = remaining
            
            history[strat_name].append({
                "Рік": year,
                "Кількість будівель (всього)": sum(current_counts.values()),
                "Поточний бюджет (у.о.)": current_base_budget,
                "Бюджет із залишком": available_budget,
                "Витрачено": spent,
                "Залишок": remaining,
                "Початкове споживання": yearly_total_base,
                "Споживання після заходів": yearly_cons,
                "Зекономлено": yearly_total_base - yearly_cons,
                "Заходи": ", ".join(applied)
            })

    # Конвертуємо результати в DataFrame
    for k in history:
        history[k] = pd.DataFrame(history[k])
        
    return history, buildings_history

# Запускаємо симуляцію
results, b_history = simulate_dynamic()

# --- 3. ВІЗУАЛІЗАЦІЯ ---
st.write("---")
col_map, col_chart = st.columns([1, 1])

with col_map:
    st.subheader("🗺️ Карта розвитку міста")
    selected_year = st.slider("Оберіть рік для перегляду карти", 1, 10, 1)
    
    # Генерація карти (scatter plot)
    fig_map, ax_map = plt.subplots(figsize=(6, 6))
    
    # Масштаб для візуалізації (щоб не малювати 40000 крапок)
    scale = {"Квартири": 100, "Приватні будинки": 20, "Громадські будівлі": 5}
    colors = {"Квартири": "#3498db", "Приватні будинки": "#2ecc71", "Громадські будівлі": "#e74c3c"}
    labels = {"Квартири": "Квартири (1:100)", "Приватні будинки": "Приватні (1:20)", "Громадські (1:5)": "Громадські"}
    
    for b_type in ["Квартири", "Приватні будинки", "Громадські будівлі"]:
        count = b_history[selected_year][b_type]
        dots_count = int(count / scale[b_type])
        
        # Генеруємо випадкові координати від 0 до 100
        x = np.random.uniform(0, 100, dots_count)
        y = np.random.uniform(0, 100, dots_count)
        
        ax_map.scatter(x, y, label=f"{b_type} ({count} шт.)", color=colors[b_type], alpha=0.7, edgecolors='w', s=50 if b_type=="Громадські будівлі" else 30)

    ax_map.set_xlim(0, 100)
    ax_map.set_ylim(0, 100)
    ax_map.set_title(f"Місто у {selected_year}-му році")
    ax_map.axis('off') # Вимикаємо осі координат, щоб виглядало як карта
    ax_map.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1))
    st.pyplot(fig_map)

with col_chart:
    st.subheader("📊 Порівняння стратегій")
    fig, ax = plt.subplots(figsize=(8, 5))
    
    plot_colors = ['#2ecc71', '#e74c3c', '#f39c12']
    for (strat_name, df), color in zip(results.items(), plot_colors):
        ax.plot(df["Рік"], df["Споживання після заходів"], marker='o', label=strat_name, color=color, linewidth=2)
    
    # Лінія базового споживання, що зростає
    ax.plot(results["Оптимальна (ROI)"]["Рік"], results["Оптимальна (ROI)"]["Початкове споживання"], 
            color='black', linestyle='--', alpha=0.5, label='Без заходів (зростаюче місто)')
            
    ax.set_xlabel("Рік")
    ax.set_ylabel("Споживання (кВт-год)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

# --- 4. ТАБЛИЦІ (ДЕТАЛЬНИЙ ЗВІТ) ---
st.write("---")
st.subheader("📋 Детальні таблиці розвитку для кожної стратегії")

# Створюємо вкладки (tabs) для зручного перегляду таблиць
tab1, tab2, tab3 = st.tabs(["Оптимальна (ROI)", "Дорогі (Макс %)", "Дешеві (Мін ціна)"])

with tab1:
    st.markdown("**Стратегія: Жадібний алгоритм (пошук найбільшої вигоди на кожну умовну одиницю).**")
    st.dataframe(results["Оптимальна (ROI)"], use_container_width=True)

with tab2:
    st.markdown("**Стратегія: Інвестування в найпотужніші технології (без урахування їх високої ціни).**")
    st.dataframe(results["Дорогі (Макс %)"], use_container_width=True)

with tab3:
    st.markdown("**Стратегія: Купівля найдешевших заходів, щоб покрити якомога більше будівель.**")
    st.dataframe(results["Дешеві (Мін ціна)"], use_container_width=True)

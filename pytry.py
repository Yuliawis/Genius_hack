import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. ВИХІДНІ ДАНІ ---
buildings = {
    "Квартири": {"count": 40000, "monthly": 250},
    "Приватні будинки": {"count": 5000, "monthly": 400},
    "Громадські будівлі": {"count": 300, "monthly": 3000}
}

base_consumption = {
    name: data["count"] * data["monthly"] * 12 
    for name, data in buildings.items()
}
total_base_consumption = sum(base_consumption.values())

measures = [
    {"name": "LED освітлення", "cost": 15, "effect": 0.08},
    {"name": "Утеплення", "cost": 25, "effect": 0.15},
    {"name": "Сонячні панелі", "cost": 30, "effect": 0.20},
    {"name": "Smart-лічильники", "cost": 10, "effect": 0.05},
    {"name": "Розумний будинок", "cost": 6, "effect": 0.03}
]

# Генеруємо всі можливі комбінації заходів
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

# Три різні стратегії
strategies = {
    "Оптимальна (ROI)": sorted(actions, key=lambda x: x["roi"], reverse=True),
    "Дорогі (Макс % ефекту)": sorted(actions, key=lambda x: x["raw_effect"], reverse=True),
    "Дешеві (Мінім. ціна)": sorted(actions, key=lambda x: x["cost"])
}

# --- 2. ФУНКЦІЯ СИМУЛЯЦІЇ З ПЕРЕНЕСЕННЯМ БЮДЖЕТУ ---
def simulate_strategy(strategy_actions, base_budget=100):
    history = []
    carried_over_budget = 0 # Залишок з попереднього року
    
    for year in range(1, 11):
        # Бюджет на цей рік = базовий + залишок
        current_year_budget = base_budget + carried_over_budget
        
        current_yearly_consumption = total_base_consumption
        applied_this_year = []
        spent_this_year = 0
        
        # Купуємо заходи
        for action in strategy_actions:
            if current_year_budget - spent_this_year >= action["cost"]:
                spent_this_year += action["cost"]
                current_yearly_consumption -= action["savings"]
                applied_this_year.append(action["action_name"])
        
        # Рахуємо залишок, який перейде на наступний рік
        remaining_budget = current_year_budget - spent_this_year
        
        history.append({
            "Рік": year,
            "Бюджет на рік": current_year_budget,
            "Витрачено": spent_this_year,
            "Залишок (на наст. рік)": remaining_budget,
            "Споживання (кВт-год)": current_yearly_consumption,
            "Зекономлено (кВт-год)": total_base_consumption - current_yearly_consumption,
            "Заходи": ", ".join(applied_this_year)
        })
        
        # Оновлюємо перенесений бюджет
        carried_over_budget = remaining_budget
        
    return pd.DataFrame(history)

# --- 3. ІНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="Енергоефективність Міста", layout="wide")
st.title("🏙️ Симуляція енергоефективності міста")
st.write("Модель враховує перенесення невитраченого бюджету на наступний рік.")

budget_input = st.sidebar.number_input("Щорічне поповнення бюджету (у.о.)", value=100)

# Симуляція для всіх стратегій
results = {}
for strat_name, strat_actions in strategies.items():
    results[strat_name] = simulate_strategy(strat_actions, base_budget=budget_input)

# Візуалізація графіка
st.subheader("📊 Порівняння стратегій (Споживання електроенергії)")
fig, ax = plt.subplots(figsize=(10, 5))

colors = ['#2ecc71', '#e74c3c', '#3498db']
for (strat_name, df), color in zip(results.items(), colors):
    ax.plot(df["Рік"], df["Споживання (кВт-год)"], marker='o', label=strat_name, color=color, linewidth=2)

ax.axhline(y=total_base_consumption, color='black', linestyle='--', alpha=0.5, label='Без впровадження заходів')
ax.set_xlabel("Рік")
ax.set_ylabel("Споживання (кВт-год)")
ax.legend()
ax.grid(True, alpha=0.3)
st.pyplot(fig)

# Виведення таблиць
st.subheader("🏆 Деталі Оптимальної стратегії (Жадібний алгоритм)")
st.dataframe(results["Оптимальна (ROI)"], use_container_width=True)

st.subheader("📉 Деталі Стратегії 'Дорогі'")
st.dataframe(results["Дорогі (Макс % ефекту)"], use_container_width=True)

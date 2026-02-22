import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. ВИХІДНІ ДАНІ ---
# Розрахунок початкового річного споживання 
buildings = {
    "Квартири": {"count": 40000, "monthly": 250},
    "Приватні будинки": {"count": 5000, "monthly": 400},
    "Громадські будівлі": {"count": 300, "monthly": 3000}
}

# Рахуємо базове споживання за рік для кожної категорії
base_consumption = {
    name: data["count"] * data["monthly"] * 12 
    for name, data in buildings.items()
}

total_base_consumption = sum(base_consumption.values())

# Доступні заходи 
measures = [
    {"name": "LED освітлення", "cost": 15, "effect": 0.08},
    {"name": "Утеплення", "cost": 25, "effect": 0.15},
    {"name": "Сонячні панелі", "cost": 30, "effect": 0.20},
    {"name": "Smart-лічильники", "cost": 10, "effect": 0.05},
    {"name": "Розумний будинок", "cost": 6, "effect": 0.03}
]

# --- 2. ГЕНЕРАЦІЯ ТА СОРТУВАННЯ ДІЙ ---
# Створюємо всі можливі комбінації (Захід + Тип будівлі)
actions = []
for b_name, b_cons in base_consumption.items():
    for m in measures:
        # Економія в кВт-год за рік від початкового споживання
        annual_savings = b_cons * m["effect"] 
        actions.append({
            "action_name": f"{m['name']} ({b_name})",
            "cost": m["cost"],
            "savings": annual_savings,
            "roi": annual_savings / m["cost"], # Скільки кВт-год рятує 1 у.о.
            "b_name": b_name
        })

# Сортуємо дії від найефективніших до найменш ефективних
actions_sorted = sorted(actions, key=lambda x: x["roi"], reverse=True)


# --- 3. ФУНКЦІЯ СИМУЛЯЦІЇ ---
def simulate_city_energy(base_budget=100, tariff=0.0):
    current_yearly_consumption = total_base_consumption
    budget = base_budget
    
    # Відстежуємо, скільки % ми вже зекономили для кожної будівлі, щоб не піти в мінус
    savings_percent = {"Квартири": 0.0, "Приватні будинки": 0.0, "Громадські будівлі": 0.0}
    
    history = []
    
    for year in range(1, 11):
        year_budget = budget
        applied_this_year = []
        
        # Жадібний алгоритм: купуємо найкращі заходи
        for action in actions_sorted:
            # Перевіряємо, чи вистачає грошей і чи не перевищили ми 100% економії для цього типу будівлі
            while year_budget >= action["cost"] and savings_percent[action["b_name"]] + 0.01 < 1.0:
                year_budget -= action["cost"]
                # Зменшуємо загальне споживання (ефект від початкового)
                current_yearly_consumption -= action["savings"]
                
                # Записуємо, що захід застосовано 
                applied_this_year.append(action["action_name"])
                
                # Додаємо відсоток до загальної скарбнички економії будівлі
                # (Шукаємо оригінальний відсоток заходу)
                original_effect = next(m["effect"] for m in measures if action["action_name"].startswith(m["name"]))
                savings_percent[action["b_name"]] += original_effect
        
        # Записуємо результати року
        # Ефект зберігається на наступні роки 
        history.append({
            "Рік": year,
            "Споживання (кВт-год)": current_yearly_consumption,
            "Витрачено у.о.": budget - year_budget,
            "Залишок у.о.": year_budget,
            "Впроваджені заходи": ", ".join(applied_this_year) if applied_this_year else "Немає"
        })
        
        # Розрахунок бюджету на наступний рік (з урахуванням економії, якщо тариф > 0) 
        saved_kwh_total = total_base_consumption - current_yearly_consumption
        bonus_budget = saved_kwh_total * tariff
        budget = base_budget + bonus_budget
        
    return pd.DataFrame(history)

# --- 4. ІНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="Енергоефективність Міста", layout="wide")
st.title("🏙️ Симуляція енергоефективності міста (10 років)")

# Бічна панель з налаштуваннями
st.sidebar.header("Параметри симуляції")
st.sidebar.write("Бюджет міста: 100 у.о./рік [cite: 8, 9]")
budget_input = st.sidebar.number_input("Базовий бюджет", value=100)
tariff_input = st.sidebar.number_input("Тариф за 1 зекономлений кВт-год (для поповнення бюджету)", value=0.000000)

# Запуск
df = simulate_city_energy(base_budget=budget_input, tariff=tariff_input)

# Візуалізація
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📉 Динаміка споживання електроенергії")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["Рік"], df["Споживання (кВт-год)"], marker='o', linewidth=2, color='#2ecc71')
    ax.set_xlabel("Рік впровадження")
    ax.set_ylabel("Загальне споживання (кВт-год)")
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Додаємо горизонтальну лінію початкового споживання
    ax.axhline(y=total_base_consumption, color='r', linestyle='-', alpha=0.3, label='Початкове споживання')
    ax.legend()
    st.pyplot(fig)

with col2:
    st.subheader("💡 Найвигідніші інвестиції (ROI)")
    # Показуємо топ-5 найвигідніших дій
    top_actions = pd.DataFrame(actions_sorted).head(5)
    top_actions = top_actions[["action_name", "roi"]].rename(columns={"action_name": "Дія", "roi": "Економія кВт-год на 1 у.о."})
    st.dataframe(top_actions, hide_index=True)

st.subheader("📋 Детальний звіт по роках")
st.dataframe(df, use_container_width=True)
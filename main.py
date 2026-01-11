import pandas as pd
import streamlit as st
import requests
import plotly.express as px
from datetime import datetime
import plotly.graph_objects as go

def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)


def current_month():
    month = datetime.now().month
    if month in [12, 1, 2]:
        return 'winter'
    elif month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    else:
        return 'autumn'


def data_first_analysis(data):
    st.header("Основная информация о данных")
    data['Скользящее_среднее'] = data['temperature'].rolling(window=30).mean()
    season_group_data = data.groupby(['city', 'season'])['temperature'].agg(['mean', 'std']).reset_index()
    data = data.merge(season_group_data, on=['city', 'season'])
    data['anomaly'] = (data['temperature'] >= data['mean'] + 2 * data['std']) | (
        data['temperature'] <= data['mean'] - 2 * data['std'])
    st.write(data.describe())
    st.write(season_group_data)
    st.write(f"В данных выявлено {data['anomaly'].sum()} аномалий")
    return data, season_group_data


def API_connect(API_KEY, cities):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={cities}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    return response


def main():
    st.title("Выявление погодных аномалий в разных городах 🌩️")

    uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])
    if uploaded_file is None:
        st.info("Загрузите CSV файл для начала работы")
        return

    data = load_data(uploaded_file)
    data, season_group_data = data_first_analysis(data)


    st.header("Подключение API и поиск аномалий")
    cities = st.selectbox('Выберете город для прогноза', data['city'].unique())
    API_KEY = st.text_input('Введите API ключ', type="password")
    if not API_KEY:
        return

    response = API_connect(API_KEY, cities)
    if response.status_code == 200:
        dates = response.json()
        st.write(f"Погода в {cities}: {dates['main']['temp']}°C")
        season = current_month()
        new_data = season_group_data[(season_group_data['season'] == season) & (season_group_data['city'] == cities)]
        if new_data['mean'].mean() - 2 * new_data['std'].mean() <= dates['main']['temp'] <= new_data['mean'].mean() + 2 * new_data['std'].mean():
            st.write(f"Погода в {cities}: не аномальна")
        else:
            st.write(f"Погода в {cities}: аномальна")
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data = data.sort_values('timestamp').reset_index(drop=True)
        data_cities = data[data['city'] == cities]

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=data_cities['timestamp'], y=data_cities['temperature'], mode='markers',
                                 name='Температура'))
        fig.add_trace(go.Scatter(x=data_cities['timestamp'], y=data_cities['temperature'].where(data_cities['anomaly']),
                                 mode='markers', name='Аномалии', marker=dict(color='red')))
        fig.add_trace(go.Scattergl(x=data_cities['timestamp'], y=data_cities['Скользящее_среднее'], mode='lines',
                                   line=dict(color="orange", width=2), name='Скользящее среднее (30 дней)'))
        st.plotly_chart(fig)

        city_season_group = season_group_data[season_group_data['city'] == cities]
        st.header(f'Сезонный профиль температуры: {cities}')
        st.write(city_season_group)
        fig = px.bar(data_cities,
            x=data_cities['season'],
            y=data_cities['temperature'])
        st.plotly_chart(fig)

    else:
        st.write("Ошибка при запросе данных")


if __name__ == "__main__":
    main()
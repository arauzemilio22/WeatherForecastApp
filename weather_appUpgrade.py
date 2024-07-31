import streamlit as st
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from streamlit_folium import folium_static
import folium
import pandas as pd
import matplotlib.pyplot as plt

# API keys
airvisual_api_key = "d2ae5113-7840-4dc9-b191-690eb50e5059"
tomorrow_api_key = "yKDVKtE3TdQkrrsX0nIDmMa2x7SkpeTI"

st.title("5 Day Forecast Weather App")
st.header("Using Tomorrow.io and AirVisual APIs")

# Function to create and display a map
@st.cache_data
def map_creator(latitude, longitude):
    m = folium.Map(location=[latitude, longitude], zoom_start=10)
    folium.Marker([latitude, longitude], popup="Station", tooltip="Station").add_to(m)
    folium_static(m)

def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32

# Fetch weather forecast data
def fetch_forecast(lat, lon):
    try:
        url = f"https://api.tomorrow.io/v4/weather/forecast?location={lat},{lon}&apikey={tomorrow_api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching forecast data: {e}")
        return {}

# Fetch air quality data
def fetch_air_quality(lat, lon):
    try:
        url = f"https://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={airvisual_api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching air quality data: {e}")
        return {}

# Fetch user's location based on IP
def fetch_ip_location():
    try:
        url = "https://ipinfo.io"
        response = requests.get(url).json()
        loc = response['loc'].split(',')
        return loc[0], loc[1]
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching IP location: {e}")
        return None, None

# Get weather description based on code
def get_weather_description(code):
    weather_descriptions = {
        1000: "Clear 🌞",
        1001: "Cloudy ☁️",
        1100: "Mostly Clear 🌤️",
        1101: "Partly Cloudy ⛅",
        1102: "Mostly Cloudy ☁️",
        2000: "Fog 🌫️",
        2100: "Light Fog 🌫️",
        3000: "Light Wind 🍃",
        3001: "Windy 🌬️",
        3002: "Strong Wind 🌪️",
        4000: "Drizzle 🌧️",
        4001: "Rain 🌧️",
        4200: "Light Rain 🌦️",
        4201: "Heavy Rain 🌧️",
        5000: "Snow ❄️",
        5001: "Flurries ❄️",
        5100: "Light Snow ❄️",
        5101: "Heavy Snow ❄️",
        6000: "Freezing Drizzle 🌧️❄️",
        6001: "Freezing Rain 🌧️❄️",
        6200: "Light Freezing Rain 🌧️❄️",
        6201: "Heavy Freezing Rain 🌧️❄️",
        7000: "Ice Pellets 🌧️❄️",
        7101: "Heavy Ice Pellets 🌧️❄️",
        7102: "Light Ice Pellets 🌧️❄️",
        8000: "Thunderstorm ⛈️"
    }
    return weather_descriptions.get(code, "Unknown")

# Get temperature emoji based on temperature
def get_temperature_emoji(temp_c):
    if temp_c <= 0:
        return "🥶"
    elif temp_c < 10:
        return "🧥"
    elif temp_c < 20:
        return "🙂"
    elif temp_c < 30:
        return "😊"
    else:
        return "🥵"

# Display current weather
def display_current_weather(weather_data, air_quality_data, location_data):
    st.write("### Current Weather:")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp_c = weather_data['values']['temperature']
    temp_f = celsius_to_fahrenheit(temp_c)
    weather_code = weather_data['values']['weatherCode']
    weather_description = get_weather_description(weather_code)
    air_quality_index = air_quality_data['data']['current']['pollution']['aqius']
    temp_emoji = get_temperature_emoji(temp_c)

    city = location_data.get("city", "Unknown city")
    state = location_data.get("region", "")
    country = location_data.get("country", "Unknown country")
    location = f"{city}, {state}, {country}".strip(", ")

    st.write(f"Location: {location}")
    st.write(f"Current Time: {current_time}")
    st.write(f"Temperature: {temp_c:.2f} °C / {temp_f:.2f} °F {temp_emoji}")
    st.write(f"Weather: {weather_description}")
    st.write(f"Air Quality Index (AQI): {air_quality_index}")
    st.write("---")

# Display 5-day weather forecast
def display_forecast_data(forecast_data, air_quality_data):
    if 'timelines' in forecast_data and 'hourly' in forecast_data['timelines'] and air_quality_data["status"] == "success":
        st.write("### 5-Day Forecast:")
        daily_data = defaultdict(lambda: {
            "morning": {"temps": [], "codes": [], "precip_probs": [], "precip_times": []},
            "afternoon": {"temps": [], "codes": [], "precip_probs": [], "precip_times": []},
            "evening": {"temps": [], "codes": [], "precip_probs": [], "precip_times": []},
            "night": {"temps": [], "codes": [], "precip_probs": [], "precip_times": []}
        })

        start_date = datetime.today()

        for interval in forecast_data['timelines']['hourly']:
            datetime_obj = datetime.fromisoformat(interval['time'][:-1])
            date = datetime_obj.strftime('%Y-%m-%d')
            time = datetime_obj.strftime('%H:%M')
            hour = datetime_obj.hour
            temp_c = interval['values']['temperature']
            temp_f = celsius_to_fahrenheit(temp_c)
            weather_code = interval['values']['weatherCode']
            precip_prob = interval['values'].get('precipitationProbability', 0)

            if 6 <= hour < 12:
                period = "morning"
            elif 12 <= hour < 18:
                period = "afternoon"
            elif 18 <= hour < 24:
                period = "evening"
            else:
                period = "night"

            daily_data[date][period]['temps'].append((temp_c, temp_f))
            daily_data[date][period]['codes'].append(weather_code)
            daily_data[date][period]['precip_probs'].append(precip_prob)
            if precip_prob > 50:
                daily_data[date][period]['precip_times'].append(time)

        # Remove the last day if more than 5 days of data
        if len(daily_data) > 5:
            dates = list(daily_data.keys())
            last_date = dates[-1]
            del daily_data[last_date]

        for i, (date, periods) in enumerate(daily_data.items()):
            day_of_week = (start_date + timedelta(days=i)).strftime('%A')
            if i == 0:
                st.markdown(f"<h3>{day_of_week}, {date}</h3>", unsafe_allow_html=True)
                for period, data in periods.items():
                    if data['temps']:
                        avg_temp_c = sum(temp[0] for temp in data['temps']) / len(data['temps'])
                        avg_temp_f = sum(temp[1] for temp in data['temps']) / len(data['temps'])
                        weather_code = max(set(data['codes']), key=lambda x: data['codes'].count(x))
                        weather_description = get_weather_description(weather_code)
                        max_precip_prob = max(data['precip_probs'])
                        rain_times = [time for time in data['precip_times']]
                        temp_emoji = get_temperature_emoji(avg_temp_c)
                        st.write(f"**{period.capitalize()}:**")
                        st.write(f"Average Temperature: {avg_temp_c:.2f} °C / {avg_temp_f:.2f} °F {temp_emoji}")
                        st.write(f"Weather: {weather_description}")
                        st.write(f"Chance of Rain: {max_precip_prob}%")
                        if rain_times:
                            st.write(f"Expected Rain Time(s): {', '.join(rain_times)}")
                        st.write("---")
                st.write(f"Air Quality Index (AQI): {air_quality_data['data']['current']['pollution']['aqius']}")
                st.write("---")
            else:
                with st.expander(f"Forecast for {day_of_week}, {date}"):
                    for period, data in periods.items():
                        if data['temps']:
                            avg_temp_c = sum(temp[0] for temp in data['temps']) / len(data['temps'])
                            avg_temp_f = sum(temp[1] for temp in data['temps']) / len(data['temps'])
                            weather_code = max(set(data['codes']), key=lambda x: data['codes'].count(x))
                            weather_description = get_weather_description(weather_code)
                            max_precip_prob = max(data['precip_probs'])
                            rain_times = [time for time in data['precip_times']]
                            temp_emoji = get_temperature_emoji(avg_temp_c)
                            st.write(f"**{period.capitalize()}:**")
                            st.write(f"Average Temperature: {avg_temp_c:.2f} °C / {avg_temp_f:.2f} °F {temp_emoji}")
                            st.write(f"Weather: {weather_description}")
                            st.write(f"Chance of Rain: {max_precip_prob}%")
                            if rain_times:
                                st.write(f"Expected Rain Time(s): {', '.join(rain_times)}")
                            st.write("---")
                    st.write(f"Air Quality Index (AQI): {air_quality_data['data']['current']['pollution']['aqius']}")
                    st.write("---")
    else:
        st.error("Failed to retrieve forecast data. Please check the city name.")
        st.json(forecast_data)
        st.json(air_quality_data)

# Display data in a table
def display_table(forecast_data):
    data = []
    for interval in forecast_data['timelines']['hourly']:
        datetime_obj = datetime.fromisoformat(interval['time'][:-1])
        date = datetime_obj.strftime('%Y-%m-%d')
        hour = datetime_obj.strftime('%H:%M')
        temp_c = interval['values']['temperature']
        temp_f = celsius_to_fahrenheit(temp_c)
        weather_code = interval['values']['weatherCode']
        weather_description = get_weather_description(weather_code)
        precip_prob = interval['values'].get('precipitationProbability', 0)
        data.append([date, hour, temp_c, temp_f, weather_description, precip_prob])
    
    df = pd.DataFrame(data, columns=['Date', 'Hour', 'Temp (C)', 'Temp (F)', 'Weather', 'Precipitation Probability'])
    st.dataframe(df)

# Plot temperature chart
def plot_temperature_chart(forecast_data):
    dates = []
    temps_c = []
    temps_f = []

    for interval in forecast_data['timelines']['hourly']:
        datetime_obj = datetime.fromisoformat(interval['time'][:-1])
        dates.append(datetime_obj)
        temp_c = interval['values']['temperature']
        temp_f = celsius_to_fahrenheit(temp_c)
        temps_c.append(temp_c)
        temps_f.append(temp_f)

    plt.figure(figsize=(10, 6))
    plt.plot(dates, temps_c, label='Temp (C)')
    plt.plot(dates, temps_f, label='Temp (F)')
    plt.xlabel('Date')
    plt.ylabel('Temperature')
    plt.title('Temperature Forecast')
    plt.legend()
    st.pyplot(plt)

# Main function
def main():
    lat, lon = fetch_ip_location()
    if lat is None or lon is None:
        st.error("Failed to retrieve IP location.")
        return
    
    location_data = requests.get("https://ipinfo.io").json()

    forecast_data = fetch_forecast(lat, lon)
    air_quality_data = fetch_air_quality(lat, lon)
    
    if forecast_data and air_quality_data:
        if 'timelines' in forecast_data and 'hourly' in forecast_data['timelines']:
            current_weather_data = forecast_data['timelines']['hourly'][0]
            display_current_weather(current_weather_data, air_quality_data, location_data)
            map_creator(lat, lon)
            display_forecast_data(forecast_data, air_quality_data)
            
            st.success("Data fetched successfully!")

            show_table = st.checkbox('Show Forecast Table', key='initial_table')
            if show_table:
                display_table(forecast_data)
            
            st.write("## Temperature Chart")
            plot_temperature_chart(forecast_data)
        else:
            st.error("Weather data is missing 'timelines' or 'hourly' information.")
            st.json(forecast_data)
    else:
        st.error("Failed to retrieve weather information.")
    
    if st.button('Refresh Data'):
        st.rerun()

if __name__ == "__main__":
    main()


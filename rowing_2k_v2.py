import streamlit as st
import numpy as np
from openai import OpenAI

def predict_2000m_time(WWmax, WW4mmol1, WWVO2max, VV_O2LT_LSS):
    speed = 3.26 + 0.000833 * WWmax + 0.00140 * WW4mmol1 + 0.00202 * WWVO2max + 0.0975 * VV_O2LT_LSS
    time = 2000 / speed
    return time

def get_P_from_pace(pace_500):
    return 2.80 / ((pace_500 / 500) ** 3)

def get_MPO_from_Vo2max(VO2max, weight):
    return (VO2max * weight - 810)/11.49 

def get_VolRel(sex: str, body_fat: float) -> float:
    sex = sex.lower()
    if sex == "men":
        body_fat_values = np.array([4, 14, 15, 21, 22, 28, 29])
        body_water_values = np.array([70, 63, 63, 57, 57, 52, 52])
    elif sex == "women":
        body_fat_values = np.array([4, 20, 21, 29, 30, 36, 37])
        body_water_values = np.array([70, 58, 58, 52, 52, 45, 45])
    else:
        raise ValueError("Sex must be 'men' or 'women'.")
    return (np.interp(body_fat, body_fat_values, body_water_values) * 0.735) / 100

# Constants
Ks4 = 10.7
Ks1 = 0.25 ** 2
Ks2 = 1.1 ** 3
Ks3 = 0.04
VolRel = 0.46305

# Streamlit UI
st.title("Pronostic Chrono 2K")
st.markdown("Estimation de performance sur 2000m Ergo.")

# User input into session_state
st.session_state.sex = st.selectbox("Sex", ["Men", "Women"])
st.session_state.pace_500 = st.slider("Meilleure allure en seconde / 500m (effort max)", 60, 80, 69)
st.session_state.vo2max = st.slider("VO2max", 30, 90, 54)
st.session_state.vlamax = st.slider("VLaMax", 0.1, 1.8, 1.2)
st.session_state.weight = st.slider("Weight (kg)", 55, 120, 102)

# Derived values
VO2ss = np.arange(1, st.session_state.vo2max - 5, 0.01)
ADP = np.sqrt((Ks1 * VO2ss) / (st.session_state.vo2max - VO2ss))
vLass = 60 * st.session_state.vlamax / (1 + (Ks2 / ADP ** 3))
LaComb = Ks3 * VO2ss
vLanet = abs(vLass - LaComb)
Intensity = ((vLass * (VolRel * st.session_state.weight) * ((1/4.3) * 22.4) / st.session_state.weight) + VO2ss) / (Ks4 / st.session_state.weight)
arg_sAT = np.argmin(vLanet)
st.session_state.sAT = Intensity[arg_sAT]

# OpenAI client


# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])  # Use secrets for security
client = OpenAI(api_key = API_KEY)
client_openai = OpenAI(api_key = API_KEY)
# Prediction
if st.button("Prédire le temps sur 2000m"):
    st.session_state.WWmax = get_P_from_pace(st.session_state.pace_500)
    st.session_state.WWVO2max = get_MPO_from_Vo2max(st.session_state.vo2max, st.session_state.weight)
    st.session_state.VV_O2LT_LSS = (st.session_state.sAT * Ks4 / st.session_state.vo2max) / 100

    predicted_time = predict_2000m_time(
        st.session_state.WWmax,
        st.session_state.sAT,
        st.session_state.WWVO2max,
        st.session_state.VV_O2LT_LSS,
    )

    st.session_state.predicted_time = predicted_time
    minutes = int(predicted_time // 60)
    seconds = int(predicted_time % 60)
    st.success(f"Temps prédit sur 2000m : {minutes} min {seconds:.2f} s")

    st.session_state.minutes = minutes
    st.session_state.seconds = seconds

# AI Analysis
if st.button("Generate AI Analysis"):
    if "predicted_time" not in st.session_state:
        st.warning("Clique d'abord sur 'Prédire le temps sur 2000m'")
    else:
        prompt = f"""
        You're a sports scientist and coach. You have to analyze the following data from a 2000m rowing ergometer test.
        According to a research paper, speed for a 2000m test is calculated using the following formula: 
        speed = 3.26 + 0.000833 * Watts_max + 0.00140 * Lt2 + 0.00202 * MPO + 0.0975 * (%Vo2max @LT2)
        The data is as follows:
        - VO2max: {st.session_state.vo2max}
        - VLaMax: {st.session_state.vlamax}
        - Weight: {st.session_state.weight}
        - Lt2: {st.session_state.sAT}
        - %Vo2max @LT2: {st.session_state.VV_O2LT_LSS}
        - MPO (Mean Power Output): {st.session_state.WWVO2max}
        - Watts_max: {st.session_state.WWmax}
        Then the 2000m time is calculated as {st.session_state.minutes} min {st.session_state.seconds:.2f} s.
        The athlete wants to qualify for the next Olympic Games.

        Please analyze the data and give a detailed analysis of the performance, including strengths and weaknesses
        What are the key points to focus on to improve the 2000m time?
        What parameters should he reach to get a 5'50 on 2000m?
        What parameters should he reach to get a 5'45 on 2000m?
        Be sharp and precise in your analysis.
        Don't output the formula in the analysis.
        Don't output the data in the analysis.
      
        """

        
        st.markdown("### Analyse IA")
        
        response = client_openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a Rowing coach - Physilogist expert."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},

            ]}
        ],
        max_tokens=1500,
        )
        st.write(response.choices[0].message.content)
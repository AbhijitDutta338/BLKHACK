import streamlit as st
import json
from api.client import post
from analytics.projections import future_value
from analytics.retirement import retirement_gap
from analytics.inflation import inflation_adjust
from analytics.fire import fire_score
from analytics.risk import risk_score
from config import EXPECTED_RETURN_INDEX, RETIREMENT_AGE_DEFAULT


def render():

    st.set_page_config(layout="wide")

    st.title("INVESTOR CONTROL PANEL")

    raw = st.text_area("Payload Input", height=250)

    if not raw:
        st.info("Paste payload to begin analysis.")
        return

    payload = json.loads(raw)

    age = payload["age"]
    wage = payload["wage"]
    inflation = payload["inflation"]
    transactions = payload["transactions"]

    _, nps_data = post("returns:nps", payload)
    _, index_data = post("returns:index", payload)

    index_profit = sum(d["profit"] for d in index_data["savingsByDates"])
    nps_profit = sum(d["profit"] for d in nps_data["savingsByDates"])
    total_corpus = index_profit + nps_profit

    # =====================================================
    # 🔥 SIDEBAR = MICRO SAVINGS FEED (Behavior Engine)
    # =====================================================
    st.sidebar.header("Micro Savings Feed")

    for t in transactions:
        if t["amount"] > 0:
            fv = future_value(
                t["amount"],
                age,
                EXPECTED_RETURN_INDEX
            )

            loss = round(fv - t["amount"], 2)

            st.sidebar.markdown(
                f"""
                **₹{t['amount']} saved on {t['date']}**

                → Value at {RETIREMENT_AGE_DEFAULT}: ₹{round(fv,2)}

                ❗ If spent instead: **₹{loss} lost future wealth**

                _Increase your P contribution to amplify compounding._
                """
            )

    # =====================================================
    # MAIN DASHBOARD (ADMIN STYLE)
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Index Profit", round(index_profit, 2))
    col2.metric("NPS Profit", round(nps_profit, 2))
    col3.metric("Total Corpus", round(total_corpus, 2))
    col4.metric("Years to 60", retirement_gap(age, RETIREMENT_AGE_DEFAULT))

    st.divider()

    # =====================================================
    # 📊 Risk Score Gauge
    # =====================================================
    st.subheader("Risk Behavior Score")

    score = risk_score(transactions, wage)

    st.progress(score / 100)
    st.write(f"Risk Score: {score}/100")

    if score > 70:
        st.error("High behavioral risk detected.")
    elif score > 40:
        st.warning("Moderate risk spending behavior.")
    else:
        st.success("Healthy financial behavior.")

    st.divider()

    # =====================================================
    # 🔥 FIRE Score
    # =====================================================
    st.subheader("FIRE Progress")

    annual_expense = wage * 0.6
    fire = fire_score(total_corpus, annual_expense)

    st.progress(fire / 100)
    st.write(f"FIRE Completion: {fire}%")

    if fire < 25:
        st.warning("Aggressive increase in P contribution recommended.")
    elif fire < 60:
        st.info("On track but acceleration needed.")
    else:
        st.success("Strong path toward financial independence.")

    st.divider()

    # =====================================================
    # 📉 Inflation Simulator
    # =====================================================
    st.subheader("Inflation Erosion Projection")

    years = RETIREMENT_AGE_DEFAULT - age
    real_value = inflation_adjust(total_corpus, inflation, years)

    colA, colB = st.columns(2)
    colA.metric("Future Nominal Corpus @60", round(total_corpus, 2))
    colB.metric("Real Value (Inflation Adjusted)", round(real_value, 2))

    st.divider()

    # =====================================================
    # 📈 Return Comparison
    # =====================================================
    st.subheader("Return Strategy Comparison")

    st.bar_chart({
        "Index": index_profit,
        "NPS": nps_profit
    })

    if index_profit > nps_profit:
        st.success("Index strategy outperforming.")
    else:
        st.info("NPS providing defensive stability.")
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  5 11:21:42 2023

@author: USER
"""


import pandas as pd
import numpy as np

import plotly.express as px
import yfinance as yf
import datetime as dt
from pandas.tseries.offsets import DateOffset
from twelvedata import TDClient
import streamlit as st 


#Parameter
Api_key = "f0a40d81fefa469ea20d4aa0371f128a"
holding_period = DateOffset(months=1)

st.title('Non Farm Payroll backtest')

#Get Data 
#https://docs.google.com/spreadsheets/d/1toJQcmq_XsyhnjJ9NL6tbR3e5KnYPY-0A801v4VoHfY/edit?usp=sharing
sheet_id ="1toJQcmq_XsyhnjJ9NL6tbR3e5KnYPY-0A801v4VoHfY"
nfp = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv")

#Data Cleaning
nfp.drop(["Unnamed: 0","actual_formatted","forecast_formatted","revised","revised_formatted"], inplace=True, axis=1)
nfp = nfp.dropna()
nfp.index = pd.to_datetime(nfp['timestamp'], unit='ms').dt.floor("D")
nfp["Deviation"] = nfp["actual"] - nfp["forecast"]
nfp["Deviation_precent%"] = (round((nfp["Deviation"]/nfp["actual"].abs())*100,4))
nfp.drop(columns="timestamp", axis=1, inplace=True)
nfp["signal"] = np.where(nfp["Deviation"]>0,"buy","sell")

#show dataframe
st.markdown("Non Farm Payroll Record")
nfp_display = nfp.sort_index(ascending=False).T
st.dataframe(data=nfp_display)

#Check buy or sell
nfp_buy_signal = nfp[nfp["signal"] == "buy"]
nfp_sell_signal = nfp[nfp["signal"] == "sell"]


st.markdown(":blue[Buy once actual more than forecast and sell once less than]")

holding_periods = ["Same day", "1 week", "1 month"]
holding_periods_select = st.selectbox("Holding Period: ", holding_periods)

if holding_periods_select == "Same day":
    holding_period= DateOffset(days=0)
elif holding_periods_select == "1 week":
    holding_period= DateOffset(weeks=1)
else:
    holding_period= DateOffset(months=1)
    
    
#Get Data 
td = TDClient(apikey=Api_key)
symbol = "SPX"
ticker = td.time_series(
    symbol=symbol,
    interval="1day",
    outputsize=5000,
    )
ticker = ticker.as_pandas()

ticker = ticker.sort_values(by=['datetime'], ascending=True)


#backtest  order 
#Buy_signal

holiday_count = 0
buy_returns_list = []
open_date_list, close_date_list = [],[]
open_price_list, close_price_list = [],[]
for i in range(len(nfp_buy_signal)):
  #if non farm payroll announcement on stock holiday
  if ticker[ticker.index == nfp_buy_signal.index[i]].empty: 
    while ticker[ticker.index == nfp_buy_signal.index[i] + DateOffset(days=holiday_count)].empty: #add 1 days until the stock market open
      holiday_count+=1 
    else:
      sub_df = ticker[(ticker.index >= nfp_buy_signal.index[i] + DateOffset(days=holiday_count)) & 
      (ticker.index <= nfp_buy_signal.index[i] + holding_period+ DateOffset(days=holiday_count))]

  else:
    sub_df = ticker[(ticker.index >= nfp_buy_signal.index[i]) & 
          (ticker.index <= nfp_buy_signal.index[i] + holding_period)]
  returns = 1+ (sub_df.close[-1] - sub_df.open[0])/sub_df.open[0]


  #record trade position 
  open_date_list.append(sub_df.index[0]) 
  close_date_list.append(sub_df.index[-1])
  open_price_list.append(round(sub_df.open[0],2))
  close_price_list.append(round(sub_df.close[-1],2))
  buy_returns_list.append(round(returns,4))


buy_trade = pd.DataFrame({"open_time":open_date_list ,"close_time":close_date_list, "open_position":open_price_list,"close_position":close_price_list,"return":buy_returns_list})

#Sell_signal

sholiday_count = 0
sell_returns_list = []
open_date_list, close_date_list = [],[]
open_price_list, close_price_list = [],[]
for i in range(len(nfp_sell_signal)):
  #if non farm payroll announcement on stock holiday
  if ticker[ticker.index == nfp_sell_signal.index[i]].empty: 
    while ticker[ticker.index == nfp_sell_signal.index[i] + DateOffset(days=holiday_count)].empty: #add 1 days until the stock market open
      holiday_count+=1 
    else:
      sub_df = ticker[(ticker.index >= nfp_sell_signal.index[i] + DateOffset(days=holiday_count)) & 
      (ticker.index <= nfp_sell_signal.index[i] + holding_period+ DateOffset(days=holiday_count))]

  else:
    sub_df = ticker[(ticker.index >= nfp_sell_signal.index[i]) & 
          (ticker.index <= nfp_sell_signal.index[i] + holding_period)]
  returns = 1+ (sub_df.open[0] - sub_df.close[-1])/sub_df.open[0]


  #record trade position 
  open_date_list.append(sub_df.index[0]) 
  close_date_list.append(sub_df.index[-1])
  open_price_list.append(round(sub_df.open[0],2))
  close_price_list.append(round(sub_df.close[-1],2))
  sell_returns_list.append(round(returns,4))

sell_trade = pd.DataFrame({"open_time":open_date_list ,"close_time":close_date_list, "open_position":open_price_list,"close_position":close_price_list,"return":sell_returns_list})

#concat the trade with signal data
nfp_buy_signal_copy = nfp_buy_signal.reset_index()
nfp_sell_signal_copy = nfp_sell_signal.reset_index()
buy_record = pd.concat([nfp_buy_signal_copy, buy_trade ], axis = 1)
sell_record = pd.concat([nfp_sell_signal_copy, sell_trade ], axis = 1)
nfp_trade_record = pd.merge(buy_record,sell_record, how="outer").sort_values(by='timestamp', ascending=True).reset_index(drop=True)

#Calculate total_return
inital = 100
acc_return, drop_down_list = [],[]
for i in range(len(nfp_trade_record)):
  inital = inital * nfp_trade_record.iloc[i,11]
  acc_return.append(round(inital,2))
  
  drop_down = max(acc_return) - inital 
  drop_down_list.append(drop_down)
  
nfp_trade_record["acc_return"] = acc_return
nfp_trade_record["drop_down"] = drop_down_list

tab1, tab2, tab3 = st.tabs(["Static", "Chart", "Trade Log"])

with tab1:
    total_return = round(nfp_trade_record.acc_return.iloc[-1] - 100,2)
    st.code(f"Return: {total_return}%")
    st.code(f"Max Drop Down: {round((max(drop_down_list)/max(acc_return))*100,2)}%")
with tab2:
    fig = px.line(
        nfp_trade_record,
        x="timestamp",
        y="acc_return")
    st.plotly_chart(fig)

with tab3:
    st.dataframe(data=nfp_trade_record.sort_values(by='timestamp', ascending=False).reset_index(drop=True))


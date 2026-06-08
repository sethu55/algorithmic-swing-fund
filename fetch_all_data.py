import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEFRAMES = {'3mo': 63, '6mo': 126, '9mo': 189, '1y': 252, '2y': 504}
FRICTION = 0.15

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORTFOLIOS = {
    'semi': ({
        'HCL Tech': 'HCLTECH.NS', 'Tata Elxsi': 'TATAELXSI.NS', 'Dixon Technologies': 'DIXON.NS',
        'CG Power': 'CGPOWER.NS', 'Kaynes Technology': 'KAYNES.NS', 'Vedanta': 'VEDL.NS',
        'BEL': 'BEL.NS', 'Data Patterns': 'DATAPATTNS.NS', 'Syrma SGS': 'SYRMA.NS',
        'Cyient DLM': 'CYIENTDLM.NS', 'PG Electroplast': 'PGEL.NS', 'Avalon Technologies': 'AVALON.NS',
        'MosChip Tech': 'MOSCHIP.NS', 'Paras Defence': 'PARAS.NS'
    }, 'semi_data.json', 'SEMICONDUCTORS', 'Scaled Elastic Band'),
    
    'ancillary': ({
        'ASM Tech (Equip)': 'ASMTEC.NS', 'RIR Power (SiC)': 'RIR.NS', 'SPEL Semi (OSAT)': 'SPEL.NS',
        'Linde India (Gases)': 'LINDEINDIA.NS', 'Navin Fluorine (Chems)': 'NAVINFLUOR.NS',
        'Archean Chem (Chems)': 'ACI.NS', 'Stallion India (Chems)': 'STALLION.BO',
        'Amber Ent (PCB)': 'AMBER.NS', 'Hitachi Energy (Power)': 'POWERINDIA.NS',
        'L&T Tech (Design)': 'LTTS.NS', 'Tata Chemicals (Silica)': 'TATACHEM.NS'
    }, 'data.json', 'ANCILLARY ECOSYSTEM', 'Scaled Elastic Band'),

    'nuclear': ({
        'BHEL (Main)': 'BHEL.NS', 'L&T (Main)': 'LT.NS', 'Walchandnagar (Main)': 'WALCHANNAG.NS',
        'Godrej Ind (Main)': 'GODREJIND.NS', 'Thermax (Ancillary)': 'THERMAX.NS',
        'KSB Ltd (Ancillary)': 'KSB.NS', 'GMM Pfaudler (Ancillary)': 'GMMPFAUDL.NS',
        'Apar Ind (Ancillary)': 'APARINDS.NS', 'Graphite India (Ancillary)': 'GRAPHITE.NS',
        'MTAR Tech (Ancillary)': 'MTARTECH.NS'
    }, 'nuclear_data.json', 'NUCLEAR ENERGY', 'Trend Follow (50/200 DMA)'),

    'water': ({
        'VA Tech Wabag (Main)': 'WABAG.NS', 'Ion Exchange (Main)': 'IONEXCHANG.NS',
        'EMS Ltd (Main)': 'EMSLIMITED.NS', 'Enviro Infra (Main)': 'ENVIROINFRA.NS',
        'Supreme Ind (Ancillary)': 'SUPREMEIND.NS', 'Astral (Ancillary)': 'ASTRAL.NS',
        'Prince Pipes (Ancillary)': 'PRINCEPIPE.NS', 'Finolex Ind (Ancillary)': 'FINPIPE.NS',
        'Kirloskar Bros (Ancillary)': 'KIRLOSBROS.NS', 'Shakti Pumps (Ancillary)': 'SHAKTIPUMP.NS'
    }, 'water_data.json', 'WATER INFRASTRUCTURE', 'MACD Momentum'),

    'drone': ({
        'ideaForge (Main)': 'IDEAFORGE.NS', 'Zen Tech (Main)': 'ZENTEC.NS',
        'Paras Defence (Main)': 'PARAS.NS', 'Data Patterns (Main)': 'DATAPATTNS.NS',
        'BEL (Ancillary)': 'BEL.NS', 'Astra Microwave (Ancillary)': 'ASTRAMC.NS',
        'Solar Ind (Ancillary)': 'SOLARINDS.NS', 'HAL (Ancillary)': 'HAL.NS',
        'Laurus Labs (Ancillary)': 'LAURUSLABS.NS', 'Cyient (Ancillary)': 'CYIENT.NS'
    }, 'drone_data.json', 'DRONE & UAV', 'Volume Breakout'),

    'datacenter': ({
        'Anant Raj (Main)': 'ANANTRAJ.NS', 'Netweb Tech (Main)': 'NETWEB.NS',
        'RateGain (Main)': 'RATEGAIN.NS', 'Blue Star (Ancillary)': 'BLUESTARCO.NS',
        'Voltas (Ancillary)': 'VOLTAS.NS', 'ABB India (Ancillary)': 'ABB.NS',
        'Siemens India (Ancillary)': 'SIEMENS.NS', 'Polycab (Ancillary)': 'POLYCAB.NS',
        'Sterlite Tech (Ancillary)': 'STLTECH.NS', 'HFCL (Ancillary)': 'HFCL.NS',
        'Schneider India (Ancillary)': 'SCHNEIDER.NS'
    }, 'datacenter_data.json', 'DATA CENTER & AI INFRA', 'Volume Breakout'),

    'hydrogen': ({
        'L&T (Main)': 'LT.NS', 'NTPC (Main)': 'NTPC.NS', 'Indian Oil (Main)': 'IOC.NS',
        'GAIL (Main)': 'GAIL.NS', 'Thermax (Ancillary)': 'THERMAX.NS',
        'Praj Ind (Ancillary)': 'PRAJ.NS', 'Kirloskar Oil (Ancillary)': 'KIRLOSENG.NS',
        'Gujarat Fluoro (Ancillary)': 'FLUOROCHEM.NS', 'Sterling & Wilson (Ancillary)': 'SWSOLAR.NS',
        'Deepak Fertilisers (Ancillary)': 'DEEPAKFERT.NS'
    }, 'hydrogen_data.json', 'GREEN HYDROGEN', 'Scaled Elastic Band')
}

def add_indicators(df):
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['High_20'] = df['High'].rolling(20).max()
    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    
    delta = df['Close'].diff(1)
    gain = delta.where(delta > 0, 0).rolling(14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    ema_fast = df['Close'].ewm(span=12, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_fast - ema_slow
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    df.bfill(inplace=True)
    return df

def run_backtest_and_status(df, strategy_name):
    buy_signals = []; sell_signals = []; trades = []
    in_position = 0.0 # 0.0 (Flat), 1.0 (Full), 0.5 (Runner)
    entry_price = 0.0; highest = 0.0; stop_loss = 0.0
    status = 'NEUTRAL'
    
    close = float(df['Close'].iloc[-1])
    vol = df['Volume'].iloc[-1]
    vol_ma = df['Vol_MA20'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_sig = df['MACD_Signal'].iloc[-1]
    sma50 = df['SMA_50'].iloc[-1]
    sma200 = df['SMA_200'].iloc[-1]
    high_20 = df['High_20'].iloc[-1]

    for i in range(20, len(df)):
        c = float(df['Close'].iloc[i])
        r = df['RSI'].iloc[i]
        m = df['MACD'].iloc[i]
        ms = df['MACD_Signal'].iloc[i]
        prev_m = df['MACD'].iloc[i-1]
        prev_ms = df['MACD_Signal'].iloc[i-1]
        s50 = df['SMA_50'].iloc[i]
        s200 = df['SMA_200'].iloc[i]
        h20 = df['High_20'].iloc[i-1]
        v = df['Volume'].iloc[i]
        vma = df['Vol_MA20'].iloc[i]
        d_str = df.index[i].strftime('%Y-%m-%d')
        
        buy_trigger = False
        strategy_exit = False
        
        if strategy_name == 'Scaled Elastic Band':
            buy_trigger = r < 30
            strategy_exit = r > 70
        elif strategy_name == 'MACD Momentum':
            buy_trigger = prev_m < prev_ms and m > ms and m < 0
            strategy_exit = prev_m > prev_ms and m < ms
        elif strategy_name == 'Trend Follow (50/200 DMA)':
            buy_trigger = s50 > s200 and c > s50 and df['Close'].iloc[i-1] <= df['SMA_50'].iloc[i-1]
            strategy_exit = c < s50
        elif strategy_name == 'Volume Breakout':
            buy_trigger = c > h20 and v > (vma * 1.5)
            strategy_exit = False # Purely trailing stop or scale out
            
        if in_position == 0.0 and buy_trigger:
            in_position = 1.0; entry_price = c; highest = c
            stop_loss = c * 0.90 # 10% Initial Stop Loss
            buy_signals.append({'date': d_str, 'price': round(c, 2), 'note': 'Algorithm Entry'})
        
        elif in_position > 0.0:
            highest = max(highest, c)
            
            if in_position == 1.0:
                if c >= entry_price * 1.25: # SCALE OUT 50%
                    in_position = 0.5
                    trades.append(((c - entry_price) / entry_price * 100 * 0.5) - FRICTION)
                    sell_signals.append({'date': d_str, 'price': round(c, 2), 'note': 'Scale Out 50%'})
                    stop_loss = entry_price # Move to Break-Even!
                elif c <= stop_loss:
                    in_position = 0.0
                    trades.append(((c - entry_price) / entry_price * 100 * 1.0) - FRICTION)
                    sell_signals.append({'date': d_str, 'price': round(c, 2), 'note': 'Stop Loss'})
                elif strategy_exit:
                    in_position = 0.0
                    trades.append(((c - entry_price) / entry_price * 100 * 1.0) - FRICTION)
                    sell_signals.append({'date': d_str, 'price': round(c, 2), 'note': 'Strategy Exit'})
                    
            elif in_position == 0.5:
                stop_loss = max(stop_loss, highest * 0.90) # 10% Trailing Runner
                if c <= stop_loss:
                    in_position = 0.0
                    trades.append(((c - entry_price) / entry_price * 100 * 0.5) - FRICTION)
                    sell_signals.append({'date': d_str, 'price': round(c, 2), 'note': 'Runner Trailing Stop'})
                elif strategy_exit:
                    in_position = 0.0
                    trades.append(((c - entry_price) / entry_price * 100 * 0.5) - FRICTION)
                    sell_signals.append({'date': d_str, 'price': round(c, 2), 'note': 'Strategy Exit Runner'})

    if strategy_name == 'Scaled Elastic Band':
        if rsi < 30: status = 'BREAKOUT ACTIVE — BUY'
        elif rsi < 35: status = 'APPROACHING BREAKOUT'
    elif strategy_name == 'MACD Momentum':
        if macd > macd_sig and df['MACD'].iloc[-2] < df['MACD_Signal'].iloc[-2]: status = 'BREAKOUT ACTIVE — BUY'
        elif macd < 0 and (macd_sig - macd) < 0.5: status = 'APPROACHING BREAKOUT'
    elif strategy_name == 'Trend Follow (50/200 DMA)':
        if sma50 > sma200 and close > sma50 and df['Close'].iloc[-2] <= df['SMA_50'].iloc[-2]: status = 'BREAKOUT ACTIVE — BUY'
        elif close > sma50 and close < sma50 * 1.02: status = 'APPROACHING BREAKOUT'
    elif strategy_name == 'Volume Breakout':
        if close > high_20 and vol > (vol_ma * 1.5): status = 'BREAKOUT ACTIVE — BUY'
        elif close > high_20 * 0.95 and vol > vol_ma: status = 'APPROACHING BREAKOUT'

    if in_position > 0.0:
        close_final = float(df['Close'].iloc[-1])
        ret = ((close_final - entry_price) / entry_price * 100 * in_position) - FRICTION
        trades.append(ret)
        sell_signals.append({'date': df.index[-1].strftime('%Y-%m-%d'), 'price': round(close_final, 2), 'note': 'End'})

    total_return = sum(trades) if trades else 0
    wins = [t for t in trades if t > 0]
    bt = {
        'strategy_name': strategy_name,
        'buy_signals': buy_signals, 'sell_signals': sell_signals,
        'individual_trades_pct': [round(t, 2) for t in trades],
        'total_return_pct': round(total_return, 2),
        'win_rate_pct': round(len(wins)/len(trades)*100, 2) if trades else 0,
        'total_trades': len(trades),
        'max_drawdown_pct': round(min(trades), 2) if trades else 0,
    }
    if status == 'NEUTRAL': status = 'NEUTRAL — BULLISH' if df['Close'].iloc[-1] > df['SMA_50'].iloc[-1] else 'NEUTRAL — BEARISH'
    return bt, status

def get_yfinance_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

def process_portfolio(tickers, output_file, label, strategy_name):
    output_path = os.path.join(ROOT_DIR, output_file)
    print(f"PROCESSING: {label} [{strategy_name}]")
    multi_tf_data = {tf: {} for tf in TIMEFRAMES}
    
    session = get_yfinance_session()
    successful_downloads = 0
    
    for name, symbol in tickers.items():
        try:
            df = yf.download(symbol, period='2y', progress=False, session=session)
            if df.empty: 
                df = yf.download(symbol.replace('.NS', '.BO'), period='2y', progress=False, session=session)
            if df.empty: 
                print(f"Failed to fetch data for {symbol}")
                continue
                
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            df.dropna(inplace=True)
            total_days = len(df)
            if total_days < 50:
                continue
                
            successful_downloads += 1
            
            for tf_name, tf_days in TIMEFRAMES.items():
                if total_days < tf_days: continue
                sliced = df.iloc[-tf_days:].copy()
                sliced = add_indicators(sliced)
                bt, zone = run_backtest_and_status(sliced, strategy_name)
                
                sliced_indexed = sliced.copy()
                sliced_indexed.index = sliced_indexed.index.strftime('%Y-%m-%d')
                chart_data = []
                for date, row in sliced_indexed.iterrows():
                    chart_data.append({
                        'time': date, 'open': round(float(row['Open']), 2), 'high': round(float(row['High']), 2),
                        'low': round(float(row['Low']), 2), 'close': round(float(row['Close']), 2),
                        'sma_50': round(float(row['SMA_50']), 2) if not np.isnan(row['SMA_50']) else None,
                        'sma_200': round(float(row['SMA_200']), 2) if not np.isnan(row['SMA_200']) else None,
                        'rsi': round(float(row['RSI']), 2) if not np.isnan(row['RSI']) else None,
                        'macd': round(float(row['MACD']), 2) if not np.isnan(row['MACD']) else None,
                        'macd_signal': round(float(row['MACD_Signal']), 2) if not np.isnan(row['MACD_Signal']) else None,
                    })
                
                bh = round((chart_data[-1]['close'] - chart_data[0]['close']) / chart_data[0]['close'] * 100, 2)
                multi_tf_data[tf_name][name] = {
                    'chart_data': chart_data, 'backtest': bt,
                    'current_price': chart_data[-1]['close'], 'current_rsi': chart_data[-1]['rsi'],
                    'buy_zone_status': zone, 'buy_hold_return_pct': bh,
                    'strategy_name': strategy_name,
                }
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            pass
            
    if successful_downloads == 0:
        raise Exception(f"CRITICAL ERROR: Failed to download any data for {label}. Yfinance may be blocking the IP. Aborting to protect JSON file integrity.")
        
    with open(output_path, 'w') as f: 
        json.dump(multi_tf_data, f)
    print(f"Successfully wrote {output_path}")

if __name__ == "__main__":
    for key, (tickers, outfile, label, strategy) in PORTFOLIOS.items():
        process_portfolio(tickers, outfile, label, strategy)
    print("Market Data Sync Complete.")

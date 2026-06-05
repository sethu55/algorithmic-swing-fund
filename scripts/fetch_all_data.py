import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

TIMEFRAMES = {'3mo': 63, '6mo': 126, '9mo': 189, '1y': 252, '2y': 504}
FRICTION = 0.15

# Use relative pathing so it runs anywhere (GitHub Actions or local)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORTFOLIOS = {
    'semi': ({
        'HCL Tech': 'HCLTECH.NS', 'Tata Elxsi': 'TATAELXSI.NS', 'Dixon Technologies': 'DIXON.NS',
        'CG Power': 'CGPOWER.NS', 'Kaynes Technology': 'KAYNES.NS', 'Vedanta': 'VEDL.NS',
        'BEL': 'BEL.NS', 'Data Patterns': 'DATAPATTNS.NS', 'Syrma SGS': 'SYRMA.NS',
        'Cyient DLM': 'CYIENTDLM.NS', 'PG Electroplast': 'PGEL.NS', 'Avalon Technologies': 'AVALON.NS',
        'MosChip Tech': 'MOSCHIP.NS', 'Paras Defence': 'PARAS.NS'
    }, 'semi_data.json', 'SEMICONDUCTORS'),
    
    'ancillary': ({
        'ASM Tech (Equip)': 'ASMTEC.NS', 'RIR Power (SiC)': 'RIR.NS', 'SPEL Semi (OSAT)': 'SPEL.NS',
        'Linde India (Gases)': 'LINDEINDIA.NS', 'Navin Fluorine (Chems)': 'NAVINFLUOR.NS',
        'Archean Chem (Chems)': 'ACI.NS', 'Stallion India (Chems)': 'STALLION.BO',
        'Amber Ent (PCB)': 'AMBER.NS', 'Hitachi Energy (Power)': 'POWERINDIA.NS',
        'L&T Tech (Design)': 'LTTS.NS', 'Tata Chemicals (Silica)': 'TATACHEM.NS'
    }, 'data.json', 'ANCILLARY ECOSYSTEM'),

    'nuclear': ({
        'BHEL (Main)': 'BHEL.NS', 'L&T (Main)': 'LT.NS', 'Walchandnagar (Main)': 'WALCHANNAG.NS',
        'Godrej Ind (Main)': 'GODREJIND.NS', 'Thermax (Ancillary)': 'THERMAX.NS',
        'KSB Ltd (Ancillary)': 'KSB.NS', 'GMM Pfaudler (Ancillary)': 'GMMPFAUDL.NS',
        'Apar Ind (Ancillary)': 'APARINDS.NS', 'Graphite India (Ancillary)': 'GRAPHITE.NS',
        'MTAR Tech (Ancillary)': 'MTARTECH.NS'
    }, 'nuclear_data.json', 'NUCLEAR ENERGY'),

    'water': ({
        'VA Tech Wabag (Main)': 'WABAG.NS', 'Ion Exchange (Main)': 'IONEXCHANG.NS',
        'EMS Ltd (Main)': 'EMSLIMITED.NS', 'Enviro Infra (Main)': 'ENVIROINFRA.NS',
        'Supreme Ind (Ancillary)': 'SUPREMEIND.NS', 'Astral (Ancillary)': 'ASTRAL.NS',
        'Prince Pipes (Ancillary)': 'PRINCEPIPE.NS', 'Finolex Ind (Ancillary)': 'FINPIPE.NS',
        'Kirloskar Bros (Ancillary)': 'KIRLOSBROS.NS', 'Shakti Pumps (Ancillary)': 'SHAKTIPUMP.NS'
    }, 'water_data.json', 'WATER INFRASTRUCTURE'),

    'drone': ({
        'ideaForge (Main)': 'IDEAFORGE.NS', 'Zen Tech (Main)': 'ZENTEC.NS',
        'Paras Defence (Main)': 'PARAS.NS', 'Data Patterns (Main)': 'DATAPATTNS.NS',
        'BEL (Ancillary)': 'BEL.NS', 'Astra Microwave (Ancillary)': 'ASTRAMC.NS',
        'Solar Ind (Ancillary)': 'SOLARINDS.NS', 'HAL (Ancillary)': 'HAL.NS',
        'Laurus Labs (Ancillary)': 'LAURUSLABS.NS', 'Cyient (Ancillary)': 'CYIENT.NS'
    }, 'drone_data.json', 'DRONE & UAV'),

    'datacenter': ({
        'Anant Raj (Main)': 'ANANTRAJ.NS', 'Netweb Tech (Main)': 'NETWEB.NS',
        'RateGain (Main)': 'RATEGAIN.NS', 'Blue Star (Ancillary)': 'BLUESTARCO.NS',
        'Voltas (Ancillary)': 'VOLTAS.NS', 'ABB India (Ancillary)': 'ABB.NS',
        'Siemens India (Ancillary)': 'SIEMENS.NS', 'Polycab (Ancillary)': 'POLYCAB.NS',
        'Sterlite Tech (Ancillary)': 'STLTECH.NS', 'HFCL (Ancillary)': 'HFCL.NS',
        'Schneider India (Ancillary)': 'SCHNEIDER.NS'
    }, 'datacenter_data.json', 'DATA CENTER & AI INFRA'),

    'hydrogen': ({
        'L&T (Main)': 'LT.NS', 'NTPC (Main)': 'NTPC.NS', 'Indian Oil (Main)': 'IOC.NS',
        'GAIL (Main)': 'GAIL.NS', 'Thermax (Ancillary)': 'THERMAX.NS',
        'Praj Ind (Ancillary)': 'PRAJ.NS', 'Kirloskar Oil (Ancillary)': 'KIRLOSENG.NS',
        'Gujarat Fluoro (Ancillary)': 'FLUOROCHEM.NS', 'Sterling & Wilson (Ancillary)': 'SWSOLAR.NS',
        'Deepak Fertilisers (Ancillary)': 'DEEPAKFERT.NS'
    }, 'hydrogen_data.json', 'GREEN HYDROGEN')
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

def backtest_swing_rotation(df):
    buy_signals = []; sell_signals = []; trades = []
    in_position = False; entry_price = 0.0; highest = 0.0
    
    for i in range(20, len(df)):
        close = float(df['Close'].iloc[i])
        high_20 = df['High_20'].iloc[i-1]
        vol = df['Volume'].iloc[i]; vol_ma = df['Vol_MA20'].iloc[i]
        date_str = df.index[i].strftime('%Y-%m-%d')
        
        if not in_position:
            if close > high_20 and vol > (vol_ma * 1.5):
                in_position = True; entry_price = close; highest = close
                buy_signals.append({'date': date_str, 'price': round(close, 2), 'note': 'Swing Breakout'})
        else:
            highest = max(highest, close)
            sell_triggered = False; note = ""
            if close >= entry_price * 1.25:
                sell_triggered = True; note = "Take Profit (+25%)"
            elif close <= highest * 0.90:
                sell_triggered = True; note = "Trailing Stop (-10%)"
                
            if sell_triggered:
                ret = ((close - entry_price) / entry_price * 100) - FRICTION
                trades.append(ret)
                sell_signals.append({'date': date_str, 'price': round(close, 2), 'note': note})
                in_position = False
                
    if in_position:
        close = float(df['Close'].iloc[-1])
        ret = ((close - entry_price) / entry_price * 100) - FRICTION
        trades.append(ret)
        sell_signals.append({'date': df.index[-1].strftime('%Y-%m-%d'), 'price': round(close, 2), 'note': 'End of Period'})

    total_return = sum(trades) if trades else 0
    wins = [t for t in trades if t > 0]
    return {
        'strategy_name': 'High-Velocity Swing Rotation',
        'buy_signals': buy_signals, 'sell_signals': sell_signals,
        'individual_trades_pct': [round(t, 2) for t in trades],
        'total_return_pct': round(total_return, 2),
        'win_rate_pct': round(len(wins)/len(trades)*100, 2) if trades else 0,
        'total_trades': len(trades),
        'max_drawdown_pct': round(min(trades), 2) if trades else 0,
    }

def get_zone_status(df):
    close = float(df['Close'].iloc[-1])
    high_20 = df['High_20'].iloc[-1]
    vol = df['Volume'].iloc[-1]; vol_ma = df['Vol_MA20'].iloc[-1]
    
    if close > high_20 and vol > (vol_ma * 1.5):
        return 'BREAKOUT ACTIVE — BUY'
    elif close > high_20 * 0.95 and vol > vol_ma:
        return 'APPROACHING BREAKOUT'
    elif close > df['SMA_50'].iloc[-1]:
        return 'NEUTRAL — BULLISH'
    else:
        return 'NEUTRAL — BEARISH'

def process_portfolio(tickers, output_file, label):
    output_path = os.path.join(ROOT_DIR, output_file)
    print(f"PROCESSING: {label}")
    multi_tf_data = {tf: {} for tf in TIMEFRAMES}
    
    for name, symbol in tickers.items():
        try:
            df = yf.download(symbol, period='2y', progress=False)
            if df.empty: df = yf.download(symbol.replace('.NS', '.BO'), period='2y', progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df.dropna(inplace=True)
            total_days = len(df)
            
            for tf_name, tf_days in TIMEFRAMES.items():
                if total_days < tf_days: continue
                sliced = df.iloc[-tf_days:].copy()
                sliced = add_indicators(sliced)
                bt = backtest_swing_rotation(sliced)
                zone = get_zone_status(sliced)
                
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
                    'strategy_name': 'High-Velocity Swing Rotation',
                }
        except Exception as e:
            print(f"Error on {name}: {e}")
            
    with open(output_path, 'w') as f: json.dump(multi_tf_data, f)

if __name__ == "__main__":
    for key, (tickers, outfile, label) in PORTFOLIOS.items():
        process_portfolio(tickers, outfile, label)
    print("Market Data Sync Complete.")

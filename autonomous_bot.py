import os
import json
import math
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTFOLIO_FILE = os.path.join(ROOT_DIR, 'portfolio.json')
LEDGER_FILE = os.path.join(ROOT_DIR, 'paper_trades.md')
FUNDAMENTALS_FILE = os.path.join(ROOT_DIR, 'fundamentals.json')

SECTORS = {
    'Nuclear': 'nuclear_data.json',
    'Water': 'water_data.json',
    'Drone': 'drone_data.json',
    'DataCenter': 'datacenter_data.json',
    'Hydrogen': 'hydrogen_data.json',
    'Semiconductors': 'semi_data.json',
    'Ancillary': 'data.json'
}

RISK_PERCENT = 0.02  # Risk exactly 2% of Total Portfolio Value per trade
STOP_LOSS_PCT = 0.10 # 10% Initial Stop Loss

def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def load_market_data():
    market = {}
    for sector, file in SECTORS.items():
        path = os.path.join(ROOT_DIR, file)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                if '1y' in data:
                    for comp, d in data['1y'].items():
                        market[comp] = d
    return market

def calculate_portfolio_value(pf, market_data):
    val = pf['cash']
    for comp, pos in pf['active_positions'].items():
        if comp in market_data:
            val += pos.get('shares', 0) * market_data[comp]['current_price']
        else:
            val += pos.get('capital_deployed', 0)
    return val

def render_ledger(pf, market_data):
    md = [
        "# High-Velocity Swing: Paper Trading Ledger",
        "> [!IMPORTANT]",
        "> **Portfolio Objective:** Outperform passive Buy & Hold through aggressive Capital Rotation.",
        "> **Exit Strategy:** Scale-out 50% at +25% Target. Trail the remaining 50% with a 10% dynamic stop.",
        "> **Position Sizing:** Institutional Risk Parity (Risk exactly 2% of Total Portfolio Value per trade).",
        "",
        "## Account Overview",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| **Starting Balance** | INR {pf['starting_balance']:,.2f} |"
    ]
    
    current_value = calculate_portfolio_value(pf, market_data)
            
    md.append(f"| **Current Portfolio Value** | **INR {current_value:,.2f}** |")
    md.append(f"| **Available Cash** | INR {pf['cash']:,.2f} |")
    
    pnl_pct = (pf['realized_pnl'] / pf['starting_balance']) * 100
    md.append(f"| **Total Realized P&L** | INR {pf['realized_pnl']:,.2f} ({pnl_pct:.2f}%) |")
    
    total_trades = pf['trades_won'] + pf['trades_lost']
    win_rate = (pf['trades_won'] / total_trades * 100) if total_trades > 0 else 0
    md.append(f"| **Win Rate** | {win_rate:.1f}% ({total_trades} Trades) |")
    md.append("")
    
    md.append("## Active Positions")
    if not pf['active_positions']:
        md.append("*Currently holding 100% Cash. Waiting for algorithmic triggers.*")
    else:
        md.append("| Date | Company | Shares | Entry Price | Target (+25%) | Trailing Stop (-10%) | Current Price | Unrealized P&L |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for comp, pos in pf['active_positions'].items():
            curr_p = market_data[comp]['current_price'] if comp in market_data else pos['entry_price']
            unrealized_val = (curr_p - pos['entry_price']) * pos.get('shares', 0)
            unrealized_pct = (curr_p - pos['entry_price']) / pos['entry_price'] * 100
            
            size_label = "Full" if pos.get('position_size', 1.0) == 1.0 else "Runner"
            shares_str = f"{pos.get('shares', 0)} ({size_label})"
            target_str = f"INR {pos['target']:.2f}" if pos.get('position_size', 1.0) == 1.0 else "Infinite (Trailing)"
            
            md.append(f"| {pos['entry_date']} | **{comp}** | {shares_str} | INR {pos['entry_price']:.2f} | {target_str} | INR {pos['stop']:.2f} | INR {curr_p:.2f} | {unrealized_pct:.2f}% (INR {unrealized_val:,.2f}) |")
            
    md.append("")
    md.append("## Closed Trade History")
    if not pf['closed_trades']:
        md.append("*No closed trades yet.*")
    else:
        md.append("| Entry | Exit | Company | Entry Price | Exit Price | Shares Sold | Realized P&L | Reason |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for t in reversed(pf['closed_trades'][-15:]): 
            md.append(f"| {t['entry_date']} | {t['exit_date']} | **{t['comp']}** | INR {t['entry_price']:.2f} | INR {t['exit_price']:.2f} | {t.get('shares_sold', 0)} | INR {t['pnl']:,.2f} | {t['reason']} |")
            
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))

def run_bot():
    default_pf = {
        'starting_balance': 1000000.0, 'cash': 1000000.0, 'realized_pnl': 0.0,
        'trades_won': 0, 'trades_lost': 0, 'active_positions': {}, 'closed_trades': []
    }
    pf = load_json(PORTFOLIO_FILE, default_pf)
    market = load_market_data()
    fundamentals = load_json(FUNDAMENTALS_FILE, {})
    
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    to_close = []
    for comp, pos in pf['active_positions'].items():
        if 'shares' not in pos:
            # Backwards compatibility fix
            pos['shares'] = math.floor(150000.0 / pos['entry_price'])
            pos['capital_deployed'] = pos['shares'] * pos['entry_price']
            
            # Reimburse the fractional change lost to the black hole
            missing_cash = 150000.0 - pos['capital_deployed']
            pf['cash'] += missing_cash
            print(f"Reimbursed {missing_cash:.2f} fractional cash for {comp}")
            
        if comp not in market: continue
        curr_p = market[comp]['current_price']
        
        if curr_p > pos['highest']:
            pos['highest'] = curr_p
            pos['stop'] = max(pos['stop'], curr_p * 0.90)
            
        reason = None
        scale_out = False
        
        if pos['position_size'] == 1.0 and curr_p >= pos['target']:
            scale_out = True
            reason = "Scale-Out (+25%)"
        elif curr_p <= pos['stop']:
            reason = "Stop Loss" if pos['position_size'] == 1.0 else "Trailing Stop (Runner Exit)"
            
        if reason:
            shares_to_sell = math.floor(pos['shares'] / 2) if scale_out else pos['shares']
            # Friction = 0.15% per trade round trip
            gross_pnl = (curr_p - pos['entry_price']) * shares_to_sell
            friction_cost = (shares_to_sell * pos['entry_price']) * 0.0015
            net_pnl = gross_pnl - friction_cost
            
            to_close.append({
                'comp': comp, 'entry_date': pos['entry_date'], 'exit_date': today,
                'entry_price': pos['entry_price'], 'exit_price': curr_p,
                'shares_sold': shares_to_sell, 'pnl': net_pnl, 
                'reason': reason, 'scale_out': scale_out
            })
            
    for t in to_close:
        active_pos = pf['active_positions'][t['comp']]
        
        pf['cash'] += (t['shares_sold'] * t['entry_price']) + t['pnl']
        pf['realized_pnl'] += t['pnl']
        if t['pnl'] > 0: pf['trades_won'] += 1
        else: pf['trades_lost'] += 1
        
        t_clean = {k:v for k,v in t.items() if k != 'scale_out'}
        pf['closed_trades'].append(t_clean)
        
        if t['scale_out']:
            active_pos['position_size'] = 0.5
            active_pos['shares'] -= t['shares_sold']
            active_pos['capital_deployed'] -= (t['shares_sold'] * active_pos['entry_price'])
            active_pos['stop'] = max(active_pos['entry_price'], active_pos['highest'] * 0.90)
            print(f"SCALED OUT: {t['comp']} | {t['reason']} | PnL: {t['pnl']:.2f} | Runner active.")
        else:
            del pf['active_positions'][t['comp']]
            print(f"CLOSED FULLY: {t['comp']} | {t['reason']} | PnL: {t['pnl']:.2f}")

    # BUY LOGIC (Institutional Risk Parity)
    current_portfolio_value = calculate_portfolio_value(pf, market)
    risk_amount = current_portfolio_value * RISK_PERCENT # Example: 20k on 1M portfolio
    capital_to_deploy = risk_amount / STOP_LOSS_PCT      # Example: 200k deployed

    for comp, d in market.items():
        status = d['buy_zone_status']
        if 'BREAKOUT ACTIVE' in status or 'BUY' in status:
            if comp not in pf['active_positions'] and pf['cash'] >= capital_to_deploy and len(pf['active_positions']) < 6:
                fund_score = fundamentals.get(comp, 0)
                if fund_score >= 50:
                    curr_p = d['current_price']
                    shares_to_buy = math.floor(capital_to_deploy / curr_p)
                    
                    if shares_to_buy > 0:
                        actual_capital = shares_to_buy * curr_p
                        pf['cash'] -= actual_capital
                        pf['active_positions'][comp] = {
                            'entry_date': today,
                            'entry_price': curr_p,
                            'highest': curr_p,
                            'target': curr_p * 1.25,
                            'stop': curr_p * 0.90,
                            'position_size': 1.0,
                            'shares': shares_to_buy,
                            'capital_deployed': actual_capital
                        }
                        print(f"BOUGHT: {comp} | Shares: {shares_to_buy} | Capital: {actual_capital:,.2f} | Score: {fund_score}")

    save_json(PORTFOLIO_FILE, pf)
    render_ledger(pf, market)
    print("Bot execution complete.")

if __name__ == "__main__":
    run_bot()

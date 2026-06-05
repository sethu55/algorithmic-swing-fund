import os
import json
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

TRADE_SIZE = 150000.0

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

def render_ledger(pf, market_data):
    md = [
        "# High-Velocity Swing: Paper Trading Ledger",
        "> [!IMPORTANT]",
        "> **Portfolio Objective:** Outperform passive Buy & Hold through aggressive Capital Rotation.",
        "",
        "## Account Overview",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| **Starting Balance** | INR {pf['starting_balance']:,.2f} |"
    ]
    
    current_value = pf['cash']
    for comp, pos in pf['active_positions'].items():
        if comp in market_data:
            current_value += (TRADE_SIZE / pos['entry_price']) * market_data[comp]['current_price']
        else:
            current_value += TRADE_SIZE 
            
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
        md.append("| Date | Company | Entry Price | Target (+25%) | Trailing Stop (-10%) | Current Price | Unrealized P&L |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for comp, pos in pf['active_positions'].items():
            curr_p = market_data[comp]['current_price'] if comp in market_data else pos['entry_price']
            unrealized = ((curr_p - pos['entry_price']) / pos['entry_price']) * 100
            md.append(f"| {pos['entry_date']} | **{comp}** | INR {pos['entry_price']:.2f} | INR {pos['target']:.2f} | INR {pos['stop']:.2f} | INR {curr_p:.2f} | {unrealized:.2f}% |")
            
    md.append("")
    md.append("## Closed Trade History")
    if not pf['closed_trades']:
        md.append("*No closed trades yet.*")
    else:
        md.append("| Entry | Exit | Company | Entry Price | Exit Price | Return % | Realized P&L | Reason |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for t in reversed(pf['closed_trades'][-10:]): 
            md.append(f"| {t['entry_date']} | {t['exit_date']} | **{t['comp']}** | INR {t['entry_price']:.2f} | INR {t['exit_price']:.2f} | {t['ret_pct']:.2f}% | INR {t['pnl']:,.2f} | {t['reason']} |")
            
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
        if comp not in market: continue
        curr_p = market[comp]['current_price']
        
        if curr_p > pos['highest']:
            pos['highest'] = curr_p
            pos['stop'] = max(pos['stop'], curr_p * 0.90)
            
        reason = None
        if curr_p >= pos['target']: reason = "Take Profit (+25%)"
        elif curr_p <= pos['stop']: reason = "Trailing Stop (-10%)"
            
        if reason:
            ret_pct = ((curr_p - pos['entry_price']) / pos['entry_price']) * 100 - 0.15 
            pnl = TRADE_SIZE * (ret_pct / 100)
            to_close.append({
                'comp': comp, 'entry_date': pos['entry_date'], 'exit_date': today,
                'entry_price': pos['entry_price'], 'exit_price': curr_p,
                'ret_pct': ret_pct, 'pnl': pnl, 'reason': reason
            })
            
    for t in to_close:
        pf['cash'] += TRADE_SIZE + t['pnl']
        pf['realized_pnl'] += t['pnl']
        if t['pnl'] > 0: pf['trades_won'] += 1
        else: pf['trades_lost'] += 1
        pf['closed_trades'].append(t)
        del pf['active_positions'][t['comp']]
        print(f"CLOSED: {t['comp']} | {t['reason']} | PnL: {t['pnl']:.2f}")

    for comp, d in market.items():
        status = d['buy_zone_status']
        if 'BREAKOUT ACTIVE' in status or 'BUY' in status:
            if comp not in pf['active_positions'] and pf['cash'] >= TRADE_SIZE and len(pf['active_positions']) < 6:
                fund_score = fundamentals.get(comp, 0)
                if fund_score >= 50:
                    curr_p = d['current_price']
                    pf['cash'] -= TRADE_SIZE
                    pf['active_positions'][comp] = {
                        'entry_date': today,
                        'entry_price': curr_p,
                        'highest': curr_p,
                        'target': curr_p * 1.25,
                        'stop': curr_p * 0.90
                    }
                    print(f"BOUGHT: {comp} at {curr_p} (Score: {fund_score})")
                else:
                    print(f"REJECTED: {comp} triggered technical signal but failed fundamental guardrail (Score: {fund_score})")

    save_json(PORTFOLIO_FILE, pf)
    render_ledger(pf, market)
    print("Bot execution complete.")

if __name__ == "__main__":
    run_bot()

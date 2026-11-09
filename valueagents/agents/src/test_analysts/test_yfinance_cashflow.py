import yfinance as yf

def inspect_cashflow(ticker):
    print(f"\n=== 检查 {ticker} 的现金流量表列名 ===")
    stock = yf.Ticker(ticker)
    cf = stock.cashflow
    if cf is None or cf.empty:
        print("❌ 无法获取现金流量表数据")
        return
    
    print("📊 现金流量表索引 (行标签):")
    print(cf.index.tolist())
    
    print("\n📅 年份列:")
    print(cf.columns.tolist())
    
    print("\n🔍 检查分红相关列:")
    possible_names = [
        'Dividends Paid',
        'Common Stock Dividends',
        'Dividends',
        'Cash Dividends',
        'Dividends Paid - Common',
        'Dividends Paid Common Stock',
        'Dividends And Other Cash Distributions'
    ]
    found = False
    for name in possible_names:
        if name in cf.index:
            print(f"  ✅ 找到: '{name}'")
            print(f"     数据: {cf.loc[name].to_dict()}")
            found = True
        else:
            print(f"  ❌ 未找到: '{name}'")
    
    if not found:
        print("\n⚠️ 未找到任何分红列。所有行标签如下:")
        print(cf.index.tolist())

if __name__ == "__main__":
    for ticker in ["MSFT", "AAPL"]:
        inspect_cashflow(ticker)

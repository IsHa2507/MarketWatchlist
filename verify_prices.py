import urllib.request, json

resp = urllib.request.urlopen("http://localhost:8000/dashboard")
d = json.loads(resp.read())

print("=== FINAL PRICE VERIFICATION ===\n")
print("Backend Dashboard API:")
for sec in ['needs_attention', 'worth_watching', 'normal']:
    for item in d.get(sec, []):
        currency = '₹' if item.get('stock_data', {}).get('currency') == 'INR' else '$'
        price = item['current_price']
        print(f"  {item['ticker']}: {currency}{price:,.2f}")

print(f"\nTotal stocks: {d['summary']['total']}")
print(f"All prices are NON-ZERO: {all(item['current_price'] > 0 for sec in ['needs_attention', 'worth_watching', 'normal'] for item in d.get(sec, []))}")

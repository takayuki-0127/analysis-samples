# Power BI 月次ダッシュボード見本用のデータを作る（UCI Online Retail、CC BY 4.0）
import pandas as pd, numpy as np, sys
src = sys.argv[1] if len(sys.argv) > 1 else "Online Retail.xlsx"
d = pd.read_pickle(src) if src.endswith(".pkl") else pd.read_excel(src, dtype={"InvoiceNo": str, "StockCode": str})
d = d[d.CustomerID.notna() & ~d.InvoiceNo.astype(str).str.startswith("C") & (d.Quantity > 0) & (d.UnitPrice > 0)].copy()
d["CustomerID"] = d.CustomerID.astype(int); d["Amount"] = (d.Quantity * d.UnitPrice).round(2)
d["OrderDate"] = d.InvoiceDate.dt.date
fact = d[["InvoiceNo", "OrderDate", "CustomerID", "StockCode", "Quantity", "UnitPrice", "Amount"]]
fact.to_csv("data/fact_sales.csv", index=False)
# 顧客：初回購入月・国・RFM 区分（期間末 2011-12-09 時点、1枚レポートと同じ定義）
ref = pd.Timestamp("2011-12-10")
c = d.groupby("CustomerID").agg(first=("InvoiceDate", "min"), last=("InvoiceDate", "max"), F=("InvoiceNo", "nunique"), M=("Amount", "sum"), Country=("Country", "first"))
c["R"] = (ref - c["last"]).dt.days
rs = pd.qcut(c.R, 5, labels=[5, 4, 3, 2, 1]).astype(int); fs = pd.qcut(c.F.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
def seg(r, f):
    if r >= 4 and f >= 4: return "優良"
    if r <= 2 and f >= 4: return "離れかけの優良"
    if r >= 4 and f <= 2: return "新規・浅い"
    if r <= 2 and f <= 2: return "離脱"
    return "中間"
c["Segment"] = [seg(a, b) for a, b in zip(rs, fs)]
c["FirstMonth"] = c["first"].dt.to_period("M").dt.to_timestamp().dt.date
c["Region"] = np.where(c.Country == "United Kingdom", "英国", "英国以外")
c.reset_index()[["CustomerID", "FirstMonth", "Country", "Region", "Segment"]].to_csv("data/dim_customer.csv", index=False)
print(len(fact), len(c), c.Segment.value_counts().to_dict())
# 検算用：月ごとの KPI（Power BI の数字と突き合わせる）
d["Month"] = d.InvoiceDate.dt.to_period("M")
m = d.groupby("Month").agg(売上=("Amount", "sum"), 注文数=("InvoiceNo", "nunique"), 顧客数=("CustomerID", "nunique"))
m["客単価"] = m.売上 / m.注文数
fm = c["first"].dt.to_period("M"); m["新規顧客数"] = fm.value_counts().reindex(m.index).fillna(0).astype(int)
m["売上_前月比%"] = (m.売上.pct_change() * 100).round(1)
m.round(2).to_csv("data/check_monthly_kpi.csv"); print(m.tail(3))

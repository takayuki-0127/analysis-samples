# 完成イメージ（Power BI で作る前の下絵）。数字は Power BI の検算にも使う
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"
f = pd.read_csv("data/fact_sales.csv", parse_dates=["OrderDate"]); c = pd.read_csv("data/dim_customer.csv", parse_dates=["FirstMonth"])
f = f.merge(c[["CustomerID", "Segment", "FirstMonth"]], on="CustomerID"); f["M"] = f.OrderDate.dt.to_period("M")
f = f[f.M <= "2011-11"]                                     # 12月は9日までなので外す
k = f.groupby("M").agg(s=("Amount", "sum"), o=("InvoiceNo", "nunique"), u=("CustomerID", "nunique")); k["a"] = k.s / k.o
cur, prev = k.loc["2011-11"], k.loc["2011-10"]
INK, SUB, ACC, GRID = "#1f2937", "#6b7280", "#2563eb", "#e5e7eb"
fig = plt.figure(figsize=(16, 9), dpi=100); fig.patch.set_facecolor("#f8fafc")
fig.text(.03, .955, "EC 月次ダッシュボード（見本）  2011年11月", fontsize=20, weight="bold", color=INK)
fig.text(.03, .925, "公開データ：UCI Online Retail（CC BY 4.0）／返品・顧客IDなしを除く", fontsize=10, color=SUB)
cards = [("売上", f"£{cur.s/1e6:.2f}M", cur.s / prev.s - 1), ("注文数", f"{cur.o:,.0f}", cur.o / prev.o - 1),
         ("購入顧客数", f"{cur.u:,.0f}", cur.u / prev.u - 1), ("客単価（1注文）", f"£{cur.a:,.0f}", cur.a / prev.a - 1)]
for i, (t, v, r) in enumerate(cards):
    ax = fig.add_axes([.03 + i * .2425, .74, .225, .155]); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(GRID)
    ax.text(.06, .78, t, fontsize=12, color=SUB, transform=ax.transAxes); ax.text(.06, .38, v, fontsize=26, weight="bold", color=INK, transform=ax.transAxes)
    ax.text(.06, .1, f"前月比 {'+' if r >= 0 else ''}{r*100:.1f}%", fontsize=12, color="#059669" if r >= 0 else "#dc2626", transform=ax.transAxes)
ax = fig.add_axes([.05, .08, .42, .56])
f["区分"] = np.where(f.M == f.FirstMonth.dt.to_period("M"), "新規（その月が初回）", "既存（2回目以降）")
seg = f.pivot_table(index="M", columns="区分", values="Amount", aggfunc="sum").fillna(0) / 1e3
cols = {"既存（2回目以降）": "#2563eb", "新規（その月が初回）": "#10b981"}
x = seg.index.astype(str); bottom = np.zeros(len(seg))
for s, col in cols.items(): ax.bar(x, seg[s], bottom=bottom, color=col, label=s, width=.7); bottom += seg[s].values
ax.set_title("顧客層別の月次売上（新規・既存、千ポンド）", loc="left", fontsize=13, color=INK); ax.grid(axis="y", color=GRID); ax.legend(frameon=False, fontsize=10, ncol=2, loc="upper left")
ax.tick_params(axis="x", rotation=45, labelsize=9); [ax.spines[s].set_visible(False) for s in ("top", "right")]
ax = fig.add_axes([.53, .08, .44, .56])
f["age"] = (f.M - f.FirstMonth.dt.to_period("M")).apply(lambda x: x.n)
co = f.groupby([f.FirstMonth.dt.to_period("M"), "age"]).CustomerID.nunique().unstack()
co = co.loc[:"2011-06", 0:6]; ret = co.div(co[0], axis=0) * 100
ax.imshow(ret.values, cmap="Blues", vmin=0, vmax=60, aspect="auto")
for i in range(ret.shape[0]):
    for j in range(ret.shape[1]):
        v = ret.values[i, j]
        if not np.isnan(v): ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=10, color="white" if v > 40 else INK)
ax.set_xticks(range(ret.shape[1]), [f"{j}か月後" if j else "初回月" for j in ret.columns], fontsize=9)
ax.set_yticks(range(ret.shape[0]), [f"{p}（{int(n)}人）" for p, n in zip(ret.index.astype(str), co[0])], fontsize=9)
ax.set_title("初回購入月別の継続率（コホート）", loc="left", fontsize=13, color=INK)
fig.savefig("out/dashboard_preview.png", facecolor=fig.get_facecolor()); print(cards)

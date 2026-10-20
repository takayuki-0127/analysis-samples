# EC の公開データ（UCI Online Retail・CC BY 4.0）で RFM 分析と月別コホートの継続率 → 「どの顧客層に何をすべきか」の1枚レポート
import os, numpy as np, pandas as pd, matplotlib.pyplot as plt
from analysis_kit import NAVY, TEAL, ORANGE, INK, MUTED, _wrap
OUT = "out"; os.makedirs(OUT, exist_ok=True)
SRC = "data/Online Retail.xlsx"
d = pd.read_pickle("retail.pkl") if os.path.exists("retail.pkl") else pd.read_excel(SRC, dtype={"InvoiceNo": str, "StockCode": str, "Description": str})
c = d[d.CustomerID.notna() & (d.Quantity > 0) & (d.UnitPrice > 0) & ~d.InvoiceNo.str.startswith("C")].copy()
c["amt"] = c.Quantity * c.UnitPrice; c["cid"] = c.CustomerID.astype(int)
SNAP = pd.Timestamp("2011-12-10")

# ---- RFM ----
r = c.groupby("cid").agg(last=("InvoiceDate", "max"), first=("InvoiceDate", "min"), F=("InvoiceNo", "nunique"), M=("amt", "sum"))
r["R"] = (SNAP - r["last"]).dt.days
r["rs"] = pd.qcut(r.R, 5, labels=[5, 4, 3, 2, 1]).astype(int)
r["fs"] = pd.qcut(r.F.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
def seg(x):
    if x.rs >= 4 and x.fs >= 4: return "優良"
    if x.rs <= 2 and x.fs >= 4: return "離れかけの優良"
    if x.rs >= 4 and x.fs <= 2: return "新規・まだ浅い"
    if x.rs <= 2 and x.fs <= 2: return "離脱"
    return "中間"
r["seg"] = r.apply(seg, axis=1)
ORDER = ["優良", "離れかけの優良", "中間", "新規・まだ浅い", "離脱"]
g = r.groupby("seg").agg(n=("M", "size"), rev=("M", "sum"), R=("R", "median"), F=("F", "median"), M=("M", "median")).reindex(ORDER)
g["客数%"] = g.n / g.n.sum() * 100; g["売上%"] = g.rev / g.rev.sum() * 100
print(g.round(1))

# ---- コホート（初回購入月ごとの、n か月後に買った人の割合） ----
c["ym"] = c.InvoiceDate.dt.to_period("M"); c = c.join(c.groupby("cid").ym.min().rename("cohort"), on="cid")
c["age"] = (c.ym - c.cohort).apply(lambda x: x.n)
co = c.groupby(["cohort", "age"]).cid.nunique().unstack()
ret = co.div(co[0], axis=0) * 100
last_full = pd.Period("2011-11", "M")                                  # 2011-12 は9日までなので使わない
for coh in ret.index:
    for a in ret.columns:
        if coh + a > last_full: ret.loc[coh, a] = np.nan
R2011 = ret.loc["2011-01":"2011-10", 0:6]
m1 = R2011[1].mean()

# ---- 2回目の購入までの日数と、その後の購入額 ----
fp = c.groupby(["cid", "InvoiceNo"]).InvoiceDate.min().reset_index().sort_values(["cid", "InvoiceDate"])
fp["k"] = fp.groupby("cid").cumcount()
first = fp[fp.k == 0].set_index("cid").InvoiceDate; second = fp[fp.k == 1].set_index("cid").InvoiceDate
gap = (second - first).dt.days.reindex(first.index)
elig = first[(first >= "2011-01-01") & (first <= "2011-06-30")].index          # 初回が2011年上半期（その後5か月以上見られる人）
x = pd.DataFrame({"gap": gap.loc[elig], "M": r.loc[elig, "M"]})
x["grp"] = np.where(x.gap <= 30, "30日以内", np.where(x.gap.notna(), "31日以降", "2回目なし"))
gx = x.groupby("grp").M.agg(["size", "median"]).reindex(["30日以内", "31日以降", "2回目なし"])
print(gx)

# ---- 図1：顧客層ごとの客数と売上の割合 ----
fig, ax = plt.subplots(figsize=(4.1, 3.0)); yy = np.arange(len(ORDER))[::-1]
ax.barh(yy + .18, g["客数%"], height=.34, color=MUTED, label="客数の割合")
ax.barh(yy - .18, g["売上%"], height=.34, color=TEAL, label="売上の割合")
for yv, a, b in zip(yy, g["客数%"], g["売上%"]):
    ax.text(a + 1, yv + .18, f"{a:.0f}%", va="center", fontsize=7); ax.text(b + 1, yv - .18, f"{b:.0f}%", va="center", fontsize=7)
ax.set_yticks(yy); ax.set_yticklabels([f"{s}（{n:,}人）" for s, n in zip(ORDER, g.n)], fontsize=7.5)
ax.set_xlim(0, 80); ax.legend(fontsize=7, loc="lower right"); ax.grid(axis="x", alpha=.3)
ax.set_title("顧客層（RFM）ごとの客数と売上", fontsize=9.5, weight="bold"); fig.tight_layout()
f1 = os.path.join(OUT, "fig1_rfm.png"); fig.savefig(f1, dpi=160); plt.close(fig)

# ---- 図2：コホートの継続率（ヒートマップ） ----
fig, ax = plt.subplots(figsize=(4.1, 3.0)); M_ = R2011.iloc[:, 1:].values
im = ax.imshow(M_, cmap="Blues", vmin=0, vmax=40, aspect="auto")
for i in range(M_.shape[0]):
    for j in range(M_.shape[1]):
        if not np.isnan(M_[i, j]): ax.text(j, i, f"{M_[i, j]:.0f}", ha="center", va="center", fontsize=6.5, color="white" if M_[i, j] > 25 else INK)
ax.set_xticks(range(M_.shape[1])); ax.set_xticklabels([f"{a}か月後" for a in R2011.columns[1:]], fontsize=6.5)
ax.set_yticks(range(len(R2011))); ax.set_yticklabels([f"{p.month}月に初回（{int(co.loc[p, 0])}人）" for p in R2011.index], fontsize=6.5)
ax.set_title("初回購入月ごとの継続率（%）", fontsize=9.5, weight="bold"); fig.tight_layout()
f2 = os.path.join(OUT, "fig2_cohort.png"); fig.savefig(f2, dpi=160); plt.close(fig)

gr = g.loc["離れかけの優良"]; gy = g.loc["優良"]
TXT = dict(
    title="EC 顧客分析レポート（サンプル）：どの顧客層に何をすべきか",
    sub=f"公開データ：UCI「Online Retail」（英国のネット通販・CC BY 4.0）2010-12〜2011-12／顧客 {len(r):,} 人・注文 {c.InvoiceNo.nunique():,} 件",
    q="売上を伸ばすために、どの顧客層に、どんな働きかけをすべきか。",
    f=[f"上位の「優良」（最近も買っていて回数も多い）は客数の {gy['客数%']:.0f}% で売上の {gy['売上%']:.0f}% を占める",
       f"「離れかけの優良」が {int(gr.n)} 人（売上の {gr['売上%']:.0f}%）。何度も買っていた（購入回数の中央値 {gr.F:.0f} 回）のに、最後の購入から中央値 {gr.R:.0f} 日たっている",
       f"新規客のうち翌月も買うのは平均 {m1:.0f}%（2011年1〜10月の初回客）。2回目を30日以内に買った人の、期間中の合計購入額の中央値は £{gx.loc['30日以内','median']:,.0f}、31日以降は £{gx.loc['31日以降','median']:,.0f}、2回目なしは £{gx.loc['2回目なし','median']:,.0f}"],
    act=[("「離れかけの優良」に呼び戻しの案内を送る",
          f"{int(gr.n)} 人をランダムに半分ずつに分け、片方にだけ限定の案内を送る。8週間後の購入率と購入額を比べる（送らない側が比べる相手）"),
         ("初回購入から30日以内に2回目を促すフォローを入れる",
          "初回購入の7日後・21日後におすすめ商品の案内を送る。月ごとに送る／送らないを分け、翌月の継続率（今は約20%）が上がるかを見る")],
    lim=["2回目が早い人ほど購入額が大きいのは、もともと買う量の多い客（卸売業者など）が早く戻るためかもしれない。フォローで2回目を早めれば購入額が増える、とまでは言えないので、打ち手は分けて比べる前提",
         "データの最終月は9日までなので継続率に使っていない。最初の月（2010年12月）の初回客には期間より前からの客が含まれるので、コホートの比較から外した",
         "顧客IDのない注文（全体の25%）と返品・キャンセルは除いた。金額は英ポンド",
         "実案件では、自社の購入データ（会員ID・注文日・金額）があれば同じ形で出せる"],
    meth="方法：最後の購入からの日数（R）・購入回数（F）・購入額（M）を5段階に分け、R と F の組み合わせで5つの層に分けた（RFM 分析）。継続率は、初回購入月ごとに「n か月後にも買った人の割合」を数えた（月別コホート）")

def report(path):
    fig = plt.figure(figsize=(8.27, 11.69))
    def T(xx, y, s, size=9.5, color=INK, weight="normal"): fig.text(xx, y, s, fontsize=size, color=color, weight=weight, va="top")
    def W(xx, y, s, n, size=9.2, color=INK, lh=.019, indent=""):
        lines = _wrap(s, n)
        for j, line in enumerate(lines): T(xx, y - j * lh, (indent if j else "") + line, size, color)
        return y - len(lines) * lh
    fig.patches.append(plt.Rectangle((0, .935), 1, .065, transform=fig.transFigure, color=NAVY, zorder=0))
    T(.05, .985, TXT["title"], 14, "white", "bold"); T(.05, .955, TXT["sub"], 8.3, "#cbd5e1")
    T(.05, .918, "問い", 12, NAVY, "bold"); y = W(.05, .893, TXT["q"], 56)
    y -= .012; T(.05, y, "わかったこと", 12, NAVY, "bold"); y -= .026
    for i, s in enumerate(TXT["f"], 1): y = W(.05, y, f"{i}. {s}", 56, 9, INK, .019, "   "); y -= .004
    for k, img in enumerate([f1, f2]):
        ax = fig.add_axes([.04 + k * .47, y - .235, .45, .23]); ax.imshow(plt.imread(img)); ax.axis("off")
    y -= .25; T(.05, y, "次の打ち手（優先順）", 12, NAVY, "bold"); y -= .026
    for i, (a, how) in enumerate(TXT["act"]):
        T(.05, y, f"{'①②'[i]} {a}", 9.8, INK, "bold"); y = W(.08, y - .021, "確かめ方：" + how, 54, 8.8, MUTED); y -= .01
    T(.05, y, "前提と限界", 12, NAVY, "bold"); y -= .025
    for s in TXT["lim"]: y = W(.05, y, "・" + s, 57, 8.5, INK, .017, "   ")
    y -= .006; W(.05, y, TXT["meth"], 66, 7.6, MUTED, .015)
    fig.savefig(path); fig.savefig(path.replace(".pdf", ".png"), dpi=120); plt.close(fig)
report(os.path.join(OUT, "ec_1page.pdf"))
g.round(2).to_csv(os.path.join(OUT, "rfm_segments.csv")); ret.round(1).to_csv(os.path.join(OUT, "cohort_retention.csv")); gx.to_csv(os.path.join(OUT, "second_purchase.csv"))
print("ok", round(m1, 1))

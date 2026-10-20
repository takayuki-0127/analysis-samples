import pandas as pd, numpy as np, json
D='../sample_public_youtube/data/'   # 元データ（CC0）は sample_public_youtube/data に置く
def load():
    d=pd.read_csv(D+'JPvideos.csv',encoding='utf-8',encoding_errors='replace')
    d['td']=pd.to_datetime(d.trending_date,format='%y.%d.%m')
    d=d[d.video_error_or_removed.astype(str).str.lower()!='true']
    g=d.sort_values('td').groupby('video_id'); f=g.first(); l=g.last(); n=g.size()
    cat=json.load(open(D+'JP_category_id_titles.json'))
    JA={'Entertainment':'エンタメ','People & Blogs':'ブログ','Sports':'スポーツ','News & Politics':'ニュース','Music':'音楽','Pets & Animals':'ペット'}
    v=pd.DataFrame({'n':n,'v0':f.views,'v1':l.views,'lk':f.likes,'cm':f.comment_count,'title':f.title.fillna(''),'cat':f.category_id.astype(str).map(cat).map(JA).fillna('その他'),'pub':pd.to_datetime(f.publish_time,utc=True).dt.tz_convert('Asia/Tokyo'),'td0':f.td,'cd':f.comments_disabled.astype(str).str.lower().eq('true').astype(int),'rd':f.ratings_disabled.astype(str).str.lower().eq('true').astype(int)})
    v['lag']=(v.td0-v.pub.dt.tz_localize(None).dt.normalize()).dt.days
    v=v[(v.pub>='2018-01-01')&(v.lag.between(0,7))&(v.rd==0)].copy()
    v['stay']=(v.n>=2).astype(int); v['lv0']=np.log(v.v0)
    v['like_pct']=(v.lk/v.v0*100).clip(upper=15); v['com_pct']=(v.cm/v.v0*100).clip(upper=5)
    t=v.title
    v['bracket']=t.str.contains('【').astype(int); v['num']=t.str.contains(r'\d').astype(int)
    v['q']=t.str.contains('[?？]').astype(int); v['ex']=t.str.contains('[!！]').astype(int)
    v['tlen']=t.str.len(); v['night']=v.pub.dt.hour.between(18,23).astype(int)
    return v

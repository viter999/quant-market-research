# Charts for "After the Comeback", TheQuantTape theme. Numbers are copied from atc_report.txt. No data is read here.
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
BG='#0b0b0b'; INK='#ecebe4'; MUTE='#8d8d86'; DIM='#3a3a36'; W='#5aa9e6'; LO='#e8964a'; S='#77776f'
MONO='DejaVu Sans Mono'; SLAB='Nimbus Mono PS'
plt.rcParams.update({'font.family':MONO,'font.size':10.5,'text.color':INK,'axes.labelcolor':MUTE,'xtick.color':MUTE,'ytick.color':MUTE,
  'axes.edgecolor':DIM,'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG,'axes.spines.top':False,'axes.spines.right':False,
  'grid.color':DIM,'grid.linestyle':(0,(3,4)),'grid.linewidth':0.8,'legend.labelcolor':INK})
FOOT='Hyperliquid perps. Wallets liquidated 1 Jan-1 Apr 2026 that opened a new position within 30 days. Vaults and market makers removed.\nDescriptive only, not a trading signal. Wallets that wait differ from those that do not. An association, not a cause.'
def frame(fig, title, tag, extra=''):
    fig.text(0.035,0.955,'AFTER_THE_COMEBACK',fontsize=9,color=MUTE)
    fig.text(0.965,0.955,'HYPERLIQUID   35,335 wallets that came back after a liquidation',fontsize=9,color=MUTE,ha='right')
    fig.add_artist(plt.Line2D([0.035,0.965],[0.935,0.935],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.875,tag,fontsize=8.5,color=BG,bbox=dict(boxstyle='round,pad=0.45',fc=INK,ec=INK))
    fig.text(0.035,0.79,title,fontsize=19,fontweight='bold',family=SLAB,color=INK)
    fig.add_artist(plt.Line2D([0.035,0.965],[0.085,0.085],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.022,FOOT+(('\n'+extra) if extra else ''),fontsize=7.3,color=MUTE,linespacing=1.5)
    fig.text(0.965,0.022,'@TheQuantTape',fontsize=8.5,color=MUTE,ha='right')
def style(ax):
    ax.grid(axis='y'); ax.set_axisbelow(True); ax.tick_params(length=0)
    for sp in ('left','bottom'): ax.spines[sp].set_linestyle((0,(3,3)))
def bars(ax, names, v, lo, hi, cols, ns):
    x=np.arange(len(v))
    ax.bar(x,v,.58,color=cols)
    ax.errorbar(x,v,yerr=[np.array(v)-np.array(lo),np.array(hi)-np.array(v)],fmt='none',ecolor=INK,elinewidth=1,capsize=3,alpha=.7)
    for i in range(len(v)):
        ax.text(x[i],hi[i]+1.8,f'{v[i]:.0f}%',ha='center',color=cols[i] if cols[i]!=S else MUTE,fontweight='bold',fontsize=12)
        ax.text(x[i],3,f'n = {ns[i]:,}',ha='center',color=BG,fontsize=8)
    ax.set_xticks(x,names); ax.set_ylim(0,92); style(ax)
# ---- Chart 1: wait
fig,ax=plt.subplots(figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21)
bars(ax,['under 1 hour','1-24 hours','1-7 days','7-30 days'],[72.6,70.0,59.3,46.8],[69.9,67.0,56.2,42.2],[75.4,72.8,62.3,51.6],[LO,LO,LO,W],[9463,14501,7913,3458])
ax.set_xlabel('time between the liquidation and the first new position'); ax.set_ylabel('% liquidated again in 30 days')
frame(fig,'The faster they come back, the more often it repeats','01 / the wait','The 30 days start at the comeback. Lines: 95% intervals. Similar prior activity: 73/70/59/46%. Same trading days afterwards: 72/70/60/48%.')
fig.savefig('chart1_wait.png',dpi=160)
# ---- Chart 2: same coin and size
fig,(a1,a2)=plt.subplots(1,2,figsize=(12,6.2),gridspec_kw={'width_ratios':[2,3]}); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21,wspace=0.16)
bars(a1,['another coin','a coin they were\njust liquidated on'],[59.5,71.1],[56.7,68.3],[62.3,73.8],[W,LO],[15404,19931])
a1.set_ylabel('% liquidated again in 30 days'); a1.set_title('first new position is on...',fontsize=10,color=MUTE,loc='left')
bars(a2,['under half\nthe usual size','about the\nusual size','double the usual\nsize or more'],[65.0,66.7,65.6],[62.1,63.9,62.9],[67.8,69.4,68.4],[S,S,S],[9106,13698,8538])
a2.set_title('first new position is...',fontsize=10,color=MUTE,loc='left'); a2.set_yticklabels([])
frame(fig,'Same coin: more repeats. Size: no difference.','02 / same coin, and size','Size is measured against the wallet\'s median position in the prior 30 days (wallets with 5+ prior positions). Deposits and leverage are not observed.')
fig.savefig('chart2_coin_size.png',dpi=160)
print('ok')

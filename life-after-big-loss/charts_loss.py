# Charts for "Life After a Big Loss" (part 2), TheQuantTape theme. Numbers come from step5_report.txt, step5x_report.txt and step6x_report.txt. No data is read here.
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
BG='#0b0b0b'; INK='#ecebe4'; MUTE='#8d8d86'; DIM='#3a3a36'; W='#5aa9e6'; LO='#e8964a'; S='#77776f'; S2='#4b4b46'
MONO='DejaVu Sans Mono'; SLAB='Nimbus Mono PS'
plt.rcParams.update({'font.family':MONO,'font.size':10.5,'text.color':INK,'axes.labelcolor':MUTE,'xtick.color':MUTE,'ytick.color':MUTE,
  'axes.edgecolor':DIM,'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG,'axes.spines.top':False,'axes.spines.right':False,
  'grid.color':DIM,'grid.linestyle':(0,(3,4)),'grid.linewidth':0.8,'legend.labelcolor':INK})
FOOT='Hyperliquid perp fills, events 1 Jan-30 Apr 2026. Big loss / win = one closed position of $1,000+ and 5x+ the wallet\'s usual result.\n"Similar" = up to 5 matched wallets with no big result in the 30 days before. Descriptive only, not a trading signal.'
def frame(fig, title, tag, extra=''):
    fig.text(0.035,0.955,'LIFE_AFTER_A_BIG_LOSS',fontsize=9,color=MUTE)
    fig.text(0.965,0.955,'HYPERLIQUID   5,997 losses   6,088 wins   30d after',fontsize=9,color=MUTE,ha='right')
    fig.add_artist(plt.Line2D([0.035,0.965],[0.935,0.935],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.875,tag,fontsize=8.5,color=BG,bbox=dict(boxstyle='round,pad=0.45',fc=INK,ec=INK))
    fig.text(0.035,0.79,title,fontsize=19,fontweight='bold',family=SLAB,color=INK)
    fig.add_artist(plt.Line2D([0.035,0.965],[0.085,0.085],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.022,FOOT+(('\n'+extra) if extra else ''),fontsize=7.3,color=MUTE,linespacing=1.5)
    fig.text(0.965,0.022,'@TheQuantTape',fontsize=8.5,color=MUTE,ha='right')
def style(ax):
    ax.grid(axis='y'); ax.set_axisbelow(True); ax.tick_params(length=0)
    for sp in ('left','bottom'): ax.spines[sp].set_linestyle((0,(3,3)))
# ---- Chart 1: the first move after a big loss
g=['back in a new position\nwithin 1 hour*','first new position\n2x usual size or more','first new position\non the same coin*']
los=[37.3,47.5,49.5]; sim=[21.2,26.6,50.5]
fig,ax=plt.subplots(figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21)
x=np.arange(3); w=.30
ax.bar(x-w/2,los,w*0.92,color=LO,label='big-loss wallets'); ax.bar(x+w/2,sim,w*0.92,color=S,label='similar wallets')
for i in range(3):
    ax.text(x[i]-w/2,los[i]+1.2,f'{los[i]:.0f}%',ha='center',color=LO,fontweight='bold',fontsize=11)
    ax.text(x[i]+w/2,sim[i]+1.2,f'{sim[i]:.0f}%',ha='center',color=MUTE,fontsize=10.5)
ax.set_xticks(x,g); ax.set_ylabel('% of wallets'); ax.set_ylim(0,64); style(ax); ax.legend(frameon=False,loc='upper left',ncol=2,fontsize=9.5,bbox_to_anchor=(0,1.09))
frame(fig,'After a big loss: back fast, and bigger','01 / the first move','*Similar wallets timed from their own last close and checked against their own last coin. Same-coin re-entry is ordinary for everyone.')
fig.savefig('chart1_first_move.png',dpi=160)
# ---- Chart 2: the next 30 days, loss vs win
g=['traded more volume in the next 30 days\nthan in the 30 before','no trades at all in the next 30 days','liquidated within 30 days']
los=[51.2,4.4,22.5]; lsim=[46.8,3.6,23.3]; win=[67.2,1.8,25.3]
fig,axs=plt.subplots(1,3,figsize=(12,6.2)); fig.subplots_adjust(left=0.065,right=0.965,top=0.69,bottom=0.21,wspace=0.22)
for ax,j,ym in zip(axs,(0,1,2),(84,6.2,34)):
    vals=[los[j],lsim[j],win[j]]; cols=[LO,S,W]; labs=['big-loss\nwallets','their similar\nwallets','big-win\nwallets']
    ax.bar(range(3),vals,color=cols,width=.62)
    for i,v in enumerate(vals): ax.text(i,v+ym*0.02,f'{v:.1f}%' if j==1 else f'{v:.0f}%',ha='center',fontweight='bold' if i!=1 else 'normal',color=cols[i] if i!=1 else MUTE,fontsize=10.5)
    ax.set_xticks(range(3),labs,fontsize=8.8); ax.set_ylim(0,ym); ax.set_title(g[j],fontsize=9.6,color=MUTE,loc='left',pad=10); style(ax)
axs[0].set_ylabel('% of wallets')
frame(fig,'The next 30 days: close to similar wallets','02 / the next 30 days','A loss removes margin and a win adds it, so part of the volume gap can be mechanical. These 30-day rows are sensitive to how similar wallets are followed.')
fig.savefig('chart2_next_30_days.png',dpi=160)
print('ok')

# Charts in the TheQuantTape theme (dark, monospace, dashed rules). Numbers come from step5_report.txt and step6x_report.txt.
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
BG='#0b0b0b'; INK='#ecebe4'; MUTE='#8d8d86'; DIM='#3a3a36'; W='#5aa9e6'; LO='#e8964a'; S='#77776f'; S2='#4b4b46'
MONO='DejaVu Sans Mono'; SLAB='Nimbus Mono PS'
plt.rcParams.update({'font.family':MONO,'font.size':10.5,'text.color':INK,'axes.labelcolor':MUTE,'xtick.color':MUTE,'ytick.color':MUTE,
  'axes.edgecolor':DIM,'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG,'axes.spines.top':False,'axes.spines.right':False,
  'grid.color':DIM,'grid.linestyle':(0,(3,4)),'grid.linewidth':0.8,'legend.labelcolor':INK})
FOOT='Hyperliquid perp fills, events 1 Jan-30 Apr 2026. Big win / loss = one closed position of $1,000+ and 5x+ the wallet\'s usual result.\n"Similar" = up to 5 matched wallets with no big result in the 30 days before. Descriptive only, not a trading signal.'
def frame(fig, title, tag, extra=''):
    fig.text(0.035,0.955,'LIFE_AFTER_A_BIG_WIN',fontsize=9,color=MUTE)
    fig.text(0.965,0.955,'HYPERLIQUID   6,088 wins   5,997 losses   30d after',fontsize=9,color=MUTE,ha='right')
    fig.add_artist(plt.Line2D([0.035,0.965],[0.935,0.935],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.875,tag,fontsize=8.5,color=BG,bbox=dict(boxstyle='round,pad=0.45',fc=INK,ec=INK))
    fig.text(0.035,0.79,title,fontsize=19,fontweight='bold',family=SLAB,color=INK)
    fig.add_artist(plt.Line2D([0.035,0.965],[0.085,0.085],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.022,FOOT+(('\n'+extra) if extra else ''),fontsize=7.3,color=MUTE,linespacing=1.5)
    fig.text(0.965,0.022,'@TheQuantTape',fontsize=8.5,color=MUTE,ha='right')
def style(ax):
    ax.grid(axis='y'); ax.set_axisbelow(True); ax.tick_params(length=0)
    for sp in ('left','bottom'): ax.spines[sp].set_linestyle((0,(3,3)))
# ---- Chart 1: comeback speed
h=['1 hour','1 day','7 days','30 days']
d=[('after a big win  (5,854 wallets)',[34.8,73.4,92.6,96.8],[11.4,60.8,88.7,95.1],W,'big-win wallets'),
   ('after a big loss  (5,771 wallets)',[37.3,68.4,86.6,92.9],[13.8,62.2,88.6,94.9],LO,'big-loss wallets')]
fig,axs=plt.subplots(1,2,figsize=(12,6.2),sharey=True); fig.subplots_adjust(left=0.085,right=0.965,top=0.70,bottom=0.19,wspace=0.08)
for ax,(k,a,b,c,lab) in zip(axs,d):
    x=np.arange(4)
    ax.plot(x,b,'--o',color=S,lw=1.8,ms=6,label='similar wallets'); ax.plot(x,a,'-o',color=c,lw=2.6,ms=7,label=lab)
    for i in range(4):
        ax.annotate(f'{a[i]:.0f}%',(x[i],a[i]),textcoords='offset points',xytext=(0,9),ha='center',color=c,fontsize=10.5,fontweight='bold')
        ax.annotate(f'{b[i]:.0f}%',(x[i],b[i]),textcoords='offset points',xytext=(0,-17),ha='center',color=MUTE,fontsize=9.5)
    ax.set_xticks(x,h); ax.set_title(k,fontsize=10.5,color=MUTE,loc='left',pad=10); ax.set_ylim(-10,112); ax.set_xlim(-.35,3.35); style(ax)
    ax.legend(frameon=False,loc='lower right',fontsize=9.5)
axs[0].set_ylabel('% that opened a new position within...')
frame(fig,'1 in 3 is back in a trade within an hour','01 / comeback speed','Similar wallets are followed from the same moment. Timed from their own last close: 21% within 1 hour, 64-65% within 1 day.')
fig.savefig('chart1_comeback.png',dpi=160)
# ---- Chart 2: same after a win or a loss
g=['back within 1 hour*','first new position\n2x usual size or more','first new position\non the same coin*']
win=[34.8,48.1,50.0]; wsim=[20.6,26.8,50.1]; los=[37.3,47.5,49.5]; lsim=[21.2,26.6,50.5]
fig,ax=plt.subplots(figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21)
x=np.arange(3); w=.19
for off,vals,col,lab,bold in ((-1.5,win,W,'big-win wallets',True),(-.5,wsim,S,'their similar wallets',False),(.5,los,LO,'big-loss wallets',True),(1.5,lsim,S2,'their similar wallets',False)):
    ax.bar(x+off*w,vals,w*0.92,color=col,label=lab)
    for i in range(3): ax.text(x[i]+off*w,vals[i]+1.2,f'{vals[i]:.0f}%',ha='center',color=col if bold else MUTE,fontweight='bold' if bold else 'normal',fontsize=10)
ax.set_xticks(x,g); ax.set_ylabel('% of wallets'); ax.set_ylim(0,66); style(ax); ax.legend(frameon=False,loc='upper left',ncol=4,fontsize=9.5,bbox_to_anchor=(0,1.09))
frame(fig,'Win or lose, the next move looks the same','02 / win vs loss','*Similar wallets timed from their own last close and checked against their own last coin. Same-coin re-entry is ordinary for everyone.')
fig.savefig('chart2_same.png',dpi=160)
# ---- Chart 3: what differs after a win
g=['traded more volume in the next 30 days\nthan in the 30 before','no trades at all in the next 30 days']
win=[67.2,1.8]; wsim=[47.1,3.3]; los=[51.2,4.4]; lsim=[46.8,3.6]
fig,axs=plt.subplots(1,2,figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.69,bottom=0.21,wspace=0.16)
for ax,j,ym in zip(axs,(0,1),(84,6.2)):
    vals=[win[j],wsim[j],los[j],lsim[j]]; cols=[W,S,LO,S2]; labs=['big-win\nwallets','their similar\nwallets','big-loss\nwallets','their similar\nwallets']
    ax.bar(range(4),vals,color=cols,width=.62)
    for i,v in enumerate(vals): ax.text(i,v+ym*0.02,f'{v:.1f}%' if j else f'{v:.0f}%',ha='center',fontweight='bold' if i in (0,2) else 'normal',color=cols[i] if i in (0,2) else MUTE,fontsize=10.5)
    ax.set_xticks(range(4),labs,fontsize=9); ax.set_ylim(0,ym); ax.set_title(g[j],fontsize=10.5,color=MUTE,loc='left',pad=10); style(ax)
axs[0].set_ylabel('% of wallets')
frame(fig,'After a win, wallets trade more','03 / what differs','A win adds margin and a loss removes it, so trading more after a win can be partly mechanical.')
fig.savefig('chart3_after_win.png',dpi=160)
print('ok')

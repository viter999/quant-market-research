# Charts for "Serial Liquidators", TheQuantTape theme. Numbers are copied from sl_report.txt. No data is read here.
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
BG='#0b0b0b'; INK='#ecebe4'; MUTE='#8d8d86'; DIM='#3a3a36'; W='#5aa9e6'; LO='#e8964a'; S='#77776f'
MONO='DejaVu Sans Mono'; SLAB='Nimbus Mono PS'
plt.rcParams.update({'font.family':MONO,'font.size':10.5,'text.color':INK,'axes.labelcolor':MUTE,'xtick.color':MUTE,'ytick.color':MUTE,
  'axes.edgecolor':DIM,'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG,'axes.spines.top':False,'axes.spines.right':False,
  'grid.color':DIM,'grid.linestyle':(0,(3,4)),'grid.linewidth':0.8,'legend.labelcolor':INK})
FOOT='Hyperliquid perp fills, 1 Dec 2025-31 May 2026. Vaults and market makers removed. Liquidation day = a UTC day on which the wallet was liquidated.\nDescriptive only, not a trading signal. More active wallets have more chances to be liquidated; activity is not held fixed in this chart.'
def frame(fig, title, tag, extra=''):
    fig.text(0.035,0.955,'SERIAL_LIQUIDATORS',fontsize=9,color=MUTE)
    fig.text(0.965,0.955,'HYPERLIQUID   177,432 liquidated wallets   596,257 liquidation days   6 months',fontsize=9,color=MUTE,ha='right')
    fig.add_artist(plt.Line2D([0.035,0.965],[0.935,0.935],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.875,tag,fontsize=8.5,color=BG,bbox=dict(boxstyle='round,pad=0.45',fc=INK,ec=INK))
    fig.text(0.035,0.79,title,fontsize=19,fontweight='bold',family=SLAB,color=INK)
    fig.add_artist(plt.Line2D([0.035,0.965],[0.085,0.085],color=DIM,lw=1,ls=(0,(3,3))))
    fig.text(0.035,0.022,FOOT+(('\n'+extra) if extra else ''),fontsize=7.3,color=MUTE,linespacing=1.5)
    fig.text(0.965,0.022,'@TheQuantTape',fontsize=8.5,color=MUTE,ha='right')
def style(ax):
    ax.grid(axis='y'); ax.set_axisbelow(True); ax.tick_params(length=0)
    for sp in ('left','bottom'): ax.spines[sp].set_linestyle((0,(3,3)))
# ---- Chart 1: wallets vs liquidation days, by how often the wallet was liquidated
g=['1 day','2 days','3-5 days','6-10 days','11+ days']
wal=[47.79,17.76,19.97,8.71,5.77]
days=[100*84788/596257,100*63026/596257,100*131510/596257,100*115467/596257,100*201466/596257]
fig,ax=plt.subplots(figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21)
x=np.arange(5); w=.34
ax.bar(x-w/2,wal,w*0.92,color=S,label='share of liquidated wallets'); ax.bar(x+w/2,days,w*0.92,color=LO,label='share of all liquidation days')
for i in range(5):
    ax.text(x[i]-w/2,wal[i]+1,f'{wal[i]:.0f}%',ha='center',color=MUTE,fontsize=10.5)
    ax.text(x[i]+w/2,days[i]+1,f'{days[i]:.0f}%',ha='center',color=LO,fontweight='bold',fontsize=11)
ax.set_xticks(x,g); ax.set_xlabel('how many days the wallet was liquidated on, in six months'); ax.set_ylabel('%'); ax.set_ylim(0,58); style(ax)
ax.legend(frameon=False,loc='upper right',fontsize=9.5)
frame(fig,'A third of wallets, three quarters of liquidations','01 / who gets liquidated','Wallets liquidated on 3 or more days are 34% of liquidated wallets and 75% of all liquidation days.')
fig.savefig('chart1_repeat.png',dpi=160)
# ---- Chart 2: counts vs dollars
g=['top 1% of liquidated wallets\n(1,775 wallets)','top 10% of liquidated wallets\n(17,744 wallets)']
d=[11.72,44.65]; n=[75.56,95.34]
fig,ax=plt.subplots(figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21)
x=np.arange(2); w=.30
ax.bar(x-w/2,d,w*0.92,color=LO,label='share of liquidation days (wallets ranked by days)'); ax.bar(x+w/2,n,w*0.92,color=W,label='share of liquidated position size (wallets ranked by size)')
for i in range(2):
    ax.text(x[i]-w/2,d[i]+1.5,f'{d[i]:.0f}%',ha='center',color=LO,fontweight='bold',fontsize=12)
    ax.text(x[i]+w/2,n[i]+1.5,f'{n[i]:.0f}%',ha='center',color=W,fontweight='bold',fontsize=12)
ax.set_xticks(x,g); ax.set_ylabel('%'); ax.set_ylim(0,112); ax.set_xlim(-.6,1.6); style(ax)
ax.legend(frameon=False,loc='upper left',fontsize=9.5)
frame(fig,'Counts are spread out. Dollars are not.','02 / counts vs dollars','Position size closed by liquidation, not money lost. The top 1% by size are only 4% of liquidation days.')
fig.savefig('chart2_dollars.png',dpi=160)
# ---- Chart 3: repeat across halves
g=['0','1','2','3-5','6+']
v=[23.67,44.16,56.14,70.19,86.94]; gone=[42.0,48.7,51.1,45.9,28.4]
fig,ax=plt.subplots(figsize=(12,6.2)); fig.subplots_adjust(left=0.075,right=0.965,top=0.70,bottom=0.21)
x=np.arange(5)
ax.bar(x,v,.58,color=[S,LO,LO,LO,LO])
for i in range(5):
    ax.text(x[i],v[i]+1.5,f'{v[i]:.0f}%',ha='center',color=MUTE if i==0 else LO,fontweight='bold',fontsize=12)
    ax.text(x[i],3,f'{gone[i]:.0f}% of group had\nstopped trading',ha='center',color=BG if i else INK,fontsize=7.8)
ax.set_xticks(x,g); ax.set_xlabel('liquidation days in Dec-Feb'); ax.set_ylabel('% liquidated in Mar-May'); ax.set_ylim(0,100); style(ax)
frame(fig,'The more often before, the more often after','03 / does it repeat','Only wallets active on 3+ days in Dec-Feb and still trading in Mar-May. At the same activity mix: 18 / 41 / 54 / 69 / 84%. An association, not a cause.')
fig.savefig('chart3_gradient.png',dpi=160)
print('ok')

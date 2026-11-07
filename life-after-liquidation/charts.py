import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
L='#E8590C'; S='#868E96'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
foot='Hyperliquid fills, liquidations 1 Jan–30 Apr 2026. "Similar" = up to 5 matched wallets not liquidated in the prior 30 days.'
# Chart 1
h=['1 hour','1 day','7 days','30 days']
d={'Fully wiped out (34,304)':([20.1,49.9,65.6,73.9],[5.2,26.3,52.0,68.0]),
   'Partly liquidated (19,876)':([22.8,62.6,84.3,92.0],[7.5,32.7,57.8,71.8])}
fig,axs=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
for ax,(k,(a,b)) in zip(axs,d.items()):
    x=np.arange(4)
    ax.plot(x,a,'-o',color=L,lw=2.5,label='Liquidated wallets'); ax.plot(x,b,'-o',color=S,lw=2.5,label='Similar wallets')
    for i in range(4):
        ax.annotate(f'{a[i]:.0f}%',(x[i],a[i]),textcoords='offset points',xytext=(0,8),ha='center',color=L,fontsize=10,fontweight='bold')
        ax.annotate(f'{b[i]:.0f}%',(x[i],b[i]),textcoords='offset points',xytext=(0,-16),ha='center',color=S,fontsize=10)
    ax.set_xticks(x,h); ax.set_title(k,fontsize=12); ax.set_ylim(-8,100); ax.grid(axis='y',alpha=.25)
axs[0].set_ylabel('% that opened a new position within…'); axs[0].legend(frameon=False,loc='lower right')
fig.suptitle('Liquidated wallets come back much faster',fontsize=15,fontweight='bold',x=0.02,ha='left')
fig.text(0.02,0.01,foot,fontsize=8,color='#555')
fig.tight_layout(rect=(0,0.04,1,0.95)); fig.savefig('chart1_comeback.png',dpi=160)
# Chart 2 and 3 grouped bars
def bars(fname,title,ylabel,groups,a,b,note):
    fig,ax=plt.subplots(figsize=(11,4.8)); x=np.arange(len(groups)); w=.38
    ax.bar(x-w/2,a,w,color=L,label='Liquidated wallets'); ax.bar(x+w/2,b,w,color=S,label='Similar wallets')
    for i in range(len(groups)):
        ax.text(x[i]-w/2,a[i]+1,f'{a[i]:.0f}%',ha='center',color=L,fontweight='bold',fontsize=10)
        ax.text(x[i]+w/2,b[i]+1,f'{b[i]:.0f}%',ha='center',color=S,fontsize=10)
    ax.set_xticks(x,groups); ax.set_ylabel(ylabel); ax.set_ylim(0,max(a+b)*1.25); ax.grid(axis='y',alpha=.25); ax.legend(frameon=False,loc='upper left')
    fig.suptitle(title,fontsize=15,fontweight='bold',x=0.02,ha='left')
    fig.text(0.02,0.01,foot+(' '+note if note else ''),fontsize=8,color='#555')
    fig.tight_layout(rect=(0,0.04,1,0.95)); fig.savefig(fname,dpi=160)
g=['All\n(54,180)','Fully wiped\n(34,304)','Partly\n(19,876)','Under \$1k\n(21,651)','\$1k–\$100k\n(30,730)','Over \$100k\n(1,799)']
bars('chart2_size.png','Most don\'t size up after liquidation — except the biggest','% whose first new position was ≥ 2× their usual size',g,
     [27.7,23.2,33.2,21.5,30.5,45.0],[29.0,28.2,29.9,29.3,28.6,30.3],'Only wallets with ≥ 5 positions in the prior 30 days.')
bars('chart3_again.png','1 in 2 liquidated wallets is liquidated again within 30 days','% liquidated again within 30 days',g,
     [52.4,48.4,59.3,54.2,50.7,60.0],[17.1,18.0,15.7,15.7,18.2,16.4],'Size bands = liquidated notional.')
print('ok')

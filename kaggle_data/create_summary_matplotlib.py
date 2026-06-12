"""
Create WORKFLOW_Summary_Statistics with matplotlib (English labels to avoid font issues)
Then overlay with PIL for cleaner results
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

# Set backend
plt.switch_backend('Agg')

# Create figure
fig, axes = plt.subplots(2, 2, figsize=(16, 12), facecolor='white')
fig.suptitle('50 Startups ML Analysis - Summary', fontsize=20, fontweight='bold', y=0.98)

# ============= Plot 1: Model Performance Comparison =============
ax1 = axes[0, 0]
models = ['Random\nForest', 'Linear\nRegression', 'Lasso/\nRidge', 'Gradient\nBoosting']
r2_scores = [0.9324, 0.9265, 0.9250, 0.9240]
colors_bar = ['#FF6B6B', '#FFD700', '#4ECDC4', '#95E1D3']

bars1 = ax1.bar(models, r2_scores, color=colors_bar, edgecolor='black', linewidth=2.5, width=0.6)
ax1.set_ylabel('R-squared Score', fontsize=13, fontweight='bold')
ax1.set_title('Model Performance Comparison', fontsize=14, fontweight='bold', pad=15)
ax1.set_ylim([0.920, 0.935])
ax1.grid(axis='y', alpha=0.3, linestyle='--')
ax1.set_axisbelow(True)

# Add value labels on bars
for bar, score in zip(bars1, r2_scores):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.0003,
             f'{score:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=12)

# Highlight best
bars1[0].set_linewidth(4)
bars1[0].set_edgecolor('#FF0000')

# ============= Plot 2: Feature Importance =============
ax2 = axes[0, 1]
features = ['R&D Spend', 'Marketing\nSpend', 'Admin', 'State']
importance = [0.97, 0.75, 0.20, 0.05]
colors_feat = ['#27AE60', '#F39C12', '#E74C3C', '#95A5A6']

bars2 = ax2.barh(features, importance, color=colors_feat, edgecolor='black', linewidth=2.5, height=0.6)
ax2.set_xlabel('Correlation Coefficient', fontsize=13, fontweight='bold')
ax2.set_title('Feature Importance Analysis', fontsize=14, fontweight='bold', pad=15)
ax2.set_xlim([0, 1.05])
ax2.grid(axis='x', alpha=0.3, linestyle='--')
ax2.set_axisbelow(True)

# Add value labels
for bar, imp in zip(bars2, importance):
    width = bar.get_width()
    ax2.text(width + 0.02, bar.get_y() + bar.get_height()/2.,
             f'{imp:.2f}', ha='left', va='center', fontweight='bold', fontsize=12)

# Highlight best
bars2[0].set_linewidth(4)
bars2[0].set_edgecolor('#000000')

# ============= Plot 3: Feature Selection Algorithms Consensus =============
ax3 = axes[1, 0]
algorithms = ['F-Test', 'Mutual\nInfo', 'RF\nImportance', 'Permutation', 'Correlation']
r2_with_1_feature = [0.9260, 0.9261, 0.9262, 0.9260, 0.9265]
r2_with_5_features = [0.9180, 0.9195, 0.9220, 0.9150, 0.9190]

x_pos = np.arange(len(algorithms))
width = 0.35

bars3a = ax3.bar(x_pos - width/2, r2_with_1_feature, width, label='1 Feature (R&D)',
                 color='#2ECC71', edgecolor='black', linewidth=2, alpha=0.8)
bars3b = ax3.bar(x_pos + width/2, r2_with_5_features, width, label='5 Features',
                 color='#E74C3C', edgecolor='black', linewidth=2, alpha=0.8)

ax3.set_ylabel('R-squared Score', fontsize=13, fontweight='bold')
ax3.set_title('Feature Selection: Algorithm Consensus', fontsize=14, fontweight='bold', pad=15)
ax3.set_xticks(x_pos)
ax3.set_xticklabels(algorithms, fontsize=11)
ax3.set_ylim([0.910, 0.930])
ax3.legend(loc='upper right', fontsize=11, framealpha=0.9)
ax3.grid(axis='y', alpha=0.3, linestyle='--')
ax3.set_axisbelow(True)

# Add trend arrows to show degradation
for i in range(len(algorithms)):
    ax3.annotate('', xy=(i, r2_with_5_features[i]), xytext=(i, r2_with_1_feature[i]),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5, alpha=0.5))

# ============= Plot 4: Summary Table =============
ax4 = axes[1, 1]
ax4.axis('off')

summary_data = [
    ['Metric', 'Value', 'Note'],
    ['Total Experiments', '80', '5 models x 16 features'],
    ['Best Model', 'Random Forest', 'R2=0.9324'],
    ['Recommended Model', 'Linear Regression', 'R2=0.9265'],
    ['RMSE', '7,714 USD', 'Test Set'],
    ['Optimal Features', '1 (R&D Only)', 'Single Feature'],
    ['Sample Size', '50 startups', 'Complete Dataset'],
    ['Data Quality', 'No Missing Values', 'Clean Data'],
    ['Key Finding', 'R&D dominates profit', 'Correlation=0.97'],
]

# Add title to table section (BEFORE table so it's not overlapped)
ax4.text(0.5, 0.95, 'Analysis Summary', transform=ax4.transAxes,
         fontsize=13, fontweight='bold', ha='center', va='top',
         bbox=dict(boxstyle='round', facecolor='#ECF0F1', alpha=0.8, pad=0.3))

# Create table with adjusted bbox to fit below title - larger height for better spacing
table = ax4.table(cellText=summary_data, cellLoc='left', loc='center',
                 colWidths=[0.22, 0.20, 0.58],
                 bbox=[0.02, 0.02, 0.96, 0.88])

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.8)

# Style the table
for i, row in enumerate(summary_data):
    for j in range(3):
        cell = table[(i, j)]
        
        # Header row
        if i == 0:
            cell.set_facecolor('#2C3E50')
            cell.set_text_props(weight='bold', color='white', fontsize=12)
            cell.set_height(0.08)
        # Data rows
        else:
            # Alternating colors
            if i % 2 == 0:
                cell.set_facecolor('#F8F9FA')
            else:
                cell.set_facecolor('white')
            
            cell.set_text_props(fontsize=11)
            
            # Highlight key findings
            if 'Recommended' in str(row[0]) or 'Key Finding' in str(row[0]):
                cell.set_facecolor('#E8F8F5')
                cell.set_text_props(weight='bold')
            
            # Value column in green
            if j == 1:
                cell.set_text_props(weight='bold', color='#27AE60')
        
        # All cells with border
        cell.set_edgecolor('#BDC3C7')
        cell.set_linewidth(1.5)

plt.tight_layout(rect=[0, 0.02, 1, 0.96])
plt.savefig('WORKFLOW_Summary_Statistics.png', dpi=150, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
print("Successfully created: WORKFLOW_Summary_Statistics.png")
plt.close()

print("Summary statistics image generated!")

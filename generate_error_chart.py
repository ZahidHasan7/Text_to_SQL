"""
Generate bar chart for SCoT error category distribution (Gemini 2.5 Pro dev_600).
Outputs publication-quality figures suitable for LaTeX thesis inclusion.
"""

import matplotlib.pyplot as plt
import matplotlib

# Set publication-quality defaults
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
matplotlib.rcParams['font.size'] = 11
matplotlib.rcParams['axes.labelsize'] = 12
matplotlib.rcParams['axes.titlesize'] = 13
matplotlib.rcParams['xtick.labelsize'] = 10
matplotlib.rcParams['ytick.labelsize'] = 10
matplotlib.rcParams['legend.fontsize'] = 10
matplotlib.rcParams['figure.titlesize'] = 14

# Data from scot_error_counts.csv (Gemini 2.5 Pro dev_600)
categories = ['Wrong Result Rows', 'Empty Result Set']
counts = [83, 11]
percentages = [88.3, 11.7]

# Create figure with appropriate size for thesis (width=6.5in typical for single column)
fig, ax = plt.subplots(figsize=(7, 5))

# Create bars with professional colors
bars = ax.bar(categories, counts, color=['#d62728', '#ff7f0e'], 
              edgecolor='black', linewidth=1.2, alpha=0.85)

# Add count labels on top of bars
for bar, count, pct in zip(bars, counts, percentages):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 1.5,
            f'{count}\n({pct}%)',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

# Customize axes
ax.set_ylabel('Number of Failures', fontweight='bold')
ax.set_xlabel('Error Category', fontweight='bold')
ax.set_title('SCoT Error Category Distribution\n(Gemini 2.5 Pro, dev_600: 94 total failures)', 
             fontweight='bold', pad=15)

# Set y-axis limit with some headroom
ax.set_ylim(0, max(counts) * 1.15)

# Add grid for readability (behind bars)
ax.set_axisbelow(True)
ax.yaxis.grid(True, linestyle='--', alpha=0.3)
ax.set_axisbelow(True)

# Add total count annotation
ax.text(0.98, 0.97, f'Total failures: 94\n(out of 600 queries)', 
        transform=ax.transAxes, fontsize=9,
        verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# Tight layout to prevent label cutoff
plt.tight_layout()

# Save in multiple formats
plt.savefig('diagrams/error_distribution_bar.png', dpi=300, bbox_inches='tight')
plt.savefig('diagrams/error_distribution_bar.pdf', bbox_inches='tight')

print("✓ Generated: diagrams/error_distribution_bar.png (300 DPI)")
print("✓ Generated: diagrams/error_distribution_bar.pdf (vector)")
print("\nRecommended LaTeX inclusion:")
print("  \\includegraphics[width=0.75\\textwidth]{diagrams/error_distribution_bar.pdf}")

plt.show()

"""
Generate comprehensive CoT vs SCoT comparison diagram.
Creates a side-by-side visual comparison showing the different approaches.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Set publication quality
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 9
plt.rcParams['figure.dpi'] = 150

# Create figure
fig, (ax_cot, ax_scot) = plt.subplots(1, 2, figsize=(14, 10))
fig.suptitle('Comparison: Chain-of-Thought vs. Structured Chain-of-Thought', 
             fontsize=14, fontweight='bold', y=0.98)

# ============ CoT Side (Left) ============
ax_cot.set_xlim(0, 10)
ax_cot.set_ylim(0, 20)
ax_cot.axis('off')
ax_cot.set_title('Chain-of-Thought (CoT)\nAccuracy: 40.17%', 
                 fontsize=12, fontweight='bold', pad=10)

# CoT boxes
cot_boxes = [
    (5, 18.5, 'Input:\nQuestion + Schema', '#e1f5ff'),
    (5, 16.5, 'Generate Reasoning\n(Clause-by-Clause)', '#fff3e0'),
    (5, 14.5, 'Step 1: FROM/JOIN', '#ffe0b2'),
    (5, 12.5, 'Step 2: WHERE', '#ffe0b2'),
    (5, 10.5, 'Step 3: GROUP BY', '#ffe0b2'),
    (5, 8.5, 'Step 4: HAVING', '#ffe0b2'),
    (5, 6.5, 'Step 5: SELECT', '#ffe0b2'),
    (5, 4.5, 'Generate\nSingle SQL', '#c8e6c9'),
    (5, 2.5, 'Execute &\nEvaluate', '#ffcdd2'),
]

for x, y, text, color in cot_boxes:
    box = FancyBboxPatch((x-2, y-0.6), 4, 1.2, boxstyle="round,pad=0.1",
                          edgecolor='black', facecolor=color, linewidth=1.5)
    ax_cot.add_patch(box)
    ax_cot.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold')

# CoT arrows
for i in range(len(cot_boxes)-1):
    y_start = cot_boxes[i][1] - 0.6
    y_end = cot_boxes[i+1][1] + 0.6
    arrow = FancyArrowPatch((5, y_start), (5, y_end),
                           arrowstyle='->', mutation_scale=20, 
                           linewidth=2, color='#1976d2')
    ax_cot.add_patch(arrow)

# CoT annotation box
annotation_cot = FancyBboxPatch((0.5, 0.3), 4, 1.5, boxstyle="round,pad=0.15",
                                edgecolor='#c62828', facecolor='#ffebee', 
                                linewidth=2, linestyle='--')
ax_cot.add_patch(annotation_cot)
ax_cot.text(2.5, 1.05, '❌ Limitations:', ha='center', fontsize=10, 
            fontweight='bold', color='#c62828')
ax_cot.text(2.5, 0.7, '• Error propagation\n• Single reasoning path\n• No validation', 
            ha='center', va='top', fontsize=8)

# ============ SCoT Side (Right) ============
ax_scot.set_xlim(0, 10)
ax_scot.set_ylim(0, 20)
ax_scot.axis('off')
ax_scot.set_title('Structured Chain-of-Thought (SCoT)\nAccuracy: 84.33%', 
                  fontsize=12, fontweight='bold', pad=10)

# SCoT boxes with more phases
scot_boxes = [
    (5, 18.5, 'Input:\nQuestion + Schema', '#e1f5ff'),
    (5, 17.2, 'Phase 1: Plan\nGeneration (JSON)', '#fff3e0'),
    (5, 15.9, 'Phase 2: Plan-Check\nValidation', '#f3e5f5'),
    (5, 14.6, 'Phase 3: Pattern\nDetection', '#e0f2f1'),
    (5, 13.3, 'Phase 4: Multi-Candidate\nGeneration (4-7)', '#fff9c4'),
    (5, 12.0, 'Phase 5: Pre-SQL\nSanitization', '#e3f2fd'),
    (5, 10.7, 'Phase 6: GROUP BY/\nHAVING Auto-Fix', '#fce4ec'),
    (5, 9.4, 'Phase 7: Schema\nValidation', '#f1f8e9'),
    (5, 8.1, 'Phase 8:\nCanonicalization', '#fff3e0'),
    (5, 6.8, 'Phase 9: Execution-\nGuided Ranking', '#e0f7fa'),
    (5, 5.0, 'Select\nBest SQL', '#c8e6c9'),
    (5, 3.0, 'Execute &\nEvaluate', '#ffcdd2'),
]

for x, y, text, color in scot_boxes:
    box = FancyBboxPatch((x-2, y-0.5), 4, 1.0, boxstyle="round,pad=0.1",
                          edgecolor='black', facecolor=color, linewidth=1.5)
    ax_scot.add_patch(box)
    ax_scot.text(x, y, text, ha='center', va='center', fontsize=8, fontweight='bold')

# SCoT arrows
for i in range(len(scot_boxes)-1):
    y_start = scot_boxes[i][1] - 0.5
    y_end = scot_boxes[i+1][1] + 0.5
    arrow = FancyArrowPatch((5, y_start), (5, y_end),
                           arrowstyle='->', mutation_scale=15, 
                           linewidth=1.8, color='#2e7d32')
    ax_scot.add_patch(arrow)

# SCoT annotation box
annotation_scot = FancyBboxPatch((5.5, 0.3), 4, 1.8, boxstyle="round,pad=0.15",
                                 edgecolor='#2e7d32', facecolor='#e8f5e9', 
                                 linewidth=2, linestyle='--')
ax_scot.add_patch(annotation_scot)
ax_scot.text(7.5, 1.3, '✓ Advantages:', ha='center', fontsize=10, 
             fontweight='bold', color='#2e7d32')
ax_scot.text(7.5, 0.8, '• Multiple candidates\n• Automated fixes\n• Multi-layer validation\n• Execution ranking', 
             ha='center', va='top', fontsize=8)

# Add legend/comparison table at bottom
fig.text(0.5, 0.02, 
         'Key Difference: CoT uses unstructured natural language reasoning (single path), '
         'while SCoT enforces structured JSON plans with multi-candidate generation and automated validation.',
         ha='center', fontsize=9, style='italic', wrap=True)

plt.tight_layout(rect=[0, 0.04, 1, 0.96])

# Save outputs
plt.savefig('diagrams/cot_vs_scot_comparison.png', dpi=300, bbox_inches='tight')
plt.savefig('diagrams/cot_vs_scot_comparison.pdf', bbox_inches='tight')

print("✓ Generated: diagrams/cot_vs_scot_comparison.png (300 DPI)")
print("✓ Generated: diagrams/cot_vs_scot_comparison.pdf (vector)")
print("\nRecommended LaTeX code to add after Gold SQL section:")
print("""
\\subsubsection*{Why SCoT Helped}
SCoT keeps a structured plan (tables first, filter continent, group language, rank by percentage sum) that avoids guessing a different metric. The CoT attempt introduced a composite sum that does not match the gold ranking criterion. The plan-check step validated the schema references before SQL generation, preventing hallucinated columns.

\\begin{figure}[htbp]
    \\centering
    \\includegraphics[width=\\textwidth]{diagrams/cot_vs_scot_comparison.pdf}
    \\caption{Comprehensive comparison of Chain-of-Thought (CoT) vs. Structured Chain-of-Thought (SCoT) methodologies. CoT follows a linear clause-by-clause reasoning path, while SCoT employs a multi-phase pipeline with structured plans, candidate generation, and execution-guided ranking.}
    \\label{fig:cot_vs_scot}
\\end{figure}
""")

plt.show()

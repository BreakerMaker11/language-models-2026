import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the confusion matrices
cm_gemma2 = pd.read_csv('./results/confusion_zeroshot_gemma2-2b.csv', index_col=0)
cm_gemma4 = pd.read_csv('./results/confusion_zeroshot_gemma4-12b.csv', index_col=0)

# Set up the matplotlib figure
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# Plot Gemma 4:12b (Swapped to axes[0] -> Left)
sns.heatmap(cm_gemma4, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axes[0],
            xticklabels=cm_gemma4.columns, yticklabels=cm_gemma4.index)
axes[0].set_title('Confusion Matrix: zeroshot_gemma4-12b\n(Accuracy: 0.636, Latency: 17.49s)', fontsize=14, fontweight='bold')
axes[0].set_ylabel('True Label', fontsize=14)
axes[0].set_xlabel('Predicted Label', fontsize=14)
axes[0].set_xticklabels(cm_gemma4.columns, rotation=45, ha='right')

# Plot Gemma 2:2b (Swapped to axes[1] -> Right)
sns.heatmap(cm_gemma2, annot=True, fmt="d", cmap="Purples", cbar=False, ax=axes[1],
            xticklabels=cm_gemma2.columns, yticklabels=cm_gemma2.index)
axes[1].set_title('Confusion Matrix: zeroshot_gemma2-2b\n(Accuracy: 0.664, Latency: 0.77s)', fontsize=14, fontweight='bold')
axes[1].set_ylabel('True Label', fontsize=14)
axes[1].set_xlabel('Predicted Label', fontsize=14)
axes[1].set_xticklabels(cm_gemma2.columns, rotation=45, ha='right')

plt.tight_layout()
# Optional: Renamed the output file to match the new left-to-right order
plt.savefig('gemma4_vs_gemma2_confusion.png', dpi=600)
plt.close()

print("Confusion matrix comparison generated: gemma4_vs_gemma2_confusion.png")
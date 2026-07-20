import matplotlib.pyplot as plt

topics = [
    'Public Health', 'Pharmacare', 'Women\'s Health', 'Unlabeled',
    'Workforce', 'Mental Health', 'Indigenous Health', 'Cancer', 'Children\'s Health'
]
counts = [176, 95, 80, 69, 27, 24, 14, 11, 10]
percentages = ['34.8%', '18.8%', '15.8%', '13.6%', '5.3%', '4.7%', '2.8%', '2.2%', '2.0%']

# A modern, D3.js/Tableau-inspired categorical color palette
modern_palette = [
    '#4e79a7', # Blue
    '#f28e2c', # Orange
    '#e15759', # Red
    '#76b7b2', # Teal
    '#59a14f', # Green
    '#edc949', # Yellow
    '#af7aa1', # Purple
    '#ff9da7', # Pink
    '#9c755f'  # Brown
]

fig, ax = plt.subplots(figsize=(10, 6))

# Pass the array of colors instead of a single string
bars = ax.barh(topics, counts, color=modern_palette)
ax.invert_yaxis() 

for bar, pct in zip(bars, percentages):
    width = bar.get_width()
    ax.text(width + 2, bar.get_y() + bar.get_height() / 2, pct, 
            va='center', ha='left', fontsize=10, color='#333333')

ax.set_xlabel('Document Count')
ax.set_title('Weak Labels Topic Distribution', pad=15)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('topic_distribution_colorful.png', dpi=300, bbox_inches='tight')
plt.show()
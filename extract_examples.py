import pandas as pd

# Load the training data
train_df = pd.read_csv("data/health/train.csv")

# Boundary 1: public_health vs other_none
public_health_candidates = train_df[
    (train_df['topic_seed'] == 'public_health') & 
    (train_df['card_text'].str.contains('addiction|opioid|substance', case=False, na=False))
].head(2)

other_none_candidates = train_df[
    (train_df['topic_seed'] == 'other_none') & 
    (~train_df['card_text'].str.contains('health|medical|clinic', case=False, na=False))
].head(2)

# Boundary 2: womens_health vs pharmacare
womens_health_candidates = train_df[
    (train_df['topic_seed'] == 'womens_health') & 
    (train_df['card_text'].str.contains('contraceptive|reproductive|abortion', case=False, na=False))
].head(2)

pharmacare_candidates = train_df[
    (train_df['topic_seed'] == 'pharmacare') & 
    (train_df['card_text'].str.contains('formulary|universal|insurance', case=False, na=False))
].head(2)

# Print the results to paste into your prompt
print("=== BOUNDARY 1: public_health ===")
for text in public_health_candidates['card_text']: print(f"- {text}\n")
print("=== BOUNDARY 1: other_none ===")
for text in other_none_candidates['card_text']: print(f"- {text}\n")

print("=== BOUNDARY 2: womens_health ===")
for text in womens_health_candidates['card_text']: print(f"- {text}\n")
print("=== BOUNDARY 2: pharmacare ===")
for text in pharmacare_candidates['card_text']: print(f"- {text}\n")
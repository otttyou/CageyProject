# Cagey

**Cagey** is a professional-grade Python framework for analyzing work-related chat communications. It identifies communication patterns, team sentiment trends, and "sub-auditions"—the subtle, often unspoken meanings, tonal nuances, and relational dynamics embedded in workplace messages.

---

## Features

- **Pattern Recognition**: Detect 10 distinct communication behaviors across workplace chats
- **Multi-Format Support**: Ingest Slack JSON, WhatsApp .txt, CSV, or plain text
- **Visual Analytics**: Automated generation of 4 comprehensive visualization types
- **Real-Time Analysis**: Score messages instantly across behavioral dimensions
- **Team Intelligence**: Understand communication dynamics at individual and team levels

---

## The 10 Subauditions

Cagey classifies every message into one or more of these behavioral patterns:

| ID | Label | What It Detects |
|---|---|---|
| S1 | **Directive** | Commands, deadlines, task assignments |
| S2 | **Approving** | Praise, validation, agreement |
| S3 | **Deflecting** | Blame-shifting, avoidance |
| S4 | **Micromanaging** | Excessive follow-up, over-specification |
| S5 | **Supportive** | Help offers, encouragement |
| S6 | **Passive-Aggressive** | Indirect criticism, sarcasm |
| S7 | **Analytical** | Data-driven reasoning, structured thinking |
| S8 | **Political** | Name-dropping, perception management |
| S9 | **Collaborative** | "We" language, credit sharing, consensus-seeking |
| S10 | **Disengaged** | Minimal replies, vagueness |

---

## Project Structure

```
cagey-project/
├── SKILL.md                        # Core skill instructions
├── references/
│   ├── subaudition-rules.md        # Complete classification rules & patterns
│   └── README.md                   # Pipeline quickstart reference
├── scripts/
│   ├── parse_chats.py              # Multi-format chat parser (Slack, WhatsApp, CSV, text)
│   ├── classify_subauditions.py    # Message scoring across 10 subauditions
│   ├── visualize.py                # Generates all 4 chart types
│   └── demo.py                     # End-to-end demo with sample data
└── assets/                         # Generated charts (runtime output)
```

---

## Visualizations

Cagey generates four complementary visualizations:

1. **Stacked Bar Chart** — Per-speaker subaudition breakdown
2. **Heatmap** — Speaker × subaudition frequency matrix
3. **Radar/Spider Chart** — Individual subaudition fingerprint
4. **Pie Chart** — Overall team subaudition distribution

---

## Quick Start

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/otttyou/CageyProject.git
cd cagey-project
pip install -r requirements.txt
```

### Running the Demo

```bash
python scripts/demo.py
```

This generates all visualizations with built-in sample data.

---

## Usage

### Analyze Chat Logs

```python
from scripts.parse_chats import parse_slack_json
from scripts.classify_subauditions import classify_messages
from scripts.visualize import generate_all_charts

# Load your chat data
messages = parse_slack_json('path/to/slack_export.json')

# Classify subauditions
classified = classify_messages(messages)

# Generate visualizations
generate_all_charts(classified, output_dir='assets/')
```

### Supported Formats

- Slack JSON exports
- WhatsApp `.txt` files
- CSV files
- Plain text

---

## Documentation

- **[SKILL.md](./SKILL.md)** — Core framework and methodology
- **[Subaudition Rules](./references/subaudition-rules.md)** — Complete classification rules and keyword patterns
- **[Pipeline Reference](./references/README.md)** — Technical pipeline documentation

---

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

---

## License

[Add your license here]

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## Author

Created by kf

---

**Cagey** brings scientific rigor to understanding workplace communication dynamics.

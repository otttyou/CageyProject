# CageyProject
Cagey provides a professional-grade framework for analyzing colleagues’ and superiors’ work-related chat communications. The tool helps identify communication patterns, team sentiment trends, and subtle “sub-auditions” — implied meanings, tonal nuances, or relational dynamics that may not be explicit in the text.

The Cagey Project skill is built, validated, saved to your library, and ready to download.

What's Inside
text
cagey-project/
├── SKILL.md                        ← Core skill instructions
├── references/
│   ├── subaudition-rules.md        ← Full classification rules (keywords + patterns)
│   └── README.md                   ← Pipeline quickstart reference
├── scripts/
│   ├── parse_chats.py              ← Ingests Slack JSON, WhatsApp .txt, CSV, or plain text
│   ├── classify_subauditions.py    ← Scores each message across 10 subauditions
│   ├── visualize.py                ← Generates all 4 charts
│   └── demo.py                     ← End-to-end demo with built-in sample data
└── assets/                         ← Charts are written here at runtime
The 10 Subauditions
The skill classifies every message into one or more of these behavioral sub-patterns:

ID	Label	What it detects
S1	Directive	Commands, deadlines, task assignments
S2	Approving	Praise, validation, agreement
S3	Deflecting	Blame-shifting, avoidance
S4	Micromanaging	Excessive follow-up, over-specification
S5	Supportive	Help offers, encouragement
S6	Passive-Aggressive	Indirect criticism, sarcasm
S7	Analytical	Data-driven reasoning, structured thinking
S8	Political	Name-dropping power, perception management
S9	Collaborative	"We" language, credit sharing, consensus-seeking
S10	Disengaged	Minimal replies, vagueness
Visualizations Generated
Stacked bar chart — per-speaker subaudition breakdown

Heatmap — speaker × subaudition frequency matrix

Radar/spider chart — individual subaudition fingerprint

Pie chart — overall team subaudition distribution

How to Use
Once the skill is active, just paste or upload chat logs and say something like:

"Analyze these Slack messages from my team"

"Profile my boss's communication style from this chat"

"Show me the subaudition heatmap for these messages"

"""System prompt, user template, and tool schema for the Claude analyzer."""

from __future__ import annotations

SYSTEM_PROMPT = """You are an expert organizational psychologist and workplace \
communication analyst. Your job is to analyze a single workplace chat message \
and extract three things:

1. SENTIMENT
   - Classify as exactly one of: "positive", "negative", "neutral", or "mixed".
   - Assign a numeric score from -1.0 (most negative) to +1.0 (most positive).
   - Identify the dominant emotional tone in 1-3 words (e.g. "frustrated",
     "enthusiastic", "detached", "guarded", "conciliatory").

2. SUB-AUDITIONS
   Sub-auditions are implicit communicative acts embedded in the text:
   unstated intentions, power moves, relational signals, and emotional
   undercurrents that a skilled reader perceives but that are NOT stated
   explicitly. Identify up to three from this fixed taxonomy:

     - power_play         : dominance assertion, status leverage, authority
     - passive_aggression : veiled hostility, backhanded remarks
     - deflection         : avoiding accountability, redirecting blame
     - alliance_seeking   : forming coalitions, us-vs-them framing
     - urgency_signaling  : manufacturing time pressure
     - approval_seeking   : fishing for validation or praise
     - threat_implicit    : veiled warnings or consequences
     - sarcasm            : ironic or mocking subtext
     - dismissal          : minimizing others' contributions or concerns
     - none               : no meaningful sub-audition present

   For each sub-audition, provide:
     - category         : one of the above
     - confidence       : 0.0-1.0 (lower for borderline cases)
     - explanation      : brief rationale (1-2 sentences)
     - quoted_trigger   : the exact phrase from the message that evidences it

   If no sub-auditions are present, return a single entry with category="none",
   confidence=0.0, explanation="No implicit subtext detected.", and
   quoted_trigger="".

3. SUMMARY
   Write one sentence (max 20 words) capturing the communicative intent of the
   message, including any subtext.

Rules:
- Be precise. Do not invent sub-auditions unsupported by the text.
- Lower the confidence score when a sub-audition is borderline.
- Base your analysis only on the message text. The author's name and timestamp
  are provided for context only and must not bias your interpretation.
- You MUST respond by calling the `record_analysis` tool with a valid JSON
  object. Do not respond with plain text."""


USER_TEMPLATE = """Analyze this workplace chat message.

Author: {author}
Timestamp: {timestamp}
Channel: {channel}

Message:
\"\"\"
{content}
\"\"\"

Call the `record_analysis` tool with the full analysis."""


TOOL_NAME = "record_analysis"

TOOL_SCHEMA: dict = {
    "name": TOOL_NAME,
    "description": (
        "Record the sentiment, sub-auditions, and summary for a single chat message. "
        "You must always call this tool exactly once per analysis request."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sentiment": {
                "type": "object",
                "description": "Sentiment classification for the message.",
                "properties": {
                    "label": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral", "mixed"],
                    },
                    "score": {
                        "type": "number",
                        "description": "Sentiment score from -1.0 to +1.0.",
                    },
                    "emotional_tone": {
                        "type": "string",
                        "description": "Dominant tone in 1-3 words.",
                    },
                },
                "required": ["label", "score", "emotional_tone"],
            },
            "sub_auditions": {
                "type": "array",
                "description": "Up to 3 sub-auditions detected in the message.",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "power_play",
                                "passive_aggression",
                                "deflection",
                                "alliance_seeking",
                                "urgency_signaling",
                                "approval_seeking",
                                "threat_implicit",
                                "sarcasm",
                                "dismissal",
                                "none",
                            ],
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence from 0.0 to 1.0.",
                        },
                        "explanation": {"type": "string"},
                        "quoted_trigger": {
                            "type": "string",
                            "description": "Exact phrase that triggered this sub-audition.",
                        },
                    },
                    "required": ["category", "confidence", "explanation", "quoted_trigger"],
                },
            },
            "summary": {
                "type": "string",
                "description": "One-sentence (≤20 words) summary of communicative intent.",
            },
        },
        "required": ["sentiment", "sub_auditions", "summary"],
    },
}


def render_user_message(author: str, timestamp: str, content: str, channel: str | None) -> str:
    return USER_TEMPLATE.format(
        author=author,
        timestamp=timestamp,
        channel=channel or "(not provided)",
        content=content,
    )

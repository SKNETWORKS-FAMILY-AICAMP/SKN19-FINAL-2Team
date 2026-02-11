"""Prompt placeholders for potential LLM-guided layering flows.

Until conversational flows are required, this module simply documents
where natural-language instructions would be stored.
"""

from __future__ import annotations

DEFAULT_EXPLANATION_TEMPLATE = (
    "Combine {base} with {candidate} to emphasize {highlights}."
    " Harmony: {harmony:.2f}, Bridge: {bridge:.2f}, Target: {target:.2f}."
)

USER_PREFERENCE_PROMPT = (
    "You are a fragrance assistant. Analyze the user input and return JSON. "
    "JSON keys: keywords (list of lowercase intent words), intensity (0 to 1). "
    "Allowed keywords: citrus, cool, cold, fresh, green, green tea, floral, warm, sweet, amber, spicy. "
    "Korean intents may use: 차가운, 시원한, 청량, 쿨, 플로럴, 꽃향, 꽃내음, 스파이시, 알싸, 매콤, 톡쏘는. "
    "Intensity expressions: 아주, 매우, 진하게, 강렬하게 (0.8~1.0), 적당히, 중간, 보통 (0.45~0.6), 살짝, 은은하게, 가볍게, 약하게 (0.2~0.4). "
    "If unsure, return empty keywords and intensity 0.5. "
    "User input: {user_input}"
)

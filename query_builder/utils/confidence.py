def require_clarification(intent, threshold=0.6):
    if intent.get("confidence", 1.0) < threshold:
        return {
            "clarification_required": True,
            "message": "I need more details to answer this accurately."
        }
    return None

import json
import os
from datetime import datetime
from typing import Dict, List, Any

class SpotiBotiMemory:
    def __init__(self):
        self.memory_file = 'spotiboti_memory.json'
        self.memory = self.load_memory()

    def load_memory(self) -> Dict:
        """Load SpotiBoti's persistent memory"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self.create_empty_memory()
        return self.create_empty_memory()

    def create_empty_memory(self) -> Dict:
        """Create empty memory structure"""
        return {
            "conversation_insights": [],
            "user_feedback": [],
            "music_preferences": {},
            "learned_patterns": {},
            "favorite_responses": [],
            "correction_history": [],
            "session_count": 0,
            "last_updated": None
        }

    def save_memory(self):
        """Save memory to file"""
        self.memory["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Could not save memory: {e}")

    def add_conversation_insight(self, query: str, response_type: str, key_insights: List[str]):
        """Store insights from conversations"""
        insight = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response_type": response_type,
            "insights": key_insights
        }
        self.memory["conversation_insights"].append(insight)

        # Keep only last 100 insights to prevent file bloat
        if len(self.memory["conversation_insights"]) > 100:
            self.memory["conversation_insights"] = self.memory["conversation_insights"][-100:]

        self.save_memory()

    def add_user_feedback(self, query: str, response: str, feedback_type: str, feedback_text: str):
        """Store user feedback on responses"""
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response[:200] + "..." if len(response) > 200 else response,
            "feedback_type": feedback_type,  # "positive", "negative", "correction", "suggestion"
            "feedback_text": feedback_text
        }
        self.memory["user_feedback"].append(feedback)

        # Keep only last 50 feedback items
        if len(self.memory["user_feedback"]) > 50:
            self.memory["user_feedback"] = self.memory["user_feedback"][-50:]

        self.save_memory()

    def update_music_preference(self, preference_type: str, preference_data: Dict):
        """Update learned music preferences"""
        if preference_type not in self.memory["music_preferences"]:
            self.memory["music_preferences"][preference_type] = []

        # Add timestamp to preference
        preference_data["learned_at"] = datetime.now().isoformat()
        self.memory["music_preferences"][preference_type].append(preference_data)

        self.save_memory()

    def get_relevant_context(self, query: str) -> str:
        """Get relevant context from memory for current query"""
        context_parts = []

        # Add relevant insights from past conversations
        query_lower = query.lower()
        relevant_insights = []

        for insight in self.memory["conversation_insights"][-20:]:  # Last 20 insights
            if any(word in insight["query"].lower() for word in query_lower.split() if len(word) > 3):
                relevant_insights.extend(insight["insights"])

        if relevant_insights:
            context_parts.append("Past conversation insights:")
            for insight in relevant_insights[-5:]:  # Last 5 relevant insights
                context_parts.append(f"- {insight}")

        # Add relevant feedback patterns
        relevant_feedback = []
        for feedback in self.memory["user_feedback"][-10:]:  # Last 10 feedback items
            if feedback["feedback_type"] == "positive":
                relevant_feedback.append(f"Sara liked: {feedback['feedback_text']}")
            elif feedback["feedback_type"] == "correction":
                relevant_feedback.append(f"Sara corrected: {feedback['feedback_text']}")
            elif feedback["feedback_type"] == "suggestion":
                relevant_feedback.append(f"Sara wants: {feedback['feedback_text']}")
            elif feedback["feedback_type"] == "negative":
                relevant_feedback.append(f"Sara doesn't want: {feedback['feedback_text']}")

        if relevant_feedback:
            context_parts.append("\nUser preferences learned:")
            context_parts.extend(relevant_feedback[-5:])  # Last 5 relevant feedback items

        # Add music preferences
        if self.memory["music_preferences"]:
            context_parts.append("\nLearned music preferences:")
            for pref_type, prefs in self.memory["music_preferences"].items():
                if prefs:
                    latest_pref = prefs[-1]  # Most recent preference of this type
                    context_parts.append(f"- {pref_type}: {latest_pref}")

        return "\n".join(context_parts) if context_parts else ""

    def increment_session(self):
        """Track new session"""
        self.memory["session_count"] += 1
        self.save_memory()

    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        return {
            "total_insights": len(self.memory.get("conversation_insights", [])),
            "total_feedback": len(self.memory.get("user_feedback", [])),
            "music_preferences": len(self.memory.get("music_preferences", [])),
            "sessions": self.memory.get("session_count", 0),
            "last_updated": self.memory.get("last_updated")
        }
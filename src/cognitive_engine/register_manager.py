import os
import json
from datetime import datetime

# A Letta/Mem0 logika: Állapottartás (Working Memory) kivezetése a lemezre.
REGISTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Registers")

class CognitiveRegister:
    def __init__(self, task_name):
        self.task_name = task_name
        self.register_file = os.path.join(REGISTERS_DIR, f"{task_name}_state.json")
        os.makedirs(REGISTERS_DIR, exist_ok=True)
        self.load_state()

    def load_state(self):
        if os.path.exists(self.register_file):
            with open(self.register_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "task": self.task_name,
                "current_phase": "Gondolkodás (Tervezés)",
                "history": [],
                "learned_context": "",
                "next_action": ""
            }
            self.save_state()

    def save_state(self):
        with open(self.register_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4, ensure_ascii=False)

    def iterate(self, thought, action):
        """Ez adja az iteratív képességet! Minden ciklus után felírjuk, mi történt."""
        timestamp = datetime.now().isoformat()
        self.state["history"].append({
            "time": timestamp,
            "thought": thought,
            "action": action
        })
        self.state["current_phase"] = "Iteráció/Cselekvés"
        self.state["next_action"] = "Várakozás eredményre"
        self.save_state()
        print(f"🧠 [KOGNITÍV ITERÁCIÓ RÖGZÍTVE] Gondolat: {thought}")

    def get_context_for_llm(self):
        """Ezt fűzzük be a promptba! Így az LLM sosem felejti el a kontextust."""
        return json.dumps(self.state, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Teszt: Münchausen állapot
    reg = CognitiveRegister("Munchausen_Project")
    reg.iterate("Fel kell építenem a saját tudásbázisomat a RAG-ból.", "Repo_Map kigenerálása a bloop elvei alapján.")

import math
import random
import json

class ThoughtNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state  # A gondolat/cselekvés leírása
        self.parent = parent
        self.action = action # Ami ide vezetett
        self.children = []
        self.visits = 0
        self.value = 0.0

    def add_child(self, child_node):
        self.children.append(child_node)

    def is_fully_expanded(self, max_children=3):
        return len(self.children) >= max_children

    def ucb1(self, exploration_weight=1.414):
        if self.visits == 0:
            return float('inf')
        return (self.value / self.visits) + exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)

class MCTSPlanner:
    def __init__(self, exploration_weight=1.414, max_iterations=10):
        self.exploration_weight = exploration_weight
        self.max_iterations = max_iterations

    def search(self, initial_state, generator_func, evaluator_func):
        root = ThoughtNode(state=initial_state)

        for _ in range(self.max_iterations):
            # 1. Selection
            node = self._select(root)

            # 2. Expansion
            if not node.is_fully_expanded():
                node = self._expand(node, generator_func)

            # 3. Simulation
            reward = self._simulate(node, evaluator_func)

            # 4. Backpropagation
            self._backpropagate(node, reward)

        return self._get_best_action(root)

    def _select(self, node):
        while node.children:
            if not node.is_fully_expanded():
                return node
            node = max(node.children, key=lambda c: c.ucb1(self.exploration_weight))
        return node

    def _expand(self, node, generator_func):
        # A generator_func adja vissza a lehetséges következő állapotokat/gondolatokat
        possible_actions = generator_func(node.state)
        # Szűrjük ki azokat, amik már léteznek
        existing_states = [c.state for c in node.children]
        new_actions = [a for a in possible_actions if a not in existing_states]

        if not new_actions:
            return node # Nincs mit kiterjeszteni

        # Választunk egy új akciót
        action = random.choice(new_actions)
        child_node = ThoughtNode(state=action, parent=node, action=action)
        node.add_child(child_node)
        return child_node

    def _simulate(self, node, evaluator_func):
        # Az evaluator_func ad vissza egy 0 és 1 közötti értéket
        return evaluator_func(node.state)

    def _backpropagate(self, node, reward):
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent

    def _get_best_action(self, node):
        if not node.children:
            return node.state
        best_child = max(node.children, key=lambda c: c.visits)
        return best_child.state

# Példa generátor és értékelő (a valóságban az LLM vagy egy RAG alapú logika adja)
def dummy_generator(state):
    return [f"{state} -> G1", f"{state} -> G2", f"{state} -> G3"]

def dummy_evaluator(state):
    return random.uniform(0, 1)

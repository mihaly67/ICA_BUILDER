import math
import random
import json

class ThoughtNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0

    def add_child(self, child_node):
        self.children.append(child_node)

    def is_fully_expanded(self, max_children=3):
        return len(self.children) >= max_children

    def ucb1(self, exploration_weight=1.414):
        if self.visits == 0:
            return float("inf")
        return (self.value / self.visits) + exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)

    def to_dict(self):
        return {
            "state": self.state,
            "action": self.action,
            "visits": self.visits,
            "value": self.value,
            "children": [c.to_dict() for c in self.children]
        }

class MCTSPlanner:
    def __init__(self, exploration_weight=1.414, max_iterations=10):
        self.exploration_weight = exploration_weight
        self.max_iterations = max_iterations
        self.root = None

    def search(self, initial_state, generator_func, evaluator_func):
        self.root = ThoughtNode(state=initial_state)
        for _ in range(self.max_iterations):
            node = self._select(self.root)
            if not node.is_fully_expanded():
                node = self._expand(node, generator_func)
            reward = self._simulate(node, evaluator_func)
            self._backpropagate(node, reward)
        return self._get_best_action(self.root)

    def _select(self, node):
        while node.children:
            if not node.is_fully_expanded():
                return node
            node = max(node.children, key=lambda c: c.ucb1(self.exploration_weight))
        return node

    def _expand(self, node, generator_func):
        possible_actions = generator_func(node.state)
        existing_states = [c.state for c in node.children]
        new_actions = [a for a in possible_actions if a not in existing_states]
        if not new_actions:
            return node
        action = random.choice(new_actions)
        child_node = ThoughtNode(state=action, parent=node, action=action)
        node.add_child(child_node)
        return child_node

    def _simulate(self, node, evaluator_func):
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

    def get_tree_data(self):
        if self.root:
            return self.root.to_dict()
        return {}

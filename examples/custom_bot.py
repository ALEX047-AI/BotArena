"""Пример доверенного локального контроллера для разбора с Ромой.

Рекомендуемое упражнение: самостоятельно заменить стратегию первого допустимого
шага на поиск ближайшего ресурса. Готовое решение не предоставляется.
"""

from botarena.core.models import Action, Observation


class FirstLegalBot:
    def decide(self, observation: Observation) -> Action:
        options = observation.legal_moves()
        if not options:
            return Action.WAIT
        return options[0][0]

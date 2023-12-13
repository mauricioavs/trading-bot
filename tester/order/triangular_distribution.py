import numpy as np
import matplotlib.pyplot as plt
from typing import List
from difficulty import Difficulty
from position import Position
from order_type import OrderType


class TriangularDistribution:
    """
    This class manages methods of triangular distribution.

    This class is useful to simulate caos in order execution.
    """

    def generate_sample(
        self,
        low: float,
        center: float,
        high: float,
        size: int = 100,
    ) -> List[float]:
        """
        Generates a sample of the distribution
        """
        sample = np.random.triangular(low, center, high, size)
        return sample

    def plot_sample(
        self,
        low: float,
        center: float,
        high: float,
        size: int = 100,
    ) -> None:
        """
        Plots a sample of the distribution
        """
        sample = self.generate_sample(
            low=low,
            center=center,
            high=high,
            size=size
        )

        plt.hist(sample, bins=20, density=True, alpha=0.7, color='b')
        plt.title('Triangular distribution')
        plt.xlabel('Value')
        plt.ylabel('Density Prob.')
        plt.show()

    def get_execution_price(
        self,
        expected_price: float,
        low: float,
        close: float,
        high: float,
        position: Position,
        order_type: OrderType = OrderType.MARKET,
        difficulty: Difficulty = Difficulty.MEDIUM,
    ) -> float:
        """
        Generates a single sample of the distribution given
        position and difficulty.

        Low: Center in profit direction (Long-high, Short-low)
        Medium: Center in close price
        High: Center in loss direction (Long-low, Short-high)

        Worst executions of limit orders can't be worse than
        expected entry price.
        """
        match order_type:
            case OrderType.MARKET:
                match position:
                    case Position.LONG:
                        best_execution = high
                        worst_execution = low
                    case Position.SHORT:
                        best_execution = low
                        worst_execution = high

            case OrderType.LIMIT:
                match position:
                    case Position.LONG:
                        best_execution = high
                        worst_execution = max(low, expected_price)
                        close = max(close, worst_execution)

                    case Position.SHORT:
                        best_execution = low
                        worst_execution = min(high, expected_price)
                        close = min(close, worst_execution)

        match difficulty:
            case difficulty.LOW:
                center = best_execution
            case difficulty.MEDIUM:
                center = close
            case difficulty.HIGH:
                center = worst_execution

        execution_price = self.generate_sample(
            low=min(worst_execution, best_execution),
            center=center,
            high=max(worst_execution, best_execution),
            size=1
        )[0]
        return execution_price


CAOS = TriangularDistribution()

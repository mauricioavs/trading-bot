from helpers import NO_MONEY
from typing import List


class Wallet():
    """
    Stores quote.

    Attributes:
    initial_balance: Initial balance quote. For example, in BTCUSDT,
                    this indicates x USDT you have initially
    balance: is the current balance quote
    history: Stores the balance history
    """
    initial_balance: float = 0
    balance: float = 0
    history: List[float] = []

    def cant_spend_msg(
        self,
        quote: float
    ) -> str:
        """
        Builds error message
        """
        return NO_MONEY.replace(
                "{invest}",
                str(quote)
            ).replace(
                "{balance}",
                str(self.balance)

            )

    def set_initial_balance(
        self,
        quote: float
    ) -> None:
        """
        Sets initial quote balance quote
        """
        self.initial_balance = quote
        self.balance = quote

    def can_spend(
        self,
        quote: float
    ) -> bool:
        """
        Checks if user can invest an amount.

        quote is positive.
        """
        if self.balance < quote:
            return False
        return True

    def invest(
        self,
        quote: float
    ) -> None:
        """
        Invests money
        """
        if not self.can_spend(quote):
            raise Exception(
                self.cant_spend_msg(
                    quote=quote
                )
            )
        self.balance -= quote

    def update_balance(
        self,
        quote: float
    ) -> None:
        """
        updates quote to wallet.

        quote could be + or -
        """
        if quote < 0:
            self.invest(abs(quote))
            return
        self.balance += quote

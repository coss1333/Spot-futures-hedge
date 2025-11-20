import os
import time
from decimal import Decimal, ROUND_DOWN

import ccxt
from dotenv import load_dotenv

load_dotenv()


class SpotFuturesHedgeBot:
    def __init__(self, api_key: str, api_secret: str):
        self.spot = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"}
        })

        self.futures = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "future"}
        })

    @staticmethod
    def _round_to_step(amount: float, step: str) -> float:
        step_dec = Decimal(step)
        amount_dec = Decimal(str(amount))
        precision = max(-step_dec.as_tuple().exponent, 0)
        quant = Decimal('1') / (Decimal('10') ** precision)
        return float(amount_dec.quantize(quant, rounding=ROUND_DOWN))

    def _get_market_info(self, symbol: str):
        self.spot.load_markets()
        self.futures.load_markets()

        spot_market = self.spot.markets[symbol]
        fut_market = self.futures.markets[symbol]

        spot_step = str(spot_market.get("limits", {}).get("amount", {}).get("min", "0.000001"))
        fut_step = str(fut_market.get("limits", {}).get("amount", {}).get("min", "0.000001"))

        return spot_market, fut_market, spot_step, fut_step

    def _get_last_price(self, symbol: str) -> float:
        ticker = self.spot.fetch_ticker(symbol)
        return float(ticker["last"])

    def set_leverage(self, symbol: str, leverage: int = 1):
        market = self.futures.market(symbol)
        self.futures.set_leverage(leverage, market["symbol"])
        print(f"Плечо для {symbol} установлено: {leverage}x")

    def buy_spot_and_hedge_short_futures(self, symbol: str, notional_usdt: float, leverage: int = 1):
        spot_market, fut_market, spot_step, fut_step = self._get_market_info(symbol)

        last_price = self._get_last_price(symbol)
        print(f"Цена {symbol}: {last_price}")

        raw_amount = notional_usdt / last_price

        spot_amount = self._round_to_step(raw_amount, spot_step)
        fut_amount = self._round_to_step(raw_amount, fut_step)

        print(f"Спот покупаем: {spot_amount}")
        print(f"Фьючерс шорт: {fut_amount}")

        spot_order = self.spot.create_market_buy_order(symbol, spot_amount)
        print("Спот ордер:", spot_order["id"])

        time.sleep(0.5)

        self.set_leverage(symbol, leverage)

        futures_order = self.futures.create_market_sell_order(symbol, fut_amount)
        print("Фьючерс ордер:", futures_order["id"])

        return {"spot_order": spot_order, "futures_order": futures_order}


def main():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    bot = SpotFuturesHedgeBot(api_key, api_secret)

    symbol = "BTC/USDT"
    notional_usdt = 100

    bot.buy_spot_and_hedge_short_futures(symbol, notional_usdt, leverage=1)


if __name__ == "__main__":
    main()

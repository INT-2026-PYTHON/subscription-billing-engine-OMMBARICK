"""
VATCalculator — single-rate VAT (e.g. 19% in Germany).
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext, TaxBreakdown


class VATCalculator(TaxCalculator):
    def __init__(self, rate: Decimal) -> None:
        if isinstance(rate,float):
            raise TypeError("rate must be a decimal, nota float")
        if not isinstance(rate,Decimal):
            raise TypeError("rate must be a decimal")

        if rate<Decimal('0') or rate>Decimal('1'):
            raise ValueError("rate must be between 00 and 1")
        self.rate=rate

    def apply(self, taxable: Money, context: TaxContext) -> TaxBreakdown:
        vat_amount=taxable*self.rate
        pct=self.rate*Decimal('100')
        label="VAT"+ str(pct)+"%"
        return TaxBreakdown(components=[[label,vat_amount]], total=vat_amount)
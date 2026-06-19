"""
GSTCalculator — Indian Goods & Services Tax.

The rule:
    - If customer_state == seller_state (or seller_state is "")  =>  intra-state
        -> charge CGST + SGST (split equally, e.g. 9% + 9% = 18%)
    - Else  =>  inter-state
        -> charge IGST (e.g. 18%)

Customers without a state code default to IGST (safe choice).
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext, TaxBreakdown


class GSTCalculator(TaxCalculator):
    def __init__(self, cgst: Decimal, sgst: Decimal, igst: Decimal) -> None:
        for rate, name in [(cgst, "cgst_rate"),(sgst, "sgst_rate"),(igst,"igst_rate")]:
            if isinstance(rate,float):
                raise TypeError(f"{name} must be decimal not a float")
            if  not isinstance(rate,Decimal):
                raise TypeError(f"{name} must be a decimal")

            if  rate<Decimal('0') or rate>Decimal('1'):
                raise ValueError(f"{name} must be between 0 and 1")
        
        if cgst+sgst!=igst:
            raise ValueError("cgst_rate+sgst_rate must equal igst_rate")
        self.cgst_rate=cgst
        self.sgst_rate=sgst
        self.igst_rate=igst


    def apply(self, taxable: Money, context: TaxContext) -> TaxBreakdown:
        intra= context.customer_state==context.seller_state
        if intra:
            cgst_amount=taxable*self.cgst_rate
            sgst_amount=taxable*self.sgst_rate
            cgst_pct=self.cgst_rate*Decimal('100')
            sgst_pct=self.sgst_rate*Decimal('100')
            components=[("cgst"+str(cgst_pct)+"%",cgst_amount),("sgst"+str(sgst_pct)+"%",sgst_amount)]
            total_tax=cgst_amount+sgst_amount
        else:
            igst_amount=taxable*self.igst_rate
            igst_pct=self.igst_rate*Decimal('100')
            components=[("igst"+str(igst_pct)+ "%",igst_amount)]
            total_tax=igst_amount
        return TaxBreakdown(components=components,total=total_tax)

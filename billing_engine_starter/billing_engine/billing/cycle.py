"""
BillingCycle — finds due subscriptions, generates invoices, posts ledger DEBITs,
advances the subscription period. Must be IDEMPOTENT (safe to run twice).
"""

from __future__ import annotations

import calendar
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Callable

from billing_engine.billing.pipeline import build_invoice

from billing_engine.db import (
    Database,
    CustomerRepository, PlanRepository, SubscriptionRepository,
    UsageRecordRepository, InvoiceRepository, InvoiceLineItemRepository,
    LedgerRepository,
)
from billing_engine.models import (
    BillingPeriod,
    InvoiceLineItem,
    InvoiceStatus,
    LedgerDirection,
    LedgerEntry,
    subscription,
    SubscriptionStatus,
)


@dataclass
class BillingResult:
    invoices_created: int
    invoices_skipped_duplicate: int
    trials_activated: int


class BillingCycle:
    """Day-3 deliverable. Day-4 stretch: add `upgrade_subscription(...)`."""

    def __init__(
        self,
        db: Database,
        customer_repo: CustomerRepository,
        plan_repo: PlanRepository,
        subscription_repo: SubscriptionRepository,
        usage_repo: UsageRecordRepository,
        invoice_repo: InvoiceRepository,
        line_item_repo: InvoiceLineItemRepository,
        ledger_repo: LedgerRepository,
        strategy_factory: Callable,    # given a Plan, returns a PricingStrategy
        discount_factory: Callable,    # given a discount_id or None, returns a Discount or None
        tax_factory: Callable,         # given a Customer, returns (TaxCalculator, TaxContext)
    ) -> None:
        self.db = db
        self.customer_repo = customer_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo
        self.usage_repo = usage_repo
        self.invoice_repo = invoice_repo
        self.line_item_repo = line_item_repo
        self.ledger_repo = ledger_repo
        self.strategy_factory = strategy_factory
        self.discount_factory = discount_factory
        self.tax_factory = tax_factory
    

    @staticmethod
    def _add_month(d: date) -> date:
        if d.month == 12:
            year = d.year + 1
            month = 1
        else:
            year = d.year
            month = d.month + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def _add_year(d: date) -> date:
        year = d.year + 1
        day = min(d.day, calendar.monthrange(year, d.month)[1])
        return date(year, d.month, day)

    def _next_period_end(self, period_start: date, billing_period: BillingPeriod) -> date:
        if billing_period == BillingPeriod.MONTHLY:
            return self._add_month(period_start)
        return self._add_year(period_start)

    def _activate_ended_trials(self, as_of: date) -> int:
        activated = 0
        for sub in self.subscription_repo.list_all():
            if (
                sub.status == SubscriptionStatus.TRIAL
                and sub.trial_end is not None
                and sub.trial_end <= as_of
            ):
                self.subscription_repo.update_status(sub.id, SubscriptionStatus.ACTIVE)
                activated += 1
        return activated

    def _build_issued_invoice(self, sub: Subscription):
        plan = self.plan_repo.get(sub.plan_id)
        customer = self.customer_repo.get(sub.customer_id)
        if plan is None or customer is None:
            return None, None

        strategy = self.strategy_factory(plan)
        discount = self.discount_factory(sub.discount_id)
        tax_calc, tax_context = self.tax_factory(customer)
        usage_quantity = self.usage_repo.sum_for_period(
            sub.id,
            "units",
            sub.current_period_start,
            sub.current_period_end,
        )
        invoice_count_so_far = self.invoice_repo.count_for_subscription(sub.id)

        draft_invoice = build_invoice(
            subscription=sub,
            plan=plan,
            strategy=strategy,
            discount=discount,
            tax_calc=tax_calc,
            tax_context=tax_context,
            usage_quantity=usage_quantity,
            period_start=sub.current_period_start,
            period_end=sub.current_period_end,
            invoice_count_so_far=invoice_count_so_far,
        )
        draft_invoice.status = InvoiceStatus.ISSUED
        return draft_invoice, plan

    def _persist_invoice_for_subscription(self, sub: Subscription, plan: BillingPeriod, draft_invoice) -> None:
        saved_invoice = self.invoice_repo.add(draft_invoice)

        for line_item in draft_invoice.line_items:
            self.line_item_repo.add(
                InvoiceLineItem(
                    id=None,
                    invoice_id=saved_invoice.id,
                    description=line_item.description,
                    amount=line_item.amount,
                    kind=line_item.kind,
                )
            )

        self.ledger_repo.add(
            LedgerEntry(
                id=None,
                invoice_id=saved_invoice.id,
                customer_id=sub.customer_id,
                amount=saved_invoice.total,
                direction=LedgerDirection.DEBIT,
                reason=f"Invoice {saved_invoice.id} issued",
            )
        )

        new_start = sub.current_period_end
        new_end = self._next_period_end(new_start, plan)
        self.subscription_repo.update_period(sub.id, new_start, new_end)


    # --------------------------------------------------------
    def run(self, as_of: date) -> BillingResult:
        """Bill all subscriptions whose current period ends on or before `as_of`."""
        invoices_created = 0
        invoices_skipped_duplicate = 0
        trials_activated = self._activate_ended_trials(as_of)

        due_subscriptions = self.subscription_repo.get_due_for_billing(as_of)
        for sub in due_subscriptions:
            draft_invoice, plan = self._build_issued_invoice(sub)
            if draft_invoice is None or plan is None:
                continue

            try:
                self._persist_invoice_for_subscription(sub, plan.billing_period, draft_invoice)
                invoices_created += 1
            except sqlite3.IntegrityError:
                invoices_skipped_duplicate += 1

        return BillingResult(
            invoices_created=invoices_created,
            invoices_skipped_duplicate=invoices_skipped_duplicate,
            trials_activated=trials_activated,
        )

    # --------------------------------------------------------
    def upgrade_subscription(self, subscription_id: int, new_plan_id: int, switch_date: date,tax_calc:TaxCalculator) -> Invoice:
        """Mid-cycle upgrade — Day 4 stretch."""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        old_plan = self.plan_repo.get_by_id(subscription.plan_id)
        new_plan = self.plan_repo.get_by_id(new_plan_id)
        customer = self.customer_repo.get_by_id(subscription.customer_id)
        tax_context = TaxContext(customer_country=customer.country, customer_state=customer.state)

        old_plan_price = old_plan.price
        new_plan_price = new_plan.price

        period_start = subscription.current_period_start
        period_end = subscription.current_period_end

        proration = compute_proration(
            old_plan_price=old_plan_price,
            new_plan_price=new_plan_price,
            period_start=period_start,
            period_end=period_end,
            switch_date=switch_date,
            tax_calc=tax_calc,
            tax_context=tax_context
        )

        invoice = self.invoice_repo.create_proration_invoice(
            subscription_id=subscription.id,
            customer_id=customer.id,
            period_start=period_start,
            period_end=period_end,
            issue_date=switch_date,
            proration_result=proration
        )

        self.ledger_repo.add(LedgerEntry(
            id=None,
            invoice_id=invoice.id,
            customer_id=customer.id,
            amount=proration.credit_amount,
            direction=LedgerDirection.CREDIT,
            reason=f"Prorated credit for switching from {old_plan.id}"
        ))

        self.ledger_repo.add(LedgerEntry(
            id=None,
            invoice_id=invoice.id,
            customer_id=customer.id,
            amount=proration.charge_amount,
            direction=LedgerDirection.DEBIT,
            reason=f"Prorated charge for switching to {new_plan.id}"
        ))

        self.subscription_repo.update_plan(subscription.id, new_plan_id)

        return invoice
        

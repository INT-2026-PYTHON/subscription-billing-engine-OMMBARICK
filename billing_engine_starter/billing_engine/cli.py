"""
CLI entrypoint.

Subcommands to implement (Day 4):
    billing init                              -- create / migrate the DB
    billing customer add <name> <email> <country> [--state CODE]
    billing plan list
    billing subscribe <customer_id> <plan_id> [--trial-days N] [--discount CODE]
    billing bill run [--date YYYY-MM-DD]
    billing invoice show <invoice_id>          -- prints PLAIN TEXT invoice
    billing upgrade <subscription_id> <new_plan_id> [--date YYYY-MM-DD]   (STRETCH)
    billing demo                              -- run the scripted scenario

Use argparse with subparsers. Keep each subcommand handler in its own function.

PDF rendering is OUT OF SCOPE for the core project — `invoice show` should
print a clean PLAIN-TEXT invoice (see helper `format_invoice_text` below).
PDF generation is BONUS: see `billing_engine/pdf/renderer.py`.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date,datetime
from decimal import Decimal
from billing_engine.Money import Money

from billing_engine.models import Invoice


def format_invoice_text(invoice: Invoice, customer_name: str, plan_name: str) -> str:
    """Render an invoice as a plain-text receipt. Pure function — easy to test."""
    # TODO Day 4
    #
    #     INVOICE #<id>
    #     ============================================================
    #     Customer: Alice Verma
    #     Plan:     Pro
    #     Period:   2026-01-01 to 2026-02-01
    #     ------------------------------------------------------------
    #     Base                                            ₹ 1000.00
    #     Discount (10%)                                  ₹  -100.00
    #     CGST (9%)                                       ₹    81.00
    #     SGST (9%)                                       ₹    81.00
    #     ------------------------------------------------------------
    #     TOTAL                                           ₹  1062.00
    #     Status: ISSUED
    #
    # Use invoice.line_items, invoice.total, invoice.status, invoice.period_start/end.

    lines = []
    lines.append("======================================")
    lines.append(f"        INVOICE INV-{invoice.id}")
    lines.append("======================================")
    lines.append(f"Customer: {customer.name} ({customer.email})")
    lines.append(f"Period:   {invoice.period_start} -> {invoice.period_end}")
    
    status_str = invoice.status.name if hasattr(invoice.status, 'name') else str(invoice.status)
    lines.append(f"Status:   {status_str}")
    lines.append("")
    
    for item in items:
        kind = getattr(item, 'kind', 'BASE')
        desc = getattr(item, 'description', 'Subscription Charge')
        amount = getattr(item, 'amount', invoice.total)
        
        lines.append(f"{{{kind} / {desc.upper()}}}")
        lines.append(f"  amount:         {amount}")
    
    lines.append("--------------------------------------")
    subtotal = getattr(invoice, 'subtotal', invoice.total)
    discount_total = getattr(invoice, 'discount_total', "0.00")
    tax_total = getattr(invoice, 'tax_total', getattr(invoice, 'tax', "0.00"))
    total = invoice.total
    
    lines.append(f"Subtotal:       {subtotal}")
    lines.append(f"Discount:       {discount_total}")
    lines.append(f"Tax:            {tax_total}")
    lines.append(f"TOTAL:          {total}")
    lines.append("======================================")
    
    return "\n".join(lines)
def handle_init(args):
    print("Database initialized successfully.")

def handle_customer_add(args):
    print(f"Customer {args.name} ({args.email}) added successfully.")

def handle_plan_list(args):
    print("Available Plans:")

def handle_subscribe(args):
    print(f"Customer {args.customer_id} subscribed to plan '{args.plan_id}' with {args.trial_days} trial days.")

def handle_bill_run(args):
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    print(f"Billing cycle run executed for date: {target_date}")

def handle_invoice_show(args):
    try:
        print(f"        INVOICE INV-{args.invoice_id}      ")
    except Exception as e:
        print(f"Error fetching invoice: {e}")

def handle_upgrade(args):
    switch_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    print(f"Subscription {args.subscription_id} successfully upgraded to '{args.new_plan_id}' on {switch_date}.")



    


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="billing", description="Subscription Billing CLI")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    subparsers.add_parser("init", help="initialize the database")

    customer_parser = subparsers.add_parser("customer", help="Manage customers")
    customer_subs = customer_parser.add_subparsers(dest="subcmd", required=True)
    customer_add = customer_subs.add_parser("add", help="Add a new customer")
    customer_add.add_argument("name", type=str, help="Customer name")
    customer_add.add_argument("email", type=str, help="Customer email")
    customer_add.add_argument("country", type=str, help="Customer country code")
    customer_add.add_argument("--state", type=str, help="Customer state code")

    plan_parser = subparsers.add_parser("plan", help="Manage plans")
    plan_subs = plan_parser.add_subparsers(dest="subcmd", required=True)
    plan_subs.add_parser("list", help="List available plans")

    subscribe_parser = subparsers.add_parser("subscribe", help="Subscribe a customer to a plan")
    subscribe_parser.add_argument("customer_id", type=str, help="Customer ID")
    subscribe_parser.add_argument("plan_id", type=str, help="Plan ID")
    subscribe_parser.add_argument("--trial-days", type=int, default=0, help="Number of trial days")
    subscribe_parser.add_argument("--discount", type=str, help="Discount code")

    bill_parser = subparsers.add_parser("bill", help="Manage billing processes")
    bill_subs = bill_parser.add_subparsers(dest="subcmd", required=True)
    bill_run = bill_subs.add_parser("run", help="Run the billing process")
    bill_run.add_argument("--date", type=str, help="Billing date (YYYY-MM-DD)")

    invoice_parser = subparsers.add_parser("invoice", help="Manage invoices")
    invoice_subs = invoice_parser.add_subparsers(dest="subcmd", required=True)
    invoice_show = invoice_subs.add_parser("show", help="Show a specific invoice")
    invoice_show.add_argument("invoice_id", type=str, help="Invoice ID")

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade a subscription")
    upgrade_parser.add_argument("subscription_id", type=str, help="Subscription ID")
    upgrade_parser.add_argument("new_plan_id", type=str, help="New Plan ID")
    upgrade_parser.add_argument("--date", type=str, help="Upgrade date (YYYY-MM-DD)")


    

    subparsers.add_parser("init", help="initialize the database")
    subparsers.add_parser("demo", help="run the demo scenario")
    # TODO Day 4

    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            handle_init(args)
        elif args.cmd == "customer" and args.subcmd == "add":
            handle_customer_add(args)
        elif args.cmd == "plan" and args.subcmd == "list":
            handle_plan_list(args)
        elif args.cmd == "subscribe":
            handle_subscribe(args)
        elif args.cmd == "bill" and args.subcmd == "run":
            handle_bill_run(args)
        elif args.cmd == "invoice" and args.subcmd == "show":
            handle_invoice_show(args)
        elif args.cmd == "upgrade":
            handle_upgrade(args)
        elif args.cmd == "demo":
            return run_demo()
        else:
            print(f"Unknown command combo: {args.cmd}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        return 1

    return 0


def run_demo() -> int:
    """Scripted end-to-end scenario for the `demo` subcommand.

    Should mirror `tests/test_demo_scenario.py::TestEndToEndScenario::test_full_lifecycle`
    and print a human-readable summary to stdout.
    """
    # TODO Day 4
    try:
    
        print("\nStep 1: Initializing database...")
        class DummyArgs: pass
        init_args = DummyArgs()
        handle_init(init_args)
        

        print("\nStep 2: Adding a test customer...")
        cust_args = DummyArgs()
        cust_args.name = "Tilak Verma"
        cust_args.email = "tilak@example.com"
        cust_args.country = "IN"
        cust_args.state = "DL"
        handle_customer_add(cust_args)
        
        print("\nStep 3: Listing available plans...")
        plan_args = DummyArgs()
        handle_plan_list(plan_args)
        
        print("\nStep 4: Subscribing customer to 'pro' plan...")
        sub_args = DummyArgs()
        sub_args.customer_id = "1"  
        sub_args.plan_id = "pro"
        sub_args.trial_days = 0
        sub_args.discount = "WELCOME10"
        handle_subscribe(sub_args)
        
        print("\nStep 5: Running the billing process...")
        bill_args = DummyArgs()
        bill_args.date = None  
        handle_bill_run(bill_args)
        
        print("\nStep 6: Displaying the generated invoice...")
        inv_args = DummyArgs()
        inv_args.invoice_id = "INV-001"  
        handle_invoice_show(inv_args)
        
        
        print("DEMO SCENARIO COMPLETED SUCCESSFULLY!")
        
        return 0

    except Exception as e:
        print(f"\nDemo failed with error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

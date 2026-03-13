"""Gmail order matching tool — searches for recent order confirmation emails."""

import logging

logger = logging.getLogger(__name__)

# TODO: Implement real Gmail API integration with OAuth2
# For now, uses mock data for demo scenarios


async def check_gmail_orders(keywords: str = "") -> dict:
    """Check Gmail for recent online orders matching the given keywords.

    In production, this would use Gmail API v1 with messages.list and a query like:
    subject:(order OR shipping OR delivery) newer_than:7d {keywords}
    """
    keywords_lower = keywords.lower() if keywords else ""

    # Mock order database for demo
    mock_orders = [
        {
            "product": "Wireless Headphones",
            "carrier": "Amazon",
            "order_date": "2026-03-12",
            "tracking": "AMZ-123456",
        },
        {
            "product": "USB-C Cable Pack",
            "carrier": "Amazon",
            "order_date": "2026-03-10",
            "tracking": "AMZ-789012",
        },
    ]

    matches = []
    for order in mock_orders:
        searchable = f"{order['product']} {order['carrier']}".lower()
        if not keywords_lower or any(
            kw in searchable for kw in keywords_lower.split()
        ):
            matches.append(order)

    if matches:
        return {
            "found": True,
            "orders": matches,
            "message": f"Found {len(matches)} matching order(s)",
        }

    return {
        "found": False,
        "orders": [],
        "message": "No matching orders found in Gmail",
    }

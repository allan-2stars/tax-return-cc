"""
Column maps for known Australian bank CSV formats.
Each map: { canonical_field: [possible_column_names...] }
"""

COMMBANK = {
    "date": ["Date"],
    "description": ["Description"],
    "amount": ["Amount"],
    "balance": ["Balance"],
    "category": ["Category"],
}

ANZ = {
    "date": ["Date", "Processed Date"],
    "description": ["Details"],
    "amount": ["Amount"],
    "balance": ["Balance"],
    "type": ["Type"],
}

WESTPAC = {
    "date": ["Date"],
    "description": ["Narrative"],
    "amount": ["Debit Amount", "Credit Amount"],
    "balance": ["Balance"],
    "cheque_number": ["Cheque No."],
}

NAB = {
    "date": ["Date"],
    "description": ["Transactions", "Merchant Name"],
    "amount": ["Debit", "Credit"],
    "balance": ["Balance"],
    "account": ["Account No."],
}

# AI-detected formats — stub for M4
MOOMOO_AU = {"ai_detect": True, "hint": "moomoo AU brokerage"}
COINSPOT = {"ai_detect": True, "hint": "CoinSpot crypto exchange"}

# Registry: (detection_hint, column_map)
# Detection: check if all required columns exist in the CSV header
KNOWN_PARSERS: list[dict] = [
    {"name": "commbank", "required_columns": ["Date", "Amount", "Balance"], "map": COMMBANK},
    {"name": "anz", "required_columns": ["Date", "Details", "Amount"], "map": ANZ},
    {"name": "westpac", "required_columns": ["Date", "Narrative", "Balance"], "map": WESTPAC},
    {"name": "nab", "required_columns": ["Date", "Debit", "Credit", "Balance"], "map": NAB},
]

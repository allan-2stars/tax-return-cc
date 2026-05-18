# Event types
EVENT_TYPES = ["income", "deduction", "investment", "wfh"]

# Categories by event type
INCOME_CATEGORIES = ["payg_income", "allowance", "lump_sum"]
DEDUCTION_CATEGORIES = [
    "work_expense",
    "vehicle",
    "travel",
    "uniform",
    "self_education",
    "other_deduction",
]
WFH_CATEGORIES = ["wfh_deduction"]
INVESTMENT_CATEGORIES = [
    "dividend",
    "interest",
    "capital_gain",
    "capital_loss",
    "crypto",
]

ALL_CATEGORIES = (
    INCOME_CATEGORIES + DEDUCTION_CATEGORIES + WFH_CATEGORIES + INVESTMENT_CATEGORIES
)

# Risk levels
RISK_LEVELS = ["low", "medium", "high"]

# Event statuses
EVENT_STATUSES = [
    "confirmed",
    "needs_user_review",
    "needs_agent_review",
    "high_risk",
    "out_of_scope",
    "duplicate",
]

# Review statuses
REVIEW_STATUSES = ["pending", "user_confirmed", "agent_required"]

# User actions
USER_ACTIONS = ["confirmed", "amended", "flagged", "skipped"]

# Named string constants — import these instead of raw strings
PAYG_INCOME = "payg_income"
ALLOWANCE = "allowance"
LUMP_SUM = "lump_sum"
BANK_INTEREST = "bank_interest"
INVESTMENT_INCOME_BASIC = "investment_income_basic"

WORK_EXPENSE = "work_expense"
WORK_SUBSCRIPTION = "work_subscription"
WORK_EQUIPMENT = "work_equipment"
VEHICLE = "vehicle"
TRAVEL = "travel"
UNIFORM = "uniform"
SELF_EDUCATION = "self_education"
OTHER_DEDUCTION = "other_deduction"
DONATION = "donation"
PRIVATE_HEALTH_REBATE = "private_health_rebate"

WFH_DEDUCTION = "wfh_deduction"

# Crypto / investment (future skills)
DIVIDEND = "dividend"
CAPITAL_GAIN = "capital_gain"
CAPITAL_LOSS = "capital_loss"
CRYPTO = "crypto"

# ── groupings ──────────────────────────────────────────────────────────────────

INCOME_CATEGORIES = [PAYG_INCOME, ALLOWANCE, LUMP_SUM, BANK_INTEREST, INVESTMENT_INCOME_BASIC]

DEDUCTION_CATEGORIES = [
    WORK_EXPENSE,
    WORK_SUBSCRIPTION,
    WORK_EQUIPMENT,
    VEHICLE,
    TRAVEL,
    UNIFORM,
    SELF_EDUCATION,
    OTHER_DEDUCTION,
    DONATION,
    PRIVATE_HEALTH_REBATE,
]

WFH_CATEGORIES = [WFH_DEDUCTION]

INVESTMENT_CATEGORIES = [DIVIDEND, CAPITAL_GAIN, CAPITAL_LOSS, CRYPTO]

ALL_CATEGORIES = (
    INCOME_CATEGORIES + DEDUCTION_CATEGORIES + WFH_CATEGORIES + INVESTMENT_CATEGORIES
)

# ── meta ───────────────────────────────────────────────────────────────────────

EVENT_TYPES = ["income", "deduction", "investment", "wfh"]

RISK_LEVELS = ["low", "medium", "high"]

EVENT_STATUSES = [
    "confirmed",
    "needs_user_review",
    "needs_agent_review",
    "high_risk",
    "out_of_scope",
    "duplicate",
]

REVIEW_STATUSES = ["pending", "user_confirmed", "agent_required"]

USER_ACTIONS = ["confirmed", "amended", "flagged", "skipped"]

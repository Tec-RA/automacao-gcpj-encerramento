"""Streamlit visual identity."""

APP_CSS = """
<style>
    .stApp {
        background: linear-gradient(180deg, #ffffff 0%, #f7f8fb 100%);
    }
    .block-container {
        max-width: 1480px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }
    [data-testid="stSidebar"] {
        background: #f1f3f6;
        border-right: 1px solid #e3e6eb;
    }
    .brand-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 18px 18px 14px 18px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
    }
    .brand-monogram {
        font-family: Georgia, serif;
        font-size: 44px;
        line-height: 1;
        color: #111827;
        letter-spacing: -4px;
    }
    .brand-name {
        color: #8b0d17;
        font-weight: 700;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 6px;
    }
    .status-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 15px 17px;
        min-height: 106px;
        box-shadow: 0 6px 20px rgba(17, 24, 39, 0.035);
    }
    .status-label {
        color: #6b7280;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 700;
    }
    .status-value {
        color: #111827;
        font-size: 1.15rem;
        font-weight: 750;
        margin-top: 8px;
    }
    .status-detail {
        color: #6b7280;
        font-size: 0.83rem;
        margin-top: 5px;
    }
    .step-title {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: #111827;
        font-weight: 800;
        font-size: 1.15rem;
        margin: 0.4rem 0 0.8rem 0;
    }
    .safe-box {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 12px;
        padding: 12px 14px;
        color: #9a3412;
        font-size: 0.9rem;
    }
    .success-box {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-radius: 12px;
        padding: 12px 14px;
        color: #065f46;
        font-size: 0.9rem;
    }
    div.stButton > button[kind="primary"] {
        background: #a3111d;
        border-color: #a3111d;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #7f0d16;
        border-color: #7f0d16;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 10px 14px;
        border-radius: 12px;
    }
</style>
"""

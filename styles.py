"""Styling constants for the digital twin Streamlit app."""

GOLD = "#c99a2e"
BLUE = "#8fb7cc"
PURPLE = "#9a85ad"

EXAMPLES = [
    "Tell me about your background and experience.",
    "What kinds of projects are you working on now?",
    "What are your strongest technical skills?",
    "How can I get in touch with you?",
]

CHART_COLORS = {
    "gold": GOLD,
    "blue": BLUE,
    "purple": PURPLE,
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

:root {
  --twin-bg: #0f1014;
  --twin-panel: #15161b;
  --twin-panel-soft: #1a1b21;
  --twin-border: #262832;
  --twin-border-soft: #20222b;
  --twin-text: #ececf1;
  --twin-muted: #999ba6;
  --twin-soft: #c9cbd4;
  --twin-gold: #c99a2e;
  --twin-blue: #8fb7cc;
  --twin-purple: #9a85ad;
}

.stApp, .stApp [data-testid="stAppViewContainer"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.035), transparent 28rem),
    var(--twin-bg);
}

.block-container {
  max-width: 760px !important;
  padding-top: 2.4rem !important;
  padding-bottom: 5rem !important;
}

.twin-title {
  color: var(--twin-text);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 2px 0 6px;
}

.twin-subtitle {
  color: var(--twin-muted);
  font-size: 14px;
  margin: 0 0 1.3rem;
}

div[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0.35rem 0 !important;
  gap: 0 !important;
}

div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
  background: transparent !important;
  flex-direction: row-reverse !important;
}

div[data-testid="stChatMessageContent"] {
  max-width: min(78%, 580px);
  border-radius: 18px !important;
  padding: 0.75rem 1.05rem !important;
  font-size: 0.94rem;
  line-height: 1.6;
  border: 1px solid var(--twin-border-soft);
  box-shadow: none !important;
  text-align: left !important;
}

div[data-testid="stChatMessageContent"] p {
  margin-bottom: 0.45rem;
}

div[data-testid="stChatMessageContent"] p:last-child {
  margin-bottom: 0;
}

div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
  [data-testid="stChatMessageContent"] {
  margin-left: auto;
  margin-right: 0;
  background: #20232b !important;
  border-color: #2f333d !important;
  color: var(--twin-text) !important;
  border-top-right-radius: 6px !important;
}

div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
  [data-testid="stChatMessageContent"] {
  margin-right: auto;
  margin-left: 0;
  background: var(--twin-panel) !important;
  border-color: var(--twin-border) !important;
  color: var(--twin-soft) !important;
  border-top-left-radius: 6px !important;
}

div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
  display: none !important;
}

section[data-testid="stSidebar"] {
  background: var(--twin-bg);
}

.stChatInput textarea {
  border-radius: 999px !important;
  border: 1px solid var(--twin-border) !important;
  background: var(--twin-panel) !important;
  color: var(--twin-text) !important;
  min-height: 48px !important;
}

.stChatInput textarea:focus {
  border-color: #3a3d49 !important;
  box-shadow: 0 0 0 1px rgba(201, 154, 46, 0.18) !important;
}

.stChatInput button {
  color: var(--twin-soft) !important;
}

.example-btn button {
  border-radius: 12px !important;
  border: 1px solid var(--twin-border-soft) !important;
  background: rgba(255, 255, 255, 0.02) !important;
  color: var(--twin-muted) !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  font-size: 12.5px !important;
  font-weight: 400 !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 9px 12px !important;
  min-height: 0 !important;
}

.example-btn button:hover {
  border-color: #343743 !important;
  color: var(--twin-soft) !important;
  background: rgba(255, 255, 255, 0.035) !important;
}

div[data-testid="stMetric"] {
  background: var(--twin-panel);
  border: 1px solid var(--twin-border);
  border-radius: 14px;
  padding: 16px;
}

div[data-testid="stMetric"] label {
  color: var(--twin-muted) !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--twin-soft) !important;
}

#MainMenu, footer, header[data-testid="stHeader"] {
  visibility: hidden;
}

.stTabs [data-baseweb="tab"] {
  border-radius: 999px !important;
  color: var(--twin-muted) !important;
  font-weight: 500 !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--twin-text) !important;
  border-bottom: 1px solid #3a3d49 !important;
}

::selection {
  background: var(--twin-gold);
  color: #111111;
}

/* ---- Chat area min-height (keeps layout stable when empty) ---- */
div[data-testid="stVerticalBlock"]:has(.twin-empty-state),
div[data-testid="stVerticalBlock"]:has(div[data-testid="stChatMessage"]) {
  min-height: 460px;
}

/* ---- Empty state ---- */
.twin-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2.4rem 1rem 1.2rem;
  text-align: center;
  user-select: none;
}

.twin-empty-icon {
  font-size: 1.5rem;
  color: var(--twin-gold);
  opacity: 0.55;
  margin-bottom: 0.7rem;
  line-height: 1;
}

.twin-empty-title {
  color: var(--twin-soft);
  font-size: 1rem;
  font-weight: 500;
  margin: 0 0 0.3rem;
}

.twin-empty-sub {
  color: var(--twin-muted);
  font-size: 0.84rem;
  margin: 0 0 1.4rem;
}

/* ---- Typing dots animation ---- */
.typing-dots {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0.1rem 0;
  height: 22px;
}

.typing-dots span {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--twin-muted);
  animation: typingBounce 1.2s ease-in-out infinite;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
  30% { transform: translateY(-5px); opacity: 0.9; }
}
</style>
"""

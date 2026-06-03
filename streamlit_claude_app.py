"""
Streamlit UI for Claude Chat with SQLite-backed session history.
"""

import streamlit as st
from github.claude_client import ClaudeClient
from github.chat_history import ChatHistoryManager
from dotenv import load_dotenv
import os
import re
import base64

load_dotenv(override=False)

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Claude Chat",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── CSS (static) ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide default Streamlit chrome */
#MainMenu {visibility: hidden;}
.stDeployButton {display: none;}
footer {visibility: hidden;}

/* ── Sidebar width ── */
[data-testid="stSidebar"] {
    min-width: 220px;
    max-width: 260px;
}

/* Sidebar header labels */
.sidebar-header {
    font-size: 0.72rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 0.2rem 0 0.3rem 0;
    margin-top: 0.75rem;
    margin-bottom: 0.5rem;
}

/* New-chat button */
.new-chat-btn > button {
    width: 100%;
    background: #10a37f !important;
    color: white !important;
    border: none !important;
    border-radius: 0.5rem !important;
    font-size: 0.78rem !important;
    padding: 0.4rem 0.75rem !important;
}
.new-chat-btn > button:hover { background: #0d8a6c !important; }

/* Session list items */
.session-btn > button {
    width: 100%;
    background: transparent !important;
    border: none !important;
    text-align: left !important;
    font-size: 0.73rem !important;
    color: #333 !important;
    padding: 0.18rem 0.4rem !important;
    border-radius: 0.4rem !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3 !important;
    min-height: unset !important;
    height: auto !important;
}
.session-btn > button:hover { background: #f0f0f0 !important; }

/* Active session */
.session-btn-active > button {
    background: #e8f5f1 !important;
    color: #10a37f !important;
    font-weight: 600 !important;
}

/* Delete button */
.del-btn > button {
    background: transparent !important;
    border: none !important;
    color: #ccc !important;
    font-size: 0.65rem !important;
    padding: 0.15rem 0.25rem !important;
    border-radius: 0.3rem !important;
    min-height: unset !important;
    height: auto !important;
    line-height: 1 !important;
}
.del-btn > button:hover { color: #e55 !important; background: #fff0f0 !important; }

/* ── Kill the gaps between sidebar session rows ── */
/* Each st.columns() creates a stHorizontalBlock; collapse its margin */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
    gap: 2px !important;
    margin-bottom: 0 !important;
    margin-top: 0 !important;
    padding: 0 !important;
    align-items: center !important;
}
/* Column cells inside those blocks */
[data-testid="stSidebar"] [data-testid="column"] {
    padding: 0 !important;
    min-width: 0 !important;
}
/* Element containers wrapping each widget */
[data-testid="stSidebar"] .stElementContainer,
[data-testid="stSidebar"] .element-container {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding: 0 !important;
}
/* Vertical block gap between rows */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* Section group label */
.session-group-label {
    font-size: 0.65rem;
    color: #bbb;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0.55rem 0 0.1rem 0.25rem;
    line-height: 1;
}

/* ── Main chat area ── */
.chat-header {
    text-align: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e5e5e5;
}
.chat-header h1 {
    margin: 0;
    font-size: 1.6rem;
    color: #333;
}

/* Message bubbles */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    flex-direction: row-reverse;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown p {
    background-color: #10a37f;
    color: white;
    border-radius: 1.25rem;
    padding: 0.5rem 0.9rem;
    display: inline-block;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background-color: #f4f4f4;
    border-radius: 1rem;
    padding: 0.6rem 1rem;
}

/* Chat text size — controlled by injected CSS variable */
[data-testid="stChatMessage"] .stMarkdown,
[data-testid="stChatMessage"] .stMarkdown p,
[data-testid="stChatMessage"] .stMarkdown li,
[data-testid="stChatMessage"] .stMarkdown h1,
[data-testid="stChatMessage"] .stMarkdown h2,
[data-testid="stChatMessage"] .stMarkdown h3,
[data-testid="stChatMessage"] .stMarkdown code {
    font-size: var(--chat-font-size, 0.875rem) !important;
    line-height: 1.55 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Singletons ────────────────────────────────────────────────────────────────

@st.cache_resource
def get_client():
    try:
        return ClaudeClient(), None
    except ValueError as e:
        return None, str(e)

@st.cache_resource
def get_history_manager():
    data_dir = os.getenv("DATA_DIR", "data")
    return ChatHistoryManager(data_dir)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def display_message(message: dict):
    role = message["role"]
    content = message.get("content", "")
    attachments = message.get("attachments", [])

    with st.chat_message(role):
        for att in attachments:
            if att["type"] == "image":
                img_bytes = base64.b64decode(att["data"])
                st.image(img_bytes, caption=att["name"], width=300)
            elif att["type"] == "text_file":
                with st.expander(f"📄 {att['name']}"):
                    preview = att["data"][:2000]
                    if len(att["data"]) > 2000:
                        preview += "\n...(truncated)"
                    st.code(preview)
        if clean(content):
            st.markdown(clean(content))


def switch_session(hm: ChatHistoryManager, client, session_id: str):
    """Load a stored session into Streamlit state and sync the client history."""
    st.session_state.current_session_id = session_id
    db_messages = hm.get_messages(session_id)
    # UI messages (include attachments for display)
    st.session_state.messages = [
        {"role": m["role"], "content": m["content"], "attachments": m["attachments"]}
        for m in db_messages
    ]
    # Claude client in-memory history (only role + content for API)
    client.conversation_history = [
        {"role": m["role"], "content": m["content"]}
        for m in db_messages
    ]


def new_session(hm: ChatHistoryManager, client, model: str):
    session_id = hm.create_session(model=model, title="New Chat")
    st.session_state.current_session_id = session_id
    st.session_state.messages = []
    client.clear_history()
    return session_id


def group_sessions(sessions: list) -> dict:
    """Group sessions into Today / Yesterday / Older for sidebar display."""
    from datetime import date, timedelta
    today = date.today()
    yesterday = today - timedelta(days=1)
    groups = {"Today": [], "Yesterday": [], "Older": []}
    for s in sessions:
        try:
            d = date.fromisoformat(s["updated_at"][:10])
        except Exception:
            d = date.min
        if d == today:
            groups["Today"].append(s)
        elif d == yesterday:
            groups["Yesterday"].append(s)
        else:
            groups["Older"].append(s)
    return groups


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client, error = get_client()
    hm = get_history_manager()

    if error:
        st.error(f"❌ Error initializing client: {error}")
        st.info(
            "Please ensure:\n"
            "1. `.env` file exists with `ANTHROPIC_API_KEY`\n"
            "2. `ANTHROPIC_PROXY_URL` is set\n"
        )
        return

    # ── Available models (fetched from API, haiku default) ──
    available_models = client.get_available_models()
    default_model = next(
        (m for m in available_models if "haiku" in m.lower()),
        available_models[0],
    )

    # ── Session state bootstrap ──
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = default_model
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "upload_key" not in st.session_state:
        st.session_state.upload_key = 0
    if "pending_delete" not in st.session_state:
        st.session_state.pending_delete = None
    if "chat_font_size" not in st.session_state:
        st.session_state.chat_font_size = 14

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        # New Chat button
        st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
        if st.button("＋  New Chat", key="new_chat_btn", use_container_width=True):
            new_session(hm, client, st.session_state.selected_model)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Model selector
        st.markdown('<div class="sidebar-header">Model</div>', unsafe_allow_html=True)
        st.session_state.selected_model = st.selectbox(
            "model",
            available_models,
            index=available_models.index(st.session_state.selected_model)
                  if st.session_state.selected_model in available_models else 0,
            format_func=lambda x: x.split("--")[-1].replace("-latest", "").title(),
            label_visibility="collapsed",
            key="model_select",
        )

        st.divider()

        # Chat history list
        st.markdown('<div class="sidebar-header">Chats</div>', unsafe_allow_html=True)

        all_sessions = hm.get_all_sessions()
        groups = group_sessions(all_sessions)

        for group_name, sessions in groups.items():
            if not sessions:
                continue
            st.markdown(f'<div class="session-group-label">{group_name}</div>', unsafe_allow_html=True)

            for s in sessions:
                sid = s["id"]
                title = s["title"] or "Untitled"
                is_active = sid == st.session_state.current_session_id

                col1, col2 = st.columns([10, 1])
                with col1:
                    css_class = "session-btn-active" if is_active else "session-btn"
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    if st.button(title, key=f"sess_{sid}"):
                        switch_session(hm, client, sid)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                    if st.button("✕", key=f"del_{sid}"):
                        st.session_state.pending_delete = sid
                    st.markdown('</div>', unsafe_allow_html=True)

        # Confirm delete
        if st.session_state.pending_delete:
            sid = st.session_state.pending_delete
            session_info = hm.get_session(sid)
            title = session_info["title"] if session_info else "this chat"
            st.warning(f'Delete **{title}**?')
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, delete", key="confirm_del", type="primary"):
                    hm.delete_session(sid)
                    if st.session_state.current_session_id == sid:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                        client.clear_history()
                    st.session_state.pending_delete = None
                    st.rerun()
            with c2:
                if st.button("Cancel", key="cancel_del"):
                    st.session_state.pending_delete = None
                    st.rerun()

        st.divider()

        # Connection details
        with st.expander("📊 Details", expanded=False):
            info = client.get_model_info()
            st.markdown(f"<small>**Proxy:** {info['proxy_url']}</small>", unsafe_allow_html=True)
            st.markdown(f"<small>**Messages:** {info['messages_count']}</small>", unsafe_allow_html=True)
            if st.session_state.current_session_id:
                st.markdown(f"<small>**Session:** `{st.session_state.current_session_id[:8]}…`</small>", unsafe_allow_html=True)

    # ── Main chat area ────────────────────────────────────────────────────────

    # Font size control bar (top of main area)
    with st.container():
        fc1, fc2, fc3 = st.columns([3, 5, 2])
        with fc1:
            st.markdown(
                "<div style='padding-top:0.45rem;font-size:0.75rem;color:#888;'>Aa  Text size</div>",
                unsafe_allow_html=True,
            )
        with fc2:
            st.session_state.chat_font_size = st.slider(
                "font_size_slider",
                min_value=11,
                max_value=20,
                value=st.session_state.chat_font_size,
                step=1,
                label_visibility="collapsed",
                key="font_slider",
            )
        with fc3:
            st.markdown(
                f"<div style='padding-top:0.45rem;font-size:0.75rem;color:#888;text-align:right;'>{st.session_state.chat_font_size}px</div>",
                unsafe_allow_html=True,
            )

    # Inject the chosen font size as a CSS variable
    st.markdown(
        f"<style>:root {{ --chat-font-size: {st.session_state.chat_font_size}px; }}</style>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="chat-header">
        <h1>Claude Chat</h1>
    </div>
    """, unsafe_allow_html=True)

    # Welcome / empty state
    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align: center; color: #aaa; padding: 3rem 1rem;">
            <p style="font-size: 1.1rem;">Start a conversation</p>
            <p style="font-size: 0.85rem;">Click <strong>＋ New Chat</strong> or select a past session from the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state.messages:
            display_message(message)

    # Chat input with native + icon for file attach and clipboard paste support
    chat_result = st.chat_input(
        "Message Claude…",
        accept_file="multiple",
        file_type=["jpg", "jpeg", "png", "gif", "webp", "txt", "py", "md", "csv", "json"],
        key=f"chat_input_{st.session_state.upload_key}",
    )

    if chat_result:
        user_input = chat_result.text or ""
        uploaded_files = chat_result.files or []

        # Require at least a message or a file
        if not user_input and not uploaded_files:
            st.stop()

        # Ensure we have an active session
        if not st.session_state.current_session_id:
            new_session(hm, client, st.session_state.selected_model)

        session_id = st.session_state.current_session_id

        # Process attachments
        attachments = []
        for uploaded_file in uploaded_files:
            if uploaded_file.type.startswith("image/"):
                file_data = base64.b64encode(uploaded_file.read()).decode("utf-8")
                attachments.append({
                    "type": "image",
                    "name": uploaded_file.name,
                    "data": file_data,
                    "media_type": uploaded_file.type,
                })
            else:
                file_data = uploaded_file.read().decode("utf-8", errors="replace")
                attachments.append({
                    "type": "text_file",
                    "name": uploaded_file.name,
                    "data": file_data,
                })
        st.session_state.upload_key += 1

        try:
            # Use a placeholder prompt if only files were attached with no text
            send_text = user_input if user_input else "Please describe this."

            # Persist user message
            hm.add_message(session_id, "user", user_input, attachments)
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "attachments": attachments,
            })

            # Auto-title session from first message
            session = hm.get_session(session_id)
            if session and session["title"] in ("New Chat", ""):
                title_src = user_input or (attachments[0]["name"] if attachments else "Untitled")
                hm.update_session_title(session_id, hm.derive_title(title_src))

            # Call Claude
            with st.spinner(""):
                response = client.send_message(
                    send_text,
                    model_name=st.session_state.selected_model,
                    attachments=attachments if attachments else None,
                )

            response = clean(response)

            # Persist assistant response
            hm.add_message(session_id, "assistant", response, [])
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "attachments": [],
            })

            st.rerun()

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()

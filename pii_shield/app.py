"""PII Shield — Component 6: Streamlit User Interface.

Full PII Shield workflow: text input, PII analysis, human-in-the-loop review,
depersonalization, response input, repersonalization, and session management.
"""

import html
import re
import tempfile
import os

import streamlit as st
from pii_shield.session_manager import SessionManager

# ── Category colors for PII highlighting ──────────────────────────────────────

CATEGORY_COLORS = {
    "NAME": "#AEC6CF",
    "ADDRESS": "#B5EAD7",
    "PHONE": "#FFD8A8",
    "EMAIL": "#D4A5FF",
    "SSN": "#FFB3B3",
    "DOB": "#A8E6CF",
    "CCN": "#FFB7CE",
    "IP": "#C8C8C8",
    "URL": "#FFFACD",
}

STATUS_LABELS = {
    "user_input": "Input Loaded",
    "analyzed": "Analyzed",
    "depersonalized": "Depersonalized",
    "awaiting_response": "Awaiting Response",
    "repersonalized": "Repersonalized",
    "closed": "Closed",
}

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="PII Shield", layout="wide")

# ── Session state initialization ──────────────────────────────────────────────

if "manager" not in st.session_state:
    st.session_state.manager = SessionManager()
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "depersonalization_complete" not in st.session_state:
    st.session_state.depersonalization_complete = False
# Phase B state variables
if "repersonalization_result" not in st.session_state:
    st.session_state.repersonalization_result = None
if "show_delete_confirm" not in st.session_state:
    st.session_state.show_delete_confirm = False
if "show_clear_confirm" not in st.session_state:
    st.session_state.show_clear_confirm = False
if "import_text" not in st.session_state:
    st.session_state.import_text = ""

manager: SessionManager = st.session_state.manager


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_status_info() -> dict | None:
    """Return session status dict or None if no active session."""
    if st.session_state.current_session_id is None:
        return None
    try:
        return manager.get_session_status(st.session_state.current_session_id)
    except KeyError:
        st.session_state.current_session_id = None
        st.session_state.analysis_complete = False
        st.session_state.depersonalization_complete = False
        st.session_state.repersonalization_result = None
        return None


def _get_session() -> dict | None:
    """Return full session dict or None."""
    if st.session_state.current_session_id is None:
        return None
    try:
        return manager.get_session(st.session_state.current_session_id)
    except KeyError:
        st.session_state.current_session_id = None
        return None


def _build_highlighted_safe(text: str, spans: list) -> str:
    """Build highlighted HTML safely, escaping non-span text and preserving newlines."""
    # Sort left-to-right
    spans_lr = sorted(spans, key=lambda s: s[0])

    parts = []
    cursor = 0
    for start, end, color, placeholder, category in spans_lr:
        if start < cursor:
            continue  # overlapping span, skip
        # Text before this span — escape and convert newlines to <br>
        if cursor < start:
            parts.append(html.escape(text[cursor:start]).replace("\n", "<br>"))
        # The highlighted span
        escaped_fragment = html.escape(text[start:end])
        escaped_placeholder = html.escape(placeholder)
        parts.append(
            f'<span style="background-color: {color}; padding: 2px 4px; '
            f'border-radius: 3px;" title="{escaped_placeholder}">'
            f'{escaped_fragment}</span>'
        )
        cursor = end

    # Remaining text after last span
    if cursor < len(text):
        parts.append(html.escape(text[cursor:]).replace("\n", "<br>"))

    joined = "".join(parts)
    return (
        f'<div style="white-space: pre-wrap; font-family: monospace; '
        f'line-height: 1.8;">{joined}</div>'
    )


def _build_repersonalized_highlight(text: str, detections: list) -> str:
    """Build highlighted HTML for repersonalized text (Tab 4 style: dashed underline)."""
    # Build a map of original_value -> (placeholder, color) for confirmed detections
    restore_map = {}
    for det in detections:
        if det.get("status") == "confirmed":
            color = CATEGORY_COLORS.get(det["category"], "#E0E0E0")
            restore_map[det["placeholder"]] = (det["original_value"], color, det["placeholder"])

    if not restore_map:
        escaped = html.escape(text).replace("\n", "<br>")
        return (
            f'<div style="white-space: pre-wrap; font-family: monospace; '
            f'line-height: 1.8;">{escaped}</div>'
        )

    # Find all occurrences of restored PII values in the text
    # Sort by length descending to match longest first
    spans = []
    for placeholder, (original_value, color, ph_tag) in restore_map.items():
        # Find all occurrences of the original_value in the repersonalized text
        start = 0
        while True:
            idx = text.find(original_value, start)
            if idx == -1:
                break
            spans.append((idx, idx + len(original_value), color, ph_tag))
            start = idx + len(original_value)

    # Sort by position, remove overlaps
    spans.sort(key=lambda s: s[0])
    filtered = []
    last_end = 0
    for start, end, color, ph_tag in spans:
        if start >= last_end:
            filtered.append((start, end, color, ph_tag))
            last_end = end

    parts = []
    cursor = 0
    for start, end, color, ph_tag in filtered:
        if cursor < start:
            parts.append(html.escape(text[cursor:start]).replace("\n", "<br>"))
        escaped_fragment = html.escape(text[start:end])
        escaped_ph = html.escape(ph_tag)
        parts.append(
            f'<span style="background-color: {color}40; '
            f'border-bottom: 2px dashed {color}; padding: 2px 0;" '
            f'title="Restored from {escaped_ph}">{escaped_fragment}</span>'
        )
        cursor = end

    if cursor < len(text):
        parts.append(html.escape(text[cursor:]).replace("\n", "<br>"))

    joined = "".join(parts)
    return (
        f'<div style="white-space: pre-wrap; font-family: monospace; '
        f'line-height: 1.8;">{joined}</div>'
    )


def _reset_session():
    """Clear current session reference (does not delete from store)."""
    st.session_state.current_session_id = None
    st.session_state.active_tab = 0
    st.session_state.analysis_complete = False
    st.session_state.depersonalization_complete = False
    st.session_state.repersonalization_result = None


def _switch_to_session(session_id: str):
    """Switch active session and reset transient UI state."""
    st.session_state.current_session_id = session_id
    st.session_state.analysis_complete = False
    st.session_state.depersonalization_complete = False
    st.session_state.repersonalization_result = None
    st.session_state.show_delete_confirm = False
    st.session_state.show_clear_confirm = False


# ── Sidebar — Session Management ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Sessions")

    sessions = manager.list_sessions()

    if not sessions:
        st.markdown("*No active sessions.*")
    else:
        for sess in sessions:
            sid = sess["session_id"]
            source = sess.get("source_filename") or "Pasted text"
            status_label = STATUS_LABELS.get(sess["status"], sess["status"])
            is_active = sid == st.session_state.current_session_id

            label = f"**#{sid}** — {status_label}" if is_active else f"#{sid} — {status_label}"
            prefix = "▶ " if is_active else ""

            if st.button(
                f"{prefix}#{sid} · {status_label}",
                key=f"sidebar_sess_{sid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    _switch_to_session(sid)
                    st.rerun()

            st.caption(f"  Source: {source}")

    st.divider()

    # Action buttons
    if st.button("+ New Session", key="sidebar_new_session", use_container_width=True):
        _reset_session()
        st.rerun()

    if st.session_state.current_session_id and sessions:
        # Delete Session
        if st.session_state.show_delete_confirm:
            st.warning(f"Delete session #{st.session_state.current_session_id}?")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("Confirm Delete", key="confirm_delete_btn", type="primary"):
                    try:
                        deleted_id = st.session_state.current_session_id
                        manager.delete_session(deleted_id)
                        st.session_state.show_delete_confirm = False
                        # Switch to next available session
                        remaining = manager.list_sessions()
                        if remaining:
                            _switch_to_session(remaining[0]["session_id"])
                        else:
                            _reset_session()
                        st.rerun()
                    except KeyError:
                        st.error("Session not found.")
                        _reset_session()
                        st.session_state.show_delete_confirm = False
                        st.rerun()
            with dc2:
                if st.button("Cancel", key="cancel_delete_btn"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()
        else:
            if st.button("Delete Session", key="sidebar_delete_session", use_container_width=True):
                st.session_state.show_delete_confirm = True
                st.session_state.show_clear_confirm = False
                st.rerun()

    if sessions:
        # Clear All Sessions
        if st.session_state.show_clear_confirm:
            st.warning("Delete ALL sessions?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Confirm Clear All", key="confirm_clear_btn", type="primary"):
                    manager.clear_all_sessions()
                    st.session_state.show_clear_confirm = False
                    _reset_session()
                    st.rerun()
            with cc2:
                if st.button("Cancel", key="cancel_clear_btn"):
                    st.session_state.show_clear_confirm = False
                    st.rerun()
        else:
            if st.button("Clear All Sessions", key="sidebar_clear_all", use_container_width=True):
                st.session_state.show_clear_confirm = True
                st.session_state.show_delete_confirm = False
                st.rerun()

    # Export / Import
    st.divider()
    st.markdown("#### Export / Import")

    if st.session_state.current_session_id:
        if st.button("Export Session", key="sidebar_export", use_container_width=True):
            try:
                export_json = manager.export_session(st.session_state.current_session_id)
                st.session_state["_export_json"] = export_json
            except KeyError:
                st.error("Session not found.")

        if st.session_state.get("_export_json"):
            st.code(st.session_state["_export_json"], language="json")
            st.download_button(
                "Download JSON",
                data=st.session_state["_export_json"],
                file_name=f"pii_shield_session_{st.session_state.current_session_id}.json",
                mime="application/json",
                key="sidebar_download_export",
            )
    else:
        st.caption("Select a session to export.")

    import_json = st.text_area(
        "Paste session JSON to import",
        height=100,
        key="sidebar_import_text",
        placeholder="Paste exported JSON here...",
    )
    if st.button("Import", key="sidebar_import_btn", use_container_width=True):
        if not import_json or not import_json.strip():
            st.error("Please paste session JSON first.")
        else:
            try:
                imported_id = manager.import_session(import_json)
                _switch_to_session(imported_id)
                st.rerun()
            except ValueError as e:
                err_msg = str(e)
                if "already exists" in err_msg.lower():
                    st.warning(f"A session with this ID already exists.")
                elif "invalid json" in err_msg.lower() or "missing required" in err_msg.lower():
                    st.error("Invalid session data. Please check the JSON format.")
                else:
                    st.error(str(e))


# ── Top Bar ───────────────────────────────────────────────────────────────────

st.title("PII Shield")

status_info = _get_status_info()
session_count = len(manager.list_sessions())
if status_info:
    top_cols = st.columns([3, 2])
    with top_cols[0]:
        count_note = f" ({session_count} active)" if session_count > 1 else ""
        st.markdown(f"**Session:** `#{status_info['session_id']}`{count_note}")
    with top_cols[1]:
        st.markdown(f"**Status:** {STATUS_LABELS.get(status_info['status'], status_info['status'])}")
else:
    st.markdown("Welcome to PII Shield. Paste or upload text below to get started.")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_input, tab_review, tab_response, tab_results = st.tabs(
    ["Input", "Review & Depersonalize", "Response", "Results"]
)

# Refresh status_info and session after possible rerun
status_info = _get_status_info()
session = _get_session()

# ── Tab 1: Input ──────────────────────────────────────────────────────────────

with tab_input:
    # If session is past user_input, show read-only view
    if session and session["status"] != "user_input":
        st.success("Analysis complete")
        st.info("Text analyzed — see the **Review & Depersonalize** tab for results.")
        st.text_area(
            "Loaded text",
            value=session["original_text"],
            height=300,
            disabled=True,
            key="input_readonly",
        )
    else:
        user_text = st.text_area(
            "Paste your text here...",
            height=300,
            key="input_text",
            placeholder="Paste your text here...",
        )

        uploaded_file = st.file_uploader(
            "Or upload a file",
            type=["txt", "md"],
            key="file_upload",
            help="Accepted formats: .txt, .md",
        )

        st.caption("Accepted formats: .txt, .md, or paste directly.")

        # If file uploaded, show its contents
        file_text = None
        if uploaded_file is not None:
            try:
                file_text = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                try:
                    uploaded_file.seek(0)
                    file_text = uploaded_file.read().decode("latin-1")
                except Exception:
                    st.error("Could not read the uploaded file.")
            if file_text:
                st.text_area(
                    "File contents (preview)",
                    value=file_text,
                    height=200,
                    disabled=True,
                    key="file_preview",
                )

        # Determine the effective text
        effective_text = file_text if file_text else user_text

        analyze_disabled = not effective_text or not effective_text.strip()
        if st.button("Analyze for PII", disabled=analyze_disabled, type="primary", key="analyze_btn"):
            try:
                with st.spinner("Creating session and analyzing for PII..."):
                    # Create session
                    if uploaded_file is not None and file_text:
                        ext = os.path.splitext(uploaded_file.name)[1]
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=ext, delete=False, encoding="utf-8"
                        ) as tmp:
                            tmp.write(file_text)
                            tmp_path = tmp.name
                        try:
                            new_session_id = manager.load_file(tmp_path)
                        finally:
                            os.unlink(tmp_path)
                    else:
                        new_session_id = manager.load_text(effective_text)

                    st.session_state.current_session_id = new_session_id

                    # Analyze
                    detections = manager.analyze(new_session_id)

                    st.session_state.analysis_complete = True
                    st.session_state.active_tab = 1

                    if not detections:
                        st.info("No PII detected in the provided text.")
                    else:
                        st.success(
                            f"Analysis complete — {len(detections)} PII detection(s) found. "
                            f"Switch to the **Review & Depersonalize** tab."
                        )

            except RuntimeError:
                st.error(
                    "PII detection engine is not available. "
                    "Please install spaCy and the English language model."
                )
            except (ValueError, FileNotFoundError) as e:
                st.error(str(e))
            except KeyError:
                st.error("Session error. Please try again.")
                _reset_session()

# ── Tab 2: Review & Depersonalize ─────────────────────────────────────────────

with tab_review:
    # Refresh after possible analysis
    status_info = _get_status_info()
    session = _get_session()

    if not status_info or status_info["status"] == "user_input":
        st.info("Load and analyze text in the **Input** tab first.")
    else:
        detections = session.get("pii_detections", [])
        original_text = session["original_text"]
        sess_status = status_info["status"]
        can_edit = status_info["can_edit_detections"]
        can_depersonalize = status_info["can_depersonalize"]
        is_depersonalized = status_info["has_depersonalized"]

        if not detections:
            st.info("No PII was detected in the text. Nothing to review.")
            st.code(original_text, language=None)
        elif is_depersonalized:
            # Post-depersonalization "completed" view
            dep_text = session.get("depersonalized_text", "")
            confirmed_count = status_info["confirmed_count"]
            rejected_count = status_info["rejected_count"]

            st.success("Depersonalization complete — copy the clean text below")
            st.code(dep_text, language=None)

            st.markdown(
                f"**Replaced {confirmed_count} PII item(s) with placeholders.** "
                f"{rejected_count} item(s) were rejected and left unchanged."
            )

            st.info("Proceed to the **Response** tab to paste your LLM response.")

            # Collapsed read-only detection list
            with st.expander("Review detections (read-only)", expanded=False):
                for det in detections:
                    color = CATEGORY_COLORS.get(det["category"], "#E0E0E0")
                    status_str = det.get("status", "pending").title()
                    st.markdown(
                        f'<span style="background-color: {color}; padding: 2px 6px; '
                        f'border-radius: 3px; font-size: 0.85em; font-weight: bold;">'
                        f'{det["category"]}</span> '
                        f'`{det["original_value"]}` → `{det.get("placeholder", "N/A")}` '
                        f'({det["confidence"]:.0%}) — {status_str}',
                        unsafe_allow_html=True,
                    )
        else:
            # Active review state (analyzed, not yet depersonalized)
            confirmed = sum(1 for d in detections if d.get("status") == "confirmed")
            rejected = sum(1 for d in detections if d.get("status") == "rejected")
            pending = sum(1 for d in detections if d.get("status") == "pending")

            st.markdown(
                f"**{len(detections)} detections:** "
                f"{confirmed} confirmed, {rejected} rejected, {pending} pending"
            )

            btn_cols = st.columns([1, 1, 3])
            with btn_cols[0]:
                if can_edit:
                    if st.button("Confirm All", key="confirm_all_btn"):
                        try:
                            manager.confirm_all_detections(st.session_state.current_session_id)
                            st.rerun()
                        except (ValueError, KeyError) as e:
                            st.error(str(e))

            with btn_cols[1]:
                if st.button(
                    "Apply Depersonalization",
                    disabled=not can_depersonalize,
                    type="primary",
                    key="depersonalize_btn",
                ):
                    if not can_depersonalize:
                        st.warning("No detections confirmed. Confirm at least one PII item before applying.")
                    else:
                        try:
                            with st.spinner("Applying depersonalization..."):
                                manager.apply_depersonalization(st.session_state.current_session_id)
                            st.session_state.depersonalization_complete = True
                            st.rerun()
                        except ValueError as e:
                            st.warning(str(e))
                        except KeyError:
                            st.error("Session not found.")
                            _reset_session()

            if not can_depersonalize and can_edit:
                st.caption("Confirm at least one detection to enable depersonalization.")

            st.divider()

            # Two-panel layout
            left_col, right_col = st.columns([2, 1])

            with left_col:
                st.markdown("##### Document Preview")
                st.markdown("**Original text** with PII highlighted:")
                highlighted_html = _build_highlighted_safe(
                    original_text,
                    [
                        (pos["start"], pos["end"],
                         CATEGORY_COLORS.get(d["category"], "#E0E0E0"),
                         d.get("placeholder", d["category"]),
                         d["category"])
                        for d in detections
                        for pos in d["positions"]
                    ]
                )
                st.markdown(highlighted_html, unsafe_allow_html=True)

                # Color legend
                categories_present = sorted(set(d["category"] for d in detections))
                legend_items = [
                    f'<span style="background-color: {CATEGORY_COLORS.get(cat, "#E0E0E0")}; '
                    f'padding: 2px 6px; border-radius: 3px; margin-right: 8px; '
                    f'font-size: 0.85em;">{cat}</span>'
                    for cat in categories_present
                ]
                st.markdown(" ".join(legend_items), unsafe_allow_html=True)

            # Scrollable detection sidebar with compact cards
            with right_col:
                st.markdown("##### Detections")
                with st.container(height=500):
                    for det in detections:
                        color = CATEGORY_COLORS.get(det["category"], "#E0E0E0")
                        st.markdown(
                            f'<span style="background-color: {color}; padding: 2px 6px; '
                            f'border-radius: 3px; font-size: 0.85em; font-weight: bold;">'
                            f'{det["category"]}</span> '
                            f'`{det["original_value"]}` → `{det.get("placeholder", "N/A")}` '
                            f'({det["confidence"]:.0%})',
                            unsafe_allow_html=True,
                        )
                        if can_edit:
                            status_options = ["pending", "confirmed", "rejected"]
                            current_status = det.get("status", "pending")
                            current_idx = (
                                status_options.index(current_status)
                                if current_status in status_options
                                else 0
                            )
                            new_status = st.selectbox(
                                f"Status for {det['id']}",
                                options=status_options,
                                index=current_idx,
                                key=f"det_status_{det['id']}",
                                label_visibility="collapsed",
                            )
                            if new_status != current_status:
                                try:
                                    manager.update_detection_status(
                                        st.session_state.current_session_id,
                                        det["id"],
                                        new_status,
                                    )
                                    st.rerun()
                                except (ValueError, KeyError) as e:
                                    st.error(str(e))
                        else:
                            st.markdown(
                                f"**Status:** {det.get('status', 'pending').title()}"
                            )
                        st.divider()

# ── Tab 3: Response Input ────────────────────────────────────────────────────

with tab_response:
    status_info = _get_status_info()
    session = _get_session()

    if not status_info or status_info["status"] in ("user_input", "analyzed"):
        st.info("Depersonalize your text first (see the Review tab), then paste the LLM response here.")
    elif status_info["status"] in ("awaiting_response", "repersonalized"):
        # Response already loaded — show read-only
        response_text = session.get("response_text", "")
        st.success("Response loaded. See the **Results** tab for the repersonalized output.")
        st.text_area(
            "LLM response (loaded)",
            value=response_text,
            height=200,
            disabled=True,
            key="response_readonly",
        )
    else:
        # status is "depersonalized" — active response input
        detections = session.get("pii_detections", [])
        dep_text = session.get("depersonalized_text", "")

        # Reference Panel: placeholder map
        with st.expander("Your placeholder map (for reference when reading the LLM response)", expanded=True):
            confirmed = [d for d in detections if d.get("status") == "confirmed"]
            if confirmed:
                map_lines = []
                for d in confirmed:
                    map_lines.append(f"`{d['placeholder']}` → {d['original_value']}")
                st.markdown(" | ".join(map_lines))
            else:
                st.caption("No confirmed placeholders.")

        # Response input area
        st.markdown("**Paste the response from your LLM that contains the placeholders above.**")
        response_input = st.text_area(
            "LLM Response",
            height=300,
            key="response_text_input",
            placeholder="Paste the LLM response here...",
        )

        response_file = st.file_uploader(
            "Or upload a response file",
            type=["txt", "md"],
            key="response_file_upload",
            help="Accepted formats: .txt, .md",
        )

        response_file_text = None
        if response_file is not None:
            try:
                response_file_text = response_file.read().decode("utf-8")
            except UnicodeDecodeError:
                try:
                    response_file.seek(0)
                    response_file_text = response_file.read().decode("latin-1")
                except Exception:
                    st.error("Could not read the uploaded file.")

        effective_response = response_file_text if response_file_text else response_input

        # Depersonalized text reference
        with st.expander("Depersonalized text you sent (for reference)", expanded=False):
            st.code(dep_text, language=None)

        # Repersonalize button
        repersonalize_disabled = not effective_response or not effective_response.strip()
        if st.button("Repersonalize", disabled=repersonalize_disabled, type="primary", key="repersonalize_btn"):
            try:
                with st.spinner("Loading response and repersonalizing..."):
                    sid = st.session_state.current_session_id

                    if response_file is not None and response_file_text:
                        ext = os.path.splitext(response_file.name)[1]
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=ext, delete=False, encoding="utf-8"
                        ) as tmp:
                            tmp.write(response_file_text)
                            tmp_path = tmp.name
                        try:
                            manager.load_response_file(sid, tmp_path)
                        finally:
                            os.unlink(tmp_path)
                    else:
                        manager.load_response_text(sid, effective_response)

                    result = manager.apply_repersonalization(sid)
                    st.session_state.repersonalization_result = result

                st.rerun()
            except ValueError as e:
                st.warning(str(e))
            except KeyError:
                st.error("Session not found.")
                _reset_session()

# ── Tab 4: Repersonalization Review ──────────────────────────────────────────

with tab_results:
    status_info = _get_status_info()
    session = _get_session()

    if not status_info or status_info["status"] != "repersonalized":
        st.info("Load an LLM response in the **Response** tab first.")
    else:
        detections = session.get("pii_detections", [])
        repersonalized_text = session.get("repersonalized_text", "")
        unmatched_placeholders = session.get("unmatched_placeholders", [])

        # Get the repersonalization result for detailed info
        rep_result = st.session_state.repersonalization_result
        if rep_result is None:
            # Reconstruct minimal info from session data
            confirmed = [d for d in detections if d.get("status") == "confirmed"]
            total = len(confirmed)
            unmatched_count = len(unmatched_placeholders)
            matched_count = total - unmatched_count
            if total == 0:
                match_summary = "No placeholders to match"
            elif matched_count == total:
                match_summary = f"{matched_count}/{total} placeholders matched and restored"
            else:
                unmatched_names = ", ".join(unmatched_placeholders)
                match_summary = (
                    f"{matched_count}/{total} placeholders matched — "
                    f"{unmatched_count} unmatched: {unmatched_names}"
                )
            matched = []
            unknown_in_text = []
        else:
            match_summary = rep_result.get("match_summary", "")
            matched = rep_result.get("matched", [])
            unmatched_placeholders = rep_result.get("unmatched_from_map", unmatched_placeholders)
            unknown_in_text = rep_result.get("unknown_in_text", [])
            confirmed = [d for d in detections if d.get("status") == "confirmed"]
            total = len(confirmed)
            matched_count = len(matched)

        # Match Summary Banner
        if total > 0 and matched_count == total:
            st.success(f"✓ {match_summary}")
        elif total > 0 and matched_count >= total * 0.5:
            st.warning(f"⚠ {match_summary}")
        elif total > 0:
            st.error(f"⚠ {match_summary}")
        else:
            st.info(match_summary)

        # Warnings Section
        if unmatched_placeholders:
            st.markdown(
                "**The following placeholders were in your session but not found in the LLM response:**"
            )
            for ph in unmatched_placeholders:
                st.markdown(f"- `{ph}`")

        if unknown_in_text:
            st.markdown(
                "**The following placeholder-like tokens were found in the response "
                "but aren't in your session map:**"
            )
            for token in unknown_in_text:
                st.markdown(f"- `{token}`")

        # Document Preview with Tab 4 highlight style
        st.markdown("##### Repersonalized Text")
        highlighted_repersonalized = _build_repersonalized_highlight(
            repersonalized_text, detections
        )
        st.markdown(highlighted_repersonalized, unsafe_allow_html=True)

        # Copy / Export
        st.divider()
        st.markdown("**Copy the final text below**")
        st.code(repersonalized_text, language=None)

        st.download_button(
            "Download as .txt",
            data=repersonalized_text,
            file_name="repersonalized_output.txt",
            mime="text/plain",
            key="download_repersonalized",
        )

# ── Status Bar ────────────────────────────────────────────────────────────────

st.divider()
status_info = _get_status_info()
if status_info:
    sb_cols = st.columns(5)
    with sb_cols[0]:
        st.caption(f"Session: #{status_info['session_id']}")
    with sb_cols[1]:
        source = status_info["source_format"]
        filename = status_info.get("source_filename")
        source_label = filename if filename else source
        st.caption(f"Source: {source_label}")
    with sb_cols[2]:
        det_count = status_info["detection_count"]
        c = status_info["confirmed_count"]
        r = status_info["rejected_count"]
        p = status_info["pending_count"]
        if det_count > 0:
            st.caption(f"{det_count} detections ({c} confirmed, {r} rejected, {p} pending)")
        else:
            st.caption("No detections")
    with sb_cols[3]:
        # Match info after repersonalization
        if status_info["status"] == "repersonalized":
            rep_result = st.session_state.repersonalization_result
            if rep_result:
                matched_count = len(rep_result.get("matched", []))
                total_map = matched_count + len(rep_result.get("unmatched_from_map", []))
                st.caption(f"Matched: {matched_count}/{total_map}")
            else:
                st.caption("Repersonalized")
        else:
            st.caption("")
    with sb_cols[4]:
        st.caption(f"State: {STATUS_LABELS.get(status_info['status'], status_info['status'])}")
else:
    st.caption("No session active")

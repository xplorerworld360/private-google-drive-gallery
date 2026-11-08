import re
import streamlit as st

from backend.access import AccessControl

user = st.session_state.get("gallery_user")
if not user or not user.get("can_manage_users"):
    st.error("You do not have permission to manage gallery access.")
    st.stop()

access = AccessControl()

st.markdown("""
<div class="glass-hero">
  <div class="eyebrow">OWNER CONTROLS</div>
  <div class="hero-title">Access Management</div>
  <div class="hero-copy">Invite people by Gmail address and decide what they can do in the shared gallery.</div>
</div>
""", unsafe_allow_html=True)

st.info("This is an access-only admin panel. It does not upload, create, rename or delete gallery media.")

owner_mode = user["role"] == "owner"

with st.container(border=True):
    st.subheader("Grant gallery access")
    with st.form("add_gallery_user", clear_on_submit=True):
        email = st.text_input("Google account Gmail", placeholder="person@gmail.com")
        if owner_mode:
            role_label = st.selectbox(
                "Privileges",
                ["Viewer · view only", "Downloader · view and download", "Access manager · manage users"],
            )
            role = {
                "Viewer · view only": "viewer",
                "Downloader · view and download": "downloader",
                "Access manager · manage users": "access_admin",
            }[role_label]
        else:
            role_label = st.selectbox(
                "Privileges",
                ["Viewer · view only", "Downloader · view and download"],
            )
            role = "viewer" if role_label.startswith("Viewer") else "downloader"

        submitted = st.form_submit_button("Grant access", type="primary", use_container_width=True)
        if submitted:
            normalized = email.strip().lower()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
                st.error("Enter a valid Gmail or Google account email.")
            else:
                try:
                    access.add_or_update_user(user["email"], normalized, role)
                    st.success(f"Access granted to {normalized}.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

st.divider()
st.subheader("People with access")
try:
    registry = access.load_registry(force=True)
except Exception as exc:
    st.error("Could not read the access registry.")
    st.exception(exc)
    st.stop()

records = list(registry.get("users", {}).values())
records.sort(key=lambda item: item.get("email", "").casefold())

active_count = sum(1 for item in records if item.get("active"))
revoked_count = len(records) - active_count
m1, m2, m3 = st.columns(3)
m1.metric("Invited accounts", len(records))
m2.metric("Active", active_count)
m3.metric("Revoked", revoked_count)

if not records:
    st.info("No users have been added yet. Add a Gmail address above to get started.")
else:
    search = st.text_input("Filter users", placeholder="Search by Gmail address…")
    if search.strip():
        term = search.strip().casefold()
        records = [item for item in records if term in item.get("email", "").casefold()]

    for record in records:
        email = record.get("email", "")
        role = record.get("role", "viewer")
        active = record.get("active", False)
        role_label = {
            "viewer": "Viewer · view only",
            "downloader": "Downloader · view + download",
            "access_admin": "Access manager",
        }.get(role, role)
        with st.container(border=True):
            left, mid, right = st.columns([2.3, 1.35, 1.2])
            with left:
                st.write(email)
                st.caption(f"{role_label} · Added by {record.get('added_by', 'owner')}")
            with mid:
                st.markdown("🟢 Active" if active else "⚪ Access revoked")
            with right:
                with st.popover("Manage", use_container_width=True):
                    if owner_mode or role != "access_admin":
                        available = ["viewer", "downloader"]
                        if owner_mode:
                            available.append("access_admin")
                        role_labels = {
                            "viewer": "Viewer",
                            "downloader": "Downloader",
                            "access_admin": "Access manager",
                        }
                        default = role if role in available else "viewer"
                        new_role = st.selectbox(
                            "Privileges",
                            available,
                            index=available.index(default),
                            format_func=lambda value: role_labels[value],
                            key=f"role_{email}",
                        )
                        if st.button("Save privileges", key=f"save_role_{email}", use_container_width=True):
                            try:
                                access.add_or_update_user(user["email"], email, new_role)
                                st.success("Privileges updated.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                    if active:
                        if st.button("Revoke access", key=f"revoke_{email}", use_container_width=True):
                            try:
                                access.set_user_active(user["email"], email, False)
                                st.success("Access revoked.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                    else:
                        if st.button("Restore access", key=f"restore_{email}", use_container_width=True):
                            try:
                                access.set_user_active(user["email"], email, True)
                                st.success("Access restored.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                    confirm = st.checkbox("Confirm permanent removal", key=f"confirm_remove_{email}")
                    if st.button("Remove user record", key=f"remove_{email}", disabled=not confirm, use_container_width=True):
                        try:
                            access.remove_user_record(user["email"], email)
                            st.success("User record removed.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

st.divider()
st.caption("The gallery owner always has full access. Access managers can add or revoke Viewer and Downloader accounts, but only the owner can appoint another Access Manager.")

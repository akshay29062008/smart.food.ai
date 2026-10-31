"""
Annapurna Community Platform — Main Application Entrypoint
Simple, friendly website connecting Canteens, Restaurants, and Charities in India.
Named after Goddess Annapurna — ensuring no one sleeps hungry.
"""

import os
import sys
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import DB_PATH, init_database, get_platform_overview_stats
from data.seed import seed_demo_data
from auth import init_session, is_authenticated, get_current_user, logout_user
from components.styles import apply_theme
from components.translations import (
    LANGUAGE_OPTIONS,
    get_current_language_label,
    set_current_language,
    t,
)

# Views
from views.landing import render_landing_page
from views.auth_view import render_auth_view
from views.canteen_dashboard import render_canteen_dashboard
from views.ngo_dashboard import render_ngo_dashboard
from views.profile_view import render_profile_view


def render_top_header() -> None:
    """
    Renders top header across all views:
    Left: Touchable Logo returning to Home
    Right: Comprehensive Language Selector with all major Indian languages.
    """
    with st.container():
        col_logo, col_lang = st.columns([3.2, 1.8], vertical_alignment="center")
        with col_logo:
            st.markdown("""
                <a href="?nav=home" target="_self" class="touchbar-logo-brand" title="अन्नपूर्णा - Tap to return Home">
                    <span class="touchbar-logo-title">अन्नपूर्णा</span>
                    <span class="touchbar-logo-motto">« अन्नदानं महादानम् »</span>
                </a>
            """, unsafe_allow_html=True)
        with col_lang:
            curr_label = get_current_language_label()
            idx = LANGUAGE_OPTIONS.index(curr_label) if curr_label in LANGUAGE_OPTIONS else 0

            def _on_lang_change():
                val = st.session_state.get("top_lang_selector")
                if val:
                    set_current_language(val)

            st.selectbox(
                "🌐 Select Language / भाषा चुनें",
                options=LANGUAGE_OPTIONS,
                index=idx,
                key="top_lang_selector",
                on_change=_on_lang_change,
                label_visibility="collapsed",
            )
        st.markdown("<hr style='margin: 0.2rem 0 1.2rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Annapurna — Stop Food Waste & Feed People",
        page_icon="🍲",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Apply friendly CSS theme & hide Deploy / default Streamlit buttons
    apply_theme()

    # Initialize database & run any pending schema migrations
    init_database(DB_PATH)
    if not os.path.exists(DB_PATH):
        seed_demo_data(DB_PATH)

    # Initialize user session
    init_session()
    user = get_current_user()

    # Query param navigation check (tap logo anywhere to return home)
    if "nav" in st.query_params:
        target = str(st.query_params.get("nav", "")).lower()
        if target == "home":
            st.session_state["guest_nav"] = "🏠 Home"
            st.session_state["side_seg"] = "🏠 Home"
            if is_authenticated():
                if user and user.get("role") in ["canteen", "restaurant"]:
                    st.session_state["portal_nav"] = "📋 Kitchen Dashboard & Planner"
                else:
                    st.session_state["portal_nav"] = "🤝 Charity Dashboard & Food Booking"
            st.query_params.clear()
            st.rerun()
        elif target in ["login", "signin", "signup", "auth"]:
            st.session_state["guest_nav"] = "🔐 Sign In / Sign Up"
            st.session_state["side_seg"] = "🔐 Sign In / Sign Up"
            st.query_params.clear()
            st.rerun()

    # Initialize touch bar navigation state
    if "guest_nav" not in st.session_state:
        st.session_state["guest_nav"] = "🏠 Home"
    if "side_seg" not in st.session_state:
        st.session_state["side_seg"] = st.session_state["guest_nav"]

    def sync_from_side():
        val = st.session_state.get("side_seg", "🏠 Home")
        st.session_state["guest_nav"] = val

    # Sidebar
    with st.sidebar:
        # Touchable sidebar logo returning to Home
        st.markdown(f"""
            <a href="?nav=home" target="_self" class="sidebar-logo-link" title="अन्नपूर्णा">
                <div style="text-align: center; padding: 0.5rem 0 0.3rem 0;">
                    <div class="sidebar-hindi-brand">अन्नपूर्णा</div>
                    <div class="sidebar-motto">« अन्नदानं महादानम् »</div>
                    <p style="color: #059669; font-size: 0.82rem; margin-top: 0.35rem; font-weight: 600;">
                        {t("tagline")}
                    </p>
                </div>
            </a>
            <hr style="margin: 0.5rem 0 0.9rem 0; border: none; border-top: 1px solid #E2E8F0;">
        """, unsafe_allow_html=True)

        if not is_authenticated():
            st.segmented_control(
                "Sidebar Touch Bar",
                options=["🏠 Home", "🔐 Sign In / Sign Up"],
                key="side_seg",
                required=True,
                on_change=sync_from_side,
                label_visibility="collapsed"
            )
            menu = st.session_state.get("guest_nav", "🏠 Home")

            st.markdown("<hr style='margin: 1.2rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

            # Quick live community stats
            stats = get_platform_overview_stats()
            st.markdown(f"##### {t('sidebar_stats_title')}")
            st.markdown(f"• **{t('kpi_meals_title')}:** `{stats['portions_rescued']:,} {t('plates_unit')}`")
            st.markdown(f"• **{t('kpi_food_title')}:** `{stats['kg_diverted']:,.0f} kg`")
            st.markdown(f"• **{t('kpi_air_title')}:** `{stats['co2_avoided']:,.0f} kg`")
            st.markdown(f"• **{t('extra_food_title')}:** `{stats['active_surplus']} {t('plates_unit')}`")

            st.markdown("<hr style='margin: 1.2rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

            # Simple Footer
            st.markdown("""
                <div style="font-size: 0.75rem; color: #64748B; text-align: center;">
                    Annapurna Initiative<br>
                    Connecting kitchens and local charities.
                </div>
            """, unsafe_allow_html=True)

        else:
            # User profile pill in sidebar
            role_label = (
                "Campus Canteen" if user["role"] == "canteen" 
                else ("Restaurant Kitchen" if user["role"] == "restaurant" else "Local Charity / Shelter")
            )
            role_class = (
                "role-canteen" if user["role"] == "canteen" 
                else ("role-restaurant" if user["role"] == "restaurant" else "role-ngo")
            )

            fssai_sidebar = (
                f"<div style='margin-top: 6px; font-size: 0.76rem; color: #0369A1; font-weight: 600; background: #E0F2FE; border-radius: 4px; padding: 2px 6px; display: inline-block;'>🛡️ FSSAI: {user['fssai_no']}</div>"
                if user.get("fssai_no")
                else ""
            )

            st.markdown(f"""
                <div style="background: #F1F5F9; border-radius: 10px; padding: 0.9rem; margin-bottom: 1rem; border: 1px solid #CBD5E1;">
                    <span class="role-pill {role_class}">{role_label}</span>
                    <h4 style="margin: 0.4rem 0 0.1rem 0; color: #0F172A; font-size: 1.05rem;">{user['org_name']}</h4>
                    <p style="margin: 0; font-size: 0.8rem; color: #475569;">Logged in as <b>{user['name']}</b></p>
                    {fssai_sidebar}
                </div>
            """, unsafe_allow_html=True)

            # Navigation tailored to role
            if user["role"] in ["canteen", "restaurant"]:
                nav_options = [
                    "📋 Kitchen Dashboard & Planner",
                    "⚙️ Kitchen Profile & Settings"
                ]
            else:
                nav_options = [
                    "🤝 Charity Dashboard & Food Booking",
                    "⚙️ Charity Profile & Settings"
                ]

            menu = st.radio("Portal Navigation", options=nav_options, index=0, key="portal_nav", label_visibility="collapsed")

            st.markdown("<hr style='margin: 1.2rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

            # Sign Out Button
            if st.button(t("sign_out"), key="sidebar_logout_btn", type="secondary", width="stretch"):
                logout_user()
                st.success("Signed out successfully.")
                st.rerun()

    # Render top header bar (Logo on left, Language Selector on right)
    render_top_header()

    # Route to Views
    if not is_authenticated():
        current_choice = st.session_state.get("guest_nav", "🏠 Home")
        if "Home" in current_choice:
            render_landing_page()
        else:
            render_auth_view()
    else:
        if "Kitchen Dashboard" in menu:
            render_canteen_dashboard()
        elif "Charity Dashboard" in menu:
            render_ngo_dashboard()
        elif "Profile" in menu:
            render_profile_view()


if __name__ == "__main__":
    main()

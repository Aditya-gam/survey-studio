"""Comprehensive navbar component for Survey Studio using Streamlit Elements.

This module provides a modularized, responsive navbar with Material-UI components
that includes form elements, theme switching, mobile menus, and loading states.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import streamlit as st
from streamlit_elements import elements, mui  # type: ignore

from survey_studio.ui.validation_components import validate_papers_input, validate_topic_input

# Constants for responsive design
MOBILE_BREAKPOINT = 480
TABLET_BREAKPOINT = 768
NAVBAR_HEIGHT = 64
NAVBAR_Z_INDEX = 1300
AUTO_MODEL_LABEL = "Auto (Best Available)"
GPT_3_5_MODEL = "gpt-3.5-turbo"
MAX_PAPERS_ALLOWED = 10
MIN_TOPIC_LENGTH = 3


def initialize_navbar_state() -> None:
    """Initialize navbar-specific session state variables."""
    if "navbar_theme" not in st.session_state:
        st.session_state.navbar_theme = "light"

    if "navbar_loading" not in st.session_state:
        st.session_state.navbar_loading = False

    if "left_drawer_open" not in st.session_state:
        st.session_state.left_drawer_open = False

    if "right_drawer_open" not in st.session_state:
        st.session_state.right_drawer_open = False

    if "navbar_scrolled" not in st.session_state:
        st.session_state.navbar_scrolled = False

    # Form state management
    if "navbar_topic" not in st.session_state:
        st.session_state.navbar_topic = ""

    if "navbar_papers" not in st.session_state:
        st.session_state.navbar_papers = 5

    if "navbar_model" not in st.session_state:
        st.session_state.navbar_model = AUTO_MODEL_LABEL


def get_theme_colors() -> dict[str, Any]:
    """Get theme-based color scheme for the navbar."""
    is_dark = st.session_state.navbar_theme == "dark"

    return {
        "primary": "#1976d2" if not is_dark else "#90caf9",
        "background": {
            "default": "#ffffff" if not is_dark else "#121212",
            "paper": "#f5f5f5" if not is_dark else "#1e1e1e",
            "transparent": "rgba(255, 255, 255, 0.9)" if not is_dark else "rgba(18, 18, 18, 0.9)",
        },
        "text": {
            "primary": "#212121" if not is_dark else "#ffffff",
            "secondary": "#757575" if not is_dark else "#b3b3b3",
        },
        "divider": "#e0e0e0" if not is_dark else "#333333",
    }


def handle_theme_switching() -> None:
    """Handle theme switching between light, dark, and system preference."""
    current_theme = st.session_state.navbar_theme

    # Cycle through: light -> dark -> system -> light
    if current_theme == "light":
        st.session_state.navbar_theme = "dark"
    elif current_theme == "dark":
        st.session_state.navbar_theme = "system"
    else:  # system
        st.session_state.navbar_theme = "light"


def get_effective_theme() -> str:
    """Get the effective theme considering system preference."""
    if st.session_state.navbar_theme == "system":
        # For now, default to light. In a real implementation,
        # you might want to detect system preference via JS
        return "light"
    return st.session_state.navbar_theme


def manage_loading_states(is_loading: bool) -> None:
    """Manage loading states for the navbar components."""
    st.session_state.navbar_loading = is_loading


def render_theme_toggle() -> None:
    """Render theme toggle button."""
    theme_icons = {
        "light": "LightMode",
        "dark": "DarkMode",
        "system": "Settings",
    }

    current_theme = st.session_state.navbar_theme
    icon_name = theme_icons.get(current_theme, "LightMode")

    with mui.Tooltip(title=f"Theme: {current_theme.title()}"):
        mui.IconButton(
            getattr(mui.icon, icon_name, mui.icon.LightMode)(),
            onClick=handle_theme_switching,
            color="inherit",
            sx={"ml": 1, "display": {"xs": "none", "md": "flex"}},
        )


def render_desktop_form_elements() -> None:
    """Render form elements for desktop layout."""
    colors = get_theme_colors()
    is_loading = st.session_state.navbar_loading

    # Research Topic Input
    mui.TextField(
        label="Research Topic",
        placeholder="e.g., transformer architectures, quantum computing",
        value=st.session_state.navbar_topic,
        onChange=lambda e: setattr(st.session_state, "navbar_topic", e.target.value),
        disabled=is_loading,
        variant="outlined",
        size="small",
        sx={
            "width": "30%",
            "mr": 2,
            "display": {"xs": "none", "md": "flex"},
            "& .MuiOutlinedInput-root": {
                "backgroundColor": colors["background"]["paper"],
            },
        },
        InputProps={"startAdornment": mui.InputAdornment(mui.icon.Search(), position="start")},
    )

    # Papers Slider Container
    with mui.Box(
        sx={
            "width": "15%",
            "mr": 2,
            "display": {"xs": "none", "md": "flex"},
            "flexDirection": "column",
            "justifyContent": "center",
        }
    ):
        mui.Typography(
            "Papers", variant="caption", sx={"color": colors["text"]["secondary"], "mb": 0.5}
        )
        mui.Slider(
            value=st.session_state.navbar_papers,
            onChange=lambda _, value: setattr(  # type: ignore
                st.session_state, "navbar_papers", value
            ),
            min=1,
            max=MAX_PAPERS_ALLOWED,
            step=1,
            marks=True,
            valueLabelDisplay="auto",
            disabled=is_loading,
            size="small",
            sx={
                "color": colors["primary"],
                "& .MuiSlider-thumb": {
                    "width": 16,
                    "height": 16,
                },
            },
        )

    # Model Selection
    mui.Select(
        value=st.session_state.navbar_model,
        onChange=lambda e: setattr(st.session_state, "navbar_model", e.target.value),
        disabled=is_loading,
        size="small",
        variant="outlined",
        displayEmpty=True,
        sx={
            "width": "20%",
            "mr": 2,
            "display": {"xs": "none", "md": "flex"},
            "& .MuiOutlinedInput-root": {
                "backgroundColor": colors["background"]["paper"],
            },
        },
        startAdornment=mui.InputAdornment(mui.icon.Psychology(), position="start"),
    )(
        mui.MenuItem(AUTO_MODEL_LABEL, value=AUTO_MODEL_LABEL),
        mui.MenuItem("gpt-4o-mini", value="gpt-4o-mini"),
        mui.MenuItem("gpt-4o", value="gpt-4o"),
        mui.MenuItem(GPT_3_5_MODEL, value=GPT_3_5_MODEL),
    )


def render_search_button(on_search_click: Callable[[], None] | None = None) -> None:
    """Render the search button with loading states."""
    colors = get_theme_colors()
    is_loading = st.session_state.navbar_loading

    button_text = "Searching..." if is_loading else "Search"
    button_icon = mui.icon.HourglassEmpty() if is_loading else mui.icon.Search()
    button_color = "grey" if is_loading else "primary"

    mui.Button(
        button_text,
        variant="contained",
        color=button_color,
        disabled=is_loading,
        onClick=on_search_click,
        startIcon=button_icon,
        sx={
            "width": {"xs": "100%", "md": "10%"},
            "minWidth": "120px",
            "height": "40px",
            "backgroundColor": colors["primary"] if not is_loading else colors["text"]["secondary"],
            "&:hover": {
                "backgroundColor": colors["primary"]
                if not is_loading
                else colors["text"]["secondary"],
                "opacity": 0.8,
            },
        },
    )


def render_mobile_hamburger_left() -> None:
    """Render left hamburger menu for mobile."""
    mui.IconButton(
        mui.icon.Menu(),
        onClick=lambda: setattr(st.session_state, "left_drawer_open", True),
        color="inherit",
        sx={
            "display": {"xs": "flex", "md": "none"},
            "mr": 1,
        },
    )


def render_mobile_hamburger_right() -> None:
    """Render right hamburger menu for mobile."""
    mui.IconButton(
        mui.icon.MoreVert(),
        onClick=lambda: setattr(st.session_state, "right_drawer_open", True),
        color="inherit",
        sx={
            "display": {"xs": "flex", "md": "none"},
            "ml": 1,
        },
    )


def render_left_drawer(on_search_click: Callable[[], None] | None = None) -> None:
    """Render left sliding drawer with main form elements."""
    colors = get_theme_colors()
    is_loading = st.session_state.navbar_loading

    with mui.Drawer(
        open=st.session_state.left_drawer_open,
        onClose=lambda: setattr(st.session_state, "left_drawer_open", False),
        anchor="left",
        sx={
            "& .MuiDrawer-paper": {
                "width": "300px",
                "backgroundColor": colors["background"]["paper"],
                "padding": "20px",
            }
        },
    ):
        # Drawer Header
        with mui.Box(sx={"display": "flex", "alignItems": "center", "mb": 3}):
            mui.Typography(
                "📚 Survey Studio",
                variant="h6",
                sx={"flexGrow": 1, "color": colors["text"]["primary"]},
            )
            mui.IconButton(
                mui.icon.Close(),
                onClick=lambda: setattr(st.session_state, "left_drawer_open", False),
                color="inherit",
            )

        # Form Elements (Mobile)
        mui.TextField(
            label="Research Topic",
            placeholder="Enter research topic",
            value=st.session_state.navbar_topic,
            onChange=lambda e: setattr(st.session_state, "navbar_topic", e.target.value),
            disabled=is_loading,
            fullWidth=True,
            variant="outlined",
            sx={"mb": 3},
            InputProps={"startAdornment": mui.InputAdornment(mui.icon.Search(), position="start")},
        )

        # Papers Selection (Mobile - as Select instead of Slider)
        mui.Select(
            value=st.session_state.navbar_papers,
            onChange=lambda e: setattr(st.session_state, "navbar_papers", e.target.value),
            disabled=is_loading,
            fullWidth=True,
            variant="outlined",
            displayEmpty=True,
            sx={"mb": 3},
            label="Number of Papers",
        )(
            *[
                mui.MenuItem(f"{i} paper{'s' if i > 1 else ''}", value=i)
                for i in range(1, MAX_PAPERS_ALLOWED + 1)
            ]
        )

        # Model Selection (Mobile)
        mui.Select(
            value=st.session_state.navbar_model,
            onChange=lambda e: setattr(st.session_state, "navbar_model", e.target.value),
            disabled=is_loading,
            fullWidth=True,
            variant="outlined",
            displayEmpty=True,
            sx={"mb": 3},
            label="AI Model",
        )(
            mui.MenuItem(AUTO_MODEL_LABEL, value=AUTO_MODEL_LABEL),
            mui.MenuItem("gpt-4o-mini", value="gpt-4o-mini"),
            mui.MenuItem("gpt-4o", value="gpt-4o"),
            mui.MenuItem(GPT_3_5_MODEL, value=GPT_3_5_MODEL),
        )

        # Search Button (Mobile)
        render_search_button(on_search_click)

        # Validation Status (Mobile)
        render_mobile_validation_status()


def render_right_drawer() -> None:
    """Render right sliding drawer with advanced options."""
    colors = get_theme_colors()

    with mui.Drawer(
        open=st.session_state.right_drawer_open,
        onClose=lambda: setattr(st.session_state, "right_drawer_open", False),
        anchor="right",
        sx={
            "& .MuiDrawer-paper": {
                "width": "350px",
                "backgroundColor": colors["background"]["paper"],
                "padding": "20px",
            }
        },
    ):
        # Drawer Header
        with mui.Box(sx={"display": "flex", "alignItems": "center", "mb": 3}):
            mui.IconButton(
                mui.icon.Close(),
                onClick=lambda: setattr(st.session_state, "right_drawer_open", False),
                color="inherit",
            )
            mui.Typography(
                "Advanced Options",
                variant="h6",
                sx={"flexGrow": 1, "color": colors["text"]["primary"], "textAlign": "center"},
            )

        # Theme Switching
        with mui.Box(sx={"mb": 3}):
            mui.Typography("Theme", variant="subtitle2", sx={"mb": 1})
            with mui.ButtonGroup(fullWidth=True, variant="outlined"):
                for theme in ["light", "dark", "system"]:
                    mui.Button(
                        theme.title(),
                        onClick=lambda t=theme: setattr(st.session_state, "navbar_theme", t),
                        variant="contained"
                        if st.session_state.navbar_theme == theme
                        else "outlined",
                        size="small",
                    )

        # About Section
        with mui.Accordion(sx={"mb": 2}):
            mui.AccordionSummary(
                mui.icon.ExpandMore(), children=[mui.Typography("About", variant="subtitle2")]
            )
            mui.AccordionDetails(
                mui.Typography(
                    (
                        "Survey Studio helps researchers synthesize literature with AI agents. "
                        "It searches arXiv for relevant papers and creates structured reviews."
                    ),
                    variant="body2",
                )
            )

        # Troubleshooting Section
        with mui.Accordion(sx={"mb": 2}):
            mui.AccordionSummary(
                mui.icon.ExpandMore(),
                children=[mui.Typography("Troubleshooting", variant="subtitle2")],
            )
            mui.AccordionDetails(
                mui.Typography(
                    (
                        "• Ensure API keys are configured\n"
                        + "• Try fewer papers or simpler topics\n"
                        + "• Check model/service status\n"
                        + "• Review validation messages"
                    ),
                    variant="body2",
                    sx={"whiteSpace": "pre-line"},
                )
            )

        # Development Mode Validation
        if os.getenv("ENV") == "development":
            render_development_validation()


def render_mobile_validation_status() -> None:
    """Render validation status in mobile drawer."""
    colors = get_theme_colors()

    # Topic validation
    topic_valid = len(st.session_state.navbar_topic.strip()) >= MIN_TOPIC_LENGTH
    topic_icon = mui.icon.CheckCircle() if topic_valid else mui.icon.Error()
    topic_color = "success" if topic_valid else "error"

    # Papers validation
    papers_valid = 1 <= st.session_state.navbar_papers <= MAX_PAPERS_ALLOWED
    papers_icon = mui.icon.CheckCircle() if papers_valid else mui.icon.Error()
    papers_color = "success" if papers_valid else "error"

    with mui.Box(sx={"mt": 3, "pt": 2, "borderTop": f"1px solid {colors['divider']}"}):
        mui.Typography("Validation Status", variant="subtitle2", sx={"mb": 2})

        # Topic Status
        with mui.Box(sx={"display": "flex", "alignItems": "center", "mb": 1}):
            mui.Icon(topic_icon, color=topic_color, sx={"mr": 1})
            mui.Typography(
                f"Topic: {'Valid' if topic_valid else 'Too short'}",
                variant="caption",
                color=topic_color,
            )

        # Papers Status
        with mui.Box(sx={"display": "flex", "alignItems": "center", "mb": 1}):
            mui.Icon(papers_icon, color=papers_color, sx={"mr": 1})
            mui.Typography(
                f"Papers: {'Valid' if papers_valid else 'Out of range'}",
                variant="caption",
                color=papers_color,
            )


def render_development_validation() -> None:
    """Render validation messages for development mode."""
    colors = get_theme_colors()

    with mui.Box(sx={"mt": 3, "pt": 2, "borderTop": f"1px solid {colors['divider']}"}):
        mui.Typography("Validation (Dev Mode)", variant="subtitle2", sx={"mb": 2})

        # Topic validation
        if st.session_state.navbar_topic:
            helper_text, state = validate_topic_input(st.session_state.navbar_topic)
            validation_color = "success" if state == "valid" else "error"

            mui.Alert(helper_text, severity=validation_color, sx={"mb": 1, "fontSize": "0.75rem"})

        # Papers validation
        helper_text, state = validate_papers_input(st.session_state.navbar_papers)
        validation_color = "success" if state == "valid" else "error"

        mui.Alert(helper_text, severity=validation_color, sx={"mb": 1, "fontSize": "0.75rem"})


def handle_responsive_behavior() -> dict[str, Any]:
    """Handle responsive design behavior and return appropriate styles."""
    return {
        "appbar": {
            "position": "fixed",
            "width": "100%",
            "height": f"{NAVBAR_HEIGHT}px",
            "zIndex": NAVBAR_Z_INDEX,
            "backgroundColor": get_theme_colors()["background"]["transparent"]
            if st.session_state.navbar_scrolled
            else get_theme_colors()["background"]["default"],
            "backdropFilter": "blur(10px)" if st.session_state.navbar_scrolled else "none",
            "transition": "all 0.3s ease",
            "borderBottom": f"1px solid {get_theme_colors()['divider']}",
        },
        "toolbar": {
            "minHeight": f"{NAVBAR_HEIGHT}px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "padding": "0 24px",
        },
    }


def render_navbar(on_search_click: Callable[[], None] | None = None) -> None:
    """Main navbar component with comprehensive functionality."""
    # Initialize state
    initialize_navbar_state()

    # Get responsive styles
    styles = handle_responsive_behavior()
    colors = get_theme_colors()

    navbar_elements = elements("navbar")
    if navbar_elements is None:
        return

    with navbar_elements:
        # Main AppBar
        with mui.AppBar(sx=styles["appbar"]):  # noqa: SIM117
            with mui.Toolbar(sx=styles["toolbar"]):
                # Left Section - Mobile hamburger + App name
                with mui.Box(sx={"display": "flex", "alignItems": "center", "flexGrow": 0}):
                    render_mobile_hamburger_left()

                    mui.Typography(
                        "📚 Survey Studio",
                        variant="h6",
                        component="div",
                        sx={
                            "fontWeight": 600,
                            "color": colors["text"]["primary"],
                            "textDecoration": "none",
                            "display": {"xs": "none", "sm": "block"},
                        },
                    )

                # Center Section - Desktop form elements
                with mui.Box(
                    sx={
                        "display": "flex",
                        "alignItems": "center",
                        "flexGrow": 1,
                        "justifyContent": "center",
                        "gap": 2,
                    }
                ):
                    render_desktop_form_elements()

                # Right Section - Search button + theme toggle + mobile hamburger
                with mui.Box(sx={"display": "flex", "alignItems": "center", "flexGrow": 0}):
                    # Desktop search button
                    with mui.Box(sx={"display": {"xs": "none", "md": "block"}}):
                        render_search_button(on_search_click)

                    render_theme_toggle()
                    render_mobile_hamburger_right()

        # Mobile Drawers
        render_left_drawer(on_search_click)
        render_right_drawer()

        # Add spacer for fixed navbar
        mui.Box(sx={"height": f"{NAVBAR_HEIGHT}px"})


def render_mobile_overlays() -> None:
    """Render mobile overlay menus (called separately if needed)."""
    mobile_elements = elements("mobile_overlays")
    if mobile_elements is None:
        return

    with mobile_elements:
        render_left_drawer()
        render_right_drawer()


def get_navbar_form_values() -> tuple[str, int, str]:
    """Get current form values from navbar state."""
    topic = st.session_state.get("navbar_topic", "")
    papers = st.session_state.get("navbar_papers", 5)
    model = st.session_state.get("navbar_model", "Auto (Best Available)")

    # Convert "Auto" selection to None for compatibility
    if model == AUTO_MODEL_LABEL:
        model = "auto"

    return topic, papers, model


def set_navbar_form_values(topic: str = "", papers: int = 5, model: str | None = "auto") -> None:
    """Set form values in navbar state."""
    st.session_state.navbar_topic = topic
    st.session_state.navbar_papers = papers

    # Convert None/auto back to display format
    if model == "auto" or model is None or model == "":
        model = AUTO_MODEL_LABEL
    st.session_state.navbar_model = model


def validate_navbar_inputs() -> tuple[bool, list[str]]:
    """Validate current navbar inputs and return status with error messages."""
    errors: list[str] = []

    # Validate topic
    if (
        not st.session_state.navbar_topic
        or len(st.session_state.navbar_topic.strip()) < MIN_TOPIC_LENGTH
    ):
        errors.append(f"Research topic must be at least {MIN_TOPIC_LENGTH} characters long")

    # Validate papers
    if not (1 <= st.session_state.navbar_papers <= MAX_PAPERS_ALLOWED):
        errors.append(f"Number of papers must be between 1 and {MAX_PAPERS_ALLOWED}")

    # Check API configuration (import here to avoid circular imports)
    try:
        from survey_studio.config import get_best_available_provider

        if not get_best_available_provider():
            errors.append("No AI providers configured - please set up API keys")
    except ImportError:
        errors.append("Configuration module not available")

    return len(errors) == 0, errors


# Scroll detection helper (would typically be implemented with custom JavaScript)
def handle_scroll_detection() -> None:
    """Handle scroll detection for navbar transparency effects.

    Note: This is a placeholder. In a real implementation, you would need
    JavaScript to detect scroll position and update st.session_state.navbar_scrolled
    """
    # This would typically be handled by JavaScript injection
    # For now, we can simulate it or leave it as a manual toggle

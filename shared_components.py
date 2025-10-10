import streamlit as st

def render_footer():
    """Render the footer component that appears on all pages"""
    st.markdown("""
    <style>
    .site-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: var(--background-color);
        padding: 8px 0;
        text-align: center;
        color: #888;
        font-size: 1rem;
        z-index: 999;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        border-top: 1px solid #333;
    }
    .footer-links {
        margin-top: 5px;
    }
    .footer-links a {
        text-decoration: none;
        margin: 0 8px;
    }
    .footer-links img {
        vertical-align: middle;
        filter: invert(1);
    }

    /* Ensure content doesn't get hidden behind footer */
    .main .block-container {
        padding-bottom: 100px !important;
    }
    </style>
    <div class='site-footer'>
        Built with ❤️ by Sara Kaczmarek<br>
        <div class='footer-links'>
            <a href="https://www.linkedin.com/in/sarakaczmarek/" target="_blank">
                <img src="https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/linkedin.svg" width="20" height="20">
            </a>
            <a href="https://github.com/sara-kaczmarek" target="_blank">
                <img src="https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/github.svg" width="20" height="20">
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
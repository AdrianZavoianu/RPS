"""
Modern dark bluish theme stylesheet for RPS application.
Inspired by modern web applications with Tailwind-style design.
"""

from gui.design_tokens import PALETTE

# Legacy color mapping for existing widgets
COLORS = {
    'background': PALETTE['bg_primary'],
    'card': PALETTE['bg_secondary'],
    'border': PALETTE['border_default'],
    'text': PALETTE['text_primary'],
    'text_primary': PALETTE['text_primary'],
    'text_secondary': PALETTE['text_secondary'],
    'muted': PALETTE['text_muted'],
    'accent': PALETTE['accent_primary'],
    'accent_hover': PALETTE['accent_hover'],
    'hover': PALETTE['bg_hover'],
    'selected': PALETTE['accent_selected'],
    'danger': PALETTE['error'],
    'danger_hover': '#b91c1c',
    'success': PALETTE['success'],
    'warning': PALETTE['warning'],
    'warning_bg': '#18130a',
    'red_600': PALETTE['error'],
    'red_700': '#b91c1c',
}

DARK_THEME_STYLESHEET = f"""
/* ==================== GLOBAL STYLES ==================== */
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
    font-weight: 400;
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

/* ==================== TOP HEADER ==================== */
#topHeader {{
    background-color: {COLORS['background']};
    border: none;
    min-height: 80px;
    max-height: 80px;
}}

#headerLogo {{
    margin-right: 8px;
}}

#navButton {{
    background-color: transparent;
    color: {COLORS['muted']};
    border: none;
    padding: 8px 24px;
    border-radius: 0px;
    font-weight: 500;
    font-size: 22px;
    min-width: 100px;
}}

#navButton:hover {{
    color: {COLORS['text']};
    background-color: transparent;
}}

#navButton:checked {{
    color: {COLORS['text']};
    background-color: transparent;
    font-weight: 600;
}}

#navButton:checked:hover {{
    color: {COLORS['text']};
    background-color: transparent;
}}

/* ==================== PAGE TYPOGRAPHY ==================== */
#pageHeadline {{
    font-size: 32px;
    font-weight: 600;
    color: {COLORS['text']};
}}

#pageSubheadline {{
    font-size: 16px;
    color: {COLORS['muted']};
}}

#pageBodyText {{
    font-size: 14px;
    line-height: 1.6;
    color: {COLORS['text']};
}}

#primaryAction {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: 600;
    padding: 12px 28px;
    border-radius: 999px;
    font-size: 15px;
}}

#primaryAction:hover {{
    background-color: {COLORS['accent_hover']};
}}

#secondaryAction {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    font-weight: 600;
    padding: 12px 28px;
    border-radius: 999px;
    font-size: 15px;
}}

#secondaryAction:hover {{
    background-color: {COLORS['hover']};
    border-color: {COLORS['accent']};
    color: {COLORS['accent']};
}}

#ghostAction {{
    background-color: transparent;
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    padding: 10px 20px;
    border-radius: 999px;
    font-weight: 500;
    font-size: 14px;
}}

#ghostAction:hover {{
    border-color: {COLORS['accent']};
    color: {COLORS['accent']};
}}

/* ==================== PROJECT CARDS ==================== */
#projectCard {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    min-width: 220px;
    max-width: 280px;
}}

#projectCard:hover {{
    border-color: {COLORS['accent']};
}}

#cardTitle {{
    font-size: 18px;
    font-weight: 600;
}}

#cardBody {{
    color: {COLORS['muted']};
    line-height: 1.5;
}}

#cardPrimaryAction {{
    background-color: transparent;
    color: {COLORS['accent']};
    border: 1px solid {COLORS['accent']};
    padding: 8px 18px;
    border-radius: 8px;
    font-weight: 500;
}}

#cardPrimaryAction:hover {{
    background-color: rgba(74, 125, 137, 0.1);
}}

#cardPrimaryAction:disabled {{
    border-color: {COLORS['border']};
    color: {COLORS['muted']};
    background-color: transparent;
    opacity: 0.7;
}}

#cardDeleteAction {{
    background-color: transparent;
    border: none;
    color: {COLORS['muted']};
    border-radius: 0px;
    padding: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}

#cardDeleteAction:hover {{
    background-color: {COLORS['hover']};
    color: {COLORS['text']};
}}

#cardDeleteAction:pressed {{
    background-color: {COLORS['hover']};
    color: {COLORS['text']};
}}

#cardStatsContainer {{
    background-color: transparent;
}}

#cardStatLabel {{
    color: {COLORS['muted']};
    font-size: 13px;
}}

#cardStatValue {{
    color: {COLORS['text']};
    font-weight: 600;
}}

#cardDivider {{
    background-color: {COLORS['border']};
    height: 1px;
}}

#cardFooterLabel {{
    color: {COLORS['muted']};
    font-size: 13px;
}}

#cardFooterValue {{
    color: {COLORS['text']};
    font-size: 13px;
}}

#summaryCard {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}

#summaryMetricValue {{
    font-size: 22px;
    font-weight: 600;
    color: {COLORS['text']};
}}

#summaryMetricLabel {{
    color: {COLORS['muted']};
    font-size: 13px;
    font: 13px;
}}

/* ==================== MENU BAR ==================== */
QMenuBar {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 4px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['hover']};
}}

QMenuBar::item:pressed {{
    background-color: {COLORS['accent']};
}}

/* ==================== MENU DROPDOWN ==================== */
QMenu {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['hover']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS['border']};
    margin: 4px 8px;
}}

/* ==================== STATUS BAR ==================== */
QStatusBar {{
    background-color: {COLORS['background']};
    color: {COLORS['muted']};
    border: none;
    padding: 4px 8px;
}}

QStatusBar QLabel {{
    background-color: transparent;
    color: {COLORS['muted']};
}}

/* ==================== BUTTONS ==================== */
/* Primary button (default) - matches GMP primary variant */
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.2s ease;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['muted']};
    opacity: 0.5;
}}

/* Secondary button style - matches GMP secondary variant */
QPushButton[styleClass="secondary"] {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text']};
    font-weight: 500;
}}

QPushButton[styleClass="secondary"]:hover {{
    background-color: {COLORS['background']};
}}

QPushButton[styleClass="secondary"]:pressed {{
    background-color: {COLORS['hover']};
}}

/* Danger button style - matches GMP danger variant */
QPushButton[styleClass="danger"] {{
    background-color: {COLORS['danger']};
    color: white;
    font-weight: 500;
}}

QPushButton[styleClass="danger"]:hover {{
    background-color: {COLORS['danger_hover']};
}}

QPushButton[styleClass="danger"]:pressed {{
    background-color: #c53030;
}}

/* Ghost button style - matches GMP ghost variant */
QPushButton[styleClass="ghost"] {{
    background-color: transparent;
    border: none;
    color: {COLORS['text']};
    font-weight: 500;
}}

QPushButton[styleClass="ghost"]:hover {{
    background-color: rgba(127, 139, 154, 0.2);
}}

QPushButton[styleClass="ghost"]:pressed {{
    background-color: rgba(127, 139, 154, 0.3);
}}

/* Small button size - matches GMP sm size */
QPushButton[size="sm"] {{
    padding: 6px 12px;
    font-size: 13px;
}}

/* Large button size - matches GMP lg size */
QPushButton[size="lg"] {{
    padding: 12px 24px;
    font-size: 16px;
}}

/* ==================== INPUT FIELDS ==================== */
/* Input field styles - matches GMP input-field class */
QLineEdit {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 14px;
    transition: all 0.2s ease;
}}

QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
    outline: none;
    box-shadow: 0 0 0 2px rgba(74, 125, 137, 0.2);
}}

QLineEdit:read-only {{
    background-color: {COLORS['card']};
    color: {COLORS['muted']};
}}

QLineEdit::placeholder {{
    color: {COLORS['muted']};
    font-weight: 400;
}}

/* ==================== COMBO BOX ==================== */
/* Select field styles - matches GMP select-field class */
QComboBox {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 14px;
    min-width: 100px;
    transition: all 0.2s ease;
}}

QComboBox:hover {{
    border-color: {COLORS['accent']};
}}

QComboBox:focus {{
    border: 1px solid {COLORS['accent']};
    outline: none;
    box-shadow: 0 0 0 2px rgba(74, 125, 137, 0.2);
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: url(none);
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {COLORS['text']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    selection-background-color: {COLORS['hover']};
    color: {COLORS['text']};
    padding: 4px;
    font-size: 14px;
}}

/* ==================== TREE WIDGET ==================== */
QTreeWidget {{
    background-color: transparent;
    border: none;
    color: {COLORS['text']};
    outline: none;
    padding: 4px;
}}

QTreeWidget::item {{
    padding: 8px 4px;
    border-radius: 4px;
}}

QTreeWidget::item:hover {{
    background-color: {COLORS['hover']};
}}

QTreeWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

QTreeWidget::branch {{
    background-color: transparent;
}}

QTreeWidget::branch:has-children:closed {{
    image: url(none);
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {COLORS['text']};
}}

QTreeWidget::branch:has-children:open {{
    image: url(none);
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-bottom: 6px solid {COLORS['text']};
}}

QHeaderView {{
    background-color: {COLORS['card']};
}}

QHeaderView::section {{
    background-color: {COLORS['card']};
    color: {COLORS['accent']};
    border: none;
    border-right: 1px solid #1e2329;
    border-bottom: 1px solid #1e2329;
    padding: 4px 4px;
    font-weight: 600;
}}

QHeaderView::section:last {{
    border-right: none;
}}

/* ==================== SCROLL BARS ==================== */
QScrollBar:vertical {{
    background-color: transparent;
    width: 6px;
    border: none;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background-color: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: rgba(255, 255, 255, 0.15);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 6px;
    border: none;
    margin: 2px 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: rgba(255, 255, 255, 0.15);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ==================== SPLITTER ==================== */
QSplitter::handle {{
    background-color: transparent;
    width: 8px;
    height: 8px;
}}

QSplitter::handle:hover {{
    background-color: rgba(255, 255, 255, 0.03);
}}

/* ==================== DIALOG ==================== */
/* Modal styles - matches GMP modal-content class */
QDialog {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
    font-weight: 500;
}}

/* ==================== GROUP BOX ==================== */
QGroupBox {{
    background-color: transparent;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    color: {COLORS['text']};
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: {COLORS['card']};
}}

/* ==================== LABELS ==================== */
QLabel {{
    background-color: transparent;
    color: {COLORS['text']};
    font-size: 14px;
    font-weight: 400;
}}

QLabel[styleClass="header"] {{
    font-size: 18px;
    font-weight: 600;
    color: {COLORS['text']};
    line-height: 1.5;
}}

QLabel[styleClass="subheader"] {{
    font-size: 22px;
    font-weight: 600;
    color: {COLORS['text']};
    line-height: 1.4;
}}

QLabel[styleClass="muted"] {{
    color: {COLORS['muted']};
    font-weight: 400;
}}

QLabel[styleClass="small"] {{
    font-size: 13px;
    color: {COLORS['muted']};
}}

QLabel[styleClass="section"] {{
    font-size: 16px;
    font-weight: 600;
    color: {COLORS['text']};
    line-height: 1.5;
}}

QLabel[styleClass="subsection"] {{
    font-size: 15px;
    font-weight: 600;
    color: {COLORS['text']};
    line-height: 1.5;
}}

/* ==================== TAB WIDGET ==================== */
QTabWidget::pane {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLORS['muted']};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 20px;
    margin-right: 4px;
}}

QTabBar::tab:hover {{
    color: {COLORS['text']};
    background-color: {COLORS['hover']};
    border-radius: 4px 4px 0 0;
}}

QTabBar::tab:selected {{
    color: {COLORS['accent']};
    border-bottom: 2px solid {COLORS['accent']};
    font-weight: 600;
}}

/* ==================== TOOLTIP ==================== */
QToolTip {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
}}

/* ==================== MESSAGE BOX ==================== */
QMessageBox {{
    background-color: {COLORS['card']};
}}

QMessageBox QLabel {{
    color: {COLORS['text']};
}}

QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ==================== PROGRESS BAR ==================== */
QProgressBar {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    text-align: center;
    color: {COLORS['text']};
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 5px;
}}
"""

def get_stylesheet():
    """Return the complete dark theme stylesheet."""
    return DARK_THEME_STYLESHEET


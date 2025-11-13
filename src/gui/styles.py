"""
Modern dark bluish theme stylesheet for RPS application.
Inspired by modern web applications with Tailwind-style design.
"""

# Color palette exactly matching GMP project
COLORS = {
    'background': '#0a0c10',      # Main background (var(--color-background))
    'card': '#161b22',            # Card/panel background (var(--color-card))
    'border': '#2c313a',          # Borders (var(--color-border))
    'text': '#d1d5db',            # Primary text (var(--color-text))
    'muted': '#7f8b9a',           # Muted/secondary text (var(--color-muted))
    'accent': '#4a7d89',          # Accent color (var(--color-accent))
    'accent_hover': '#3f6b73',    # Accent hover (accent/90)
    'hover': '#1c2128',           # Hover background
    'selected': '#1f2937',        # Selected item background
    'danger': '#dc2626',          # Error/danger color (red-600)
    'danger_hover': '#b91c1c',    # Danger hover (red-700)
    'success': '#10b981',         # Success color
    'warning': '#f59e0b',         # Warning color (amber-500)
    'warning_bg': '#18130a',      # Warning background (dark amber)
    'red_600': '#dc2626',         # GMP red variants
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
    background-color: {COLORS['card']};
    border-bottom: 1px solid {COLORS['border']};
    min-height: 88px;
    max-height: 88px;
}}

#headerLogo {{
    margin-right: 8px;
}}

#navButton {{
    background-color: transparent;
    color: {COLORS['muted']};
    border: none;
    padding: 12px 20px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 16px;
    min-width: 80px;
    max-height: 48px;
}}

#navButton:hover {{
    color: {COLORS['text']};
    background-color: {COLORS['hover']};
}}

#navButton:checked {{
    color: {COLORS['accent']};
    background-color: transparent;
    border-bottom: 2px solid {COLORS['accent']};
}}

#navButton:checked:hover {{
    color: {COLORS['accent']};
    background-color: {COLORS['hover']};
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
    color: #f87171;
    border-radius: 18px;
}}

#cardDeleteAction:hover {{
    background-color: rgba(248, 113, 113, 0.12);
    color: #fca5a5;
}}

#cardDeleteAction:pressed {{
    background-color: rgba(248, 113, 113, 0.2);
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
    background-color: {COLORS['card']};
    color: {COLORS['muted']};
    border-top: 1px solid {COLORS['border']};
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
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
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

QHeaderView::section {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px 4px;
    font-weight: 600;
}}

/* ==================== SCROLL BARS ==================== */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['accent']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['accent']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ==================== SPLITTER ==================== */
QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 1px;
    height: 1px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['accent']};
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


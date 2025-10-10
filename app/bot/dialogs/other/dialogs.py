# This file is deprecated. 
# Dialogs have been moved to separate directories:
# - navigation_dialog -> app.bot.dialogs.navigation
# - faq_dialog -> app.bot.dialogs.faq  
# - registration_dialog -> app.bot.dialogs.registration

# Import from new locations for backward compatibility
from app.bot.dialogs.navigation import navigation_dialog
from app.bot.dialogs.faq import faq_dialog
from app.bot.dialogs.registration import registration_dialog

__all__ = ["navigation_dialog", "faq_dialog", "registration_dialog"]

# Import states from individual dialog modules
from app.bot.dialogs.navigation.states import NavigationSG
from app.bot.dialogs.faq.states import FaqSG
from app.bot.dialogs.registration.states import RegistrationSG

# Re-export for backward compatibility
__all__ = ["NavigationSG", "FaqSG", "RegistrationSG"]

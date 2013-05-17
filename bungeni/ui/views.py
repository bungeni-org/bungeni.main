from bungeni.alchemist import Session
from bungeni.models.domain import UserEditing
from bungeni.models.utils import get_login_user
from datetime import datetime, timedelta
from zope.publisher.browser import BrowserView


# !!!! cleanout out src !!!!


class StoreNowEditView(BrowserView):
    """View that is periodically called
    with ajax requests to store the document
    id that the user is being currently
    editing"""

    def __call__(self):
        session = Session()

        # Current logged in user id
        user = get_login_user()

        # Looking if there is appropriate object to store
        # currently editing document data
        user_editing = session.query(UserEditing)\
                                            .filter(UserEditing.principal_id == user.user_id)\
                                            .first()

        # If not creating one for the current user
        if not user_editing:
            user_editing = UserEditing()
            user_editing.principal_id = user.user_id
            session.add(user_editing)

        # Assigning current document id
        document_id = self.context.doc_id
        user_editing.doc_id = document_id

        # And the current date and time
        current_datetime = datetime.now()
        ago_datetime = current_datetime - timedelta(seconds=20)
        user_editing.date = current_datetime


        # Fetching amount of users that are being editing the document
        # taking into account that last time the ajax request was sent
        # no longer than 20 seconds ago
        count = session.query(UserEditing)\
                       .filter(UserEditing.doc_id == document_id)\
                       .filter(UserEditing.principal_id != user.user_id)\
                       .filter(UserEditing.date.between(ago_datetime, current_datetime))\
                       .count()
        
        # Returning the amount, excluding current document editing
        return str(count)


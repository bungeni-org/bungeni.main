from bungeni.alchemist import Session
from bungeni.models.domain import CurrentlyEditingDocument
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
        currently_editing_document = session.query(CurrentlyEditingDocument)\
                                            .filter(CurrentlyEditingDocument.user_id == user.user_id)\
                                            .first()

        # If not creating one for the current user
        if not currently_editing_document:
            currently_editing_document = CurrentlyEditingDocument()
            currently_editing_document.user_id = user.user_id
            session.add(currently_editing_document)

        # Assigning current document id
        document_id = self.context.doc_id
        currently_editing_document.currently_editing_id = document_id

        # And the current date and time
        current_datetime = datetime.now()
        ago_datetime = current_datetime - timedelta(seconds=20)
        currently_editing_document.editing_date = current_datetime


        # Fetching amount of users that are being editing the document
        # taking into account that last time the ajax request was sent
        # no longer than 20 seconds ago
        count = session.query(CurrentlyEditingDocument)\
                       .filter(CurrentlyEditingDocument.currently_editing_id == document_id)\
                       .filter(CurrentlyEditingDocument.user_id != user.user_id)\
                       .filter(CurrentlyEditingDocument.editing_date.between(ago_datetime, current_datetime))\
                       .count()

        # Returning the amount, excluding current document editing
        return str(count)


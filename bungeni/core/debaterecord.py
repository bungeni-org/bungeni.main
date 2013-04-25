from zope.component.zcml import handler
from interfaces import IDebateRecordConfig
from zope.interface import implements


class DebateRecordConfig(object):
    implements(IDebateRecordConfig)
    transcriber_role = ""
    media_type = ""
    take_duration = None

    def __init__(self, transcriber_role, take_duration, media_type):
        self.transcriber_role = transcriber_role
        self.take_duration = take_duration
        self.media_type = media_type

    def get_transcriber_role(self):
        return self.transcriber_role

    def get_take_duration(self):
        return self.take_duration

    def get_media_type(self):
        return self.media_type

def registerDebateRecordConfig(context, transcriber_role, take_duration,
     media_type):
    context.action(
        discriminator=(
            'RegisterDebateRecordConfig', transcriber_role, take_duration,
            media_type
        ),
        callable=handler,
        args = ('registerUtility', 
            DebateRecordConfig(transcriber_role, take_duration, media_type), 
            IDebateRecordConfig)
    )
